"""
Trace-to-Plotly converter — builds ``go.Figure`` from ``TraceBuildResult``.

This module replaces the *reverse* extraction path that used to go
``go.Figure`` → ``PlotlyTraceExtractor`` → ``List[TraceConfig]``.
Now plot types produce ``TraceBuildResult`` directly (forward direction)
and this converter builds the Plotly figure from it.
"""

from __future__ import annotations

from typing import Any, Dict, List

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)


def traces_to_plotly(result: TraceBuildResult) -> go.Figure:
    """Convert a ``TraceBuildResult`` into a Plotly ``go.Figure``.

    The returned figure contains all traces, shapes, annotations,
    barmode, and custom tick overrides from the build result.
    Styling (typography, colors, legends, etc.) is applied *separately*
    by the ``FigureSpecToPlotly`` connector.

    Args:
        result: Engine-agnostic output from a plot type.

    Returns:
        A fully populated (but unstyled) ``go.Figure``.
    """
    if result.secondary_y:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    for trace in result.traces:
        plotly_trace = _convert_trace(trace)
        if result.secondary_y:
            secondary = trace.yaxis == "y2"
            fig.add_trace(plotly_trace, secondary_y=secondary)
        else:
            fig.add_trace(plotly_trace)

    # Layout updates
    layout_updates: Dict[str, Any] = {"barmode": result.barmode}

    if result.custom_x_ticks:
        xaxis_update: Dict[str, Any] = {
            "tickmode": "array",
            "tickvals": result.custom_x_ticks["vals"],
            "ticktext": result.custom_x_ticks["text"],
        }
        # When hide_ticks is set, completely hide tick marks and labels
        if result.custom_x_ticks.get("hide_ticks"):
            xaxis_update["showticklabels"] = False
            xaxis_update["ticks"] = ""
        layout_updates["xaxis"] = xaxis_update

    if result.shapes:
        layout_updates["shapes"] = result.shapes

    if result.annotations or result.layout_annotations:
        all_annotations: List[Dict[str, Any]] = []
        if result.annotations:
            all_annotations.extend(_convert_annotations(result.annotations))
        if result.layout_annotations:
            all_annotations.extend(result.layout_annotations)
        layout_updates["annotations"] = all_annotations

    fig.update_layout(**layout_updates)

    return fig


# ── Private helpers ──────────────────────────────────────────────────────


def _convert_trace(trace: TraceConfig) -> go.BaseTraceType:
    """Dispatch to the appropriate trace converter."""
    if isinstance(trace, BarTraceConfig):
        return _bar_trace(trace)
    elif isinstance(trace, LineTraceConfig):
        return _line_trace(trace)
    elif isinstance(trace, ScatterTraceConfig):
        return _scatter_trace(trace)
    elif isinstance(trace, HistogramTraceConfig):
        return _histogram_trace(trace)
    else:
        # Fallback for base TraceConfig — render as bar
        return _bar_trace_from_base(trace)


def _bar_trace(trace: BarTraceConfig) -> go.Bar:
    """Convert a ``BarTraceConfig`` to ``go.Bar``."""
    # Use x_positions for manually positioned bars, else use x values
    x_data = trace.x_positions if trace.x_positions else trace.x

    kwargs: Dict[str, Any] = {
        "x": x_data,
        "y": trace.y,
        "name": trace.name,
        "opacity": trace.opacity,
        "width": trace.bar_width if trace.bar_width != 0.8 else None,
        "showlegend": trace.show_in_legend,
        "visible": trace.visible,
        "legendgroup": trace.legendgroup or trace.name,
    }

    if trace.yaxis == "y2":
        kwargs["yaxis"] = "y2"

    # Marker styling
    marker: Dict[str, Any] = {}
    if trace.color:
        marker["color"] = trace.color
    if trace.pattern:
        marker["pattern"] = {"shape": trace.pattern}
    if trace.border_width > 0:
        marker["line"] = {
            "width": trace.border_width,
            "color": trace.border_color or "black",
        }
    if marker:
        kwargs["marker"] = marker

    # Offset for grouped bars
    if trace.offset != 0.0:
        kwargs["offset"] = trace.offset

    # Text/data labels
    if trace.text_values:
        kwargs["text"] = trace.text_values
        kwargs["textposition"] = trace.text_position
        kwargs["textangle"] = trace.text_angle
        kwargs["textfont"] = {"size": trace.text_font_size}

    # Error bars
    if trace.error_y:
        kwargs["error_y"] = {
            "type": "data",
            "array": trace.error_y,
            "visible": True,
        }

    # Custom data
    if trace.custom_data:
        kwargs["customdata"] = trace.custom_data.get("customdata")
        if "hovertemplate" in trace.custom_data:
            kwargs["hovertemplate"] = trace.custom_data["hovertemplate"]

    return go.Bar(**{k: v for k, v in kwargs.items() if v is not None})


