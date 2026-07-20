"""Tests for non-mutating, field-level plot configuration comparison."""

from __future__ import annotations

import copy
from typing import Any

import pandas as pd
import pytest

from src.core.services.visualization.plot_configuration_comparison_service import (
    compare_plot_configurations,
)


class _Plot:
    def __init__(self, plot_id: int, *, plot_type: str = "bar") -> None:
        self.plot_id = plot_id
        self.name = f"Plot {plot_id}"
        self.plot_type = plot_type
        self.config: dict[str, Any] = {}
        self.legend_mappings: dict[str, str] = {}
        self.legend_mappings_by_column: dict[str, dict[str, str]] = {}
        self.source_data: pd.DataFrame | None = None
        self.processed_data: pd.DataFrame | None = None


def test_comparison_reports_nested_leaves_sections_and_replacement_safety() -> None:
    # [test->req~ring5.plots.configuration-comparison~1]
    source, destination = _Plot(1), _Plot(2)
    source.config = {
        "x": "benchmark",
        "y": "ipc",
        "title": "Source",
        "series_styles": {"ipc": {"color": "red", "width": 2}},
    }
    destination.config = {
        "x": "benchmark",
        "y": "latency",
        "plot_specific": True,
        "series_styles": {"ipc": {"color": "blue"}},
    }
    source.legend_mappings = {"A": "Alpha"}
    source.processed_data = pd.DataFrame({"benchmark": ["A"], "ipc": [1.0]})
    destination.processed_data = pd.DataFrame({"benchmark": ["A"], "latency": [2.0]})
    source_snapshot = copy.deepcopy(source.config)
    destination_snapshot = copy.deepcopy(destination.config)

    result = compare_plot_configurations(source, destination)

    by_path = {difference.path: difference for difference in result.differences}
    assert by_path["y"].change == "changed"
    assert by_path["title"].change == "source_only"
    assert by_path["plot_specific"].change == "destination_only"
    assert by_path["series_styles.ipc.color"].section == "Colors and series styles"
    assert by_path["legend_mappings.A"].section == "Legends"
    assert by_path["y"].section == "Data mappings"
    assert result.matching_fields == 2
    assert result.total_fields == 8
    assert not result.identical
    assert result.difference_count == 6
    assert not result.can_replace
    assert result.replacement_reason == (
        "Destination plot is missing processed columns required by the source: ipc."
    )
    assert source.config == source_snapshot
    assert destination.config == destination_snapshot


def test_identical_configuration_and_plot_type_compatibility_are_explicit() -> None:
    source, destination = _Plot(1), _Plot(2)
    source.config = destination.config = {"title": None, "show_values": False}

    result = compare_plot_configurations(source, destination)

    assert result.identical
    assert result.difference_count == 0
    assert result.matching_fields == result.total_fields
    assert result.can_replace
    assert result.replacement_reason is None

    destination.plot_type = "line"
    incompatible = compare_plot_configurations(source, destination)
    assert not incompatible.can_replace
    assert incompatible.replacement_reason == (
        "Complete configurations can only be copied between the same plot type."
    )


def test_comparison_rejects_the_same_plot() -> None:
    plot = _Plot(1)

    with pytest.raises(ValueError, match="two different plots"):
        compare_plot_configurations(plot, plot)
