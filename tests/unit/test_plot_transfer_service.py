"""Tests for atomic configuration and pipeline transfers between plots."""

from __future__ import annotations

import copy
from typing import Any

import pandas as pd
import pytest

from src.core.services.visualization.plot_transfer_service import copy_plot_content


class _Plot:
    def __init__(self, plot_id: int, plot_type: str = "bar") -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type
        self.name = f"Plot {plot_id}"
        self.config: dict[str, Any] = {}
        self.pipeline: list[Any] = []
        self.pipeline_counter = 0
        self.legend_mappings: dict[str, str] = {}
        self.legend_mappings_by_column: dict[str, dict[str, str]] = {}
        self.source_data: pd.DataFrame | None = None
        self.processed_data: pd.DataFrame | None = None
        self.invalidated = False

    def invalidate_figure(self) -> None:
        self.invalidated = True

    def replace_processed_data(self, data: pd.DataFrame | None) -> None:
        self.processed_data = data
        self.invalidated = True


def test_selected_settings_copy_only_requested_presentation_values() -> None:
    # [test->req~ring5.plots.copy-settings-pipeline~1]
    source, target = _Plot(1), _Plot(2, "line")
    source.config = {
        "x": "source_x",
        "y": "source_y",
        "title": "Source title",
        "font_family": "serif",
        "color_palette": "wong",
        "shapes": [{"type": "line"}],
    }
    target.config = {"x": "target_x", "y": "target_y", "title": "Target"}

    result = copy_plot_content(source, target, "settings", sections=["labels", "colors"])

    assert target.config["x"] == "target_x"
    assert target.config["y"] == "target_y"
    assert target.config["title"] == "Source title"
    assert target.config["color_palette"] == "wong"
    assert "font_family" not in target.config
    assert "shapes" not in target.config
    assert target.invalidated
    assert result.copied_keys == ("color_palette", "title")


def test_complete_configuration_is_defensive_and_requires_compatible_plot() -> None:
    source, target = _Plot(1), _Plot(2)
    source.processed_data = pd.DataFrame({"x": ["A"], "y": [1.0]})
    target.processed_data = source.processed_data.copy()
    source.config = {"x": "x", "y": "y", "series_styles": {"y": {"color": "red"}}}
    source.legend_mappings = {"A": "Alpha"}

    result = copy_plot_content(source, target, "configuration")
    source.config["series_styles"]["y"]["color"] = "blue"

    assert target.config["series_styles"]["y"]["color"] == "red"
    assert target.legend_mappings == {"A": "Alpha"}
    assert result.copied_keys == ("series_styles", "x", "y")

    incompatible = _Plot(3, "scatter")
    incompatible.processed_data = target.processed_data
    with pytest.raises(ValueError, match="same plot type"):
        copy_plot_content(source, incompatible, "configuration")


def test_pipeline_copy_requires_source_schema_and_clears_stale_output() -> None:
    source, target = _Plot(1), _Plot(2)
    source.source_data = pd.DataFrame({"benchmark": ["A"], "ipc": [1.0]})
    target.source_data = source.source_data.copy()
    target.processed_data = target.source_data.copy()
    source.pipeline = [{"id": 4, "type": "sort", "config": {"order_dict": {"ipc": True}}}]
    source.pipeline_counter = 4

    result = copy_plot_content(source, target, "pipeline")
    source.pipeline[0]["config"]["order_dict"]["ipc"] = False

    assert target.pipeline[0]["config"]["order_dict"]["ipc"] is True
    assert target.pipeline_counter == 4
    assert target.processed_data is None
    assert result.pipeline_steps == 1
    assert result.requires_finalize

    target.source_data = pd.DataFrame({"benchmark": ["A"]})
    with pytest.raises(ValueError, match="missing source columns.*ipc"):
        copy_plot_content(source, target, "pipeline")


@pytest.mark.parametrize(
    ("mode", "sections", "message"),
    [
        ("settings", [], "at least one"),
        ("settings", ["unknown"], "Unknown"),
        ("invalid", [], "Copy mode"),
    ],
)
def test_rejects_ambiguous_transfers(mode: str, sections: list[str], message: str) -> None:
    source, target = _Plot(1), _Plot(2)
    with pytest.raises(ValueError, match=message):
        copy_plot_content(source, target, mode, sections=sections)  # type: ignore[arg-type]


def test_rejects_copy_to_self_without_mutation() -> None:
    plot = _Plot(1)
    plot.config = {"title": "Keep"}
    snapshot = copy.deepcopy(plot.config)

    with pytest.raises(ValueError, match="different plots"):
        copy_plot_content(plot, plot, "settings", sections=["labels"])

    assert plot.config == snapshot
