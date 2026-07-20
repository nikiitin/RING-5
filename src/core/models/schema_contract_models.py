"""Immutable dataset schema declarations and validation results."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, TypeAlias

import pandas as pd

SchemaDataType: TypeAlias = Literal["any", "numeric", "integer", "boolean", "datetime", "string"]
ContractValue: TypeAlias = str | int | float | bool

_SCHEMA_DATA_TYPES = frozenset({"any", "numeric", "integer", "boolean", "datetime", "string"})


@dataclass(frozen=True, slots=True)
class ColumnContract:
    """Validation rules for one named dataset column."""

    # [impl->req~ring5.data.schema-contracts~1]

    name: str
    data_type: SchemaDataType = "any"
    required: bool = True
    nullable: bool = False
    minimum: float | None = None
    maximum: float | None = None
    accepted_values: tuple[ContractValue, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Contract column names must be non-empty strings.")
        object.__setattr__(self, "name", self.name.strip())
        if len(self.name) > 100 or any(ord(character) < 32 for character in self.name):
            raise ValueError("Contract column names must be at most 100 printable characters.")
        if self.data_type not in _SCHEMA_DATA_TYPES:
            choices = ", ".join(sorted(_SCHEMA_DATA_TYPES))
            raise ValueError(f"Invalid schema data type {self.data_type!r}. Use {choices}.")
        if not isinstance(self.required, bool) or not isinstance(self.nullable, bool):
            raise TypeError("Contract required and nullable flags must be booleans.")
        if self.minimum is not None or self.maximum is not None:
            if self.data_type not in {"numeric", "integer"}:
                raise ValueError("Numeric ranges require a numeric or integer data type.")
            for label, value in (("minimum", self.minimum), ("maximum", self.maximum)):
                if value is not None and (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                ):
                    raise ValueError(f"Column {label} must be a finite number.")
        if self.minimum is not None and self.maximum is not None:
            if float(self.minimum) > float(self.maximum):
                raise ValueError("Column minimum cannot exceed maximum.")
        if isinstance(self.accepted_values, (str, bytes)):
            raise TypeError("Accepted categorical values must be provided as a tuple.")
        accepted = tuple(self.accepted_values)
        if len(accepted) > 1_000:
            raise ValueError("A column contract cannot accept more than 1,000 categorical values.")
        for accepted_value in accepted:
            if not isinstance(accepted_value, (str, int, float, bool)) or (
                isinstance(accepted_value, float) and not math.isfinite(accepted_value)
            ):
                raise TypeError("Accepted categorical values must be finite scalar values.")
        if len({(type(value).__name__, repr(value)) for value in accepted}) != len(accepted):
            raise ValueError("Accepted categorical values must be unique.")
        object.__setattr__(self, "accepted_values", accepted)


@dataclass(frozen=True, slots=True)
class DatasetSchemaContract:
    """Named collection of column rules for a dataset boundary."""

    # [impl->req~ring5.data.schema-contracts~1]

    name: str
    columns: tuple[ColumnContract, ...]
    allow_extra_columns: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Schema contract names must be non-empty strings.")
        object.__setattr__(self, "name", self.name.strip())
        if len(self.name) > 100 or any(ord(character) < 32 for character in self.name):
            raise ValueError("Schema contract names must be at most 100 printable characters.")
        columns = tuple(self.columns)
        if not columns:
            raise ValueError("A schema contract must define at least one column.")
        if any(not isinstance(column, ColumnContract) for column in columns):
            raise TypeError("Schema contract columns must be ColumnContract values.")
        names = [column.name for column in columns]
        if len(set(names)) != len(names):
            raise ValueError("Schema contract column names must be unique.")
        if not isinstance(self.allow_extra_columns, bool):
            raise TypeError("allow_extra_columns must be a boolean.")
        object.__setattr__(self, "columns", columns)

    def to_frame(self) -> pd.DataFrame:
        """Return editable column rules as a newly allocated DataFrame."""
        return pd.DataFrame(
            {
                "column": [column.name for column in self.columns],
                "required": [column.required for column in self.columns],
                "data_type": [column.data_type for column in self.columns],
                "nullable": [column.nullable for column in self.columns],
                "minimum": [column.minimum for column in self.columns],
                "maximum": [column.maximum for column in self.columns],
                "accepted_values": [
                    ", ".join(str(value) for value in column.accepted_values)
                    for column in self.columns
                ],
            }
        )


@dataclass(frozen=True, slots=True)
class SchemaViolation:
    """One failed contract rule with bounded row-position evidence."""

    rule: str
    column: str | None
    message: str
    affected_rows: int
    sample_row_numbers: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class SchemaValidationReport:
    """Deterministic result of validating a dataset against a contract."""

    contract_name: str
    row_count: int
    column_count: int
    violations: tuple[SchemaViolation, ...]

    @property
    def valid(self) -> bool:
        """Whether every declared schema rule passed."""
        return not self.violations

    @property
    def issue_count(self) -> int:
        """Number of distinct failed rules."""
        return len(self.violations)

    @property
    def affected_value_count(self) -> int:
        """Total affected rows across all failed rules."""
        return sum(violation.affected_rows for violation in self.violations)

    def to_frame(self) -> pd.DataFrame:
        """Return one row per failed rule as a newly allocated DataFrame."""
        return pd.DataFrame(
            (
                {
                    "rule": violation.rule,
                    "column": violation.column,
                    "message": violation.message,
                    "affected_rows": violation.affected_rows,
                    "sample_row_numbers": ", ".join(
                        str(row) for row in violation.sample_row_numbers
                    ),
                }
                for violation in self.violations
            ),
            columns=("rule", "column", "message", "affected_rows", "sample_row_numbers"),
        )
