"""
Plotly trace renderer — builds a ``go.Figure`` from ``TraceSpec`` instances.

Symmetric counterpart to ``MatplotlibTraceRenderer``.  Each ``TraceSpec``
sub-class is converted to the equivalent Plotly trace object
(``go.Bar``, ``go.Scatter``, ``go.Histogram``).

This module is the **only** place where the Plotly library is used to
build traces from the engine-agnostic ``TraceSpec`` model.  Plot type
classes no longer create ``go.Figure`` directly.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import plotly.graph_objects as go

from src.core.visualization.trace_spec import (
    BarTraceSpec,
    HistogramTraceSpec,
    LineTraceSpec,
    ScatterTraceSpec,
    TraceSpec,
)

logger = logging.getLogger(__name__)


class PlotlyTraceRenderer:
    """Build a ``go.Figure`` from engine-agnostic ``TraceSpec`` instances.

    All methods are ``@staticmethod`` — the class is purely a namespace.
    """

    # ── public API ────────────────────────────────────────────────────────

    @staticmethod
    def build_figure(
        traces: List[TraceSpec],
        *,
        barmode: str = "group",
        title: str = "",
        xaxis_title: str = "",
        yaxis_title: str = "",
        legend_title: str = "",
        palette_colors: Optional[List[str]] = None,
        extra_layout: Optional[Dict[str, Any]] = None,
    ) -> go.Figure:
        """Build a ``go.Figure`` from a list of ``TraceSpec`` instances.

        Args:
            traces: Ordered list of traces.
            barmode: Bar arrangement (``"group"`` / ``"stack"`` / ``"overlay"``).
            title: Figure title.
            xaxis_title: X-axis label.
            yaxis_title: Y-axis label.
            legend_title: Legend label.
            palette_colors: Resolved palette hex colours for automatic
                colouring when the trace has no explicit colour.
            extra_layout: Optional additional ``layout`` kwargs to merge.

        Returns:
            A fully populated ``go.Figure``.
        """
        fig = go.Figure()

        for idx, trace in enumerate(traces):
            override: Optional[str] = None
            if palette_colors and not trace.color:
                override = palette_colors[idx % len(palette_colors)]

            try:
                if isinstance(trace, BarTraceSpec):
                    PlotlyTraceRenderer._add_bar(fig, trace, override)
                elif isinstance(trace, LineTraceSpec):
                    PlotlyTraceRenderer._add_line(fig, trace, override)
                elif isinstance(trace, ScatterTraceSpec):
                    PlotlyTraceRenderer._add_scatter(fig, trace, override)
                elif isinstance(trace, HistogramTraceSpec):
                    PlotlyTraceRenderer._add_histogram(fig, trace, override)
                else:
                    logger.warning(
                        "Unknown TraceSpec type: %s",
                        type(trace).__name__,
                    )
            except Exception:
                logger.exception("Failed to render trace %s to Plotly", trace.name)

        layout: Dict[str, Any] = {
            "barmode": barmode,
            "title": title,
            "xaxis_title": xaxis_title,
            "yaxis_title": yaxis_title,
            "legend_title": legend_title,
        }
        if extra_layout:
            layout.update(extra_layout)

        fig.update_layout(**layout)

        return fig

    # ── bar ────────────────────────────────────────────────────────────────

    @staticmethod
    def _add_bar(
        fig: go.Figure,
        spec: BarTraceSpec,
        override_color: Optional[str] = None,
    ) -> None:
        """Add a ``go.Bar`` trace from ``BarTraceSpec``."""
        color = override_color or spec.color or None

        marker: Dict[str, Any] = {}
        if color:
            marker["color"] = color
        if spec.pattern:
            marker["pattern"] = {"shape": spec.pattern, "fillmode": "replace"}
        if spec.border_width and spec.border_color:
            marker["line"] = {
                "width": spec.border_width,
                "color": spec.border_color,
            }

        kwargs: Dict[str, Any] = {
            "x": spec.x_positions if spec.x_positions else spec.x,
            "y": spec.y,
            "name": spec.name,
            "opacity": spec.opacity,
            "visible": spec.visible,
        }

        if marker:
            kwargs["marker"] = marker

        if spec.bar_width:
            kwargs["width"] = spec.bar_width

        if spec.offset:
            kwargs["offset"] = spec.offset

        if spec.error_y:
            kwargs["error_y"] = {
                "type": "data",
                "array": spec.error_y,
                "visible": True,
            }

        if spec.text_values:
            kwargs["text"] = spec.text_values
            kwargs["textposition"] = spec.text_position
            kwargs["textangle"] = spec.text_angle
            kwargs["textfont"] = {"size": spec.text_font_size}

        if spec.custom_data:
            if "customdata" in spec.custom_data:
                kwargs["customdata"] = spec.custom_data["customdata"]
            if "hovertemplate" in spec.custom_data:
                kwargs["hovertemplate"] = spec.custom_data["hovertemplate"]

        if spec.legendgroup:
            kwargs["legendgroup"] = spec.legendgroup

        if not spec.show_in_legend:
            kwargs["showlegend"] = False

        fig.add_trace(go.Bar(**kwargs))

    # ── line ───────────────────────────────────────────────────────────────

    @staticmethod
    def _add_line(
        fig: go.Figure,
        spec: LineTraceSpec,
        override_color: Optional[str] = None,
    ) -> None:
        """Add a ``go.Scatter`` line trace from ``LineTraceSpec``."""
        color = override_color or spec.color or None

        mode_parts = ["lines"]
        if spec.show_markers:
            mode_parts.append("markers")
        mode = "+".join(mode_parts)

        line_dict: Dict[str, Any] = {}
        if color:
            line_dict["color"] = color
        if spec.line_width:
            line_dict["width"] = spec.line_width
        if spec.line_dash and spec.line_dash != "solid":
            line_dict["dash"] = spec.line_dash

        marker_dict: Dict[str, Any] = {}
        if spec.show_markers:
            marker_dict["size"] = spec.marker_size
            marker_dict["symbol"] = spec.marker_symbol

        kwargs: Dict[str, Any] = {
            "x": spec.x,
            "y": spec.y,
            "name": spec.name,
            "mode": mode,
            "opacity": spec.opacity,
        }

        if line_dict:
            kwargs["line"] = line_dict
        if marker_dict:
            kwargs["marker"] = marker_dict

        if spec.error_y:
            kwargs["error_y"] = {
                "type": "data",
                "array": spec.error_y,
                "visible": True,
            }

        if spec.fill != "none":
            kwargs["fill"] = spec.fill

        if spec.legendgroup:
            kwargs["legendgroup"] = spec.legendgroup

        if not spec.show_in_legend:
            kwargs["showlegend"] = False

        fig.add_trace(go.Scatter(**kwargs))

    # ── scatter ────────────────────────────────────────────────────────────

    @staticmethod
    def _add_scatter(
        fig: go.Figure,
        spec: ScatterTraceSpec,
        override_color: Optional[str] = None,
    ) -> None:
        """Add a ``go.Scatter`` scatter trace from ``ScatterTraceSpec``."""
        color = override_color or spec.color or None

        marker_dict: Dict[str, Any] = {
            "size": spec.marker_size,
            "symbol": spec.marker_symbol,
        }
        if color:
            marker_dict["color"] = color
        if spec.marker_line_width:
            marker_dict["line"] = {
                "width": spec.marker_line_width,
                "color": spec.marker_line_color or "white",
            }
        if spec.colorscale:
            marker_dict["colorscale"] = spec.colorscale
        if spec.size_values:
            marker_dict["size"] = spec.size_values

        kwargs: Dict[str, Any] = {
            "x": spec.x,
            "y": spec.y,
            "name": spec.name,
            "mode": "markers",
            "marker": marker_dict,
            "opacity": spec.opacity,
        }

        if spec.error_y:
            kwargs["error_y"] = {
                "type": "data",
                "array": spec.error_y,
                "visible": True,
            }

        if spec.legendgroup:
            kwargs["legendgroup"] = spec.legendgroup

        if not spec.show_in_legend:
            kwargs["showlegend"] = False

        fig.add_trace(go.Scatter(**kwargs))

    # ── histogram ──────────────────────────────────────────────────────────

    @staticmethod
    def _add_histogram(
        fig: go.Figure,
        spec: HistogramTraceSpec,
        override_color: Optional[str] = None,
    ) -> None:
        """Add a ``go.Histogram`` trace from ``HistogramTraceSpec``."""
        color = override_color or spec.color or None

        kwargs: Dict[str, Any] = {
            "x": spec.x,
            "name": spec.name,
            "opacity": spec.opacity,
        }

        if color:
            kwargs["marker"] = {"color": color}

        if spec.nbins:
            kwargs["nbinsx"] = spec.nbins

        if spec.normalization:
            kwargs["histnorm"] = spec.normalization

        if spec.cumulative:
            kwargs["cumulative"] = {"enabled": True}

        if spec.legendgroup:
            kwargs["legendgroup"] = spec.legendgroup

        if not spec.show_in_legend:
            kwargs["showlegend"] = False

        fig.add_trace(go.Histogram(**kwargs))
