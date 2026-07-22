"""Immutable, presentation-ready differences between two plot configurations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ConfigurationChange = Literal["changed", "source_only", "destination_only"]


@dataclass(frozen=True)
class ConfigurationDifference:
    """One configuration leaf whose values differ between two plots."""

    path: str
    section: str
    change: ConfigurationChange
    source_value: str
    destination_value: str


@dataclass(frozen=True)
class PlotConfigurationComparison:
    # [impl->req~ring5.plots.configuration-comparison~1]
    """Immutable summary of a non-mutating plot-configuration comparison."""

    source_plot_id: int
    destination_plot_id: int
    source_name: str
    destination_name: str
    source_plot_type: str
    destination_plot_type: str
    differences: tuple[ConfigurationDifference, ...]
    matching_fields: int
    total_fields: int
    can_replace: bool
    replacement_reason: str | None = None

    @property
    def difference_count(self) -> int:
        """Return the number of configuration leaves that differ."""
        return len(self.differences)

    @property
    def identical(self) -> bool:
        """Return whether every configuration leaf has the same value."""
        return not self.differences


__all__ = [
    "ConfigurationChange",
    "ConfigurationDifference",
    "PlotConfigurationComparison",
]
