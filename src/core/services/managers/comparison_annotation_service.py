"""Plot-ready annotations for baseline comparison results."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal, TypeAlias

import pandas as pd

ChangeMode: TypeAlias = Literal["threshold", "percentage", "absolute"]

_COMPARISON_COLUMNS = frozenset(
    {
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
    }
)
_SUPPORTED_OUTCOMES = frozenset(
    {
        "improvement",
        "regression",
        "unchanged",
        "not_comparable",
        "missing_baseline",
        "missing_candidate",
        "missing_value",
    }
)
_OUTCOME_STYLE = {
    "improvement": ("▲", "triangle-up", "#0072B2"),
    "regression": ("▼", "triangle-down", "#D55E00"),
    "unchanged": ("●", "circle", "#6B7280"),
    "not_comparable": ("?", "x", "#8A8A8A"),
    "missing_baseline": ("?", "x", "#8A8A8A"),
    "missing_candidate": ("?", "x", "#8A8A8A"),
    "missing_value": ("?", "x", "#8A8A8A"),
}


class ComparisonAnnotationService:
    """Enrich comparison rows with accessible labels and marker styles."""

    @classmethod
    def annotate(
        cls,
        comparison: pd.DataFrame,
        *,
        label_columns: Sequence[str] | None = None,
        change_mode: ChangeMode = "threshold",
    ) -> pd.DataFrame:
        """Return comparison rows with plot labels, changes, and outcome styles.

        Args:
            comparison: Long-form output from ``ComparisonService.compare``.
            label_columns: Columns combined with the metric to label each point.
                By default, every non-comparison column is used.
            change_mode: Plot percentage change, absolute change, or the change
                matching each row's configured threshold mode.

        Returns:
            A new DataFrame with six ``annotation_*`` columns.

        Raises:
            ValueError: The comparison schema, outcomes, labels, or mode are invalid.
        """
        # [impl->req~ring5.analysis.regression-annotations~1]
        cls._validate_schema(comparison)
        labels = cls._resolve_label_columns(comparison, label_columns)
        mode = cls._validate_mode(change_mode)

        result = comparison.copy(deep=True)
        changes = cls._resolve_changes(result, mode)
        outcomes = result["outcome"].astype(str)
        styles = outcomes.map(_OUTCOME_STYLE)

        result["annotation_label"] = cls._labels(result, labels)
        result["annotation_change"] = changes
        result["annotation_symbol"] = styles.map(lambda style: style[0])
        result["annotation_marker"] = styles.map(lambda style: style[1])
        result["annotation_color"] = styles.map(lambda style: style[2])
        result["annotation_text"] = [
            cls._annotation_text(outcome, symbol, change, cls._unit(row_mode, mode))
            for outcome, symbol, change, row_mode in zip(
                outcomes,
                result["annotation_symbol"],
                changes,
                result["threshold_mode"],
                strict=True,
            )
        ]
        return result

    @staticmethod
    def _validate_schema(comparison: pd.DataFrame) -> None:
        if any(not isinstance(column, str) or not column for column in comparison.columns):
            raise ValueError("Comparison result requires non-empty string column names.")
        if comparison.columns.duplicated().any():
            raise ValueError("Comparison result requires unique column names.")
        column_names = {column for column in comparison.columns if isinstance(column, str)}
        missing = sorted(_COMPARISON_COLUMNS - column_names)
        if missing:
            raise ValueError(f"Comparison result is missing columns: {', '.join(missing)}.")
        collisions = sorted(
            column
            for column in comparison
            if isinstance(column, str) and column.startswith("annotation_")
        )
        if collisions:
            raise ValueError(
                "Comparison result already contains annotation columns: "
                f"{', '.join(collisions)}."
            )
        outcomes = set(comparison["outcome"].dropna().astype(str))
        invalid = sorted(outcomes - _SUPPORTED_OUTCOMES)
        if comparison["outcome"].isna().any() or invalid:
            details = ", ".join(invalid) if invalid else "missing outcome"
            raise ValueError(f"Comparison result contains invalid outcomes: {details}.")
        modes = set(comparison["threshold_mode"].dropna().astype(str))
        if comparison["threshold_mode"].isna().any() or not modes <= {"percentage", "absolute"}:
            raise ValueError("Comparison result contains invalid threshold modes.")

    @staticmethod
    def _resolve_label_columns(
        comparison: pd.DataFrame, label_columns: Sequence[str] | None
    ) -> list[str]:
        if label_columns is None:
            return [
                column
                for column in comparison.columns
                if isinstance(column, str) and column not in _COMPARISON_COLUMNS
            ]
        labels = list(label_columns)
        if any(not isinstance(column, str) or not column for column in labels):
            raise ValueError("Every label column must be a non-empty string.")
        if len(labels) != len(set(labels)):
            raise ValueError("Duplicate label columns are not allowed.")
        missing = [column for column in labels if column not in comparison.columns]
        if missing:
            raise ValueError(f"Comparison result is missing label columns: {', '.join(missing)}.")
        return labels

    @staticmethod
    def _validate_mode(mode: str) -> ChangeMode:
        if mode == "threshold":
            return "threshold"
        if mode == "percentage":
            return "percentage"
        if mode == "absolute":
            return "absolute"
        raise ValueError("change_mode must be 'threshold', 'percentage', or 'absolute'.")

    @staticmethod
    def _resolve_changes(comparison: pd.DataFrame, mode: ChangeMode) -> pd.Series:
        if mode == "percentage":
            return pd.to_numeric(comparison["percentage_change"], errors="coerce")
        if mode == "absolute":
            return pd.to_numeric(comparison["absolute_change"], errors="coerce")
        return pd.Series(
            [
                percentage if threshold_mode == "percentage" else absolute
                for percentage, absolute, threshold_mode in zip(
                    comparison["percentage_change"],
                    comparison["absolute_change"],
                    comparison["threshold_mode"],
                    strict=True,
                )
            ],
            index=comparison.index,
            dtype="float64",
        )

    @staticmethod
    def _labels(comparison: pd.DataFrame, label_columns: list[str]) -> pd.Series:
        def label(row: pd.Series) -> str:
            values = ["∅" if pd.isna(row[column]) else str(row[column]) for column in label_columns]
            values.append(str(row["metric"]))
            return " · ".join(values)

        return comparison.apply(label, axis=1)

    @staticmethod
    def _unit(row_mode: object, requested_mode: ChangeMode) -> str:
        is_percentage = requested_mode == "percentage" or (
            requested_mode == "threshold" and row_mode == "percentage"
        )
        return "%" if is_percentage else ""

    @staticmethod
    def _annotation_text(outcome: str, symbol: str, change: object, unit: str) -> str:
        title = outcome.replace("_", " ").title()
        try:
            number = float(str(change))
        except (TypeError, ValueError):
            number = math.nan
        if not math.isfinite(number):
            return f"{symbol} {title}"
        return f"{symbol} {title}: {number:+.2f}{unit}"
