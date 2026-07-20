"""Immutable result contract for inspecting rows behind a plotted value."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True, eq=False)
class DrillDownResult:
    # [impl->req~ring5.plots.drill-down~1]
    """A defensive snapshot of rows matched by one plot-point interaction."""

    plot_id: int
    filters: tuple[tuple[str, Any], ...]
    _rows: pd.DataFrame = field(repr=False)

    def __post_init__(self) -> None:
        """Detach the stored snapshot from the caller-owned DataFrame."""
        object.__setattr__(self, "_rows", self._rows.copy(deep=True))

    @property
    def rows(self) -> pd.DataFrame:
        """Return a defensive copy of the matching source rows."""
        return self._rows.copy(deep=True)

    @property
    def row_count(self) -> int:
        """Return the number of matching source rows."""
        return len(self._rows)

    @property
    def columns(self) -> tuple[str, ...]:
        """Return the visible source column labels."""
        return tuple(str(column) for column in self._rows.columns)


__all__ = ["DrillDownResult"]
