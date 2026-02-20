"""
Integration tests for the Matplotlib rendering path.

Validates the full pipeline:
  Plotly figure → PlotlyTraceExtractor → MatplotlibTraceRenderer → matplotlib Figure
"""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import matplotlib
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from src.core.models.visualization.resolvers import resolve_config
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.web.rendering.matplotlib_connector import (
    FigureSpecToMatplotlib,
)
from src.web.rendering.matplotlib_trace_renderer import (
    MatplotlibTraceRenderer,
)
from src.web.rendering.plotly_trace_extractor import (
    PlotlyTraceExtractor,
)

# Use non-interactive backend for tests
matplotlib.use("Agg")


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_bar_figure() -> go.Figure:
    """Create a simple grouped bar Plotly figure."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["A", "B", "C"], y=[10, 20, 30], name="Series 1"))
    fig.add_trace(go.Bar(x=["A", "B", "C"], y=[15, 25, 35], name="Series 2"))
    fig.update_layout(barmode="group")
    return fig


def _make_line_figure() -> go.Figure:
    """Create a simple line Plotly figure."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[10, 20, 30], mode="lines", name="Line 1"))
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[15, 25, 35], mode="lines", name="Line 2"))
    return fig


def _make_scatter_figure() -> go.Figure:
    """Create a simple scatter Plotly figure."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[10, 20, 30], mode="markers", name="Scatter 1"))
    return fig


def _make_stacked_bar_figure() -> go.Figure:
    """Create a stacked bar Plotly figure."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["X", "Y"], y=[10, 20], name="Bottom"))
    fig.add_trace(go.Bar(x=["X", "Y"], y=[5, 15], name="Top"))
    fig.update_layout(barmode="stack")
    return fig


def _minimal_config() -> Dict[str, Any]:
    """Return a minimal config dict for ConfigSpecBuilder."""
    return {
        "title": "Test Plot",
        "x_label": "X Axis",
        "y_label": "Y Axis",
        "width": 800,
        "height": 500,
    }


# ─── MatplotlibTraceRenderer Tests ──────────────────────────────────────────


class TestMatplotlibTraceRenderer:
    """Test trace conversion from TraceConfig → matplotlib artists."""

    def test_render_bar_traces(self) -> None:
        """Bar traces should produce matplotlib bar containers."""
        plotly_fig = _make_bar_figure()
        traces = PlotlyTraceExtractor.extract(plotly_fig)
        barmode = PlotlyTraceExtractor.extract_barmode(plotly_fig)
        fig, ax = plt.subplots()

        count = MatplotlibTraceRenderer.render(traces, ax, barmode=barmode)

        assert count == 2
        assert len(ax.containers) >= 2
        plt.close(fig)

    def test_render_line_traces(self) -> None:
        """Line traces should produce matplotlib Line2D artists."""
        plotly_fig = _make_line_figure()
        traces = PlotlyTraceExtractor.extract(plotly_fig)
        fig, ax = plt.subplots()

        count = MatplotlibTraceRenderer.render(traces, ax)

        assert count == 2
        assert len(ax.lines) >= 2
        plt.close(fig)

    def test_render_scatter_traces(self) -> None:
        """Scatter traces should produce matplotlib PathCollection."""
        plotly_fig = _make_scatter_figure()
        traces = PlotlyTraceExtractor.extract(plotly_fig)
        fig, ax = plt.subplots()

        count = MatplotlibTraceRenderer.render(traces, ax)

        assert count == 1
        assert len(ax.collections) >= 1
        plt.close(fig)

    def test_render_stacked_bars(self) -> None:
        """Stacked bars should have proper bottom offsets."""
        plotly_fig = _make_stacked_bar_figure()
        traces = PlotlyTraceExtractor.extract(plotly_fig)
        barmode = PlotlyTraceExtractor.extract_barmode(plotly_fig)
        fig, ax = plt.subplots()

        count = MatplotlibTraceRenderer.render(traces, ax, barmode=barmode)

        assert count == 2
        assert len(ax.containers) == 2
        plt.close(fig)

    def test_render_empty_figure(self) -> None:
        """Empty trace list should return 0."""
        fig, ax = plt.subplots()

        count = MatplotlibTraceRenderer.render([], ax)

        assert count == 0
        plt.close(fig)

    def test_secondary_yaxis(self) -> None:
        """Traces on y2 should create a twin axis."""
        plotly_fig = go.Figure()
        plotly_fig.add_trace(go.Bar(x=["A"], y=[10], name="Primary"))
        plotly_fig.add_trace(
            go.Scatter(x=["A"], y=[0.5], mode="markers", name="Secondary", yaxis="y2")
        )
        traces = PlotlyTraceExtractor.extract(plotly_fig)

        fig, ax = plt.subplots()
        count = MatplotlibTraceRenderer.render(traces, ax)

        assert count == 2
        assert hasattr(ax, "_ring5_twin")
        plt.close(fig)

    def test_line_dash_styles(self) -> None:
        """Plotly dash styles should map to matplotlib linestyles."""
        plotly_fig = go.Figure()
        plotly_fig.add_trace(
            go.Scatter(
                x=[1, 2],
                y=[1, 2],
                mode="lines",
                name="dashed",
                line={"dash": "dash"},
            )
        )
        traces = PlotlyTraceExtractor.extract(plotly_fig)
        fig, ax = plt.subplots()

        count = MatplotlibTraceRenderer.render(traces, ax)

        assert count == 1
        line = ax.lines[0]
        assert line.get_linestyle() == "--"
        plt.close(fig)

    def test_color_normalization(self) -> None:
        """Plotly rgb() colors should be converted to hex via extractor."""
        plotly_fig = go.Figure()
        plotly_fig.add_trace(
            go.Bar(
                x=["A"],
                y=[10],
                name="Coloured",
                marker={"color": "rgb(102, 194, 165)"},
            )
        )
        traces = PlotlyTraceExtractor.extract(plotly_fig)
        fig, ax = plt.subplots()

        MatplotlibTraceRenderer.render(traces, ax)

        container = ax.containers[0]
        patches = container.patches
        assert len(patches) == 1
        fc = patches[0].get_facecolor()
        assert fc[0] < 0.5  # R channel ~0.4
        plt.close(fig)