def _line_trace(trace: LineTraceConfig) -> go.Scatter:
    """Convert a ``LineTraceConfig`` to ``go.Scatter`` with lines mode."""
    mode = "lines+markers" if trace.show_markers else "lines"

    kwargs: Dict[str, Any] = {
        "x": trace.x,
        "y": trace.y,
        "name": trace.name,
        "mode": mode,
        "opacity": trace.opacity,
        "showlegend": trace.show_in_legend,
        "visible": trace.visible,
        "legendgroup": trace.legendgroup or trace.name,
        "line": {
            "width": trace.line_width,
            "dash": trace.line_dash,
        },
    }

    if trace.color:
        kwargs["line"]["color"] = trace.color

    if trace.show_markers:
        marker_dict: Dict[str, Any] = {
            "symbol": trace.marker_symbol,
            "size": trace.marker_size,
        }
        if trace.color:
            marker_dict["color"] = trace.color
        kwargs["marker"] = marker_dict

    if trace.yaxis == "y2":
        kwargs["yaxis"] = "y2"

    if trace.fill != "none":
        kwargs["fill"] = trace.fill

    if trace.error_y:
        kwargs["error_y"] = {
            "type": "data",
            "array": trace.error_y,
            "visible": True,
        }

    return go.Scatter(**{k: v for k, v in kwargs.items() if v is not None})


def _scatter_trace(trace: ScatterTraceConfig) -> go.Scatter:
    """Convert a ``ScatterTraceConfig`` to ``go.Scatter`` with markers mode."""
    marker: Dict[str, Any] = {
        "symbol": trace.marker_symbol,
        "size": trace.size_values or trace.marker_size,
    }
    if trace.color:
        marker["color"] = trace.color
    if trace.marker_line_width > 0:
        marker["line"] = {
            "width": trace.marker_line_width,
            "color": trace.marker_line_color or "black",
        }
    if trace.colorscale:
        marker["colorscale"] = trace.colorscale

    kwargs: Dict[str, Any] = {
        "x": trace.x,
        "y": trace.y,
        "name": trace.name,
        "mode": "markers",
        "opacity": trace.opacity,
        "showlegend": trace.show_in_legend,
        "visible": trace.visible,
        "legendgroup": trace.legendgroup or trace.name,
        "marker": marker,
    }

    if trace.yaxis == "y2":
        kwargs["yaxis"] = "y2"

    if trace.error_y:
        kwargs["error_y"] = {
            "type": "data",
            "array": trace.error_y,
            "visible": True,
        }

    return go.Scatter(**{k: v for k, v in kwargs.items() if v is not None})


def _histogram_trace(trace: HistogramTraceConfig) -> go.Histogram:
    """Convert a ``HistogramTraceConfig`` to ``go.Histogram``."""
    kwargs: Dict[str, Any] = {
        "x": trace.x,
        "name": trace.name,
        "opacity": trace.opacity,
        "showlegend": trace.show_in_legend,
        "visible": trace.visible,
        "legendgroup": trace.legendgroup or trace.name,
        "nbinsx": trace.nbins,
    }

    if trace.color:
        kwargs["marker"] = {"color": trace.color}

    if trace.normalization:
        kwargs["histnorm"] = trace.normalization

    if trace.cumulative:
        kwargs["cumulative"] = {"enabled": True}

    return go.Histogram(**{k: v for k, v in kwargs.items() if v is not None})


def _bar_trace_from_base(trace: TraceConfig) -> go.Bar:
    """Fallback: convert a base ``TraceConfig`` to ``go.Bar``."""
    kwargs: Dict[str, Any] = {
        "x": trace.x,
        "y": trace.y,
        "name": trace.name,
        "opacity": trace.opacity,
        "showlegend": trace.show_in_legend,
        "visible": trace.visible,
    }
    if trace.color:
        kwargs["marker"] = {"color": trace.color}
    return go.Bar(**{k: v for k, v in kwargs.items() if v is not None})


def _convert_annotations(
    annotations: List[AnnotationConfig],
) -> List[Dict[str, Any]]:
    """Convert ``AnnotationConfig`` list to Plotly annotation dicts."""

    result: List[Dict[str, Any]] = []
    for ann in annotations:
        if not isinstance(ann, AnnotationConfig):
            continue
        d: Dict[str, Any] = {
            "text": ann.text,
            "x": ann.x,
            "y": ann.y,
            "xref": ann.xref,
            "yref": ann.yref,
            "xanchor": ann.xanchor,
            "yanchor": ann.yanchor,
            "showarrow": ann.show_arrow,
            "font": {},
        }
        if ann.text_angle:
            d["textangle"] = ann.text_angle
        if ann.font_size > 0:
            d["font"]["size"] = ann.font_size
        if ann.font_color:
            d["font"]["color"] = ann.font_color
        if ann.font_bold:
            d["font"]["weight"] = "bold"
        if ann.bgcolor:
            d["bgcolor"] = ann.bgcolor
        if ann.border_color:
            d["bordercolor"] = ann.border_color
        if ann.border_width > 0:
            d["borderwidth"] = ann.border_width
        if ann.border_pad > 0:
            d["borderpad"] = ann.border_pad
        if ann.show_arrow and ann.arrow_head:
            d["arrowhead"] = ann.arrow_head
        result.append(d)
    return result
