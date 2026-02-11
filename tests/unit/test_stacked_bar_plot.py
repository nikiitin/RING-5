"""Unit tests for StackedBarPlot — stacked bar plot implementation.

Covers create_figure, _prepare_data, _get_hover_template,
_create_stacked_figure, _add_bar_trace, _build_totals_annotations,
_get_total_position, and get_legend_column.
"""

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go

from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "benchmark": ["bfs", "pr", "sssp", "cc"],
            "ipc": [1.2, 0.9, 1.5, 1.1],
            "cpi": [0.8, 1.1, 0.7, 0.9],
        }
    )


def _base_config() -> Dict[str, Any]:
    return {"x": "benchmark", "y_columns": ["ipc", "cpi"]}


# ===================================================================
# _prepare_data
# ===================================================================


class TestPrepareData:
    """Tests for StackedBarPlot._prepare_data."""

    def test_returns_copy(self) -> None:
        plot = StackedBarPlot(1, "test")
        df = _sample_df()
        result = plot._prepare_data(df, "benchmark", ["ipc", "cpi"], {})
        assert result is not df

    def test_x_converted_to_str(self) -> None:
        plot = StackedBarPlot(1, "test")
        df = pd.DataFrame({"idx": [1, 2], "val": [10, 20]})
        result = plot._prepare_data(df, "idx", ["val"], {})
        assert result["idx"].dtype == object  # str

    def test_total_column_added(self) -> None:
        plot = StackedBarPlot(1, "test")
        result = plot._prepare_data(_sample_df(), "benchmark", ["ipc", "cpi"], {})
        assert "__total" in result.columns
        expected = _sample_df()["ipc"] + _sample_df()["cpi"]
        pd.testing.assert_series_equal(result["__total"], expected, check_names=False)

    def test_x_filter_applied(self) -> None:
        plot = StackedBarPlot(1, "test")
        config: Dict[str, Any] = {"x_filter": ["bfs", "sssp"]}
        result = plot._prepare_data(_sample_df(), "benchmark", ["ipc", "cpi"], config)
        assert set(result["benchmark"]) == {"bfs", "sssp"}

    def test_no_x_filter(self) -> None:
        plot = StackedBarPlot(1, "test")
        result = plot._prepare_data(_sample_df(), "benchmark", ["ipc", "cpi"], {})
        assert len(result) == 4


# ===================================================================
# _get_hover_template
# ===================================================================


class TestGetHoverTemplate:
    """Tests for hover template generation."""

    def test_contains_format(self) -> None:
        plot = StackedBarPlot(1, "test")
        tmpl = plot._get_hover_template()
        assert "%{y:.4f}" in tmpl
        assert "%{customdata:.4f}" in tmpl
        assert "<extra></extra>" in tmpl


# ===================================================================
# _get_total_position
# ===================================================================


class TestGetTotalPosition:
    """Tests for _get_total_position."""

    def test_outside(self) -> None:
        plot = StackedBarPlot(1, "test")
        y, anchor = plot._get_total_position(10.0, "Outside", "End")
        assert y == 10.0
        assert anchor == "bottom"

    def test_inside_end(self) -> None:
        plot = StackedBarPlot(1, "test")
        y, anchor = plot._get_total_position(10.0, "Inside", "End")
        assert y == 10.0
        assert anchor == "top"

    def test_inside_middle(self) -> None:
        plot = StackedBarPlot(1, "test")
        y, anchor = plot._get_total_position(10.0, "Inside", "Middle")
        assert y == 5.0
        assert anchor == "middle"

    def test_inside_start(self) -> None:
        plot = StackedBarPlot(1, "test")
        y, anchor = plot._get_total_position(10.0, "Inside", "Start")
        assert y == 0
        assert anchor == "bottom"

    def test_unknown_position(self) -> None:
        plot = StackedBarPlot(1, "test")
        y, anchor = plot._get_total_position(5.0, "Unknown", "End")
        assert y == 5.0
        assert anchor == "bottom"


# ===================================================================
# _build_totals_annotations
# ===================================================================


class TestBuildTotalsAnnotations:
    """Tests for _build_totals_annotations."""

    def test_basic_annotations(self) -> None:
        plot = StackedBarPlot(1, "test")
        df = _sample_df()
        df["__total"] = df["ipc"] + df["cpi"]
        annotations = plot._build_totals_annotations(df, "benchmark", {})
        assert len(annotations) == 4
        assert annotations[0]["xref"] == "x"
        assert annotations[0]["yref"] == "y"

    def test_threshold_filters(self) -> None:
        plot = StackedBarPlot(1, "test")
        df = pd.DataFrame({"cat": ["a", "b", "c"], "v1": [0.1, 5.0, 10.0], "v2": [0.0, 1.0, 2.0]})
        df["__total"] = df["v1"] + df["v2"]
        annotations = plot._build_totals_annotations(df, "cat", {"total_threshold": 2.0})
        # Only rows with total > 2.0: b (6.0), c (12.0)
        assert len(annotations) == 2

    def test_format_string(self) -> None:
        plot = StackedBarPlot(1, "test")
        df = pd.DataFrame({"x": ["a"], "v": [3.14159]})
        df["__total"] = df["v"]
        annotations = plot._build_totals_annotations(df, "x", {"net_total_format": ".1f"})
        assert annotations[0]["text"] == "3.1"

    def test_font_config(self) -> None:
        plot = StackedBarPlot(1, "test")
        df = pd.DataFrame({"x": ["a"], "v": [1.0]})
        df["__total"] = df["v"]
        config: Dict[str, Any] = {
            "total_font_size": 16,
            "total_font_color": "#FF0000",
        }
        annotations = plot._build_totals_annotations(df, "x", config)
        assert annotations[0]["font"]["size"] == 16
        assert annotations[0]["font"]["color"] == "#FF0000"

    def test_rotation_and_offset(self) -> None:
        plot = StackedBarPlot(1, "test")
        df = pd.DataFrame({"x": ["a"], "v": [2.0]})
        df["__total"] = df["v"]
        config: Dict[str, Any] = {"total_rotation": 45, "total_offset": 5}
        annotations = plot._build_totals_annotations(df, "x", config)
        assert annotations[0]["textangle"] == 45
        assert annotations[0]["yshift"] == 5


