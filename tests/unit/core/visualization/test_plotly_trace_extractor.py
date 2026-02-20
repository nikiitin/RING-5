"""Tests for PlotlyTraceExtractor — Plotly go.Figure → TraceConfig conversion."""

from __future__ import annotations

import plotly.graph_objects as go

from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
)
from src.core.visualization.connectors.plotly_trace_extractor import (
    PlotlyTraceExtractor,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_bar_fig(barmode: str = "group") -> go.Figure:
    """Create a simple bar figure with two traces."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["a", "b", "c"], y=[1, 2, 3], name="series_1"))
    fig.add_trace(go.Bar(x=["a", "b", "c"], y=[4, 5, 6], name="series_2"))
    fig.update_layout(barmode=barmode)
    return fig


def _make_numeric_bar_fig() -> go.Figure:
    """Create a bar figure with numeric x-positions."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[1.0, 2.0, 3.0], y=[10, 20, 30], name="num_bars"))
    return fig


def _make_stacked_bar_fig() -> go.Figure:
    """Create a stacked bar figure."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["a", "b"], y=[10, 20], name="bottom"))
    fig.add_trace(go.Bar(x=["a", "b"], y=[5, 8], name="top"))
    fig.update_layout(barmode="stack")
    return fig


def _make_line_fig() -> go.Figure:
    """Create a line figure."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[1, 2, 3],
            y=[10, 20, 30],
            mode="lines+markers",
            name="line_1",
            line={"color": "rgb(255,0,0)", "width": 3, "dash": "dash"},
            marker={"size": 10, "symbol": "square"},
        )
    )
    return fig


def _make_scatter_fig() -> go.Figure:
    """Create a scatter figure (markers only)."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[1, 2, 3],
            y=[10, 20, 30],
            mode="markers",
            name="scatter_1",
            marker={"color": "#00FF00", "size": 12, "symbol": "diamond"},
        )
    )
    return fig


def _make_histogram_fig() -> go.Figure:
    """Create a histogram figure."""
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=[1, 2, 2, 3, 3, 3, 4, 4, 5], name="hist_1", nbinsx=5))
    return fig


def _make_mixed_fig() -> go.Figure:
    """Create a figure with bar + scatter traces (dual axis scenario)."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["a", "b"], y=[10, 20], name="bars"))
    fig.add_trace(
        go.Scatter(
            x=["a", "b"],
            y=[0.5, 0.8],
            mode="markers",
            name="dots",
            yaxis="y2",
        )
    )
    return fig


# ── Test: bar extraction ─────────────────────────────────────────────────────


class TestBarExtraction:
    """Tests for go.Bar → BarTraceConfig conversion."""

    def test_basic_categorical(self) -> None:
        fig = _make_bar_fig("group")
        specs = PlotlyTraceExtractor.extract(fig)
        assert len(specs) == 2
        assert all(isinstance(s, BarTraceConfig) for s in specs)
        assert specs[0].name == "series_1"
        assert specs[1].name == "series_2"
        assert specs[0].x == ["a", "b", "c"]
        assert specs[0].y == [1.0, 2.0, 3.0]

    def test_grouped_positions(self) -> None:
        fig = _make_bar_fig("group")
        specs = PlotlyTraceExtractor.extract(fig)
        s1 = specs[0]
        s2 = specs[1]
        assert isinstance(s1, BarTraceConfig)
        assert isinstance(s2, BarTraceConfig)
        # Grouped bars should have different x_positions
        assert s1.x_positions != s2.x_positions
        # Bar width should be 0.8 / 2 = 0.4
        assert abs(s1.bar_width - 0.4) < 0.01

    def test_stacked_positions(self) -> None:
        fig = _make_stacked_bar_fig()
        specs = PlotlyTraceExtractor.extract(fig)
        s1 = specs[0]
        s2 = specs[1]
        assert isinstance(s1, BarTraceConfig)
        assert isinstance(s2, BarTraceConfig)
        # Stacked bars share x_positions
        assert s1.x_positions == s2.x_positions
        assert s1.bar_width == 0.8

    def test_numeric_x(self) -> None:
        fig = _make_numeric_bar_fig()
        specs = PlotlyTraceExtractor.extract(fig)
        assert len(specs) == 1
        s = specs[0]
        assert isinstance(s, BarTraceConfig)
        assert s.x_positions == [1.0, 2.0, 3.0]

    def test_bar_with_marker_color(self) -> None:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["a"],
                y=[10],
                name="colored",
                marker={"color": "rgb(255,128,0)"},
            )
        )
        specs = PlotlyTraceExtractor.extract(fig)
        s = specs[0]
        assert isinstance(s, BarTraceConfig)
        assert s.color == "#ff8000"

    def test_bar_with_pattern(self) -> None:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["a"],
                y=[10],
                name="hatched",
                marker={"pattern": {"shape": "/"}},
            )
        )
        specs = PlotlyTraceExtractor.extract(fig)
        s = specs[0]
        assert isinstance(s, BarTraceConfig)
        assert s.pattern == "/"

    def test_bar_with_error_y(self) -> None:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["a", "b"],
                y=[10, 20],
                name="errs",
                error_y={"type": "data", "array": [1.5, 2.5]},
            )
        )
        specs = PlotlyTraceExtractor.extract(fig)
        s = specs[0]
        assert isinstance(s, BarTraceConfig)
        assert s.error_y is not None
        assert len(s.error_y) == 2
        assert abs(s.error_y[0] - 1.5) < 0.01


