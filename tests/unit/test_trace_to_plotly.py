"""Tests for trace_to_plotly — converts TraceBuildResult to go.Figure."""

from __future__ import annotations

from typing import Any, cast

import plotly.graph_objects as go

from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    BoxTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)
from src.web.rendering.trace_to_plotly import (
    _bar_trace,
    _box_trace,
    _bar_trace_from_base,
    _convert_annotations,
    _convert_trace,
    _histogram_trace,
    _line_trace,
    _scatter_trace,
    traces_to_plotly,
)

# traces_to_plotly (main entry)


class TestTracesToPlotly:
    # [test->req~ring5.render.engine-independent-traces~1]
    # [test->req~ring5.render.plotly~1]
    """Tests for the top-level ``traces_to_plotly`` function."""

    def test_empty_result_returns_figure(self) -> None:
        result = TraceBuildResult()
        fig = traces_to_plotly(result)
        assert isinstance(fig, go.Figure)
        assert len(cast(tuple[Any, ...], fig.data)) == 0

    def test_single_bar_trace(self) -> None:
        trace = BarTraceConfig(name="series1", x=["a", "b"], y=[1, 2], color="#ff0000")
        result = TraceBuildResult(traces=[trace], barmode="group")
        fig = traces_to_plotly(result)
        assert len(cast(tuple[Any, ...], fig.data)) == 1
        assert isinstance(fig.data[0], go.Bar)
        assert cast(Any, fig.layout).barmode == "group"

    def test_box_trace_sets_grouped_box_layout(self) -> None:
        trace = BoxTraceConfig(name="A", category="A", values=[1.0, 2.0, 3.0])
        fig = traces_to_plotly(TraceBuildResult(traces=[trace], boxmode="group"))
        assert isinstance(fig.data[0], go.Box)
        assert cast(Any, fig.layout).boxmode == "group"

    def test_secondary_y_creates_subplots(self) -> None:
        t1 = BarTraceConfig(name="left", x=["a"], y=[1], yaxis="y")
        t2 = BarTraceConfig(name="right", x=["a"], y=[2], yaxis="y2")
        result = TraceBuildResult(traces=[t1, t2], secondary_y=True)
        fig = traces_to_plotly(result)
        assert len(cast(tuple[Any, ...], fig.data)) == 2

    def test_custom_x_ticks_applied(self) -> None:
        result = TraceBuildResult(custom_x_ticks={"vals": [0.0, 1.0], "text": ["A", "B"]})
        fig = traces_to_plotly(result)
        layout = cast(Any, fig.layout)
        assert layout.xaxis.tickmode == "array"
        assert list(layout.xaxis.tickvals) == [0.0, 1.0]
        assert list(layout.xaxis.ticktext) == ["A", "B"]

    def test_custom_x_ticks_hide_ticks(self) -> None:
        result = TraceBuildResult(
            custom_x_ticks={
                "vals": [0.0],
                "text": ["X"],
                "hide_ticks": [True],
            }
        )
        fig = traces_to_plotly(result)
        layout = cast(Any, fig.layout)
        assert layout.xaxis.showticklabels is False
        assert layout.xaxis.ticks == ""

    def test_separators_and_shades_converted_to_shapes(self) -> None:
        from src.core.models.visualization.trace_build_result import (
            SeparatorLine,
            ShadedRegion,
        )

        result = TraceBuildResult(
            separator_lines=[SeparatorLine(x=1.5, color="#E0E0E0", dash="dash", width=1.0)],
            shaded_regions=[ShadedRegion(x0=0.0, x1=1.0, color="#F5F5F5", opacity=0.5)],
        )
        fig = traces_to_plotly(result)
        layout = cast(Any, fig.layout)
        assert layout.shapes is not None
        # One rect (shade) + one line (separator); shade drawn first.
        assert len(layout.shapes) == 2
        types = [s.type for s in layout.shapes]
        assert types == ["rect", "line"]

    def test_annotations_converted(self) -> None:
        ann = AnnotationConfig(text="Hello", x=0.5, y=0.5, xref="paper", yref="paper")
        result = TraceBuildResult(annotations=[ann])
        fig = traces_to_plotly(result)
        annotations = cast(Any, fig.layout).annotations
        assert annotations is not None
        assert len(annotations) == 1
        assert annotations[0].text == "Hello"

    def test_layout_annotations_appended(self) -> None:
        layout_ann: list[dict[str, Any]] = [{"text": "raw", "x": 0, "y": 0}]
        result = TraceBuildResult(layout_annotations=layout_ann)
        fig = traces_to_plotly(result)
        annotations = cast(Any, fig.layout).annotations
        assert annotations is not None
        assert len(annotations) == 1

    def test_both_annotation_types_combined(self) -> None:
        ann = AnnotationConfig(text="typed", x=0, y=0, xref="paper", yref="paper")
        layout_ann: list[dict[str, Any]] = [{"text": "raw", "x": 1, "y": 1}]
        result = TraceBuildResult(annotations=[ann], layout_annotations=layout_ann)
        fig = traces_to_plotly(result)
        annotations = cast(Any, fig.layout).annotations
        assert len(annotations) == 2


