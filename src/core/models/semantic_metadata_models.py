"""Immutable, human-readable semantic metadata for dataset columns."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class ColumnSemantics:
    """Meaning and optional physical unit attached to one column."""

    # [impl->req~ring5.data.semantic-units~1]

    name: str
    label: str = ""
    unit: str = ""

    def __post_init__(self) -> None:
        for field_name, value in (("name", self.name), ("label", self.label), ("unit", self.unit)):
            if not isinstance(value, str):
                raise TypeError(f"Column semantic {field_name} must be a string.")
            resolved = value.strip()
            if field_name == "name" and not resolved:
                raise ValueError("Column semantic names must be non-empty strings.")
            if len(resolved) > 100 or any(ord(character) < 32 for character in resolved):
                raise ValueError(
                    f"Column semantic {field_name} must be at most 100 printable characters."
                )
            object.__setattr__(self, field_name, resolved)

    @property
    def display_label(self) -> str:
        """Return the figure/export label a person should see."""
        base = self.label or self.name
        return f"{base} ({self.unit})" if self.unit else base


@dataclass(frozen=True, slots=True)
class DatasetSemantics:
    """Ordered semantic metadata retained with a dataset."""

    # [impl->req~ring5.data.semantic-units~1]

    columns: tuple[ColumnSemantics, ...] = ()

    def __post_init__(self) -> None:
        columns = tuple(self.columns)
        if any(not isinstance(column, ColumnSemantics) for column in columns):
            raise TypeError("Dataset semantics must contain ColumnSemantics values.")
        names = [column.name for column in columns]
        if len(set(names)) != len(names):
            raise ValueError("Dataset semantic column names must be unique.")
        object.__setattr__(self, "columns", columns)

    def for_column(self, name: str) -> ColumnSemantics | None:
        """Return metadata for *name*, if it has been declared."""
        return next((column for column in self.columns if column.name == name), None)

    def to_frame(self) -> pd.DataFrame:
        """Return ordered metadata as a newly allocated table."""
        return pd.DataFrame(
            (
                {
                    "column": column.name,
                    "semantic_label": column.label,
                    "unit": column.unit,
                    "display_label": column.display_label,
                }
                for column in self.columns
            ),
            columns=("column", "semantic_label", "unit", "display_label"),
        )
