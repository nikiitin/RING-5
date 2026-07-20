"""Immutable data-quality report models."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class ColumnQuality:
    """Quality measurements for one dataset column."""

    # [impl->req~ring5.data.quality-profiler~1]

    name: str
    dtype: str
    inferred_type: str
    non_null: int
    missing: int
    missing_percent: float
    unique: int
    constant: bool
    infinite: int
    iqr_outliers: int
    expected_type: str | None
    invalid_type_values: int


@dataclass(frozen=True, slots=True)
class DataQualityReport:
    """Dataset-level and per-column quality measurements."""

    # [impl->req~ring5.data.quality-profiler~1]

    row_count: int
    column_count: int
    duplicate_rows: int
    missing_cells: int
    infinite_cells: int
    iqr_outlier_cells: int
    schema_violations: int
    constant_columns: tuple[str, ...]
    schema_errors: tuple[str, ...]
    columns: tuple[ColumnQuality, ...]

    @property
    def has_issues(self) -> bool:
        """Whether any duplicate, missing, infinite, outlier, or schema issue exists."""
        return any(
            (
                self.duplicate_rows,
                self.missing_cells,
                self.infinite_cells,
                self.iqr_outlier_cells,
                self.schema_violations,
                len(self.constant_columns),
                len(self.schema_errors),
            )
        )

    def to_frame(self) -> pd.DataFrame:
        """Return per-column measurements as a new DataFrame.

        Returns:
            One row per input column in source order.
        """
        return pd.DataFrame(asdict(column) for column in self.columns)