# _convert_trace dispatch


class TestConvertTrace:
    # [test->req~ring5.render.engine-independent-traces~1]
    """Tests for the dispatch ``_convert_trace``."""

    def test_bar_trace_dispatch(self) -> None:
        trace = BarTraceConfig(name="bar", x=["a"], y=[1])
        result = _convert_trace(trace)
        assert isinstance(result, go.Bar)

    def test_box_trace_dispatch(self) -> None:
        result = _convert_trace(BoxTraceConfig(name="box", category="A", values=[1.0]))
        assert isinstance(result, go.Box)


class TestBoxTrace:
    """Tests for the Plotly box-trace conversion contract."""

    def test_horizontal_box_controls_and_style(self) -> None:
        # [test->req~ring5.plot.box~1]
        trace = BoxTraceConfig(
            name="base",
            category="A",
            values=[1.0, 2.0, 10.0],
            orientation="horizontal",
            quartile_method="exclusive",
            lower_whisker=1.0,
            upper_whisker=2.0,
            point_mode="all",
            jitter=0.3,
            point_position=-0.2,
            box_width=0.4,
            whisker_cap_width=0.7,
            notched=True,
            show_mean=True,
            color="#ff0000",
        )

        result = _box_trace(trace)

        assert result.orientation == "h"
        assert list(cast(Any, result.x)) == trace.values
        assert result.quartilemethod == "exclusive"
        assert result.boxpoints == "all"
        assert result.notched
        assert result.boxmean
        assert result.fillcolor == "#ff0000"

    def test_line_trace_dispatch(self) -> None:
        trace = LineTraceConfig(name="line", x=["a"], y=[1])
        result = _convert_trace(trace)
        assert isinstance(result, go.Scatter)

    def test_scatter_trace_dispatch(self) -> None:
        trace = ScatterTraceConfig(name="scatter", x=["a"], y=[1])
        result = _convert_trace(trace)
        assert isinstance(result, go.Scatter)

    def test_histogram_trace_dispatch(self) -> None:
        trace = HistogramTraceConfig(name="hist", x=[1, 2, 3])
        result = _convert_trace(trace)
        assert isinstance(result, go.Histogram)

    def test_base_trace_fallback_to_bar(self) -> None:
        trace = TraceConfig(name="base", x=["a"], y=[1])
        result = _convert_trace(trace)
        assert isinstance(result, go.Bar)


# _bar_trace


class TestBarTrace:
    """Tests for ``_bar_trace`` converter."""

    def test_basic_bar(self) -> None:
        trace = BarTraceConfig(name="s1", x=["a", "b"], y=[1, 2])
        bar = _bar_trace(trace)
        assert bar.name == "s1"
        assert list(cast(Any, bar.x)) == ["a", "b"]
        assert list(cast(Any, bar.y)) == [1, 2]

    def test_x_positions_override_x(self) -> None:
        trace = BarTraceConfig(x=["a", "b"], y=[1, 2], x_positions=[0.5, 1.5])
        bar = _bar_trace(trace)
        assert list(cast(Any, bar.x)) == [0.5, 1.5]

    def test_bar_color(self) -> None:
        trace = BarTraceConfig(x=["a"], y=[1], color="#ff0000")
        bar = _bar_trace(trace)
        assert cast(Any, bar.marker).color == "#ff0000"

    def test_bar_pattern(self) -> None:
        trace = BarTraceConfig(x=["a"], y=[1], pattern="/")
        bar = _bar_trace(trace)
        assert cast(Any, bar.marker).pattern.shape == "/"

    def test_bar_border(self) -> None:
        trace = BarTraceConfig(x=["a"], y=[1], border_width=2.0, border_color="black")
        bar = _bar_trace(trace)
        marker = cast(Any, bar.marker)
        assert marker.line.width == 2.0
        assert marker.line.color == "black"

    def test_bar_offset(self) -> None:
        trace = BarTraceConfig(x=["a"], y=[1], offset=0.3)
        bar = _bar_trace(trace)
        assert bar.offset == 0.3

    def test_bar_text_values(self) -> None:
        trace = BarTraceConfig(
            x=["a"],
            y=[1],
            text_values=["1.0"],
            text_position="outside",
            text_angle=45.0,
            text_font_size=10,
        )
        bar = _bar_trace(trace)
        assert bar.text == ("1.0",)
        assert bar.textposition == "outside"

    def test_bar_error_y(self) -> None:
        # [test->req~ring5.figure.error-bars~1]
        trace = BarTraceConfig(x=["a"], y=[1], error_y=[0.1])
        bar = _bar_trace(trace)
        error_y = cast(Any, bar.error_y)
        assert error_y.array == (0.1,)
        assert error_y.visible is True

    def test_bar_custom_data(self) -> None:
        trace = BarTraceConfig(
            x=["a"],
            y=[1],
            custom_data={
                "customdata": [[1, 2]],
                "hovertemplate": "%{customdata[0]}",
            },
        )
        bar = _bar_trace(trace)
        assert bar.customdata is not None
        assert bar.hovertemplate == "%{customdata[0]}"

    def test_bar_yaxis_y2(self) -> None:
        trace = BarTraceConfig(x=["a"], y=[1], yaxis="y2")
        bar = _bar_trace(trace)
        assert bar.yaxis == "y2"

    def test_bar_non_default_width(self) -> None:
        trace = BarTraceConfig(x=["a"], y=[1], bar_width=0.5)
        bar = _bar_trace(trace)
        assert bar.width == 0.5


