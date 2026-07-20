"""Stateless dataset schema inference and validation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.core.models.schema_contract_models import (
    ColumnContract,
    DatasetSchemaContract,
    SchemaDataType,
    SchemaValidationReport,
    SchemaViolation,
)

_BOOLEAN_VALUES = frozenset({"true", "false", "1", "0", "yes", "no"})


class SchemaContractService:
    """Infer editable rules and validate data without mutating either input."""

    @classmethod
    def infer(cls, data: pd.DataFrame, *, name: str = "dataset") -> DatasetSchemaContract:
        """Infer conservative type and nullability rules from a dataframe."""
        cls._validate_data(data)
        return DatasetSchemaContract(
            name=name,
            columns=tuple(
                ColumnContract(
                    name=column,
                    data_type=cls._inferred_type(data[column]),
                    nullable=bool(data[column].isna().any()),
                )
                for column in data.columns
            ),
        )

    @classmethod
    def validate(
        cls,
        data: pd.DataFrame,
        contract: DatasetSchemaContract,
    ) -> SchemaValidationReport:
        """Validate required columns, types, nullability, ranges, and categories."""
        # [impl->req~ring5.data.schema-contracts~1]
        cls._validate_data(data)
        if not isinstance(contract, DatasetSchemaContract):
            raise TypeError("contract must be a DatasetSchemaContract.")

        rules = {column.name: column for column in contract.columns}
        violations: list[SchemaViolation] = []
        for rule in contract.columns:
            if rule.name not in data.columns:
                if rule.required:
                    violations.append(
                        SchemaViolation(
                            rule="required",
                            column=rule.name,
                            message=f"Required column {rule.name!r} is missing.",
                            affected_rows=0,
                        )
                    )
                continue
            cls._validate_column(data[rule.name], rule, violations)

        if not contract.allow_extra_columns:
            for column in data.columns:
                if column not in rules:
                    violations.append(
                        SchemaViolation(
                            rule="extra_column",
                            column=column,
                            message=f"Unexpected column {column!r} is not allowed.",
                            affected_rows=0,
                        )
                    )

        return SchemaValidationReport(
            contract_name=contract.name,
            row_count=len(data),
            column_count=len(data.columns),
            violations=tuple(violations),
        )

    @classmethod
    def _validate_column(
        cls,
        series: pd.Series,
        rule: ColumnContract,
        violations: list[SchemaViolation],
    ) -> None:
        missing = series.isna().to_numpy(dtype=bool)
        if not rule.nullable:
            cls._append_mask_violation(
                violations,
                mask=missing,
                rule="nullable",
                column=rule.name,
                message=f"Column {rule.name!r} contains missing values.",
            )

        type_invalid = cls._invalid_type_mask(series, rule.data_type)
        cls._append_mask_violation(
            violations,
            mask=type_invalid,
            rule="data_type",
            column=rule.name,
            message=f"Column {rule.name!r} contains values outside type {rule.data_type!r}.",
        )

        if rule.minimum is not None or rule.maximum is not None:
            converted = pd.to_numeric(series, errors="coerce").to_numpy(
                dtype=float, na_value=np.nan
            )
            comparable = ~np.isnan(converted)
            if rule.minimum is not None:
                cls._append_mask_violation(
                    violations,
                    mask=comparable & (converted < float(rule.minimum)),
                    rule="minimum",
                    column=rule.name,
                    message=f"Column {rule.name!r} contains values below {rule.minimum}.",
                )
            if rule.maximum is not None:
                cls._append_mask_violation(
                    violations,
                    mask=comparable & (converted > float(rule.maximum)),
                    rule="maximum",
                    column=rule.name,
                    message=f"Column {rule.name!r} contains values above {rule.maximum}.",
                )

        if rule.accepted_values:
            accepted = series.isin(rule.accepted_values).to_numpy(dtype=bool)
            cls._append_mask_violation(
                violations,
                mask=~missing & ~accepted,
                rule="accepted_values",
                column=rule.name,
                message=(f"Column {rule.name!r} contains values outside its accepted categories."),
            )

    @staticmethod
    def _append_mask_violation(
        violations: list[SchemaViolation],
        *,
        mask: np.ndarray,
        rule: str,
        column: str,
        message: str,
    ) -> None:
        positions = np.flatnonzero(mask)
        if not len(positions):
            return
        violations.append(
            SchemaViolation(
                rule=rule,
                column=column,
                message=message,
                affected_rows=len(positions),
                sample_row_numbers=tuple(int(position) for position in positions[:10]),
            )
        )

    @staticmethod
    def _invalid_type_mask(series: pd.Series, expected: SchemaDataType) -> np.ndarray:
        missing = series.isna().to_numpy(dtype=bool)
        if expected == "any":
            return np.zeros(len(series), dtype=bool)
        values = series[~series.isna()]
        if expected == "numeric":
            invalid_non_null = pd.to_numeric(values, errors="coerce").isna().to_numpy()
        elif expected == "integer":
            converted = pd.to_numeric(values, errors="coerce")
            invalid_non_null = (converted.isna() | converted.mod(1).ne(0)).to_numpy()
        elif expected == "boolean":
            if pd.api.types.is_bool_dtype(values.dtype):
                invalid_non_null = np.zeros(len(values), dtype=bool)
            else:
                normalized = values.astype(str).str.strip().str.lower()
                invalid_non_null = (~normalized.isin(_BOOLEAN_VALUES)).to_numpy()
        elif expected == "datetime":
            invalid_non_null = (
                pd.to_datetime(
                    values,
                    errors="coerce",
                    format="mixed",
                )
                .isna()
                .to_numpy()
            )
        else:
            invalid_non_null = (~values.map(lambda value: isinstance(value, str))).to_numpy()
        result = np.zeros(len(series), dtype=bool)
        result[np.flatnonzero(~missing)] = invalid_non_null
        return result

    @staticmethod
    def _inferred_type(series: pd.Series) -> SchemaDataType:
        if pd.api.types.is_bool_dtype(series.dtype):
            return "boolean"
        if pd.api.types.is_integer_dtype(series.dtype):
            return "integer"
        if pd.api.types.is_numeric_dtype(series.dtype):
            return "numeric"
        if pd.api.types.is_datetime64_any_dtype(series.dtype):
            return "datetime"
        return "string"

    @staticmethod
    def _validate_data(data: pd.DataFrame) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Schema validation data must be a pandas DataFrame.")
        if any(not isinstance(column, str) or not column for column in data.columns):
            raise ValueError("Schema validation requires non-empty string column names.")
        if data.columns.duplicated().any():
            raise ValueError("Schema validation requires unique column names.")
