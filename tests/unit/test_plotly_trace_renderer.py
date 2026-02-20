"""Tests for PlotlyTraceRenderer — TraceSpec → go.Figure conversion."""

import plotly.graph_objects as go

from src.core.visualization.connectors.plotly_trace_renderer import PlotlyTraceRenderer
from src.core.visualization.trace_spec import (
    BarTraceSpec,
    HistogramTraceSpec,
    LineTraceSpec,
    ScatterTraceSpec,
)


class TestPlotlyTraceRendererBar:
    """Test bar trace rendering."""

    def test_simple_bar(self) -> None:
        traces = [
            BarTraceSpec(
                name="s1",
                x=["a", "b", "c"],
                y=[1.0, 2.0, 3.0],
                x_positions=[0.0, 1.0, 2.0],
                bar_width=0.8,
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == "bar"
        assert list(fig.data[0].y) == [1.0, 2.0, 3.0]

    def test_bar_with_color_and_pattern(self) -> None:
        traces = [
            BarTraceSpec(
                name="s1",
                x=["a"],
                y=[5.0],
                x_positions=[0.0],
                color="#FF0000",
                pattern="/",
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert fig.data[0].marker.color == "#FF0000"
        assert fig.data[0].marker.pattern.shape == "/"

    def test_bar_with_error_bars(self) -> None:
        traces = [
            BarTraceSpec(
                name="s1",
                x=["a", "b"],
                y=[5.0, 10.0],
                x_positions=[0.0, 1.0],
                error_y=[0.5, 1.0],
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert fig.data[0].error_y.visible is True
        assert list(fig.data[0].error_y.array) == [0.5, 1.0]

    def test_bar_with_custom_data(self) -> None:
        traces = [
            BarTraceSpec(
                name="s1",
                x=["a"],
                y=[1.0],
                x_positions=[0.0],
                custom_data={
                    "customdata": [10.0],
                    "hovertemplate": "<b>%{x}</b>",
                },
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert fig.data[0].hovertemplate == "<b>%{x}</b>"

    def test_stacked_barmode(self) -> None:
        traces = [
            BarTraceSpec(name="s1", x=["a"], y=[1.0], x_positions=[0.0]),
            BarTraceSpec(name="s2", x=["a"], y=[2.0], x_positions=[0.0]),
        ]
        fig = PlotlyTraceRenderer.build_figure(traces, barmode="stack")
        assert fig.layout.barmode == "stack"
        assert len(fig.data) == 2


class TestPlotlyTraceRendererLine:
    """Test line trace rendering."""

    def test_simple_line(self) -> None:
        traces = [
            LineTraceSpec(
                name="line1",
                x=[1, 2, 3],
                y=[10.0, 20.0, 30.0],
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert len(fig.data) == 1
        assert fig.data[0].type == "scatter"
        assert "lines" in fig.data[0].mode

    def test_line_with_markers(self) -> None:
        traces = [
            LineTraceSpec(
                name="line1",
                x=[1, 2],
                y=[10.0, 20.0],
                show_markers=True,
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert "markers" in fig.data[0].mode

    def test_line_without_markers(self) -> None:
        traces = [
            LineTraceSpec(
                name="line1",
                x=[1, 2],
                y=[10.0, 20.0],
                show_markers=False,
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert fig.data[0].mode == "lines"

    def test_line_with_dash_style(self) -> None:
        traces = [
            LineTraceSpec(
                name="line1",
                x=[1, 2],
                y=[10.0, 20.0],
                line_dash="dash",
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert fig.data[0].line.dash == "dash"

    def test_line_with_fill(self) -> None:
        traces = [
            LineTraceSpec(
                name="line1",
                x=[1, 2],
                y=[10.0, 20.0],
                fill="tozeroy",
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert fig.data[0].fill == "tozeroy"


class TestPlotlyTraceRendererScatter:
    """Test scatter trace rendering."""

    def test_simple_scatter(self) -> None:
        traces = [
            ScatterTraceSpec(
                name="scatter1",
                x=[1, 2, 3],
                y=[10.0, 20.0, 30.0],
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert len(fig.data) == 1
        assert fig.data[0].mode == "markers"

    def test_scatter_with_size_values(self) -> None:
        traces = [
            ScatterTraceSpec(
                name="scatter1",
                x=[1, 2],
                y=[10.0, 20.0],
                size_values=[5.0, 15.0],
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert list(fig.data[0].marker.size) == [5.0, 15.0]

    def test_scatter_with_colorscale(self) -> None:
        traces = [
            ScatterTraceSpec(
                name="scatter1",
                x=[1, 2],
                y=[10.0, 20.0],
                colorscale="Viridis",
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert fig.data[0].marker.colorscale is not None


class TestPlotlyTraceRendererHistogram:
    """Test histogram trace rendering."""

    def test_simple_histogram(self) -> None:
        traces = [
            HistogramTraceSpec(
                name="hist1",
                x=[1, 2, 3, 4, 5, 1, 2, 3],
                y=[],
                nbins=5,
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert len(fig.data) == 1
        assert fig.data[0].type == "histogram"

    def test_histogram_with_normalization(self) -> None:
        traces = [
            HistogramTraceSpec(
                name="hist1",
                x=[1, 2, 3],
                y=[],
                normalization="percent",
            )
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert fig.data[0].histnorm == "percent"


class TestPlotlyTraceRendererLayout:
    """Test layout configuration."""

    def test_layout_titles(self) -> None:
        traces = [BarTraceSpec(name="s1", x=["a"], y=[1.0], x_positions=[0.0])]
        fig = PlotlyTraceRenderer.build_figure(
            traces,
            title="My Title",
            xaxis_title="X Label",
            yaxis_title="Y Label",
            legend_title="Legend",
        )
        assert fig.layout.title.text == "My Title"
        assert fig.layout.xaxis.title.text == "X Label"
        assert fig.layout.yaxis.title.text == "Y Label"

    def test_palette_override(self) -> None:
        traces = [
            BarTraceSpec(name="s1", x=["a"], y=[1.0], x_positions=[0.0]),
            BarTraceSpec(name="s2", x=["a"], y=[2.0], x_positions=[0.0]),
        ]
        fig = PlotlyTraceRenderer.build_figure(
            traces,
            palette_colors=["#FF0000", "#00FF00"],
        )
        assert fig.data[0].marker.color == "#FF0000"
        assert fig.data[1].marker.color == "#00FF00"

    def test_palette_skipped_when_trace_has_color(self) -> None:
        traces = [
            BarTraceSpec(name="s1", x=["a"], y=[1.0], x_positions=[0.0], color="#0000FF"),
        ]
        fig = PlotlyTraceRenderer.build_figure(
            traces,
            palette_colors=["#FF0000"],
        )
        # Trace has explicit color → palette should NOT override
        assert fig.data[0].marker.color == "#0000FF"

    def test_extra_layout(self) -> None:
        traces = [BarTraceSpec(name="s1", x=["a"], y=[1.0], x_positions=[0.0])]
        fig = PlotlyTraceRenderer.build_figure(
            traces,
            extra_layout={
                "xaxis": {"tickmode": "array", "tickvals": [0], "ticktext": ["A"]},
            },
        )
        assert fig.layout.xaxis.tickmode == "array"
        assert list(fig.layout.xaxis.tickvals) == [0]

    def test_mixed_trace_types(self) -> None:
        traces = [
            BarTraceSpec(name="bar", x=["a"], y=[1.0], x_positions=[0.0]),
            LineTraceSpec(name="line", x=[0], y=[2.0]),
            ScatterTraceSpec(name="scat", x=[0], y=[3.0]),
        ]
        fig = PlotlyTraceRenderer.build_figure(traces)
        assert len(fig.data) == 3
        assert fig.data[0].type == "bar"
        assert fig.data[1].type == "scatter"
        assert fig.data[1].mode == "lines+markers"
        assert fig.data[2].type == "scatter"
        assert fig.data[2].mode == "markers"

    def test_empty_traces(self) -> None:
        fig = PlotlyTraceRenderer.build_figure([])
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0
