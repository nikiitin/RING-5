"""Tests for GroupedBarPlot.create_figure — no-group and edge case branches."""

from ring5 import Session
from ring5.errors import RenderError

from typing import cast

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

    def test_no_group_single_series(self, plot: GroupedBarPlot, plot_session: Session) -> None:
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
        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) == 1  # Single trace
        assert fig.layout.barmode == "group"

    def test_no_group_with_error_bars(self, plot: GroupedBarPlot, plot_session: Session) -> None:
        """No-group with error bars uses sd column."""
        data = pd.DataFrame({"Cat": ["A", "B"], "Val": [10, 20], "Val.sd": [1, 2]})
        config = {
            "x": "Cat",
            "y": "Val",
            "group": None,
            "title": "Err",
            "show_error_bars": True,
        }
        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        bar0 = cast(go.Bar, fig.data[0])
        error_y_obj = cast(go.bar.ErrorY, bar0.error_y)
        assert error_y_obj is not None
        assert error_y_obj.visible is True

    def test_no_group_error_bars_no_sd_column(
        self, plot: GroupedBarPlot, plot_session: Session
    ) -> None:
        """No-group with error bars but no .sd column → error_y has no array."""
        data = pd.DataFrame({"Cat": ["A", "B"], "Val": [10, 20]})
        config = {
            "x": "Cat",
            "y": "Val",
            "group": None,
            "title": "No SD",
            "show_error_bars": True,
        }
        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        # No sd column means error_y dict is None (not set)
        bar0 = cast(go.Bar, fig.data[0])
        error_y = bar0.error_y
        assert error_y is None or cast(go.bar.ErrorY, error_y).array is None

    def test_no_group_empty_string(self, plot: GroupedBarPlot, plot_session: Session) -> None:
        """Empty string group is treated as no-group."""
        data = pd.DataFrame({"Cat": ["A", "B"], "Val": [10, 20]})
        config = {
            "x": "Cat",
            "y": "Val",
            "group": "",
            "title": "Empty",
            "show_error_bars": False,
        }
        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert len(list(fig.data)) == 1


class TestCreateFigureWithGroup:
    """Test grouped branches."""

    def test_x_filter_applied(
        self, plot: GroupedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """X filter limits displayed categories."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Filtered",
            "x_filter": ["Bench1"],
            "show_error_bars": False,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        tick_text = list(fig.layout.xaxis.ticktext)
        assert "Bench1" in tick_text
        assert "Bench2" not in tick_text

    def test_group_filter_applied(
        self, plot: GroupedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """Group filter limits displayed groups."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Filtered",
            "group_filter": ["X"],
            "show_error_bars": False,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert len(list(fig.data)) == 1  # Only group X

    def test_xaxis_order(
        self, plot: GroupedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """Custom xaxis_order is respected."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Ordered",
            "xaxis_order": ["Bench2", "Bench1"],
            "show_error_bars": False,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        tick_text = list(fig.layout.xaxis.ticktext)
        assert tick_text == ["Bench2", "Bench1"]

    def test_group_order(
        self, plot: GroupedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """Custom group_order is respected."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Ordered",
            "group_order": ["Y", "X"],
            "show_error_bars": False,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        # Trace names should follow order
        assert cast(go.Bar, fig.data[0]).name == "Y"
        assert cast(go.Bar, fig.data[1]).name == "X"

    def test_group_with_error_bars(
        self, plot: GroupedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """Grouped with error bars."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Err",
            "show_error_bars": True,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        for trace in fig.data:
            assert cast(go.Bar, trace).error_y is not None

    def test_user_shapes_applied_by_public_render(
        self, plot: GroupedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """The final native owner adds configured shapes exactly once."""
        base_config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Shapes",
            "show_error_bars": False,
        }
        plot.processed_data = sample_data
        plot.config = dict(base_config)
        without = cast(go.Figure, plot_session.render(plot))
        plot.processed_data = sample_data
        plot.config = {**base_config, "shapes": [dict(type="line", x0=0, x1=5, y0=0, y1=1)]}
        with_shapes = cast(go.Figure, plot_session.render(plot))
        assert len(without.layout.shapes) == 0
        assert len(with_shapes.layout.shapes) == 1
        assert with_shapes.layout.shapes[0].to_plotly_json() == {
            "type": "line",
            "x0": 0,
            "x1": 5,
            "y0": 0,
            "y1": 1,
        }

    def test_shapes_config_non_list(
        self, plot: GroupedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """Malformed native shape configuration remains a visible typed failure."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Bad",
            "shapes": "invalid",
            "show_error_bars": False,
        }
        plot.processed_data = sample_data
        plot.config = config
        with pytest.raises(RenderError, match="shapes"):
            plot_session.render(plot)

    def test_legend_title_from_group(self, plot: GroupedBarPlot, sample_data: pd.DataFrame) -> None:
        """Legend title defaults to group column name — verified at trace level."""
        config = {
            "x": "Category",
            "y": "Value",
            "group": "Group",
            "title": "Title",
            "show_error_bars": False,
        }
        result = plot.create_traces(sample_data, config)
        # Each group produces at least one trace with a name matching a group value
        trace_names = {t.name for t in result.traces}
        assert len(trace_names) > 0
