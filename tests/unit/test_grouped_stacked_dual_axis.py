"""Tests for GroupedStackedBarPlot dual-axis feature."""

from typing import Any, cast
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


# Figure creation tests


class TestDualAxisCreateFigure:
    """Test create_figure with dual_axis=True."""

    # [test->req~ring5.plot.grouped-stacked-bar~1]

    def test_dual_axis_bars_right(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dual-axis with bars on both axes produces correct traces."""
        config: dict[str, Any] = {
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
        assert len(list(fig.data)) == 3
        # All traces are Bar type
        for trace in fig.data:
            assert isinstance(trace, go.Bar)

        # Layout has secondary Y-axis
        assert fig.layout.yaxis2 is not None

    def test_dual_axis_dots_right(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dual-axis with dots on the right axis."""
        config: dict[str, Any] = {
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
        assert len(list(fig.data)) == 2
        assert isinstance(fig.data[0], go.Bar)
        assert isinstance(fig.data[1], go.Scatter)

    def test_dual_axis_dots_with_lines(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dots on right axis with lines enabled."""
        config: dict[str, Any] = {
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

        scatter_trace = cast(go.Scatter, fig.data[1])
        assert scatter_trace.mode == "lines+markers"
        scatter_marker = cast(go.scatter.Marker, scatter_trace.marker)
        assert scatter_marker.size == 12
        assert scatter_marker.symbol == "diamond"
        scatter_line = cast(go.scatter.Line, scatter_trace.line)
        assert scatter_line.width == 3

    def test_dual_axis_dots_no_lines(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dots on right axis with lines disabled."""
        config: dict[str, Any] = {
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

        scatter_trace = cast(go.Scatter, fig.data[1])
        assert scatter_trace.mode == "markers"

    def test_dual_axis_ylabel_right(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dual-axis mode enables secondary_y and assigns traces correctly."""
        config: dict[str, Any] = {
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
        result = plot.create_traces(sample_data, config)

        assert result.secondary_y is True
        # Left-axis traces exist
        left_traces = [t for t in result.traces if t.yaxis != "y2"]
        assert len(left_traces) > 0
        # Right-axis traces exist
        right_traces = [t for t in result.traces if t.yaxis == "y2"]
        assert len(right_traces) > 0

    def test_dual_axis_multiple_right_columns(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Multiple columns on the right axis produce multiple traces."""
        config: dict[str, Any] = {
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
        assert len(list(fig.data)) == 3
        for trace in fig.data:
            assert isinstance(trace, go.Bar)

    def test_dual_axis_empty_right_columns(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dual-axis with no right columns still works (only left bars)."""
        config: dict[str, Any] = {
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
        assert len(list(fig.data)) == 1
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
        config: dict[str, Any] = {
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
        right_trace = cast(go.Bar, fig.data[-1])
        assert right_trace.error_y is not None
        right_error_y = cast(go.bar.ErrorY, right_trace.error_y)
        assert right_error_y.visible is True

    def test_dual_axis_with_series_styles(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Series styles (color, pattern, rename) apply to right-axis traces."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "series_styles": {
                "IPC": {
                    "name": "Renamed IPC",
                    "color": "#FF0000",
                    "use_color": True,
                },
            },
            "title": "Styled",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        right_trace = cast(go.Bar, fig.data[-1])
        assert right_trace.name == "Renamed IPC"
        right_marker = cast(go.bar.Marker, right_trace.marker)
        assert right_marker.color == "#FF0000"


class TestDualAxisDisabled:
    """Verify that dual_axis=False keeps the existing behavior."""

    def test_no_dual_axis_same_as_before(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Standard (non-dual) creates go.Figure, not make_subplots."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks", "Energy"],
            "title": "Normal",
            "ylabel": "Value",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)

        assert len(list(fig.data)) == 2
        # No secondary Y-axis — accessing yaxis2 raises AttributeError
        with pytest.raises(AttributeError):
            _ = fig.layout.yaxis2


class TestApplyCommonLayoutDual:
    """Test that apply_common_layout fixes secondary Y after StyleApplicator."""

    def test_secondary_y_title_preserved(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """apply_common_layout converts secondary Y title to annotation."""
        config: dict[str, Any] = {
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

        # Native title is cleared; the label is now an annotation
        assert fig.layout.yaxis2.title.text == ""
        right_ann = [a for a in fig.layout.annotations if a.text == "Right Y"]
        assert len(right_ann) == 1
        assert right_ann[0].textangle == 90


class TestDualAxisDotScenarios:
    """Additional edge cases for dot traces on secondary axis."""

    def test_dot_with_pattern_style(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Dots ignore bar-specific styles like pattern."""
        config: dict[str, Any] = {
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

        scatter = cast(go.Scatter, fig.data[-1])
        assert scatter.name == "Custom IPC"
        assert isinstance(scatter, go.Scatter)

    def test_bars_with_pattern(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Right-axis bars support pattern fill."""
        config: dict[str, Any] = {
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

        right_trace = cast(go.Bar, fig.data[-1])
        right_marker = cast(go.bar.Marker, right_trace.marker)
        right_pattern = cast(go.bar.marker.Pattern, right_marker.pattern)
        assert right_pattern.shape == "/"


# Config UI tests
_MOD = "src.web.pages.ui.plotting.types.grouped_stacked_bar_plot"
_CFG_MOD = "src.web.components.plotting.config.grouped_stacked_bar_config"


def _ctx() -> MagicMock:
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=m)
    m.__exit__ = MagicMock(return_value=False)
    return m


class TestDualAxisConfigUI:
    """Test render_config_ui dual-axis section."""

    @patch(f"{_CFG_MOD}.PlotConfigComponents")
    @patch(f"{_CFG_MOD}.detect_column_types")
    @patch(f"{_CFG_MOD}.st")
    def test_checkbox_disabled_produces_default_keys(
        self, mock_st: MagicMock, mock_detect: MagicMock, mock_pcc: MagicMock
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

        mock_detect.return_value = (["V1", "V2"], ["Bench", "Cfg"])

        # Mocks: col1/col2 context managers
        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.selectbox.side_effect = ["Bench", "Cfg"]
        mock_st.multiselect.side_effect = [
            ["V1"],  # y_columns
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

        result: dict[str, Any] = plot.render_config_ui(data, {})

        assert result["dual_axis"] is False
        assert result["y_columns_right"] == []
        assert result["right_axis_type"] == "bars"
        assert result["ylabel_right"] == ""

    @patch(f"{_CFG_MOD}.PlotConfigComponents")
    @patch(f"{_CFG_MOD}.detect_column_types")
    @patch(f"{_CFG_MOD}.st")
    def test_checkbox_enabled_with_dots(
        self, mock_st: MagicMock, mock_detect: MagicMock, mock_pcc: MagicMock
    ) -> None:
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

        mock_detect.return_value = (["V1", "V2"], ["Bench", "Cfg"])

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.selectbox.side_effect = ["Bench", "Cfg"]

        # multiselect calls in order:
        # y_columns
        # y_columns_right (inside dual_axis block)
        # x_filter (from PlotConfigComponents mock → but we mock it)
        # group_filter
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
        # segmented_control: right_axis_type → "dots"
        mock_st.segmented_control.return_value = "dots"
        # text_input: ylabel_right
        mock_st.text_input.return_value = "Right Label"

        result: dict[str, Any] = plot.render_config_ui(data, {})

        assert result["dual_axis"] is True
        assert result["y_columns_right"] == ["V2"]
        assert result["right_axis_type"] == "dots"
        assert result["ylabel_right"] == "Right Label"


# Y-axis rotation tests


class TestDualAxisTitleRotation:
    """Test Y-axis title rotation in dual-axis mode."""

    def test_right_ylabel_rendered_as_annotation(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Right Y-label should be an annotation with textangle=90."""
        config: dict[str, Any] = {
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
        fig = plot.apply_common_layout(fig, config)

        # Native yaxis2 title should be cleared
        assert fig.layout.yaxis2.title.text == ""

        # Find the annotation with the right-axis label
        right_annotations = [a for a in fig.layout.annotations if a.text == "Right Y"]
        assert len(right_annotations) == 1

        ann = right_annotations[0]
        assert ann.textangle == 90
        assert ann.xref == "paper"
        assert ann.yref == "paper"
        assert ann.x == 1.0
        assert ann.y == 0.5
        assert ann.captureevents is False

    def test_left_ylabel_also_annotation_in_dual_axis(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """In dual-axis mode the left Y is ALSO an annotation for visual symmetry."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "ylabel": "Left Y",
            "ylabel_right": "Right Y",
            "title": "Test",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        # Native primary Y title should be cleared
        assert fig.layout.yaxis.title.text == ""

        left_annotations = [a for a in fig.layout.annotations if a.text == "Left Y"]
        assert len(left_annotations) == 1

        ann = left_annotations[0]
        assert ann.textangle == -90
        assert ann.xref == "paper"
        assert ann.yref == "paper"
        assert ann.x == 0
        assert ann.y == 0.5
        assert ann.captureevents is False

    def test_both_annotations_share_font_color(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Both Y-axis annotations share the same font colour."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "ylabel": "Left Y",
            "ylabel_right": "Right Y",
            "axis_color": "#0000ff",
            "title": "Test",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        left_ann = [a for a in fig.layout.annotations if a.text == "Left Y"]
        right_ann = [a for a in fig.layout.annotations if a.text == "Right Y"]
        assert left_ann[0].font.color == "#0000ff"
        assert right_ann[0].font.color == "#0000ff"

    def test_empty_right_ylabel_no_annotation(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """No annotation should be added when ylabel_right is empty."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "ylabel": "Left",
            "ylabel_right": "",
            "title": "Test",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        # No annotation with textangle=90 should exist
        rotated_90 = [a for a in fig.layout.annotations if getattr(a, "textangle", None) == 90]
        assert len(rotated_90) == 0

    def test_right_ylabel_font_size_falls_back_to_primary(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Right Y-label falls back to yaxis_title_font_size when no override."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "ylabel": "Left",
            "ylabel_right": "Right Y",
            "yaxis_title_font_size": 20,
            "title": "Test",
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        left_ann = [a for a in fig.layout.annotations if a.text == "Left"]
        right_ann = [a for a in fig.layout.annotations if a.text == "Right Y"]
        # Both should use the primary font size (20)
        assert left_ann[0].font.size == 20
        assert right_ann[0].font.size == 20


# Grid line per-axis tests


class TestDualAxisGridLines:
    """Test grid line show/hide per axis in dual-axis mode."""

    def test_both_grids_enabled(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Both grids enabled by default."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "show_y_grid": True,
            "y2show_y_grid": True,
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.yaxis.showgrid is True
        assert fig.layout.yaxis2.showgrid is True

    def test_left_grid_disabled(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Disabling left grid hides only primary Y grid lines."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "show_y_grid": False,
            "y2show_y_grid": True,
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.yaxis.showgrid is False
        assert fig.layout.yaxis2.showgrid is True

    def test_right_grid_disabled(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Disabling right grid hides only secondary Y grid lines."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "show_y_grid": True,
            "y2show_y_grid": False,
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.yaxis.showgrid is True
        assert fig.layout.yaxis2.showgrid is False

    def test_both_grids_disabled(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Both grids can be disabled simultaneously."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "show_y_grid": False,
            "y2show_y_grid": False,
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.yaxis.showgrid is False
        assert fig.layout.yaxis2.showgrid is False


# Legend unification tests


class TestDualAxisLegendUnification:
    """Test unified vs. separate legend in dual-axis mode."""

    def test_unified_legend_default(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Default (unified_legend=True) keeps all traces in one legend."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "unified_legend": True,
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        # No trace uses the secondary legend.
        for trace in fig.data:
            legend_attr = getattr(trace, "legend", None)
            assert legend_attr != "legend2"

    def test_separate_legend(self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame) -> None:
        """When unified_legend=False, traces are split into legend + legend2."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks", "Energy"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "unified_legend": False,
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        # 2 left traces → legend, 1 right trace → legend2
        assert cast(go.Bar, fig.data[0]).legend == "legend"
        assert cast(go.Bar, fig.data[1]).legend == "legend"
        assert cast(go.Bar, fig.data[2]).legend == "legend2"

    def test_separate_legend_positions(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Separate legends are positioned on left (legend) and right (legend2)."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "unified_legend": False,
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.legend.x == 0.0
        assert fig.layout.legend.xanchor == "left"
        assert fig.layout.legend2.x == 1.0
        assert fig.layout.legend2.xanchor == "right"

    def test_separate_legend_dots_mode(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Separate legends work correctly with dots on the right axis."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "dots",
            "title": "Test",
            "unified_legend": False,
        }
        fig: go.Figure = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        # 1 left (bar) → legend, 1 right (scatter) → legend2
        assert cast(go.Bar, fig.data[0]).legend == "legend"
        assert cast(go.Scatter, fig.data[1]).legend == "legend2"


# Dual-axis display settings UI test


class TestDualAxisDisplaySettingsUI:
    """Test _render_dual_axis_display_settings sets config keys."""

    @patch(f"{_MOD}.st")
    def test_display_settings_keys_in_config(self, mock_st: MagicMock) -> None:
        """Config dict contains grid and legend keys after render."""
        plot = GroupedStackedBarPlot(99, "Test")
        config: dict[str, Any] = {}

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.checkbox.side_effect = [False, True, True]  # left_grid, right_grid, unified

        plot._render_dual_axis_display_settings({}, config)

        assert "show_y_grid" in config
        assert "y2show_y_grid" in config
        assert "unified_legend" in config


# Secondary Y typography tests


class TestSecondaryYTypography:
    """Test _apply_dual_axis_titles applies yaxis2_* config keys."""

    def test_yaxis2_title_font_size(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """yaxis2_title_font_size controls the right Y-label annotation size."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "ylabel": "Left",
            "ylabel_right": "Right Y",
            "yaxis2_title_font_size": 24,
            "title": "Test",
        }
        fig = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        right_ann = [a for a in fig.layout.annotations if a.text == "Right Y"]
        assert len(right_ann) == 1
        assert right_ann[0].font.size == 24

    def test_yaxis2_title_standoff(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """yaxis2_title_standoff adjusts the annotation xshift."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "ylabel_right": "Right Y",
            "yaxis2_title_standoff": 80,
            "title": "Test",
        }
        fig = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        right_ann = [a for a in fig.layout.annotations if a.text == "Right Y"]
        # xshift = standoff + 40  →  80 + 40 = 120
        assert right_ann[0].xshift == 120
        # x stays at 1.0 (paper coords); actual offset is via xshift
        assert right_ann[0].x == 1.0

    def test_yaxis2_tickfont_applied(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """yaxis2_tickfont_size and color are applied to yaxis2."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "ylabel_right": "Right",
            "yaxis2_tickfont_size": 18,
            "yaxis2_tickfont_color": "#ff00ff",
            "title": "Test",
        }
        fig = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.yaxis2.tickfont.size == 18
        assert fig.layout.yaxis2.tickfont.color == "#ff00ff"


# Separate legends with full controls tests


class TestSeparateLegendControls:
    """Test _apply_separate_legends reads legend2_* config keys."""

    def test_legend2_position_from_config(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """legend2_x/y/xanchor/yanchor control legend2 position."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "unified_legend": False,
            "legend2_x": 0.8,
            "legend2_y": 0.3,
            "legend2_xanchor": "center",
            "legend2_yanchor": "bottom",
        }
        fig = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.legend2.x == 0.8
        assert fig.layout.legend2.y == 0.3
        assert fig.layout.legend2.xanchor == "center"
        assert fig.layout.legend2.yanchor == "bottom"

    def test_legend2_bgcolor(self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame) -> None:
        """legend2_bgcolor is applied."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "unified_legend": False,
            "legend2_bgcolor": "rgba(200,200,200,0.5)",
        }
        fig = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.legend2.bgcolor == "rgba(200,200,200,0.5)"

    def test_legend2_font(self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame) -> None:
        """legend2_font_color and legend2_font_size are applied."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "unified_legend": False,
            "legend2_font_color": "#123456",
            "legend2_font_size": 14,
        }
        fig = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.legend2.font.color == "#123456"
        assert fig.layout.legend2.font.size == 14

    def test_legend2_border(self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame) -> None:
        """legend2_bordercolor and legend2_borderwidth are applied."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "unified_legend": False,
            "legend2_border_color": "#abcdef",
            "legend2_border_width": 3,
        }
        fig = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.legend2.bordercolor == "#abcdef"
        assert fig.layout.legend2.borderwidth == 3

    def test_legend2_orientation(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """legend2_orientation controls horizontal/vertical layout."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "unified_legend": False,
            "legend2_orientation": "h",
        }
        fig = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.legend2.orientation == "h"

    def test_legend2_title_text(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """legend2_title sets the legend2 title."""
        config: dict[str, Any] = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "right_axis_type": "bars",
            "title": "Test",
            "unified_legend": False,
            "legend2_title": "Right Series",
        }
        fig = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)

        assert fig.layout.legend2.title.text == "Right Series"