# _line_trace


class TestLineTrace:
    """Tests for ``_line_trace`` converter."""

    def test_basic_line(self) -> None:
        trace = LineTraceConfig(name="l1", x=["a"], y=[1])
        scatter = _line_trace(trace)
        assert isinstance(scatter, go.Scatter)
        assert scatter.mode == "lines+markers"

    def test_lines_only_mode(self) -> None:
        trace = LineTraceConfig(name="l1", x=["a"], y=[1], show_markers=False)
        scatter = _line_trace(trace)
        assert scatter.mode == "lines"

    def test_line_color(self) -> None:
        trace = LineTraceConfig(x=["a"], y=[1], color="#00ff00")
        scatter = _line_trace(trace)
        assert cast(Any, scatter.line).color == "#00ff00"

    def test_line_markers_with_color(self) -> None:
        trace = LineTraceConfig(x=["a"], y=[1], color="#00ff00", show_markers=True)
        scatter = _line_trace(trace)
        assert cast(Any, scatter.marker).color == "#00ff00"

    def test_line_yaxis_y2(self) -> None:
        trace = LineTraceConfig(x=["a"], y=[1], yaxis="y2")
        scatter = _line_trace(trace)
        assert scatter.yaxis == "y2"

    def test_line_fill(self) -> None:
        trace = LineTraceConfig(x=["a"], y=[1], fill="tozeroy")
        scatter = _line_trace(trace)
        assert scatter.fill == "tozeroy"

    def test_line_error_y(self) -> None:
        trace = LineTraceConfig(x=["a"], y=[1], error_y=[0.2])
        scatter = _line_trace(trace)
        assert cast(Any, scatter.error_y).array == (0.2,)


# _scatter_trace


class TestScatterTrace:
    """Tests for ``_scatter_trace`` converter."""

    def test_basic_scatter(self) -> None:
        trace = ScatterTraceConfig(name="s1", x=["a"], y=[1])
        scatter = _scatter_trace(trace)
        assert isinstance(scatter, go.Scatter)
        assert scatter.mode == "markers"

    def test_scatter_color(self) -> None:
        trace = ScatterTraceConfig(x=["a"], y=[1], color="#0000ff")
        scatter = _scatter_trace(trace)
        assert cast(Any, scatter.marker).color == "#0000ff"

    def test_scatter_marker_line(self) -> None:
        trace = ScatterTraceConfig(x=["a"], y=[1], marker_line_width=1.5, marker_line_color="red")
        scatter = _scatter_trace(trace)
        marker = cast(Any, scatter.marker)
        assert marker.line.width == 1.5
        assert marker.line.color == "red"

    def test_scatter_colorscale(self) -> None:
        trace = ScatterTraceConfig(x=["a"], y=[1], colorscale="Viridis")
        scatter = _scatter_trace(trace)
        # Plotly expands named colorscales into tuples
        marker = cast(Any, scatter.marker)
        assert marker.colorscale is not None
        assert len(marker.colorscale) > 0

    def test_scatter_yaxis_y2(self) -> None:
        trace = ScatterTraceConfig(x=["a"], y=[1], yaxis="y2")
        scatter = _scatter_trace(trace)
        assert scatter.yaxis == "y2"

    def test_scatter_error_y(self) -> None:
        trace = ScatterTraceConfig(x=["a"], y=[1], error_y=[0.3])
        scatter = _scatter_trace(trace)
        assert cast(Any, scatter.error_y).array == (0.3,)

    def test_scatter_size_values(self) -> None:
        trace = ScatterTraceConfig(x=["a", "b"], y=[1, 2], size_values=[10.0, 20.0])
        scatter = _scatter_trace(trace)
        assert list(cast(Any, scatter.marker).size) == [10.0, 20.0]


