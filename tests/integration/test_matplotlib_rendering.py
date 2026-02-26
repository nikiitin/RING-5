"""
Integration tests for the Matplotlib rendering path.

Validates the full pipeline:
  Plotly figure → PlotlyTraceExtractor → MatplotlibTraceRenderer → matplotlib Figure
"""

from typing import Any, cast

import matplotlib
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.figure import Figure

from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
)
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer

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


def _minimal_config() -> dict[str, Any]:
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
        traces = [
            BarTraceConfig(
                name="Series 1",
                x=["A", "B", "C"],
                y=[10, 20, 30],
                x_positions=[-0.2, 0.8, 1.8],
                bar_width=0.4,
            ),
            BarTraceConfig(
                name="Series 2",
                x=["A", "B", "C"],
                y=[15, 25, 35],
                x_positions=[0.2, 1.2, 2.2],
                bar_width=0.4,
            ),
        ]
        barmode = "group"
        fig, ax = plt.subplots()
        assert isinstance(ax, Axes)

        count = MatplotlibTraceRenderer.render(traces, ax, barmode=barmode)

        assert count == 2
        assert len(ax.containers) >= 2
        plt.close(fig)

    def test_render_line_traces(self) -> None:
        """Line traces should produce matplotlib Line2D artists."""
        traces = [
            LineTraceConfig(name="Line 1", x=[1, 2, 3], y=[10, 20, 30]),
            LineTraceConfig(name="Line 2", x=[1, 2, 3], y=[15, 25, 35]),
        ]
        fig, ax = plt.subplots()
        assert isinstance(ax, Axes)

        count = MatplotlibTraceRenderer.render(traces, ax)

        assert count == 2
        assert len(ax.lines) >= 2
        plt.close(fig)

    def test_render_scatter_traces(self) -> None:
        """Scatter traces should produce matplotlib PathCollection."""
        traces = [
            ScatterTraceConfig(name="Scatter 1", x=[1, 2, 3], y=[10, 20, 30]),
        ]
        fig, ax = plt.subplots()
        assert isinstance(ax, Axes)

        count = MatplotlibTraceRenderer.render(traces, ax)

        assert count == 1
        assert len(ax.collections) >= 1
        plt.close(fig)

    def test_render_stacked_bars(self) -> None:
        """Stacked bars should have proper bottom offsets."""
        traces = [
            BarTraceConfig(
                name="Bottom",
                x=["X", "Y"],
                y=[10, 20],
                x_positions=[0.0, 1.0],
                bar_width=0.8,
            ),
            BarTraceConfig(
                name="Top",
                x=["X", "Y"],
                y=[5, 15],
                x_positions=[0.0, 1.0],
                bar_width=0.8,
            ),
        ]
        barmode = "stack"
        fig, ax = plt.subplots()
        assert isinstance(ax, Axes)

        count = MatplotlibTraceRenderer.render(traces, ax, barmode=barmode)

        assert count == 2
        assert len(ax.containers) == 2
        plt.close(fig)

    def test_render_empty_figure(self) -> None:
        """Empty trace list should return 0."""
        fig, ax = plt.subplots()
        assert isinstance(ax, Axes)

        count = MatplotlibTraceRenderer.render([], ax)

        assert count == 0
        plt.close(fig)

    def test_secondary_yaxis(self) -> None:
        """Traces on y2 should create a twin axis."""
        traces = [
            BarTraceConfig(
                name="Primary",
                x=["A"],
                y=[10],
                x_positions=[0.0],
                bar_width=0.8,
            ),
            ScatterTraceConfig(name="Secondary", x=["A"], y=[0.5], yaxis="y2"),
        ]

        fig, ax = plt.subplots()
        assert isinstance(ax, Axes)
        count = MatplotlibTraceRenderer.render(traces, ax)

        assert count == 2
        assert hasattr(ax, "_ring5_twin")
        plt.close(fig)

    def test_line_dash_styles(self) -> None:
        """Plotly dash styles should map to matplotlib linestyles."""
        traces = [
            LineTraceConfig(name="dashed", x=[1, 2], y=[1, 2], line_dash="dash"),
        ]
        fig, ax = plt.subplots()
        assert isinstance(ax, Axes)

        count = MatplotlibTraceRenderer.render(traces, ax)

        assert count == 1
        line = ax.lines[0]
        assert line.get_linestyle() == "--"
        plt.close(fig)

    def test_color_normalization(self) -> None:
        """Hex colour on BarTraceConfig is applied to matplotlib patch."""
        traces = [
            BarTraceConfig(
                name="Coloured",
                x=["A"],
                y=[10],
                color="#66c2a5",
                x_positions=[0.0],
                bar_width=0.8,
            ),
        ]
        fig, ax = plt.subplots()
        assert isinstance(ax, Axes)

        MatplotlibTraceRenderer.render(traces, ax)

        container = ax.containers[0]
        bar_patches = cast(BarContainer, container).patches
        assert len(bar_patches) == 1
        fc = cast(tuple[float, ...], bar_patches[0].get_facecolor())
        assert fc[0] < 0.5  # R channel ~0.4
        plt.close(fig)


# ─── Full Pipeline Integration ───────────────────────────────────────────────


class TestMatplotlibFullPipeline:
    """Test the complete FigureConfig → matplotlib pipeline."""

    def test_bar_pipeline(self) -> None:
        """Config + Plotly bar figure → styled matplotlib figure."""
        config = _minimal_config()
        config["title"] = "Bar Chart"
        spec = ConfigSpecBuilder.from_config(config, "bar")
        spec = resolve_config(spec)

        traces = [
            BarTraceConfig(
                name="Series 1",
                x=["A", "B", "C"],
                y=[10, 20, 30],
                x_positions=[-0.2, 0.8, 1.8],
                bar_width=0.4,
            ),
            BarTraceConfig(
                name="Series 2",
                x=["A", "B", "C"],
                y=[15, 25, 35],
                x_positions=[0.2, 1.2, 2.2],
                bar_width=0.4,
            ),
        ]
        barmode = "group"

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
        spec = ConfigSpecBuilder.from_config(config, "line")
        spec = resolve_config(spec)

        traces = [
            LineTraceConfig(name="Line 1", x=[1, 2, 3], y=[10, 20, 30]),
            LineTraceConfig(name="Line 2", x=[1, 2, 3], y=[15, 25, 35]),
        ]

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
        spec = ConfigSpecBuilder.from_config(config, "scatter")
        spec = resolve_config(spec)

        traces = [
            ScatterTraceConfig(name="Scatter 1", x=[1, 2, 3], y=[10, 20, 30]),
        ]

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
