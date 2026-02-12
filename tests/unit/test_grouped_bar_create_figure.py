"""Tests for GroupedBarPlot.create_figure — no-group and edge case branches."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.types.grouped_bar_plot import GroupedBarPlot


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Category": ["Bench1", "Bench1", "Bench2", "Bench2"],
            "Group": ["X", "Y", "X", "Y"],
            "Value": [10, 20, 15, 25],
            "Value.sd": [1, 2, 1.5, 2.5],
        }
    )


@pytest.fixture
def plot() -> GroupedBarPlot:
    return GroupedBarPlot(1, "Test")


class TestCreateFigureNoGroup:
    """Test the no-group (single series) branch."""

    def test_no_group_single_series(self, plot: GroupedBarPlot) -> None:
        """When group is None, creates a single bar trace."""
        data = pd.DataFrame({"Cat": ["A", "B", "C"], "Val": [10, 20, 30]})
        config = {
            "x": "Cat",
            "y": "Val",
            "group": None,
            "title": "No Group",
            "xlabel": "Category",
            "ylabel": "Value",
            "show_error_bars": False,
        }
        fig = plot.create_figure(data, config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1  # Single trace
        assert fig.layout.barmode == "group"

    def test_no_group_with_error_bars(self, plot: GroupedBarPlot) -> None:
        """No-group with error bars uses sd column."""
        data = pd.DataFrame({"Cat": ["A", "B"], "Val": [10, 20], "Val.sd": [1, 2]})
        config = {
            "x": "Cat",
            "y": "Val",
            "group": None,
            "title": "Err",
            "show_error_bars": True,
        }
        fig = plot.create_figure(data, config)
        assert fig.data[0].error_y is not None
        assert fig.data[0].error_y.visible is True

    def test_no_group_error_bars_no_sd_column(self, plot: GroupedBarPlot) -> None:
        """No-group with error bars but no .sd column → error_y has no array."""
        data = pd.DataFrame({"Cat": ["A", "B"], "Val": [10, 20]})
        config = {
            "x": "Cat",
            "y": "Val",
            "group": None,
            "title": "No SD",
            "show_error_bars": True,
        }
        fig = plot.create_figure(data, config)
        # No sd column means error_y dict is None (not set)
        error_y = fig.data[0].error_y
        assert error_y is None or error_y.array is None

    def test_no_group_empty_string(self, plot: GroupedBarPlot) -> None:
        """Empty string group is treated as no-group."""
        data = pd.DataFrame({"Cat": ["A", "B"], "Val": [10, 20]})
        config = {
            "x": "Cat",
            "y": "Val",
            "group": "",
            "title": "Empty",
            "show_error_bars": False,
        }
        fig = plot.create_figure(data, config)
        assert len(fig.data) == 1


class TestCreateFigureWithGroup:
    """Test grouped branches."""

    def test_x_filter_applied(self, plot: GroupedBarPlot, sample_data: pd.DataFrame) -> None:
        """X filter limits displayed categories."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Filtered",
            "x_filter": ["Bench1"],
            "show_error_bars": False,
        }
        fig = plot.create_figure(sample_data, config)
        tick_text = list(fig.layout.xaxis.ticktext)
        assert "Bench1" in tick_text
        assert "Bench2" not in tick_text

    def test_group_filter_applied(self, plot: GroupedBarPlot, sample_data: pd.DataFrame) -> None:
        """Group filter limits displayed groups."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Filtered",
            "group_filter": ["X"],
            "show_error_bars": False,
        }
        fig = plot.create_figure(sample_data, config)
        assert len(fig.data) == 1  # Only group X

    def test_xaxis_order(self, plot: GroupedBarPlot, sample_data: pd.DataFrame) -> None:
        """Custom xaxis_order is respected."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Ordered",
            "xaxis_order": ["Bench2", "Bench1"],
            "show_error_bars": False,
        }
        fig = plot.create_figure(sample_data, config)
        tick_text = list(fig.layout.xaxis.ticktext)
        assert tick_text == ["Bench2", "Bench1"]

    def test_group_order(self, plot: GroupedBarPlot, sample_data: pd.DataFrame) -> None:
        """Custom group_order is respected."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Ordered",
            "group_order": ["Y", "X"],
            "show_error_bars": False,
        }
        fig = plot.create_figure(sample_data, config)
        # Trace names should follow order
        assert fig.data[0].name == "Y"
        assert fig.data[1].name == "X"

    def test_group_with_error_bars(self, plot: GroupedBarPlot, sample_data: pd.DataFrame) -> None:
        """Grouped with error bars."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Err",
            "show_error_bars": True,
        }
        fig = plot.create_figure(sample_data, config)
        for trace in fig.data:
            assert trace.error_y is not None

    def test_shapes_config_combined(self, plot: GroupedBarPlot, sample_data: pd.DataFrame) -> None:
        """User shapes and distinction shapes are combined."""
        user_shape = dict(type="line", x0=0, x1=5, y0=0, y1=1)
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Shapes",
            "shapes": [user_shape],
            "show_error_bars": False,
        }
        fig = plot.create_figure(sample_data, config)
        shapes = list(fig.layout.shapes)
        assert len(shapes) >= 1

    def test_shapes_config_non_list(self, plot: GroupedBarPlot, sample_data: pd.DataFrame) -> None:
        """Non-list shapes handled gracefully."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Bad",
            "shapes": "invalid",
            "show_error_bars": False,
        }
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)

    def test_legend_title_from_group(self, plot: GroupedBarPlot, sample_data: pd.DataFrame) -> None:
        """Legend title defaults to group column name."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Title",
            "show_error_bars": False,
        }
        fig = plot.create_figure(sample_data, config)
        assert fig.layout.legend.title.text == "Group"