# _histogram_trace


class TestHistogramTrace:
    """Tests for ``_histogram_trace`` converter."""

    def test_basic_histogram(self) -> None:
        trace = HistogramTraceConfig(name="h1", x=[1, 2, 3, 4])
        hist = _histogram_trace(trace)
        assert isinstance(hist, go.Histogram)
        assert hist.nbinsx == 20

    def test_histogram_color(self) -> None:
        trace = HistogramTraceConfig(x=[1, 2], color="#aabbcc")
        hist = _histogram_trace(trace)
        assert cast(Any, hist.marker).color == "#aabbcc"

    def test_histogram_normalization(self) -> None:
        trace = HistogramTraceConfig(x=[1, 2], normalization="percent")
        hist = _histogram_trace(trace)
        assert hist.histnorm == "percent"

    def test_histogram_cumulative(self) -> None:
        trace = HistogramTraceConfig(x=[1, 2], cumulative=True)
        hist = _histogram_trace(trace)
        assert cast(Any, hist.cumulative).enabled is True


# _bar_trace_from_base


class TestBarTraceFromBase:
    """Tests for the fallback ``_bar_trace_from_base``."""

    def test_basic_fallback(self) -> None:
        trace = TraceConfig(name="base", x=["a"], y=[1])
        bar = _bar_trace_from_base(trace)
        assert isinstance(bar, go.Bar)
        assert bar.name == "base"

    def test_fallback_with_color(self) -> None:
        trace = TraceConfig(name="c", x=["a"], y=[1], color="#123456")
        bar = _bar_trace_from_base(trace)
        assert cast(Any, bar.marker).color == "#123456"


# _convert_annotations


class TestConvertAnnotations:
    """Tests for ``_convert_annotations``."""

    def test_empty_list(self) -> None:
        assert _convert_annotations([]) == []

    def test_single_annotation(self) -> None:
        ann = AnnotationConfig(text="test", x=0.5, y=1.0)
        result = _convert_annotations([ann])
        assert len(result) == 1
        assert result[0]["text"] == "test"
        assert result[0]["x"] == 0.5
        assert result[0]["y"] == 1.0

    def test_annotation_with_font(self) -> None:
        ann = AnnotationConfig(
            text="styled",
            font_size=14,
            font_color="red",
            font_bold=True,
        )
        result = _convert_annotations([ann])
        assert result[0]["font"]["size"] == 14
        assert result[0]["font"]["color"] == "red"
        assert result[0]["font"]["weight"] == "bold"

    def test_annotation_with_text_angle(self) -> None:
        ann = AnnotationConfig(text="angled", text_angle=45.0)
        result = _convert_annotations([ann])
        assert result[0]["textangle"] == 45.0

    def test_annotation_with_bgcolor(self) -> None:
        ann = AnnotationConfig(text="bg", bgcolor="white")
        result = _convert_annotations([ann])
        assert result[0]["bgcolor"] == "white"

    def test_annotation_with_border(self) -> None:
        ann = AnnotationConfig(
            text="bordered",
            border_color="black",
            border_width=2.0,
            border_pad=4.0,
        )
        result = _convert_annotations([ann])
        assert result[0]["bordercolor"] == "black"
        assert result[0]["borderwidth"] == 2.0
        assert result[0]["borderpad"] == 4.0

    def test_annotation_with_arrow(self) -> None:
        ann = AnnotationConfig(text="arrowed", show_arrow=True, arrow_head=3, arrow_color="#FF0000")
        result = _convert_annotations([ann])
        assert result[0]["showarrow"] is True
        assert result[0]["arrowhead"] == 3
        assert result[0]["arrowcolor"] == "#FF0000"

    def test_annotation_without_arrow_omits_arrowcolor(self) -> None:
        ann = AnnotationConfig(text="plain", show_arrow=False, arrow_color="#FF0000")
        result = _convert_annotations([ann])
        assert result[0]["showarrow"] is False
        assert "arrowcolor" not in result[0]

    def test_non_annotation_skipped(self) -> None:
        """Non-AnnotationConfig items are silently skipped."""
        result = _convert_annotations(["not_an_annotation"])  # type: ignore[list-item]
        assert result == []
