"""Statistical comparison of repeated baseline and candidate measurements."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

_MIN_BOOTSTRAP_SAMPLES = 100
_MAX_BOOTSTRAP_SAMPLES = 50_000
_BOOTSTRAP_CELL_BUDGET = 1_000_000


@dataclass(frozen=True, slots=True)
class _SampleStatistics:
    mean: float
    variance: float
    size: int


class StatisticalComparisonService:
    """Calculate repeated-sample evidence for baseline and candidate groups."""

    @classmethod
    def compare(
        cls,
        baseline: pd.DataFrame,
        candidate: pd.DataFrame,
        group_columns: Sequence[str],
        metric_columns: Sequence[str],
        *,
        confidence_level: float = 0.95,
        alpha: float = 0.05,
        bootstrap_samples: int = 2_000,
        random_seed: int = 0,
        minimum_sample_size: int = 5,
    ) -> pd.DataFrame:
        """Compare repeated measurements with Welch and bootstrap estimates.

        Args:
            baseline: Reference observations.
            candidate: Candidate observations.
            group_columns: Columns defining independent comparison groups. An
                empty sequence compares all rows as one group.
            metric_columns: Numeric measurements to compare.
            confidence_level: Two-sided confidence level between zero and one.
            alpha: P-value threshold used for the ``significant`` result.
            bootstrap_samples: Resample count from 100 through 50,000.
            random_seed: Seed for deterministic resampling.
            minimum_sample_size: Per-side count below which a warning is emitted.

        Returns:
            One row per group and metric with means, confidence intervals,
            Hedges' g, a Welch p-value, bootstrap estimates, and warnings.

        Raises:
            ValueError: Columns, numeric options, or input values are invalid.
        """
        # [impl->req~ring5.analysis.statistical-comparison~1]
        groups = cls._validated_groups(group_columns)
        metrics = cls._validated_metrics(metric_columns)
        cls._validate_frames(baseline, candidate, groups, metrics)
        confidence = cls._probability(confidence_level, "confidence_level")
        significance_alpha = cls._probability(alpha, "alpha")
        resamples = cls._bootstrap_count(bootstrap_samples)
        seed = cls._integer(random_seed, "random_seed", minimum=0)
        minimum = cls._integer(minimum_sample_size, "minimum_sample_size", minimum=2)

        baseline_groups = cls._group_indices(baseline, groups)
        candidate_groups = cls._group_indices(candidate, groups)
        ordered_groups = list(baseline_groups)
        ordered_groups.extend(key for key in candidate_groups if key not in baseline_groups)

        rows: list[dict[str, object]] = []
        for group_index, group_key in enumerate(ordered_groups):
            baseline_indices = baseline_groups.get(group_key, np.array([], dtype=int))
            candidate_indices = candidate_groups.get(group_key, np.array([], dtype=int))
            for metric_index, metric in enumerate(metrics):
                row = cls._compare_metric(
                    baseline,
                    candidate,
                    baseline_indices,
                    candidate_indices,
                    metric,
                    confidence,
                    significance_alpha,
                    resamples,
                    seed,
                    minimum,
                    group_index,
                    metric_index,
                )
                row.update(dict(zip(groups, group_key, strict=True)))
                rows.append(row)

        columns = groups + cls._result_columns()
        return pd.DataFrame(rows, columns=columns)

    @staticmethod
    def _validated_groups(columns: Sequence[str]) -> list[str]:
        groups = list(columns)
        if any(not isinstance(column, str) or not column for column in groups):
            raise ValueError("Every group column must be a non-empty string.")
        if len(set(groups)) != len(groups):
            raise ValueError("Duplicate group columns are not allowed.")
        reserved = set(groups) & set(StatisticalComparisonService._result_columns())
        if reserved:
            raise ValueError(
                "Group columns use reserved statistical names: " f"{', '.join(sorted(reserved))}."
            )
        return groups

    @staticmethod
    def _validated_metrics(columns: Sequence[str]) -> list[str]:
        metrics = list(columns)
        if not metrics:
            raise ValueError("At least one metric column is required.")
        if any(not isinstance(column, str) or not column for column in metrics):
            raise ValueError("Every metric column must be a non-empty string.")
        if len(set(metrics)) != len(metrics):
            raise ValueError("Duplicate metric columns are not allowed.")
        return metrics

    @staticmethod
    def _validate_frames(
        baseline: pd.DataFrame,
        candidate: pd.DataFrame,
        groups: list[str],
        metrics: list[str],
    ) -> None:
        overlap = set(groups) & set(metrics)
        if overlap:
            raise ValueError(f"Group and metric columns overlap: {', '.join(sorted(overlap))}.")
        for label, frame in (("Baseline", baseline), ("Candidate", candidate)):
            missing = [column for column in groups + metrics if column not in frame.columns]
            if missing:
                raise ValueError(f"{label} is missing columns: {', '.join(missing)}.")
            non_numeric = [
                metric
                for metric in metrics
                if not pd.api.types.is_numeric_dtype(frame[metric].dtype)
            ]
            if non_numeric:
                raise ValueError(f"{label} metrics must be numeric: {', '.join(non_numeric)}.")
            if groups and frame[groups].isna().any(axis=None):
                raise ValueError(f"{label} group columns cannot contain missing values.")

    @staticmethod
    def _probability(value: float, field: str) -> float:
        if isinstance(value, bool):
            raise ValueError(f"{field} must be a finite number between zero and one.")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be a finite number between zero and one.") from exc
        if not math.isfinite(number) or not 0.0 < number < 1.0:
            raise ValueError(f"{field} must be a finite number between zero and one.")
        return number

    @staticmethod
    def _integer(value: int, field: str, *, minimum: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"{field} must be an integer greater than or equal to {minimum}.")
        return value

    @classmethod
    def _bootstrap_count(cls, value: int) -> int:
        count = cls._integer(value, "bootstrap_samples", minimum=_MIN_BOOTSTRAP_SAMPLES)
        if count > _MAX_BOOTSTRAP_SAMPLES:
            raise ValueError(f"bootstrap_samples cannot exceed {_MAX_BOOTSTRAP_SAMPLES:,}.")
        return count

    @staticmethod
    def _group_indices(
        frame: pd.DataFrame, groups: list[str]
    ) -> dict[tuple[object, ...], np.ndarray]:
        if not groups:
            return {(): np.arange(len(frame), dtype=int)}
        grouper: str | list[str] = groups[0] if len(groups) == 1 else groups
        result: dict[tuple[object, ...], np.ndarray] = {}
        for raw_key, indices in frame.groupby(grouper, sort=False, observed=True).indices.items():
            key = raw_key if isinstance(raw_key, tuple) else (raw_key,)
            result[key] = np.asarray(indices, dtype=int)
        return result

    @classmethod
    def _compare_metric(
        cls,
        baseline: pd.DataFrame,
        candidate: pd.DataFrame,
        baseline_indices: np.ndarray,
        candidate_indices: np.ndarray,
        metric: str,
        confidence_level: float,
        alpha: float,
        bootstrap_samples: int,
        random_seed: int,
        minimum_sample_size: int,
        group_index: int,
        metric_index: int,
    ) -> dict[str, object]:
        raw_baseline = baseline.iloc[baseline_indices][metric].to_numpy(dtype=float, copy=True)
        raw_candidate = candidate.iloc[candidate_indices][metric].to_numpy(dtype=float, copy=True)
        baseline_values = raw_baseline[np.isfinite(raw_baseline)]
        candidate_values = raw_candidate[np.isfinite(raw_candidate)]
        baseline_stats = cls._sample_statistics(baseline_values)
        candidate_stats = cls._sample_statistics(candidate_values)
        difference = candidate_stats.mean - baseline_stats.mean

        warnings = cls._warnings(
            raw_baseline,
            raw_candidate,
            baseline_stats,
            candidate_stats,
            minimum_sample_size,
        )
        ci_low, ci_high, p_value = cls._welch_results(
            baseline_stats,
            candidate_stats,
            difference,
            confidence_level,
        )
        effect_size = cls._hedges_g(baseline_stats, candidate_stats, difference)
        if baseline_stats.size >= 2 and candidate_stats.size >= 2 and math.isnan(effect_size):
            warnings.append("zero_variance")
        bootstrap_estimate, bootstrap_low, bootstrap_high = cls._bootstrap_difference(
            baseline_values,
            candidate_values,
            bootstrap_samples,
            confidence_level,
            random_seed,
            group_index,
            metric_index,
        )
        significant: bool | None = None if math.isnan(p_value) else p_value < alpha
        return {
            "metric": metric,
            "baseline_n": baseline_stats.size,
            "candidate_n": candidate_stats.size,
            "baseline_mean": baseline_stats.mean,
            "candidate_mean": candidate_stats.mean,
            "mean_difference": difference,
            "confidence_level": confidence_level,
            "difference_ci_low": ci_low,
            "difference_ci_high": ci_high,
            "effect_size_hedges_g": effect_size,
            "test": "welch_t",
            "p_value": p_value,
            "alpha": alpha,
            "significant": significant,
            "bootstrap_samples": bootstrap_samples,
            "bootstrap_difference": bootstrap_estimate,
            "bootstrap_ci_low": bootstrap_low,
            "bootstrap_ci_high": bootstrap_high,
            "warning": ";".join(dict.fromkeys(warnings)),
        }

    @staticmethod
    def _sample_statistics(values: np.ndarray) -> _SampleStatistics:
        size = len(values)
        if size == 0:
            return _SampleStatistics(math.nan, math.nan, 0)
        variance = float(np.var(values, ddof=1)) if size >= 2 else math.nan
        return _SampleStatistics(float(np.mean(values)), variance, size)

    @staticmethod
    def _warnings(
        raw_baseline: np.ndarray,
        raw_candidate: np.ndarray,
        baseline: _SampleStatistics,
        candidate: _SampleStatistics,
        minimum_sample_size: int,
    ) -> list[str]:
        warnings: list[str] = []
        if len(raw_baseline) != baseline.size:
            warnings.append("baseline_nonfinite_values_dropped")
        if len(raw_candidate) != candidate.size:
            warnings.append("candidate_nonfinite_values_dropped")
        if baseline.size == 0:
            warnings.append("missing_baseline_group")
        elif baseline.size < 2:
            warnings.append("insufficient_baseline_samples")
        elif baseline.size < minimum_sample_size:
            warnings.append("small_baseline_sample")
        if candidate.size == 0:
            warnings.append("missing_candidate_group")
        elif candidate.size < 2:
            warnings.append("insufficient_candidate_samples")
        elif candidate.size < minimum_sample_size:
            warnings.append("small_candidate_sample")
        return warnings

    @staticmethod
    def _welch_results(
        baseline: _SampleStatistics,
        candidate: _SampleStatistics,
        difference: float,
        confidence_level: float,
    ) -> tuple[float, float, float]:
        if baseline.size < 2 or candidate.size < 2:
            return math.nan, math.nan, math.nan
        baseline_term = baseline.variance / baseline.size
        candidate_term = candidate.variance / candidate.size
        standard_error_squared = baseline_term + candidate_term
        if standard_error_squared == 0.0:
            p_value = 1.0 if difference == 0.0 else 0.0
            return difference, difference, p_value
        standard_error = math.sqrt(standard_error_squared)
        denominator = baseline_term**2 / (baseline.size - 1)
        denominator += candidate_term**2 / (candidate.size - 1)
        degrees_of_freedom = standard_error_squared**2 / denominator
        quantile = float(stats.t.ppf((1.0 + confidence_level) / 2.0, degrees_of_freedom))
        margin = quantile * standard_error
        statistic = difference / standard_error
        p_value = float(2.0 * stats.t.sf(abs(statistic), degrees_of_freedom))
        return difference - margin, difference + margin, p_value

    @staticmethod
    def _hedges_g(
        baseline: _SampleStatistics,
        candidate: _SampleStatistics,
        difference: float,
    ) -> float:
        if baseline.size < 2 or candidate.size < 2:
            return math.nan
        degrees_of_freedom = baseline.size + candidate.size - 2
        pooled_variance = (
            (baseline.size - 1) * baseline.variance + (candidate.size - 1) * candidate.variance
        ) / degrees_of_freedom
        if pooled_variance <= 0.0:
            return math.nan
        correction = 1.0 - 3.0 / (4.0 * (baseline.size + candidate.size) - 9.0)
        return difference / math.sqrt(pooled_variance) * correction

    @staticmethod
    def _bootstrap_difference(
        baseline: np.ndarray,
        candidate: np.ndarray,
        samples: int,
        confidence_level: float,
        random_seed: int,
        group_index: int,
        metric_index: int,
    ) -> tuple[float, float, float]:
        if len(baseline) == 0 or len(candidate) == 0:
            return math.nan, math.nan, math.nan
        generator = np.random.default_rng(
            np.random.SeedSequence([random_seed, group_index, metric_index])
        )
        chunk_size = max(
            1,
            min(samples, _BOOTSTRAP_CELL_BUDGET // (len(baseline) + len(candidate))),
        )
        differences = np.empty(samples, dtype=float)
        offset = 0
        while offset < samples:
            current = min(chunk_size, samples - offset)
            baseline_draws = generator.integers(0, len(baseline), size=(current, len(baseline)))
            candidate_draws = generator.integers(0, len(candidate), size=(current, len(candidate)))
            differences[offset : offset + current] = candidate[candidate_draws].mean(axis=1)
            differences[offset : offset + current] -= baseline[baseline_draws].mean(axis=1)
            offset += current
        tail = (1.0 - confidence_level) / 2.0
        low, high = np.quantile(differences, [tail, 1.0 - tail])
        return float(np.mean(differences)), float(low), float(high)

    @staticmethod
    def _result_columns() -> list[str]:
        return [
            "metric",
            "baseline_n",
            "candidate_n",
            "baseline_mean",
            "candidate_mean",
            "mean_difference",
            "confidence_level",
            "difference_ci_low",
            "difference_ci_high",
            "effect_size_hedges_g",
            "test",
            "p_value",
            "alpha",
            "significant",
            "bootstrap_samples",
            "bootstrap_difference",
            "bootstrap_ci_low",
            "bootstrap_ci_high",
            "warning",
        ]
