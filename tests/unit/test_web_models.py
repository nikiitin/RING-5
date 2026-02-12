"""
Tests for web layer models (Layer 5).

Validates that TypedDicts can be instantiated, type-checked,
and are JSON-serializable (critical for portfolio save/load).
"""

import json
from typing import Any, Dict, List

from src.web.models.plot_models import (
    AnnotationShapeConfig,
    MarginsConfig,
    PlotDisplayConfig,
    RelayoutEventData,
    SeriesStyleConfig,
    ShaperStep,
    TypographyConfig,
)

# ─── AnnotationShapeConfig ───────────────────────────────────────────────────


class TestAnnotationShapeConfig:
    """Tests for AnnotationShapeConfig TypedDict."""

    def test_create_line_shape(self) -> None:
        shape: AnnotationShapeConfig = {
            "type": "line",
            "x0": 0.0,
            "y0": 0.5,
            "x1": 1.0,
            "y1": 0.5,
            "line": {"color": "#FF0000", "width": 2},
        }
        assert shape["type"] == "line"
        assert shape["x0"] == 0.0
        assert shape["line"]["color"] == "#FF0000"

    def test_create_rect_shape(self) -> None:
        shape: AnnotationShapeConfig = {
            "type": "rect",
            "x0": "category_a",
            "y0": 0.0,
            "x1": "category_b",
            "y1": 1.0,
            "line": {"color": "#000000", "width": 1},
        }
        assert shape["type"] == "rect"
        assert shape["x0"] == "category_a"

    def test_partial_shape(self) -> None:
        """AnnotationShapeConfig is total=False, so partial is valid."""
        shape: AnnotationShapeConfig = {"type": "circle"}
        assert shape["type"] == "circle"
        assert "x0" not in shape

    def test_json_serializable(self) -> None:
        shape: AnnotationShapeConfig = {
            "type": "line",
            "x0": 1.5,
            "y0": 2.0,
            "x1": 3.0,
            "y1": 4.0,
            "line": {"color": "#00FF00", "width": 3},
        }
        json_str: str = json.dumps(shape)
        restored: AnnotationShapeConfig = json.loads(json_str)
        assert restored == shape


# ─── SeriesStyleConfig ───────────────────────────────────────────────────────


class TestSeriesStyleConfig:
    """Tests for SeriesStyleConfig TypedDict."""

    def test_create_full_style(self) -> None:
        style: SeriesStyleConfig = {
            "name": "Custom Label",
            "color": "#FF5733",
            "marker_symbol": "diamond",
            "pattern": "/",
        }
        assert style["name"] == "Custom Label"
        assert style["color"] == "#FF5733"

    def test_partial_style(self) -> None:
        style: SeriesStyleConfig = {"color": "#333333"}
        assert style["color"] == "#333333"
        assert "name" not in style

    def test_empty_pattern(self) -> None:
        style: SeriesStyleConfig = {"pattern": ""}
        assert style["pattern"] == ""

    def test_json_serializable(self) -> None:
        style: SeriesStyleConfig = {
            "name": "Series A",
            "color": "#AABBCC",
            "marker_symbol": "circle",
            "pattern": "x",
        }
        json_str: str = json.dumps(style)
        restored: SeriesStyleConfig = json.loads(json_str)
        assert restored == style


# ─── ShaperStep ──────────────────────────────────────────────────────────────


class TestShaperStep:
    """Tests for ShaperStep TypedDict."""

    def test_create_column_selector(self) -> None:
        step: ShaperStep = {
            "id": 0,
            "type": "columnSelector",
            "config": {"columns": ["col_a", "col_b"]},
        }
        assert step["id"] == 0
        assert step["type"] == "columnSelector"
        assert step["config"]["columns"] == ["col_a", "col_b"]

    def test_create_sort_shaper(self) -> None:
        step: ShaperStep = {
            "id": 1,
            "type": "sort",
            "config": {"by": "value", "ascending": True},
        }
        assert step["type"] == "sort"
        assert step["config"]["ascending"] is True

    def test_create_empty_config(self) -> None:
        step: ShaperStep = {"id": 2, "type": "mean", "config": {}}
        assert step["config"] == {}

    def test_json_serializable(self) -> None:
        step: ShaperStep = {
            "id": 5,
            "type": "normalize",
            "config": {"baseline": "config_a", "column": "ipc"},
        }
        json_str: str = json.dumps(step)
        restored: ShaperStep = json.loads(json_str)
        assert restored == step


# ─── RelayoutEventData ───────────────────────────────────────────────────────


class TestRelayoutEventData:
    """Tests for RelayoutEventData TypedDict."""

    def test_zoom_event(self) -> None:
        event: RelayoutEventData = {
            "xaxis_range": [0.5, 10.5],
            "yaxis_range": [0.0, 1.0],
        }
        assert event["xaxis_range"] == [0.5, 10.5]
        assert event["yaxis_range"] == [0.0, 1.0]

    def test_legend_drag_event(self) -> None:
        event: RelayoutEventData = {
            "legend_x": 0.8,
            "legend_y": 0.95,
            "legend_xanchor": "left",
        }
        assert event["legend_x"] == 0.8

    def test_autorange_event(self) -> None:
        event: RelayoutEventData = {
            "xaxis_autorange": True,
            "yaxis_autorange": True,
        }
        assert event["xaxis_autorange"] is True


