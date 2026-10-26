"""Assemble a native Plotly artifact from one prepared neutral figure."""

import plotly.graph_objects as go

from src.core.models.visualization.figure_config import FigureConfig
from src.web.rendering._connector_protocol import uses_heatmap_panels
from src.web.rendering.figure_preparation import PreparedFigure
from src.web.rendering.plotly_connector import FigureSpecToPlotly
from src.web.rendering.trace_to_plotly import traces_to_plotly
from src.web.rendering._render_result import PlotlyRenderResult


def apply_axis_title_annotations(spec: FigureConfig, figure: go.Figure) -> None:
    """Project rotated axis-title roles without inspecting other annotation text."""
    for axis, x, size, color, name in (
        (
            spec.axes.y,
            0.0,
            spec.typography.font_size_ylabel,
            spec.axes.y.axis_color,
            "ring5-y-title",
        ),
        (
            spec.axes.y2,
            1.0,
            spec.typography.font_size_y2label,
            spec.axes.y2.axis_color if spec.axes.y2 is not None else "",
            "ring5-y2-title",
        ),
    ):
        if axis is None or axis.title_angle is None or not axis.label:
            continue
        figure.add_annotation(
            name=name,
            text=axis.label,
            x=x,
            y=axis.label_position + axis.title_vshift / 100.0,
            xref="paper",
            yref="paper",
            xanchor="right" if x == 0.0 else "left",
            yanchor="middle",
            textangle=axis.title_angle,
            showarrow=False,
            captureevents=False,
            font={"size": size, "color": color, "family": spec.font_family},
            xshift=(-1.0 if x == 0.0 else 1.0) * (axis.label_standoff + 40.0),
        )


def apply_heatmap_panel_axes(prepared: PreparedFigure, figure: go.Figure) -> None:
    """Label only the bottom X axis of an actual all-heatmap facet result."""
    if not uses_heatmap_panels(prepared.trace_result):
        return
    figure.update_xaxes(title_text=None, showticklabels=False)
    bottom = getattr(figure.layout, f"xaxis{len(prepared.trace_result.traces)}")
    bottom.title.text = prepared.spec.axes.x.label
    bottom.showticklabels = prepared.spec.axes.x.show_tick_labels


def build_plotly_figure(prepared: PreparedFigure) -> PlotlyRenderResult:
    """Build and style one native figure without preparing or resolving it again.

    Args:
        prepared: Owned neutral output and the resolved styling for this render.

    Returns:
        A styled native figure with explicit source bindings and editable Plotly shapes.
    """
    # [impl->req~ring5.figure.shapes-annotations~1]
    # [impl->req~ring5.render.plotly~1]
    rendered = traces_to_plotly(prepared.trace_result)
    FigureSpecToPlotly.apply(prepared.spec, rendered)
    figure = rendered.figure
    apply_axis_title_annotations(prepared.spec, figure)
    apply_heatmap_panel_axes(prepared, figure)
    shapes = prepared.config.get("shapes")
    if shapes:
        figure.update_layout(shapes=[*(figure.layout.shapes or ()), *shapes])
    if not prepared.trace_result.traces:
        figure.update_layout(title_text="Please select at least one X and one Y column.")
    rendered.validate()
    return rendered
