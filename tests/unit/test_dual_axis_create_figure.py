"""Tests for DualAxisBarDotPlot.create_figure — all execution branches."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot import DualAxisBarDotPlot


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Benchmark": ["A", "A", "B", "B", "Mean", "Mean"],
            "Config": ["c1", "c2", "c1", "c2", "c1", "c2"],
            "Ticks": [100, 200, 150, 250, 125, 225],
            "IPC": [1.5, 1.2, 1.8, 1.0, 1.65, 1.1],
            "Ticks.sd": [5, 10, 7, 12, 3, 6],
            "IPC.sd": [0.1, 0.2, 0.15, 0.3, 0.05, 0.1],
        }
    )


@pytest.fixture
def plot() -> DualAxisBarDotPlot:
    return DualAxisBarDotPlot(1, "Test")


@pytest.fixture
def base_config() -> dict:
    return {
        "x": "Benchmark",
        "y_bar": "Ticks",
        "y_dot": "IPC",
        "title": "Test",
        "xlabel": "Bench",
        "ylabel_bar": "Ticks",
        "ylabel_dot": "IPC",
        "show_lines": True,
        "dot_size": 10,
        "dot_symbol": "circle",
        "line_width": 2,
    }


class TestNoColorGrouping:
    """Test single-trace (no color) branches."""

    def test_basic_no_color(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Basic dual-axis with no color grouping."""
        fig = plot.create_figure(sample_data, base_config)
        assert isinstance(fig, go.Figure)
        # 1 bar trace + 1 scatter trace
        assert len(fig.data) == 2
        assert isinstance(fig.data[0], go.Bar)
        assert isinstance(fig.data[1], go.Scatter)

    def test_no_lines(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """show_lines=False creates markers-only scatter."""
        base_config["show_lines"] = False
        fig = plot.create_figure(sample_data, base_config)
        scatter = fig.data[1]
        assert scatter.mode == "markers"

    def test_with_dot_color(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Explicit dot_color is applied to marker."""
        base_config["dot_color"] = "#FF0000"
        fig = plot.create_figure(sample_data, base_config)
        scatter = fig.data[1]
        assert scatter.marker.color == "#FF0000"

    def test_with_error_bars(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Error bars from .sd columns."""
        base_config["show_error_bars"] = True
        fig = plot.create_figure(sample_data, base_config)
        assert fig.data[0].error_y is not None  # Bar error
        assert fig.data[1].error_y is not None  # Dot error

    def test_isolate_last_no_color(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Isolate last category with no color → 3 traces (bar + main scatter + iso scatter)."""
        base_config["isolate_last_group"] = True
        base_config["xaxis_order"] = ["A", "B", "Mean"]
        fig = plot.create_figure(sample_data, base_config)
        # 1 bar + 1 main scatter (A,B) + 1 isolated scatter (Mean)
        assert len(fig.data) == 3
        # Isolated trace has markers-only mode
        iso_trace = fig.data[2]
        assert iso_trace.mode == "markers"
        assert iso_trace.showlegend is False

    def test_isolate_last_with_error_bars(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Isolate last + error bars on both main and isolated traces."""
        base_config["isolate_last_group"] = True
        base_config["show_error_bars"] = True
        base_config["xaxis_order"] = ["A", "B", "Mean"]
        fig = plot.create_figure(sample_data, base_config)
        # Main scatter should have error bars
        main_scatter = fig.data[1]
        assert main_scatter.error_y is not None
        # Isolated scatter should also have error bars
        iso_scatter = fig.data[2]
        assert iso_scatter.error_y is not None


class TestWithColorGrouping:
    """Test color-grouped branches."""

    def test_basic_color_grouped(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Color grouping creates bar+scatter per group."""
        base_config["color"] = "Config"
        fig = plot.create_figure(sample_data, base_config)
        # 2 groups × (1 bar + 1 scatter) = 4 traces
        assert len(fig.data) == 4
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(bar_traces) == 2
        assert len(scatter_traces) == 2

    def test_color_grouped_no_lines(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Color grouped with no lines → markers mode."""
        base_config["color"] = "Config"
        base_config["show_lines"] = False
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for s in scatter_traces:
            assert s.mode == "markers"

    def test_color_grouped_with_error_bars(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Color grouped with error bars on both bar and dot."""
        base_config["color"] = "Config"
        base_config["show_error_bars"] = True
        fig = plot.create_figure(sample_data, base_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        for bt in bar_traces:
            assert bt.error_y is not None

    def test_color_grouped_isolate_last(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Color grouped + isolate last: extra isolated scatter per group."""
        base_config["color"] = "Config"
        base_config["isolate_last_group"] = True
        base_config["xaxis_order"] = ["A", "B", "Mean"]
        fig = plot.create_figure(sample_data, base_config)
        # 2 groups × (1 bar + 1 main scatter + 1 iso scatter) = 6 traces
        assert len(fig.data) == 6
        # Isolated traces have showlegend=False
        iso_traces = [t for t in fig.data if isinstance(t, go.Scatter) and t.showlegend is False]
        assert len(iso_traces) >= 1

    def test_color_grouped_isolate_with_error_bars(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Color grouped + isolate + error bars."""
        base_config["color"] = "Config"
        base_config["isolate_last_group"] = True
        base_config["show_error_bars"] = True
        base_config["xaxis_order"] = ["A", "B", "Mean"]
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for st_trace in scatter_traces:
            assert st_trace.error_y is not None

    def test_color_grouped_custom_legend_order(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Custom legend_order changes trace ordering."""
        base_config["color"] = "Config"
        base_config["legend_order"] = ["c2", "c1"]
        fig = plot.create_figure(sample_data, base_config)
        # First bar trace should be c2
        assert "c2" in fig.data[0].name


class TestLayout:
    """Test layout configuration."""

    def test_layout_titles(
        self, plot: DualAxisBarDotPlot, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Layout has correct titles."""
        fig = plot.create_figure(sample_data, base_config)
        assert fig.layout.title.text == "Test"
        assert fig.layout.barmode == "group"

    def test_get_legend_column(self, plot: DualAxisBarDotPlot) -> None:
        assert plot.get_legend_column({"color": "Config"}) == "Config"
        assert plot.get_legend_column({}) is None
        assert plot.get_legend_column({"color": None}) is None