# ─── MarginsConfig ───────────────────────────────────────────────────────────


class TestMarginsConfig:
    """Tests for MarginsConfig TypedDict."""

    def test_full_margins(self) -> None:
        margins: MarginsConfig = {
            "top": 50,
            "bottom": 80,
            "left": 60,
            "right": 40,
        }
        assert margins["top"] == 50
        assert margins["bottom"] == 80

    def test_partial_margins(self) -> None:
        margins: MarginsConfig = {"bottom": 100}
        assert margins["bottom"] == 100
        assert "top" not in margins


# ─── TypographyConfig ────────────────────────────────────────────────────────


class TestTypographyConfig:
    """Tests for TypographyConfig TypedDict."""

    def test_full_typography(self) -> None:
        typo: TypographyConfig = {
            "font_size": 14,
            "title_font_size": 20,
            "xaxis_title_font_size": 16,
            "yaxis_title_font_size": 16,
            "legend_font_size": 12,
            "tick_font_size": 10,
            "title_color": "#000000",
            "xaxis_title_color": "#333333",
            "yaxis_title_color": "#333333",
        }
        assert typo["font_size"] == 14
        assert typo["title_color"] == "#000000"


# ─── PlotDisplayConfig ───────────────────────────────────────────────────────


class TestPlotDisplayConfig:
    """Tests for PlotDisplayConfig TypedDict."""

    def test_minimal_config(self) -> None:
        config: PlotDisplayConfig = {
            "x": "benchmark",
            "y": "ipc",
            "title": "IPC by Benchmark",
        }
        assert config["x"] == "benchmark"
        assert config["y"] == "ipc"
        assert config["title"] == "IPC by Benchmark"

    def test_full_config(self) -> None:
        config: PlotDisplayConfig = {
            "x": "benchmark",
            "y": "ipc",
            "title": "IPC by Benchmark",
            "xlabel": "Benchmark",
            "ylabel": "IPC",
            "legend_title": "Configuration",
            "color": "config",
            "group": None,
            "width": 800,
            "height": 500,
            "xaxis_tickangle": -45,
            "show_error_bars": False,
            "bargap": 0.2,
            "download_format": "pdf",
            "export_scale": 2,
            "enable_editable": False,
            "shapes": [],
            "series_styles": {},
        }
        assert config["width"] == 800
        assert config["download_format"] == "pdf"
        assert config["shapes"] == []

    def test_json_round_trip(self) -> None:
        config: PlotDisplayConfig = {
            "x": "benchmark",
            "y": "cycles",
            "title": "Cycles",
            "xlabel": "Bench",
            "ylabel": "Cycles",
            "width": 1000,
            "height": 600,
            "bargap": 0.15,
            "series_styles": {
                "config_a": {"name": "Config A", "color": "#FF0000"},
                "config_b": {"name": "Config B", "color": "#0000FF"},
            },
            "shapes": [
                {"type": "line", "x0": 0, "y0": 1, "x1": 10, "y1": 1},
            ],
        }
        json_str: str = json.dumps(config)
        restored: Dict[str, Any] = json.loads(json_str)
        assert restored["x"] == "benchmark"
        assert restored["series_styles"]["config_a"]["color"] == "#FF0000"
        assert len(restored["shapes"]) == 1

    def test_config_with_none_values(self) -> None:
        config: PlotDisplayConfig = {
            "x": "benchmark",
            "y": "ipc",
            "color": None,
            "group": None,
            "range_x": None,
            "range_y": None,
        }
        assert config["color"] is None
        assert config["range_x"] is None

    def test_config_with_interactive_state(self) -> None:
        config: PlotDisplayConfig = {
            "x": "benchmark",
            "y": "ipc",
            "range_x": [0.5, 10.5],
            "range_y": [0.0, 1.0],
            "legend_x": 0.8,
            "legend_y": 0.95,
            "legend_xanchor": "left",
            "legend_yanchor": "top",
        }
        assert config["range_x"] == [0.5, 10.5]
        assert config["legend_x"] == 0.8


# ─── Pipeline (List of ShaperSteps) ─────────────────────────────────────────


class TestPipeline:
    """Tests for a pipeline as a list of ShaperSteps."""

    def test_create_pipeline(self) -> None:
        pipeline: List[ShaperStep] = [
            {"id": 0, "type": "columnSelector", "config": {"columns": ["a", "b"]}},
            {"id": 1, "type": "sort", "config": {"by": "a"}},
            {"id": 2, "type": "mean", "config": {"group_by": "a"}},
        ]
        assert len(pipeline) == 3
        assert pipeline[0]["type"] == "columnSelector"
        assert pipeline[2]["type"] == "mean"

    def test_json_round_trip(self) -> None:
        pipeline: List[ShaperStep] = [
            {"id": 0, "type": "normalize", "config": {"baseline": "x", "column": "y"}},
            {"id": 1, "type": "conditionSelector", "config": {"condition": "a > 5"}},
        ]
        json_str: str = json.dumps(pipeline)
        restored: List[Dict[str, Any]] = json.loads(json_str)
        assert len(restored) == 2
        assert restored[0]["type"] == "normalize"
