"""Tests for GroupedStackedBarPlot dual-axis feature."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.types.grouped_stacked_bar_plot import (
    GroupedStackedBarPlot,
)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """DataFrame with 2 categorical + 4 numeric columns."""
    return pd.DataFrame(
        {
            "Benchmark": ["A", "A", "B", "B"],
            "Config": ["c1", "c2", "c1", "c2"],
            "Ticks": [100, 200, 150, 250],
            "Energy": [10, 20, 15, 25],
            "IPC": [1.2, 1.5, 1.1, 1.4],
            "Cycles": [3200, 2900, 7800, 7100],
        }
    )


@pytest.fixture
def plot() -> GroupedStackedBarPlot:
    return GroupedStackedBarPlot(1, "Test")


# ── Figure creation tests ────────────────────────────────────────


class TestDualAxisCreateFigure:
    """Test create_figure with dual_axis=True."""

    def test_dual_axis_bars_right(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dual-axis with bars on both axes produces correct traces."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks", "Energy"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Dual Bars",
            "xlabel": "Bench",
            "ylabel": "Left",
            "ylabel_right": "Right",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        # 2 left-axis bars + 1 right-axis bar = 3 traces
        assert len(fig.data) == 3
        # All traces are Bar type
        for trace in fig.data:
            assert isinstance(trace, go.Bar)

        # Layout has secondary Y-axis
        assert fig.layout.yaxis2 is not None

    def test_dual_axis_dots_right(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dual-axis with dots on the right axis."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "dots",
            "title": "Bars+Dots",
            "xlabel": "Bench",
            "ylabel": "Left",
            "ylabel_right": "IPC",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        # 1 left-axis bar + 1 right-axis scatter = 2 traces
        assert len(fig.data) == 2
        assert isinstance(fig.data[0], go.Bar)
        assert isinstance(fig.data[1], go.Scatter)

    def test_dual_axis_dots_with_lines(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dots on right axis with lines enabled."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "dots",
            "right_show_lines": True,
            "right_dot_size": 12,
            "right_dot_symbol": "diamond",
            "right_line_width": 3,
            "title": "With Lines",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        scatter_trace: go.Scatter = fig.data[1]  # type: ignore[assignment]
        assert scatter_trace.mode == "lines+markers"
        assert scatter_trace.marker.size == 12
        assert scatter_trace.marker.symbol == "diamond"
        assert scatter_trace.line.width == 3

    def test_dual_axis_dots_no_lines(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dots on right axis with lines disabled."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "dots",
            "right_show_lines": False,
            "title": "Markers Only",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        scatter_trace: go.Scatter = fig.data[1]  # type: ignore[assignment]
        assert scatter_trace.mode == "markers"

    def test_dual_axis_ylabel_right(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Right Y-axis label is set correctly."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "ylabel": "Left Axis",
            "ylabel_right": "Right Axis",
            "title": "Labels",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        # Primary Y
        assert fig.layout.yaxis.title.text == "Left Axis"
        # Secondary Y
        assert fig.layout.yaxis2.title.text == "Right Axis"

    def test_dual_axis_multiple_right_columns(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Multiple columns on the right axis produce multiple traces."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC", "Cycles"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Multi Right",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        # 1 left + 2 right = 3 traces
        assert len(fig.data) == 3
        for trace in fig.data:
            assert isinstance(trace, go.Bar)

    def test_dual_axis_empty_right_columns(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dual-axis with no right columns still works (only left bars)."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": [],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Empty Right",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        # Only left-axis traces
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Bar)

    def test_dual_axis_with_error_bars(self, plot: GroupedStackedBarPlot) -> None:
        """Error bars are handled for right-axis traces."""
        data: pd.DataFrame = pd.DataFrame(
            {
                "Bench": ["A", "A", "B", "B"],
                "Cfg": ["c1", "c2", "c1", "c2"],
                "Val": [10, 20, 15, 25],
                "IPC": [1.2, 1.5, 1.1, 1.4],
                "IPC.sd": [0.1, 0.2, 0.15, 0.1],
            }
        )
        config: Dict[str, Any] = {
            "x": "Bench",
            "group": "Cfg",
            "y_columns": ["Val"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "show_error_bars": True,
            "title": "Error Bars",
        }
        fig: go.Figure = plot.create_figure(data, config)

        # Right-axis bar should have error bars
        right_trace: go.Bar = fig.data[-1]  # type: ignore[assignment]
        assert right_trace.error_y is not None
        assert right_trace.error_y.visible is True

    def test_dual_axis_with_series_styles(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Series styles (color, pattern, rename) apply to right-axis traces."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "series_styles": {
                "IPC": {"name": "Renamed IPC", "color": "#FF0000"},
            },
            "title": "Styled",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        right_trace: go.Bar = fig.data[-1]  # type: ignore[assignment]
        assert right_trace.name == "Renamed IPC"
        assert right_trace.marker.color == "#FF0000"


class TestDualAxisDisabled:
    """Verify that dual_axis=False keeps the existing behavior."""

    def test_no_dual_axis_same_as_before(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Standard (non-dual) creates go.Figure, not make_subplots."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks", "Energy"],
            "title": "Normal",
            "ylabel": "Value",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        assert len(fig.data) == 2
        # No secondary Y-axis — accessing yaxis2 raises AttributeError
        with pytest.raises(AttributeError):
            _ = fig.layout.yaxis2


class TestApplyCommonLayoutDual:
    """Test that apply_common_layout fixes secondary Y after StyleApplicator."""

    def test_secondary_y_title_preserved(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """apply_common_layout re-applies secondary Y title."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "ylabel": "Left",
            "ylabel_right": "Right Y",
            "title": "Test",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        # Simulate what apply_common_layout does (it's called by the renderer)
        # We call it directly to test the secondary Y re-application
        fig = plot.apply_common_layout(fig, config)

        # Secondary Y title should survive even after StyleApplicator run
        assert fig.layout.yaxis2.title.text == "Right Y"


