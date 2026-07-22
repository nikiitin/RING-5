"""Dataset quality profiling without input mutation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, TypeAlias

import numpy as np
import pandas as pd

from src.core.models.quality_models import ColumnQuality, DataQualityReport

ExpectedDataType: TypeAlias = Literal["numeric", "integer", "boolean", "datetime", "string"]
_EXPECTED_TYPES = frozenset({"numeric", "integer", "boolean", "datetime", "string"})
_BOOLEAN_VALUES = frozenset({"true", "false", "1", "0", "yes", "no"})


class QualityProfileService:
    """Calculate table-level and per-column quality measurements."""

    @classmethod
    def profile(
        cls,
        data: pd.DataFrame,
        *,
        expected_types: Mapping[str, ExpectedDataType] | None = None,
    ) -> DataQualityReport:
        """Profile missing, duplicate, constant, infinite, outlier, and type issues.

        Args:
            data: Dataset to inspect.
            expected_types: Optional column-to-type expectations. Supported values
                are ``numeric``, ``integer``, ``boolean``, ``datetime``, and ``string``.

        Returns:
            Immutable dataset summary and ordered column measurements.

        Raises:
            ValueError: Column names or expected type declarations are invalid.
        """
        # [impl->req~ring5.data.quality-profiler~1]
        cls._validate_columns(data)
        expectations = cls._validate_expectations(expected_types)
        missing_expected = [column for column in expectations if column not in data.columns]
        schema_errors = tuple(f"Missing expected column: {column}" for column in missing_expected)

        profiles: list[ColumnQuality] = []
        for column in data.columns:
            series = data[column]
            missing = int(series.isna().sum())
            infinite = cls._infinite_count(series)
            outliers = cls._outlier_count(series)
            expected = expectations.get(column)
            invalid = cls._invalid_type_count(series, expected) if expected else 0
            profiles.append(
                ColumnQuality(
                    name=column,
                    dtype=str(series.dtype),
                    inferred_type=cls._inferred_type(series),
                    non_null=int(series.notna().sum()),
                    missing=missing,
                    missing_percent=(missing / len(data) * 100.0 if len(data) else 0.0),
                    unique=int(series.nunique(dropna=True)),
                    constant=series.nunique(dropna=True) <= 1,
                    infinite=infinite,
                    iqr_outliers=outliers,
                    expected_type=expected,
                    invalid_type_values=invalid,
                )
            )

        return DataQualityReport(
            row_count=len(data),
            column_count=len(data.columns),
            duplicate_rows=int(data.duplicated().sum()),
            missing_cells=sum(profile.missing for profile in profiles),
            infinite_cells=sum(profile.infinite for profile in profiles),
            iqr_outlier_cells=sum(profile.iqr_outliers for profile in profiles),
            schema_violations=(
                len(schema_errors) + sum(profile.invalid_type_values for profile in profiles)
            ),
            constant_columns=tuple(profile.name for profile in profiles if profile.constant),
            schema_errors=schema_errors,
            columns=tuple(profiles),
        )

    @staticmethod
    def _validate_columns(data: pd.DataFrame) -> None:
        if any(not isinstance(column, str) or not column for column in data.columns):
            raise ValueError("Data quality profiling requires non-empty string column names.")
        if data.columns.duplicated().any():
            raise ValueError("Data quality profiling requires unique column names.")

    @staticmethod
    def _validate_expectations(
        expected_types: Mapping[str, ExpectedDataType] | None,
    ) -> dict[str, ExpectedDataType]:
        if expected_types is None:
            return {}
        result: dict[str, ExpectedDataType] = {}
        for column, expected in expected_types.items():
            if not isinstance(column, str) or not column:
                raise ValueError("Expected-type column names must be non-empty strings.")
            if expected not in _EXPECTED_TYPES:
                choices = ", ".join(sorted(_EXPECTED_TYPES))
                raise ValueError(
                    f"Invalid expected type for {column!r}: {expected!r}. Use {choices}."
                )
            result[column] = expected
        return result

    @staticmethod
    def _inferred_type(series: pd.Series) -> str:
        if pd.api.types.is_bool_dtype(series.dtype):
            return "boolean"
        if pd.api.types.is_integer_dtype(series.dtype):
            return "integer"
        if pd.api.types.is_numeric_dtype(series.dtype):
            return "numeric"
        if pd.api.types.is_datetime64_any_dtype(series.dtype):
            return "datetime"
        if isinstance(series.dtype, pd.CategoricalDtype):
            return "category"
        return "string"

    @staticmethod
    def _infinite_count(series: pd.Series) -> int:
        if not pd.api.types.is_numeric_dtype(series.dtype):
            return 0
        values = series.to_numpy(dtype=float, na_value=np.nan)
        return int(np.isinf(values).sum())

    @staticmethod
    def _outlier_count(series: pd.Series) -> int:
        if not pd.api.types.is_numeric_dtype(series.dtype):
            return 0
        values = series.to_numpy(dtype=float, na_value=np.nan)
        values = values[np.isfinite(values)]
        if len(values) < 4:
            return 0
        q1, q3 = np.quantile(values, [0.25, 0.75])
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        return int(((values < lower) | (values > upper)).sum())

    @staticmethod
    def _invalid_type_count(series: pd.Series, expected: ExpectedDataType) -> int:
        values = series.dropna()
        if expected == "numeric":
            converted = pd.to_numeric(values, errors="coerce")
            return int(converted.isna().sum())
        if expected == "integer":
            converted = pd.to_numeric(values, errors="coerce")
            invalid = converted.isna() | converted.mod(1).ne(0)
            return int(invalid.sum())
        if expected == "boolean":
            if pd.api.types.is_bool_dtype(values.dtype):
                return 0
            normalized = values.astype(str).str.strip().str.lower()
            return int((~normalized.isin(_BOOLEAN_VALUES)).sum())
        if expected == "datetime":
            converted = pd.to_datetime(values, errors="coerce", format="mixed")
            return int(converted.isna().sum())
        return int((~values.map(lambda value: isinstance(value, str))).sum())