# ===================================================================
# _add_bar_trace
# ===================================================================


class TestAddBarTrace:
    """Tests for _add_bar_trace."""

    def test_basic_trace(self) -> None:
        plot = StackedBarPlot(1, "test")
        fig = go.Figure()
        df = _sample_df()
        df["__total"] = df["ipc"] + df["cpi"]
        fig = plot._add_bar_trace(fig, df, "ipc", "benchmark", None, "", {})
        assert len(fig.data) == 1
        assert fig.data[0].name == "ipc"

    def test_error_bars(self) -> None:
        plot = StackedBarPlot(1, "test")
        fig = go.Figure()
        df = _sample_df()
        df["__total"] = df["ipc"] + df["cpi"]
        df["ipc.sd"] = [0.1, 0.2, 0.1, 0.15]
        config: Dict[str, Any] = {"show_error_bars": True}
        fig = plot._add_bar_trace(fig, df, "ipc", "benchmark", None, "", config)
        assert fig.data[0].error_y.visible is True

    def test_series_color(self) -> None:
        plot = StackedBarPlot(1, "test")
        fig = go.Figure()
        df = _sample_df()
        df["__total"] = df["ipc"] + df["cpi"]
        config: Dict[str, Any] = {"series_styles": {"ipc": {"color": "#00FF00"}}}
        fig = plot._add_bar_trace(fig, df, "ipc", "benchmark", None, "", config)
        assert fig.data[0].marker.color == "#00FF00"

    def test_series_pattern(self) -> None:
        plot = StackedBarPlot(1, "test")
        fig = go.Figure()
        df = _sample_df()
        df["__total"] = df["ipc"] + df["cpi"]
        config: Dict[str, Any] = {"series_styles": {"ipc": {"pattern": "x"}}}
        fig = plot._add_bar_trace(fig, df, "ipc", "benchmark", None, "", config)
        assert fig.data[0].marker.pattern.shape == "x"

    def test_custom_name(self) -> None:
        plot = StackedBarPlot(1, "test")
        fig = go.Figure()
        df = _sample_df()
        df["__total"] = df["ipc"] + df["cpi"]
        config: Dict[str, Any] = {"series_styles": {"ipc": {"name": "Instructions/Cycle"}}}
        fig = plot._add_bar_trace(fig, df, "ipc", "benchmark", None, "", config)
        assert fig.data[0].name == "Instructions/Cycle"

    def test_bar_width(self) -> None:
        plot = StackedBarPlot(1, "test")
        fig = go.Figure()
        df = _sample_df()
        df["__total"] = df["ipc"] + df["cpi"]
        fig = plot._add_bar_trace(fig, df, "ipc", "benchmark", 0.4, "", {})
        assert fig.data[0].width == 0.4


# ===================================================================
# create_figure
# ===================================================================


class TestCreateFigure:
    """Tests for create_figure end-to-end."""

    def test_missing_x_shows_message(self) -> None:
        plot = StackedBarPlot(1, "test")
        fig = plot.create_figure(_sample_df(), {"y_columns": ["ipc"]})
        assert "Please select" in fig.layout.title.text

    def test_missing_y_shows_message(self) -> None:
        plot = StackedBarPlot(1, "test")
        fig = plot.create_figure(_sample_df(), {"x": "benchmark", "y_columns": []})
        assert "Please select" in fig.layout.title.text

    def test_creates_traces(self) -> None:
        plot = StackedBarPlot(1, "test")
        config = _base_config()
        fig = plot.create_figure(_sample_df(), config)
        assert len(fig.data) == 2  # ipc + cpi
        assert fig.layout.barmode == "stack"

    def test_layout_titles(self) -> None:
        plot = StackedBarPlot(1, "test")
        config = {**_base_config(), "title": "My Stacked", "xlabel": "Bench", "ylabel": "Val"}
        fig = plot.create_figure(_sample_df(), config)
        assert fig.layout.title.text == "My Stacked"

    def test_with_totals(self) -> None:
        plot = StackedBarPlot(1, "test")
        config = {**_base_config(), "show_totals": True}
        fig = plot.create_figure(_sample_df(), config)
        assert len(fig.layout.annotations) == 4  # One per row


# ===================================================================
# get_legend_column
# ===================================================================


class TestGetLegendColumn:
    """Tests for get_legend_column."""

    def test_returns_none(self) -> None:
        plot = StackedBarPlot(1, "test")
        assert plot.get_legend_column({}) is None
