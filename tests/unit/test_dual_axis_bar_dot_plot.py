"""Tests for the DualAxisBarDot plot type."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot import DualAxisBarDotPlot


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Sample data with two numeric columns suitable for dual-axis plotting."""
    return pd.DataFrame(
        {
            "Benchmark": ["A", "A", "B", "B", "C", "C"],
            "Config": ["Low", "High", "Low", "High", "Low", "High"],
            "CycleCount": [1000, 2000, 1500, 2500, 1200, 1800],
            "IPC": [1.2, 0.9, 1.5, 1.1, 1.3, 0.8],
            "CycleCount.sd": [50, 100, 75, 120, 60, 90],
            "IPC.sd": [0.05, 0.04, 0.06, 0.05, 0.04, 0.03],
        }
    )


@pytest.fixture
def base_config() -> dict:
    """Base configuration for dual-axis plot."""
    return {
        "x": "Benchmark",
        "y_bar": "CycleCount",
        "y_dot": "IPC",
        "color": "Config",
        "title": "Cycles vs IPC",
        "xlabel": "Benchmark",
        "ylabel_bar": "Cycle Count",
        "ylabel_dot": "IPC",
        "show_error_bars": False,
        "show_lines": True,
        "dot_size": 10,
        "dot_symbol": "circle",
        "line_width": 2,
    }


class TestDualAxisBarDotPlotInitialization:
    """Test DualAxisBarDotPlot initialization."""

    def test_initialization(self) -> None:
        """Test basic plot initialization."""
        plot = DualAxisBarDotPlot(1, "Test Dual Axis")
        assert plot.plot_id == 1
        assert plot.name == "Test Dual Axis"
        assert plot.plot_type == "dual_axis_bar_dot"
        assert plot.config == {}
        assert plot.processed_data is None

    def test_inherits_base_plot(self) -> None:
        """Test that DualAxisBarDotPlot is a proper BasePlot subclass."""
        from src.web.pages.ui.plotting.base_plot import BasePlot

        plot = DualAxisBarDotPlot(1, "Test")
        assert isinstance(plot, BasePlot)


class TestDualAxisBarDotPlotFactory:
    """Test factory registration and creation."""

    def test_factory_creates_dual_axis(self) -> None:
        """Test that PlotFactory can create a DualAxisBarDotPlot."""
        plot = PlotFactory.create_plot("dual_axis_bar_dot", 1, "Test")
        assert isinstance(plot, DualAxisBarDotPlot)
        assert plot.plot_type == "dual_axis_bar_dot"

    def test_factory_lists_dual_axis(self) -> None:
        """Test that dual_axis_bar_dot appears in available types."""
        types = PlotFactory.get_available_plot_types()
        assert "dual_axis_bar_dot" in types