# ─── Full Pipeline Integration ───────────────────────────────────────────────


class TestMatplotlibFullPipeline:
    """Test the complete FigureConfig → matplotlib pipeline."""

    def test_bar_pipeline(self) -> None:
        """Config + Plotly bar figure → styled matplotlib figure."""
        config = _minimal_config()
        config["title"] = "Bar Chart"
        plotly_fig = _make_bar_figure()

        spec = ConfigSpecBuilder.from_config(config, "bar")
        spec = resolve_config(spec)

        traces = PlotlyTraceExtractor.extract(plotly_fig)
        barmode = PlotlyTraceExtractor.extract_barmode(plotly_fig)

        mpl_fig, ax = FigureSpecToMatplotlib.create_figure(spec)
        MatplotlibTraceRenderer.render(traces, ax, barmode=barmode)
        FigureSpecToMatplotlib.apply(spec, ax)

        assert isinstance(mpl_fig, Figure)
        assert isinstance(ax, Axes)
        assert ax.get_title() == "Bar Chart"
        assert len(ax.containers) >= 2
        plt.close(mpl_fig)

    def test_line_pipeline(self) -> None:
        """Config + Plotly line figure → styled matplotlib figure."""
        config = _minimal_config()
        config["title"] = "Line Plot"
        plotly_fig = _make_line_figure()

        spec = ConfigSpecBuilder.from_config(config, "line")
        spec = resolve_config(spec)

        traces = PlotlyTraceExtractor.extract(plotly_fig)

        mpl_fig, ax = FigureSpecToMatplotlib.create_figure(spec)
        MatplotlibTraceRenderer.render(traces, ax)
        FigureSpecToMatplotlib.apply(spec, ax)

        assert isinstance(mpl_fig, Figure)
        assert ax.get_title() == "Line Plot"
        assert len(ax.lines) >= 2
        plt.close(mpl_fig)

    def test_scatter_pipeline(self) -> None:
        """Config + Plotly scatter figure → styled matplotlib figure."""
        config = _minimal_config()
        config["title"] = "Scatter Plot"
        plotly_fig = _make_scatter_figure()

        spec = ConfigSpecBuilder.from_config(config, "scatter")
        spec = resolve_config(spec)

        traces = PlotlyTraceExtractor.extract(plotly_fig)

        mpl_fig, ax = FigureSpecToMatplotlib.create_figure(spec)
        MatplotlibTraceRenderer.render(traces, ax)
        FigureSpecToMatplotlib.apply(spec, ax)

        assert isinstance(mpl_fig, Figure)
        assert ax.get_title() == "Scatter Plot"
        assert len(ax.collections) >= 1
        plt.close(mpl_fig)

    def test_dimensions_from_spec(self) -> None:
        """FigureConfig dimensions should control matplotlib figure size."""
        config = _minimal_config()
        config["width"] = 1000
        config["height"] = 600

        spec = ConfigSpecBuilder.from_config(config, "bar")
        spec = resolve_config(spec)

        mpl_fig, ax = FigureSpecToMatplotlib.create_figure(spec)

        w, h = mpl_fig.get_size_inches()
        assert w > 0
        assert h > 0
        plt.close(mpl_fig)


# ─── PlotRenderer._render_matplotlib integration ─────────────────────────────


class TestRendererMatplotlibBranch:
    """Test the _render_matplotlib static method via PlotRenderer."""

    @patch("src.web.pages.ui.plotting.plot_renderer.render_download_section")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    def test_render_matplotlib_calls_pyplot(
        self, mock_st: MagicMock, mock_download: MagicMock
    ) -> None:
        """_render_matplotlib should call st.pyplot with a Figure."""
        from src.web.pages.ui.plotting.plot_renderer import PlotRenderer

        mock_st.session_state = {}

        plot = MagicMock()
        plot.plot_id = 1
        plot.config = _minimal_config()
        plot.plot_type = "bar"

        plotly_fig = _make_bar_figure()

        PlotRenderer._render_matplotlib(plot, plotly_fig)

        mock_st.pyplot.assert_called_once()
        args, _ = mock_st.pyplot.call_args
        assert isinstance(args[0], Figure)

    @patch("src.web.pages.ui.plotting.plot_renderer.render_download_section")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    def test_render_matplotlib_stores_fig_in_state(
        self, mock_st: MagicMock, mock_download: MagicMock
    ) -> None:
        """Matplotlib figure should be stored in session state for download."""
        from src.web.pages.ui.plotting.plot_renderer import PlotRenderer

        state: Dict[str, Any] = {}
        mock_st.session_state = state

        plot = MagicMock()
        plot.plot_id = 7
        plot.config = _minimal_config()
        plot.plot_type = "bar"

        plotly_fig = _make_bar_figure()

        PlotRenderer._render_matplotlib(plot, plotly_fig)

        assert "plot.7.mpl_fig" in state
        assert isinstance(state["plot.7.mpl_fig"], Figure)
