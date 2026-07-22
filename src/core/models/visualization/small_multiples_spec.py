"""Engine-independent configuration for faceting one plot into a grid."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FacetPanel:
    """One resolved facet combination and its human-readable panel title."""

    values: tuple[Any, ...]
    title: str

    def __post_init__(self) -> None:
        """Reject panel data that cannot identify a facet unambiguously."""
        if not self.values:
            raise ValueError("A facet panel needs at least one value.")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("Every facet panel needs a non-empty title.")


@dataclass(frozen=True)
class SmallMultiplesSpec:
    # [impl->req~ring5.plots.small-multiples~1]
    """Immutable resolved layout for repeated views of one registered plot."""

    plot_id: int
    facet_columns: tuple[str, ...]
    panels: tuple[FacetPanel, ...]
    rows: int
    columns: int
    title: str = ""
    width: int = 1200
    height: int = 640
    shared_xaxes: bool = True
    shared_yaxes: bool = True
    shared_legend: bool = True
    x_title: str = ""
    y_title: str = ""

    def __post_init__(self) -> None:
        """Reject incomplete, duplicate, or impossible facet layouts."""
        if isinstance(self.plot_id, bool) or not isinstance(self.plot_id, int):
            raise ValueError("Small-multiples plot_id must be an integer.")
        if not self.facet_columns or any(
            not isinstance(column, str) or not column.strip() for column in self.facet_columns
        ):
            raise ValueError("Small multiples needs at least one named facet column.")
        if len(set(self.facet_columns)) != len(self.facet_columns):
            raise ValueError("Small-multiples facet columns must be unique.")
        if len(self.panels) < 2:
            raise ValueError("Small multiples needs at least two facet panels.")
        if any(len(panel.values) != len(self.facet_columns) for panel in self.panels):
            raise ValueError("Every facet panel needs one value per facet column.")
        try:
            unique_panels = {panel.values for panel in self.panels}
        except TypeError as exc:
            raise ValueError("Facet panel values must be scalar and hashable.") from exc
        if len(unique_panels) != len(self.panels):
            raise ValueError("Small-multiples facet panels must be unique.")
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (self.rows, self.columns, self.width, self.height)
        ):
            raise ValueError("Small-multiples rows, columns, width, and height must be integers.")
        if self.rows < 1 or self.columns < 1:
            raise ValueError("Small-multiples rows and columns must both be at least 1.")
        if self.rows * self.columns < len(self.panels):
            raise ValueError("The small-multiples grid has too few cells for its facet panels.")
        if self.width < 320 or self.height < 240:
            raise ValueError("Small-multiples dimensions must be at least 320 x 240 pixels.")


__all__ = ["FacetPanel", "SmallMultiplesSpec"]