class TestDualAxisBarDotPlotCreateFigure:
    """Test figure creation logic."""

    def test_create_figure_returns_figure(
        self, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Test that create_figure returns a valid Plotly figure."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        assert isinstance(fig, go.Figure)

    def test_has_bar_traces(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that figure contains bar traces."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) > 0, "Figure must contain at least one bar trace"

    def test_has_dot_traces(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that figure contains scatter (dot) traces."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(scatter_traces) > 0, "Figure must contain at least one scatter trace"

    def test_dots_always_present_with_lines(
        self, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Test that dots (markers) are always visible when lines are shown."""
        base_config["show_lines"] = True
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            # Mode should include 'markers'
            assert (
                "markers" in trace.mode
            ), f"Trace '{trace.name}' mode '{trace.mode}' must include 'markers'"

    def test_dots_present_without_lines(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that dots are shown even when lines are disabled."""
        base_config["show_lines"] = False
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            assert (
                trace.mode == "markers"
            ), f"When show_lines=False, mode should be 'markers', got '{trace.mode}'"

    def test_secondary_yaxis_present(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that the figure has a secondary y-axis for the dot series."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        # Check that scatter traces are assigned to yaxis2
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            assert (
                trace.yaxis == "y2"
            ), f"Scatter trace '{trace.name}' should use yaxis='y2', got '{trace.yaxis}'"

    def test_secondary_yaxis_layout(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that the layout includes yaxis2 configuration."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        assert fig.layout.yaxis2 is not None, "Layout must have yaxis2 defined"
        assert fig.layout.yaxis2.overlaying == "y", "yaxis2 must overlay the primary y-axis"
        assert fig.layout.yaxis2.side == "right", "yaxis2 should be on the right side"

    def test_bar_traces_on_primary_yaxis(
        self, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Test that bar traces use the primary y-axis."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        for trace in bar_traces:
            # By default, bars should use y (primary) axis
            # yaxis can be None or "y" — both mean primary
            assert (
                trace.yaxis is None or trace.yaxis == "y"
            ), f"Bar trace '{trace.name}' should use primary yaxis"


class TestDualAxisBarDotPlotColorGrouping:
    """Test color and grouping behavior."""

    def test_grouped_by_color(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that data is grouped by the color column for both bars and dots."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        # With 2 Config values (Low, High), we expect 2 bar traces + 2 dot traces
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(bar_traces) == 2, f"Expected 2 bar traces, got {len(bar_traces)}"
        assert len(scatter_traces) == 2, f"Expected 2 scatter traces, got {len(scatter_traces)}"

    def test_no_color_grouping(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test figure creation without color grouping."""
        base_config["color"] = None
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(bar_traces) == 1, f"Expected 1 bar trace, got {len(bar_traces)}"
        assert len(scatter_traces) == 1, f"Expected 1 scatter trace, got {len(scatter_traces)}"


class TestDualAxisBarDotPlotDotCustomization:
    """Test dot/marker customization options."""

    def test_dot_size_applied(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that custom dot size is applied to scatter traces."""
        base_config["dot_size"] = 15
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            assert trace.marker.size == 15

    def test_dot_symbol_applied(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that custom dot symbol is applied to scatter traces."""
        base_config["dot_symbol"] = "diamond"
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            assert trace.marker.symbol == "diamond"

    def test_dot_color_applied(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that custom dot color is applied when specified."""
        base_config["dot_color"] = "#FF0000"
        base_config["color"] = None  # No grouping to test single color
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            assert trace.marker.color == "#FF0000"

    def test_line_width_applied(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that custom line width is applied when lines are shown."""
        base_config["show_lines"] = True
        base_config["line_width"] = 4
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            assert trace.line.width == 4

    def test_default_dot_size(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that default dot size is applied when not specified."""
        del base_config["dot_size"]
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            assert trace.marker.size == 10  # Default size should be 10

    def test_default_dot_symbol(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that default dot symbol is circle."""
        del base_config["dot_symbol"]
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            assert trace.marker.symbol == "circle"


class TestDualAxisBarDotPlotErrorBars:
    """Test error bar support."""

    def test_bar_error_bars(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test error bars on bar traces when enabled."""
        base_config["show_error_bars"] = True
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        for trace in bar_traces:
            assert trace.error_y is not None
            assert trace.error_y.visible is True

    def test_dot_error_bars(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test error bars on dot traces when enabled."""
        base_config["show_error_bars"] = True
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            assert trace.error_y is not None
            assert trace.error_y.visible is True


class TestDualAxisBarDotPlotLegend:
    """Test legend behavior."""

    def test_get_legend_column(self) -> None:
        """Test getting legend column."""
        plot = DualAxisBarDotPlot(1, "Test")
        assert plot.get_legend_column({"color": "Config"}) == "Config"
        assert plot.get_legend_column({"color": None}) is None
        assert plot.get_legend_column({}) is None

    def test_legend_group_pairing(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that bar and dot traces with the same group have matching legendgroup."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]

        bar_groups = {t.legendgroup for t in bar_traces}
        scatter_groups = {t.legendgroup for t in scatter_traces}
        # The groups should match (same color categories)
        assert (
            bar_groups == scatter_groups
        ), f"Bar groups {bar_groups} should match scatter groups {scatter_groups}"


class TestDualAxisBarDotPlotSerialization:
    """Test serialization / deserialization."""

    def test_to_dict(self, sample_data: pd.DataFrame) -> None:
        """Test serialization preserves plot_type."""
        plot = DualAxisBarDotPlot(1, "Test Dual")
        plot.processed_data = sample_data
        plot.config = {"x": "Benchmark", "y_bar": "CycleCount", "y_dot": "IPC"}
        data_dict = plot.to_dict()
        assert data_dict["plot_type"] == "dual_axis_bar_dot"
        assert data_dict["id"] == 1
        assert data_dict["name"] == "Test Dual"

    def test_from_dict_roundtrip(self, sample_data: pd.DataFrame) -> None:
        """Test round-trip serialization."""
        from src.web.pages.ui.plotting.base_plot import BasePlot

        plot = DualAxisBarDotPlot(1, "Test Dual")
        plot.processed_data = sample_data
        plot.config = {"x": "Benchmark", "y_bar": "CycleCount", "y_dot": "IPC"}
        data_dict = plot.to_dict()
        restored = BasePlot.from_dict(data_dict)
        assert isinstance(restored, DualAxisBarDotPlot)
        assert restored.plot_type == "dual_axis_bar_dot"
        assert restored.config == plot.config


class TestDualAxisBarDotPlotIsolateLastGroup:
    """Test isolate_last_group behavior on dot traces."""

    def test_isolated_last_no_line_to_last(
        self, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """When isolate_last_group=True, the last x-category dot must be markers-only."""
        base_config["isolate_last_group"] = True
        base_config["show_lines"] = True
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]

        # There should be extra traces for the isolated last element
        # With color grouping (2 groups) we expect:
        #   2 main scatter traces (lines+markers) + 2 isolated dot traces (markers only)
        main_traces = [t for t in scatter_traces if t.mode == "lines+markers"]
        isolated_traces = [t for t in scatter_traces if t.mode == "markers"]
        assert len(main_traces) == 2, f"Expected 2 main traces, got {len(main_traces)}"
        assert len(isolated_traces) == 2, f"Expected 2 isolated traces, got {len(isolated_traces)}"

    def test_isolated_last_markers_only_no_color(
        self, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Without color grouping, isolation still splits last category."""
        base_config["isolate_last_group"] = True
        base_config["show_lines"] = True
        base_config["color"] = None
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]

        main_traces = [t for t in scatter_traces if t.mode == "lines+markers"]
        isolated_traces = [t for t in scatter_traces if t.mode == "markers"]
        assert len(main_traces) == 1
        assert len(isolated_traces) == 1

    def test_no_isolation_all_lines(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """When isolate_last_group=False, all dots have lines."""
        base_config["isolate_last_group"] = False
        base_config["show_lines"] = True
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            assert trace.mode == "lines+markers"

    def test_isolation_with_lines_off(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """When show_lines=False, isolation has no extra effect — all are markers."""
        base_config["isolate_last_group"] = True
        base_config["show_lines"] = False
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for trace in scatter_traces:
            assert trace.mode == "markers"

    def test_isolated_dot_has_same_legendgroup(
        self, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Isolated dot traces share legendgroup with their bar counterparts."""
        base_config["isolate_last_group"] = True
        base_config["show_lines"] = True
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]

        bar_groups = {t.legendgroup for t in bar_traces}
        scatter_groups = {t.legendgroup for t in scatter_traces}
        assert bar_groups == scatter_groups

    def test_isolated_dot_showlegend_false(
        self, sample_data: pd.DataFrame, base_config: dict
    ) -> None:
        """Isolated dot traces should not create duplicate legend entries."""
        base_config["isolate_last_group"] = True
        base_config["show_lines"] = True
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        isolated_traces = [t for t in scatter_traces if t.mode == "markers"]
        for trace in isolated_traces:
            assert (
                trace.showlegend is False
            ), f"Isolated trace '{trace.name}' should have showlegend=False"


class TestDualAxisBarDotPlotAxisLabels:
    """Test axis labeling."""

    def test_bar_yaxis_label(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that the primary Y-axis label comes from ylabel_bar."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        assert fig.layout.yaxis.title.text == "Cycle Count"

    def test_dot_yaxis_label(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that the secondary Y-axis label comes from ylabel_dot."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        assert fig.layout.yaxis2.title.text == "IPC"

    def test_title_applied(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that the title is correctly applied."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        assert fig.layout.title.text == "Cycles vs IPC"

    def test_xlabel_applied(self, sample_data: pd.DataFrame, base_config: dict) -> None:
        """Test that the x-axis label is correctly applied."""
        plot = DualAxisBarDotPlot(1, "Test")
        fig = plot.create_figure(sample_data, base_config)
        assert fig.layout.xaxis.title.text == "Benchmark"