class TestDualAxisDotScenarios:
    """Additional edge cases for dot traces on secondary axis."""

    def test_dot_with_pattern_style(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dots ignore bar-specific styles like pattern."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "dots",
            "series_styles": {"IPC": {"name": "Custom IPC"}},
            "title": "Dot Style",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        scatter: go.Scatter = fig.data[-1]  # type: ignore[assignment]
        assert scatter.name == "Custom IPC"
        assert isinstance(scatter, go.Scatter)

    def test_bars_with_pattern(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Right-axis bars support pattern fill."""
        config: Dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "series_styles": {
                "IPC": {"pattern": "/"},
            },
            "title": "Pattern",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        right_trace: go.Bar = fig.data[-1]  # type: ignore[assignment]
        assert right_trace.marker.pattern.shape == "/"


# ── Config UI tests ──────────────────────────────────────────────

_MOD = "src.web.pages.ui.plotting.types.grouped_stacked_bar_plot"


def _ctx() -> MagicMock:
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=m)
    m.__exit__ = MagicMock(return_value=False)
    return m


class TestDualAxisConfigUI:
    """Test render_config_ui dual-axis section."""

    @patch(f"{_MOD}.PlotConfigComponents")
    @patch(f"{_MOD}.st")
    def test_checkbox_disabled_produces_default_keys(
        self, mock_st: MagicMock, mock_pcc: MagicMock
    ) -> None:
        """When dual_axis checkbox is unchecked, config has default values."""
        plot = GroupedStackedBarPlot(99, "Test")
        data = pd.DataFrame(
            {
                "Bench": ["A", "B"],
                "Cfg": ["c1", "c2"],
                "V1": [1.0, 2.0],
                "V2": [3.0, 4.0],
            }
        )

        # Mocks: col1/col2 context managers
        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.selectbox.side_effect = ["Bench", "Cfg"]
        mock_st.multiselect.side_effect = [
            ["V1"],  # y_columns
            None,  # x_filter
            None,  # group_filter
        ]

        mock_pcc.render_title_labels_section.return_value = {
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "legend_title": "L",
        }
        mock_pcc.render_filter_multiselects.return_value = (None, None)

        # dual_axis checkbox unchecked
        mock_st.checkbox.return_value = False

        result: Dict[str, Any] = plot.render_config_ui(data, {})

        assert result["dual_axis"] is False
        assert result["y_columns_right"] == []
        assert result["right_axis_type"] == "bars"
        assert result["ylabel_right"] == ""

    @patch(f"{_MOD}.PlotConfigComponents")
    @patch(f"{_MOD}.st")
    def test_checkbox_enabled_with_dots(self, mock_st: MagicMock, mock_pcc: MagicMock) -> None:
        """When dual_axis is enabled + dots, config has right-axis keys."""
        plot = GroupedStackedBarPlot(99, "Test")
        data = pd.DataFrame(
            {
                "Bench": ["A", "B"],
                "Cfg": ["c1", "c2"],
                "V1": [1.0, 2.0],
                "V2": [3.0, 4.0],
            }
        )

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.selectbox.side_effect = ["Bench", "Cfg"]

        # multiselect calls in order:
        # 1. y_columns
        # 2. y_columns_right (inside dual_axis block)
        # 3. x_filter (from PlotConfigComponents mock → but we mock it)
        # 4. group_filter
        mock_st.multiselect.side_effect = [
            ["V1"],  # y_columns
            ["V2"],  # y_columns_right
        ]

        mock_pcc.render_title_labels_section.return_value = {
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "legend_title": "L",
        }
        mock_pcc.render_filter_multiselects.return_value = (None, None)

        # checkbox calls: dual_axis → True
        mock_st.checkbox.return_value = True
        # radio: right_axis_type → "dots"
        mock_st.radio.return_value = "dots"
        # text_input: ylabel_right
        mock_st.text_input.return_value = "Right Label"

        result: Dict[str, Any] = plot.render_config_ui(data, {})

        assert result["dual_axis"] is True
        assert result["y_columns_right"] == ["V2"]
        assert result["right_axis_type"] == "dots"
        assert result["ylabel_right"] == "Right Label"
