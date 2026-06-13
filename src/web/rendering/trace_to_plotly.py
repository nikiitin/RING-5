"""
Trace-to-Plotly converter — builds ``go.Figure`` from ``TraceBuildResult``.

This module replaces the *reverse* extraction path that used to go
``go.Figure`` → ``PlotlyTraceExtractor`` → ``List[TraceConfig]``.
Now plot types produce ``TraceBuildResult`` directly (forward direction)
and this converter builds the Plotly figure from it.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    HeatmapTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)
from src.web.rendering._heatmap_utils import is_dark_cell


def _error_y_dict(error_y: list[float] | None) -> dict[str, Any] | None:
    """Build the Plotly error_y dict if error data is present."""
    if not error_y:
        return None
    return {"type": "data", "array": error_y, "visible": True}


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
    traces_list = list(result.traces)
    heatmap_only = (
        len(traces_list) > 1
        and all(isinstance(trace, HeatmapTraceConfig) for trace in traces_list)
        and not result.secondary_y
    )

    if heatmap_only:
        subplot_titles = [trace.name for trace in traces_list]
        fig = make_subplots(
            rows=len(traces_list),
            cols=1,
            subplot_titles=subplot_titles,
            vertical_spacing=0.08,
        )
    elif result.secondary_y:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    for index, trace in enumerate(traces_list, start=1):
        plotly_trace = _convert_trace(trace)
        if heatmap_only:
            fig.add_trace(plotly_trace, row=index, col=1)
        elif result.secondary_y:
            secondary = trace.yaxis == "y2"
            fig.add_trace(plotly_trace, secondary_y=secondary)
        else:
            fig.add_trace(plotly_trace)

    # Layout updates
    layout_updates: dict[str, Any] = {"barmode": result.barmode}

    if result.custom_x_ticks:
        xaxis_update: dict[str, Any] = {
            "tickmode": "array",
            "tickvals": result.custom_x_ticks["vals"],
            "ticktext": result.custom_x_ticks["text"],
        }
        # When hide_ticks is set, completely hide tick marks and labels
        if result.custom_x_ticks.get("hide_ticks"):
            xaxis_update["showticklabels"] = False
            xaxis_update["ticks"] = ""
        layout_updates["xaxis"] = xaxis_update

    separator_shapes: list[dict[str, Any]] = [
        {
            "type": "line",
            "xref": "x",
            "yref": "paper",
            "x0": sep.x,
            "x1": sep.x,
            "y0": 0,
            "y1": 1,
            "line": {"color": sep.color, "width": sep.width, "dash": sep.dash},
            "layer": "below",
        }
        for sep in result.separator_lines
    ]
    rule_shapes: list[dict[str, Any]] = [
        {
            "type": "line",
            "xref": "x",
            "yref": "paper",
            "x0": rule.x0,
            "x1": rule.x1,
            "y0": rule.y,
            "y1": rule.y,
            "line": {"color": rule.color, "width": rule.width},
        }
        for rule in result.rule_lines
    ]
    shade_shapes: list[dict[str, Any]] = [
        {
            "type": "rect",
            "xref": "x",
            "yref": "paper",
            "x0": band.x0,
            "x1": band.x1,
            "y0": 0,
            "y1": 1,
            "fillcolor": band.color,
            "opacity": band.opacity,
            "layer": "below",
            "line_width": 0,
        }
        for band in result.shaded_regions
    ]
    if separator_shapes or shade_shapes or rule_shapes:
        # Shades first (drawn under), then separators, then span rules.
        layout_updates["shapes"] = shade_shapes + separator_shapes + rule_shapes

    if result.annotations or result.layout_annotations:
        all_annotations: list[dict[str, Any]] = []
        if result.annotations:
            all_annotations.extend(_convert_annotations(result.annotations))
        if result.layout_annotations:
            all_annotations.extend(result.layout_annotations)
        layout_updates["annotations"] = all_annotations

    fig.update_layout(**layout_updates)

    # Heatmap cell-value annotations (rendered on top of all traces)
    _add_heatmap_annotations(fig, traces_list, heatmap_only)

    # Heatmap totals separator lines
    _add_heatmap_separator_lines(fig, traces_list, heatmap_only)

    return fig


# ── Private helpers ──────────────────────────────────────────────────────


def _convert_trace(trace: TraceConfig) -> go.BaseTraceType:  # type: ignore[name-defined]
    """Dispatch to the appropriate trace converter."""
    if isinstance(trace, BarTraceConfig):
        return _bar_trace(trace)
    elif isinstance(trace, LineTraceConfig):
        return _line_trace(trace)
    elif isinstance(trace, ScatterTraceConfig):
        return _scatter_trace(trace)
    elif isinstance(trace, HistogramTraceConfig):
        return _histogram_trace(trace)
    elif isinstance(trace, HeatmapTraceConfig):
        return _heatmap_trace(trace)
    else:
        # Fallback for base TraceConfig — render as bar
        return _bar_trace_from_base(trace)


def _bar_trace(trace: BarTraceConfig) -> go.Bar:
    """Convert a ``BarTraceConfig`` to ``go.Bar``."""
    # Use x_positions for manually positioned bars, else use x values
    x_data = trace.x_positions if trace.x_positions else trace.x

    kwargs: dict[str, Any] = {
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
    marker: dict[str, Any] = {}
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
    if error_y := _error_y_dict(trace.error_y):
        kwargs["error_y"] = error_y

    # Custom data
    if trace.custom_data:
        kwargs["customdata"] = trace.custom_data.get("customdata")
        if "hovertemplate" in trace.custom_data:
            kwargs["hovertemplate"] = trace.custom_data["hovertemplate"]

    return go.Bar(**{k: v for k, v in kwargs.items() if v is not None})


def _line_trace(trace: LineTraceConfig) -> go.Scatter:
    """Convert a ``LineTraceConfig`` to ``go.Scatter`` with lines mode."""
    mode = "lines+markers" if trace.show_markers else "lines"

    kwargs: dict[str, Any] = {
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
        marker_dict: dict[str, Any] = {
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

    if error_y := _error_y_dict(trace.error_y):
        kwargs["error_y"] = error_y

    return go.Scatter(**{k: v for k, v in kwargs.items() if v is not None})


def _scatter_trace(trace: ScatterTraceConfig) -> go.Scatter:
    """Convert a ``ScatterTraceConfig`` to ``go.Scatter`` with markers mode."""
    marker: dict[str, Any] = {
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

    kwargs: dict[str, Any] = {
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

    if error_y := _error_y_dict(trace.error_y):
        kwargs["error_y"] = error_y

    return go.Scatter(**{k: v for k, v in kwargs.items() if v is not None})


def _histogram_trace(trace: HistogramTraceConfig) -> go.Histogram:
    """Convert a ``HistogramTraceConfig`` to ``go.Histogram``."""
    kwargs: dict[str, Any] = {
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
    kwargs: dict[str, Any] = {
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


def _heatmap_trace(trace: HeatmapTraceConfig) -> go.Heatmap:
    """Convert a ``HeatmapTraceConfig`` to ``go.Heatmap``.

    Cell-value text is rendered as layout annotations (not texttemplate)
    by :func:`_build_heatmap_annotations` so that text always appears
    on top of the cells with proper auto-contrast colouring.
    """
    kwargs: dict[str, Any] = {
        "x": trace.col_labels,
        "y": trace.row_labels,
        "z": trace.z,
        "colorscale": trace.colorscale,
        "name": trace.name,
        "showlegend": False,
    }
    kwargs["hoverongaps"] = False
    return go.Heatmap(**{k: v for k, v in kwargs.items() if v is not None})


def _add_heatmap_annotations(
    fig: go.Figure,
    traces_list: list[TraceConfig],
    heatmap_only: bool,
) -> None:
    """Append per-cell annotations for every heatmap trace that has text.

    Using layout annotations (instead of ``texttemplate``) guarantees that
    text renders **above** the coloured cells and supports per-cell
    auto-contrast colouring (white text on dark cells, black on light).
    """
    annotations: list[dict[str, Any]] = []
    for idx, trace in enumerate(traces_list):
        if not isinstance(trace, HeatmapTraceConfig):
            continue
        if not (trace.show_values and trace.text):
            continue

        # Subplot axis references: row 1 → "x"/"y", row N → "xN"/"yN"
        if heatmap_only:
            xref = "x" if idx == 0 else f"x{idx + 1}"
            yref = "y" if idx == 0 else f"y{idx + 1}"
        else:
            xref, yref = "x", "y"

        font_size = getattr(trace, "text_font_size", 10)

        for i, text_row in enumerate(trace.text):
            for j, cell_text in enumerate(text_row):
                if not cell_text:
                    continue
                is_dark = is_dark_cell(trace.z, i, j)

                # Determine text colour
                color_mode = getattr(trace, "text_color_mode", "contrast")
                if color_mode == "custom":
                    text_color = getattr(trace, "text_color", "#000000")
                else:
                    text_color = "white" if is_dark else "black"

                annotations.append(
                    {
                        "text": str(cell_text),
                        "x": trace.col_labels[j],
                        "y": trace.row_labels[i],
                        "xref": xref,
                        "yref": yref,
                        "showarrow": False,
                        "font": {"size": font_size, "color": text_color},
                    }
                )

    if annotations:
        existing = list(fig.layout.annotations or [])
        fig.update_layout(annotations=existing + annotations)


def _add_heatmap_separator_lines(
    fig: go.Figure,
    traces_list: list[TraceConfig],
    heatmap_only: bool,
) -> None:
    """Draw separator lines between main data cells and totals."""
    shapes: list[dict[str, Any]] = []
    for idx, trace in enumerate(traces_list):
        if not isinstance(trace, HeatmapTraceConfig):
            continue
        if not trace.totals_position or trace.totals_count == 0:
            continue

        # Subplot axis references: row 1 → "x"/"y", row N → "xN"/"yN"
        if heatmap_only:
            xref = "x" if idx == 0 else f"x{idx + 1}"
            yref = "y" if idx == 0 else f"y{idx + 1}"
        else:
            xref, yref = "x", "y"

        n_cols = len(trace.col_labels)
        n_rows = len(trace.row_labels)

        if trace.totals_position == "right" and n_cols > 1:
            # Vertical separator before the totals column.
            # Plotly maps categorical labels to integer positions 0, 1, ...
            # A line at x = n_cols - 1.5 sits between the last data column
            # and the totals column.
            x_pos = n_cols - 1.5
            shapes.append(
                {
                    "type": "line",
                    "x0": x_pos,
                    "x1": x_pos,
                    "y0": -0.5,
                    "y1": n_rows - 0.5,
                    "xref": xref,
                    "yref": yref,
                    "line": {"color": "black", "width": 2},
                }
            )
        elif trace.totals_position == "top" and n_rows > 1:
            # Horizontal separator below the totals row (first row).
            y_pos = 0.5
            shapes.append(
                {
                    "type": "line",
                    "x0": -0.5,
                    "x1": n_cols - 0.5,
                    "y0": y_pos,
                    "y1": y_pos,
                    "xref": xref,
                    "yref": yref,
                    "line": {"color": "black", "width": 2},
                }
            )

    if shapes:
        existing = list(fig.layout.shapes or [])
        fig.update_layout(shapes=existing + shapes)


def _convert_annotations(
    annotations: list[AnnotationConfig],
) -> list[dict[str, Any]]:
    """Convert ``AnnotationConfig`` list to Plotly annotation dicts."""

    result: list[dict[str, Any]] = []
    for ann in annotations:
        if not isinstance(ann, AnnotationConfig):
            continue
        d: dict[str, Any] = {
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
