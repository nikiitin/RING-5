"""Aligned baseline and candidate metric comparison."""

from __future__ import annotations

import math
from collections.abc import Collection, Iterable, Mapping, Sequence
from typing import Literal, TypeAlias

import numpy as np
import pandas as pd

MetricDirection: TypeAlias = Literal["higher", "lower"]
ThresholdMode: TypeAlias = Literal["percentage", "absolute"]

_OUTPUT_COLUMNS = (
    "metric",
    "baseline_name",
    "candidate_name",
    "baseline_value",
    "candidate_value",
    "absolute_change",
    "percentage_change",
    "direction",
    "threshold",
    "threshold_mode",
    "outcome",
)


class ComparisonService:
    """Compare numeric metrics after one-to-one key alignment."""

    @classmethod
    def compare(
        cls,
        baseline: pd.DataFrame,
        candidate: pd.DataFrame,
        key_columns: Sequence[str],
        metric_columns: Sequence[str],
        *,
        directions: MetricDirection | Mapping[str, MetricDirection] = "higher",
        thresholds: float | Mapping[str, float] = 0.0,
        threshold_mode: ThresholdMode = "percentage",
        baseline_name: str = "baseline",
        candidate_name: str = "candidate",
    ) -> pd.DataFrame:
        """Return a long-form comparison of aligned metric values.

        Args:
            baseline: Reference measurements with one row per key.
            candidate: Measurements evaluated against the reference.
            key_columns: Columns that uniquely identify corresponding rows.
            metric_columns: Numeric columns to compare.
            directions: Global or per-metric optimization direction.
            thresholds: Global or per-metric non-negative regression tolerance.
            threshold_mode: Interpret thresholds as percentages or absolute values.
            baseline_name: Label stored with every comparison row.
            candidate_name: Label stored with every comparison row.

        Returns:
            One row per aligned key and metric. Unmatched and non-comparable rows
            remain present with an explanatory outcome.

        Raises:
            ValueError: Columns, keys, directions, thresholds, or labels are invalid.
        """
        # [impl->req~ring5.analysis.regression-comparison~1]
        keys = cls._validated_columns(key_columns, "key")
        metrics = cls._validated_columns(metric_columns, "metric")
        cls._validate_inputs(baseline, candidate, keys, metrics)
        mode = cls._validate_mode(threshold_mode)
        direction_by_metric = cls._resolve_directions(metrics, directions)
        threshold_by_metric = cls._resolve_thresholds(metrics, thresholds)
        baseline_label = cls._validate_label(baseline_name, "baseline_name")
        candidate_label = cls._validate_label(candidate_name, "candidate_name")

        baseline_columns = cls._internal_columns(list(baseline.columns), metrics, "baseline")
        occupied: set[object] = set(baseline.columns) | set(baseline_columns.values())
        candidate_columns = cls._internal_columns(occupied, metrics, "candidate")
        occupied.update(candidate_columns.values())
        indicator_column = cls._available_internal_name(occupied, "alignment")

        baseline_values = baseline.loc[:, keys + metrics].rename(columns=baseline_columns)
        candidate_values = candidate.loc[:, keys + metrics].rename(columns=candidate_columns)
        aligned = baseline_values.merge(
            candidate_values,
            how="outer",
            on=keys,
            sort=False,
            validate="one_to_one",
            indicator=indicator_column,
        )

        comparisons = [
            cls._compare_metric(
                aligned,
                keys,
                metric,
                baseline_columns[metric],
                candidate_columns[metric],
                indicator_column,
                direction_by_metric[metric],
                threshold_by_metric[metric],
                mode,
                baseline_label,
                candidate_label,
            )
            for metric in metrics
        ]
        if not comparisons:
            return pd.DataFrame(columns=keys + list(_OUTPUT_COLUMNS))
        return pd.concat(comparisons, ignore_index=True)

    @staticmethod
    def _validated_columns(columns: Sequence[str], kind: str) -> list[str]:
        resolved = list(columns)
        if not resolved:
            raise ValueError(f"At least one {kind} column is required.")
        if any(not isinstance(column, str) or not column for column in resolved):
            raise ValueError(f"Every {kind} column must be a non-empty string.")
        if len(set(resolved)) != len(resolved):
            raise ValueError(f"Duplicate {kind} columns are not allowed.")
        return resolved

    @classmethod
    def _validate_inputs(
        cls,
        baseline: pd.DataFrame,
        candidate: pd.DataFrame,
        keys: list[str],
        metrics: list[str],
    ) -> None:
        overlap = set(keys) & set(metrics)
        if overlap:
            raise ValueError(f"Key and metric columns overlap: {', '.join(sorted(overlap))}.")
        reserved = set(keys) & set(_OUTPUT_COLUMNS)
        if reserved:
            raise ValueError(
                "Key columns use reserved comparison names: " f"{', '.join(sorted(reserved))}."
            )
        for label, frame in (("Baseline", baseline), ("Candidate", candidate)):
            missing = [column for column in keys + metrics if column not in frame.columns]
            if missing:
                raise ValueError(f"{label} is missing columns: {', '.join(missing)}.")
            non_numeric = [
                metric
                for metric in metrics
                if not pd.api.types.is_numeric_dtype(frame[metric].dtype)
            ]
            if non_numeric:
                raise ValueError(f"{label} metrics must be numeric: {', '.join(non_numeric)}.")
            if frame[keys].isna().any(axis=None):
                raise ValueError(f"{label} key columns cannot contain missing values.")
            duplicated = frame.duplicated(keys, keep=False)
            if duplicated.any():
                sample = frame.loc[duplicated, keys].head(3).to_dict("records")
                raise ValueError(f"{label} key columns are not unique; examples: {sample}.")

    @staticmethod
    def _validate_mode(mode: str) -> ThresholdMode:
        if mode == "percentage":
            return "percentage"
        if mode == "absolute":
            return "absolute"
        raise ValueError("threshold_mode must be 'percentage' or 'absolute'.")

    @staticmethod
    def _validate_label(value: str, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string.")
        return value.strip()

    @staticmethod
    def _resolve_directions(
        metrics: list[str],
        directions: MetricDirection | Mapping[str, MetricDirection],
    ) -> dict[str, MetricDirection]:
        if isinstance(directions, str):
            resolved = {metric: directions for metric in metrics}
        else:
            unknown = set(directions) - set(metrics)
            if unknown:
                raise ValueError(
                    f"Directions reference unknown metrics: {', '.join(sorted(unknown))}."
                )
            resolved = {metric: directions.get(metric, "higher") for metric in metrics}
        invalid = {
            metric: value for metric, value in resolved.items() if value not in ("higher", "lower")
        }
        if invalid:
            details = ", ".join(f"{metric}={value!r}" for metric, value in invalid.items())
            raise ValueError(f"Invalid metric directions: {details}.")
        return resolved

    @staticmethod
    def _resolve_thresholds(
        metrics: list[str], thresholds: float | Mapping[str, float]
    ) -> dict[str, float]:
        if isinstance(thresholds, Mapping):
            unknown = set(thresholds) - set(metrics)
            if unknown:
                raise ValueError(
                    f"Thresholds reference unknown metrics: {', '.join(sorted(unknown))}."
                )
            raw = {metric: thresholds.get(metric, 0.0) for metric in metrics}
        else:
            raw = {metric: thresholds for metric in metrics}
        resolved: dict[str, float] = {}
        for metric, value in raw.items():
            if isinstance(value, bool):
                raise ValueError(f"Threshold for {metric!r} must be a finite non-negative number.")
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Threshold for {metric!r} must be a finite non-negative number."
                ) from exc
            if not math.isfinite(number) or number < 0:
                raise ValueError(f"Threshold for {metric!r} must be a finite non-negative number.")
            resolved[metric] = number
        return resolved

    @classmethod
    def _internal_columns(
        cls, occupied: Iterable[object], metrics: list[str], stem: str
    ) -> dict[str, str]:
        names = set(occupied)
        result: dict[str, str] = {}
        for index, metric in enumerate(metrics):
            name = cls._available_internal_name(names, f"{stem}_{index}")
            names.add(name)
            result[metric] = name
        return result

    @staticmethod
    def _available_internal_name(occupied: Collection[object], stem: str) -> str:
        prefix = f"__ring5_{stem}"
        candidate = prefix
        suffix = 1
        while candidate in occupied:
            candidate = f"{prefix}_{suffix}"
            suffix += 1
        return candidate

    @staticmethod
    def _compare_metric(
        aligned: pd.DataFrame,
        keys: list[str],
        metric: str,
        baseline_column: str,
        candidate_column: str,
        indicator_column: str,
        direction: MetricDirection,
        threshold: float,
        threshold_mode: ThresholdMode,
        baseline_name: str,
        candidate_name: str,
    ) -> pd.DataFrame:
        result = aligned.loc[:, keys].copy()
        baseline_values = aligned[baseline_column].astype(float)
        candidate_values = aligned[candidate_column].astype(float)
        absolute_change = candidate_values - baseline_values
        percentage_change = absolute_change.div(baseline_values.abs()).mul(100.0)
        both_zero = baseline_values.eq(0.0) & candidate_values.eq(0.0)
        percentage_change = percentage_change.mask(both_zero, 0.0)
        percentage_change = percentage_change.replace([np.inf, -np.inf], np.nan)

        alignment = aligned[indicator_column]
        missing_baseline = alignment.eq("right_only")
        missing_candidate = alignment.eq("left_only")
        finite_values = np.isfinite(baseline_values) & np.isfinite(candidate_values)
        missing_value = alignment.eq("both") & ~finite_values
        signal = percentage_change if threshold_mode == "percentage" else absolute_change
        if direction == "lower":
            signal = -signal

        outcome = pd.Series("not_comparable", index=aligned.index, dtype="string")
        comparable = alignment.eq("both") & finite_values & signal.notna()
        at_boundary = pd.Series(
            np.isclose(signal.abs(), threshold, rtol=1e-12, atol=1e-12),
            index=aligned.index,
        )
        within_threshold = signal.abs().le(threshold) | at_boundary
        outcome.loc[comparable & signal.gt(threshold) & ~within_threshold] = "improvement"
        outcome.loc[comparable & signal.lt(-threshold) & ~within_threshold] = "regression"
        outcome.loc[comparable & within_threshold] = "unchanged"
        outcome.loc[missing_value] = "missing_value"
        outcome.loc[missing_baseline] = "missing_baseline"
        outcome.loc[missing_candidate] = "missing_candidate"

        result["metric"] = metric
        result["baseline_name"] = baseline_name
        result["candidate_name"] = candidate_name
        result["baseline_value"] = baseline_values
        result["candidate_value"] = candidate_values
        result["absolute_change"] = absolute_change
        result["percentage_change"] = percentage_change
        result["direction"] = direction
        result["threshold"] = threshold
        result["threshold_mode"] = threshold_mode
        result["outcome"] = outcome
        return result