# ── Test: line extraction ────────────────────────────────────────────────────


class TestLineExtraction:
    """Tests for go.Scatter(mode='lines*') → LineTraceConfig."""

    def test_basic_line(self) -> None:
        fig = _make_line_fig()
        specs = PlotlyTraceExtractor.extract(fig)
        assert len(specs) == 1
        s = specs[0]
        assert isinstance(s, LineTraceConfig)
        assert s.name == "line_1"
        assert s.y == [10.0, 20.0, 30.0]

    def test_line_properties(self) -> None:
        fig = _make_line_fig()
        specs = PlotlyTraceExtractor.extract(fig)
        s = specs[0]
        assert isinstance(s, LineTraceConfig)
        assert s.color == "#ff0000"
        assert s.line_width == 3.0
        assert s.line_dash == "dash"
        assert s.show_markers is True
        assert s.marker_size == 10
        assert s.marker_symbol == "square"

    def test_lines_only_mode(self) -> None:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2], y=[3, 4], mode="lines", name="lines_only"))
        specs = PlotlyTraceExtractor.extract(fig)
        s = specs[0]
        assert isinstance(s, LineTraceConfig)
        assert s.show_markers is False


# ── Test: scatter extraction ─────────────────────────────────────────────────


class TestScatterExtraction:
    """Tests for go.Scatter(mode='markers') → ScatterTraceConfig."""

    def test_basic_scatter(self) -> None:
        fig = _make_scatter_fig()
        specs = PlotlyTraceExtractor.extract(fig)
        assert len(specs) == 1
        s = specs[0]
        assert isinstance(s, ScatterTraceConfig)
        assert s.name == "scatter_1"
        assert s.color == "#00FF00"
        assert s.marker_size == 12
        assert s.marker_symbol == "diamond"

    def test_scatter_yaxis(self) -> None:
        fig = _make_mixed_fig()
        specs = PlotlyTraceExtractor.extract(fig)
        scatter = [s for s in specs if isinstance(s, ScatterTraceConfig)]
        assert len(scatter) == 1
        assert scatter[0].yaxis == "y2"


# ── Test: histogram extraction ───────────────────────────────────────────────


class TestHistogramExtraction:
    """Tests for go.Histogram → HistogramTraceConfig."""

    def test_basic_histogram(self) -> None:
        fig = _make_histogram_fig()
        specs = PlotlyTraceExtractor.extract(fig)
        assert len(specs) == 1
        s = specs[0]
        assert isinstance(s, HistogramTraceConfig)
        assert s.name == "hist_1"
        assert s.nbins == 5


# ── Test: mixed figures ──────────────────────────────────────────────────────


class TestMixedFigures:
    """Tests for figures with multiple trace types."""

    def test_bar_and_scatter(self) -> None:
        fig = _make_mixed_fig()
        specs = PlotlyTraceExtractor.extract(fig)
        assert len(specs) == 2
        assert isinstance(specs[0], BarTraceConfig)
        assert isinstance(specs[1], ScatterTraceConfig)

    def test_extract_barmode(self) -> None:
        fig = _make_stacked_bar_fig()
        assert PlotlyTraceExtractor.extract_barmode(fig) == "stack"

    def test_extract_barmode_default(self) -> None:
        fig = go.Figure()
        assert PlotlyTraceExtractor.extract_barmode(fig) == "group"


# ── Test: edge cases ─────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge cases and robustness tests."""

    def test_empty_figure(self) -> None:
        fig = go.Figure()
        specs = PlotlyTraceExtractor.extract(fig)
        assert specs == []

    def test_none_values_in_y(self) -> None:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["a", "b"], y=[10, None], name="nones"))
        specs = PlotlyTraceExtractor.extract(fig)
        s = specs[0]
        assert isinstance(s, BarTraceConfig)
        assert s.y == [10.0, 0.0]

    def test_showlegend_false(self) -> None:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["a"], y=[10], name="hidden", showlegend=False))
        specs = PlotlyTraceExtractor.extract(fig)
        assert specs[0].show_in_legend is False

    def test_legendgroup(self) -> None:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1], y=[2], mode="markers", name="g1", legendgroup="group_A"))
        specs = PlotlyTraceExtractor.extract(fig)
        assert specs[0].legendgroup == "group_A"

    def test_rgba_color_normalisation(self) -> None:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["a"],
                y=[10],
                name="rgba",
                marker={"color": "rgba(100, 200, 50, 0.7)"},
            )
        )
        specs = PlotlyTraceExtractor.extract(fig)
        s = specs[0]
        assert isinstance(s, BarTraceConfig)
        assert s.color == "#64c832"
