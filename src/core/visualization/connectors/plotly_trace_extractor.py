"""
Plotly trace extractor — converts ``go.Figure.data`` to ``TraceConfig`` list.

This adapter sits in the Plotly-facing part of the connector layer.
It reads Plotly-specific trace attributes and produces engine-agnostic
``TraceConfig`` instances that the Matplotlib connector can render
without ever importing Plotly.

Design notes:
    * **Stateless** — all methods are ``@staticmethod``.
    * **One-way** — Plotly → TraceConfig only; the reverse is done by
      ``PlotlyConnector``.
    * **Colour-safe** — normalises ``rgb()/rgba()`` to hex strings.
"""

from __future__ import annotations

import logging
import re
from typing import Any, List, Literal, Optional

import plotly.graph_objects as go

from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)

logger = logging.getLogger(__name__)


class PlotlyTraceExtractor:
    """Extract ``TraceConfig`` instances from a Plotly ``go.Figure``."""

    @staticmethod
    def extract(fig: go.Figure) -> List[TraceConfig]:
        """Convert every trace in *fig* to a ``TraceConfig``.

        Args:
            fig: A finalised Plotly figure.

        Returns:
            Ordered list of ``TraceConfig`` sub-class instances.
            Unsupported trace types are logged and skipped.
        """
        specs: List[TraceConfig] = []
        bar_traces: List[go.Bar] = [t for t in fig.data if t.type == "bar"]
        barmode: str = getattr(fig.layout, "barmode", "group") or "group"

        for idx, trace in enumerate(fig.data):
            try:
                spec = PlotlyTraceExtractor._convert_trace(trace, idx, bar_traces, barmode)
                if spec is not None:
                    specs.append(spec)
            except Exception:
                logger.exception(
                    "Failed to extract trace %d (%s)", idx, getattr(trace, "name", "?")
                )
        return specs

    @staticmethod
    def extract_barmode(fig: go.Figure) -> str:
        """Return the barmode from the figure layout."""
        return str(getattr(fig.layout, "barmode", "group") or "group")

    # ── private dispatch ──────────────────────────────────────────────────

    @staticmethod
    def _convert_trace(
        trace: Any,
        idx: int,
        bar_traces: List[go.Bar],
        barmode: str,
    ) -> Optional[TraceConfig]:
        """Dispatch a single trace to the correct extractor."""
        ttype = getattr(trace, "type", None)
        if ttype == "bar":
            return PlotlyTraceExtractor._extract_bar(trace, idx, bar_traces, barmode)
        if ttype == "scatter":
            mode = str(getattr(trace, "mode", "lines") or "lines")
            if "markers" in mode and "lines" not in mode:
                return PlotlyTraceExtractor._extract_scatter(trace)
            return PlotlyTraceExtractor._extract_line(trace)
        if ttype == "histogram":
            return PlotlyTraceExtractor._extract_histogram(trace)
        logger.warning("Unsupported Plotly trace type: %s", ttype)
        return None

    # ── bar ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_bar(
        trace: go.Bar,
        idx: int,
        bar_traces: List[go.Bar],
        barmode: str,
    ) -> BarTraceConfig:
        """Convert a ``go.Bar`` trace to ``BarTraceConfig``."""
        x_raw = _to_list(trace.x)
        y_raw = _to_list(trace.y)
        color = _normalize_color(trace.marker.color if trace.marker else None) or ""

        # Pre-compute positions for categorical data
        is_categorical = bool(x_raw) and isinstance(x_raw[0], str)
        n_bars = len(bar_traces)
        bar_idx = bar_traces.index(trace) if trace in bar_traces else idx

        x_positions: List[float]
        bar_width: float
        offset: float = 0.0

        if is_categorical:
            n_pos = len(x_raw)
            positions = list(range(n_pos))

            if barmode == "stack":
                x_positions = [float(p) for p in positions]
                bar_width = 0.8
            elif n_bars > 1:
                bw = 0.8 / n_bars
                bar_width = bw
                offset = -0.4 + (bar_idx + 0.5) * bw
                x_positions = [p + offset for p in positions]
            else:
                bar_width = 0.8
                x_positions = [float(p) for p in positions]
        else:
            # Numeric x — use as-is
            x_positions = [float(v) for v in x_raw]
            bar_width = _infer_bar_width_from_list(trace, x_positions)

        # Error bars
        error_y = _extract_error_y(trace)

        # Pattern / hatching
        pattern = ""
        if trace.marker and hasattr(trace.marker, "pattern"):
            pat = trace.marker.pattern
            if pat is not None:
                shape = getattr(pat, "shape", None)
                if shape:
                    pattern = str(shape)

        # Border
        border_width = 0.0
        border_color = ""
        if trace.marker and hasattr(trace.marker, "line"):
            mline = trace.marker.line
            if mline is not None:
                bw_val = getattr(mline, "width", None)
                if bw_val is not None:
                    border_width = float(bw_val)
                bc = getattr(mline, "color", None)
                if bc is not None:
                    border_color = _normalize_color(bc) or ""

        # Text labels
        text_values: Optional[List[str]] = None
        text_raw = getattr(trace, "text", None)
        if text_raw is not None:
            text_values = [str(t) for t in _to_list(text_raw)]

        text_position_raw = getattr(trace, "textposition", "none") or "none"
        tp_map = {"inside": "inside", "outside": "outside", "auto": "auto"}
        text_position: str = tp_map.get(text_position_raw, "none")

        return BarTraceConfig(
            name=str(getattr(trace, "name", "") or ""),
            x=x_raw,
            y=[float(v) if v is not None else 0.0 for v in y_raw],
            yaxis=_extract_yaxis(trace),
            color=color,
            opacity=float(getattr(trace, "opacity", 1.0) or 1.0),
            visible=bool(getattr(trace, "visible", True)),
            show_in_legend=bool(getattr(trace, "showlegend", True)),
            legendgroup=str(getattr(trace, "legendgroup", "") or ""),
            x_positions=x_positions,
            bar_width=bar_width,
            offset=offset,
            pattern=pattern,
            border_width=border_width,
            border_color=border_color,
            text_values=text_values,
            text_position=text_position,  # type: ignore[arg-type]
            error_y=error_y,
        )

    # ── line ──────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_line(trace: go.Scatter) -> LineTraceConfig:
        """Convert a ``go.Scatter`` with lines to ``LineTraceConfig``."""
        color = ""
        line_width = 2.0
        line_dash: str = "solid"

        if trace.line:
            color = _normalize_color(trace.line.color) or ""
            if trace.line.width is not None:
                line_width = float(trace.line.width)
            if trace.line.dash:
                line_dash = str(trace.line.dash)

        # Fallback colour from marker
        if not color and trace.marker:
            color = _normalize_color(trace.marker.color) or ""

        mode = str(getattr(trace, "mode", "lines") or "lines")
        show_markers = "markers" in mode

        marker_size = 6
        marker_symbol = "circle"
        if trace.marker:
            if trace.marker.size is not None:
                marker_size = int(trace.marker.size)
            if trace.marker.symbol:
                marker_symbol = str(trace.marker.symbol)

        return LineTraceConfig(
            name=str(getattr(trace, "name", "") or ""),
            x=_to_list(trace.x),
            y=[float(v) if v is not None else 0.0 for v in _to_list(trace.y)],
            yaxis=_extract_yaxis(trace),
            color=color,
            opacity=float(getattr(trace, "opacity", 1.0) or 1.0),
            visible=bool(getattr(trace, "visible", True)),
            show_in_legend=bool(getattr(trace, "showlegend", True)),
            legendgroup=str(getattr(trace, "legendgroup", "") or ""),
            line_width=line_width,
            line_dash=line_dash,  # type: ignore[arg-type]
            marker_symbol=marker_symbol,
            marker_size=marker_size,
            show_markers=show_markers,
            error_y=_extract_error_y(trace),
        )

    # ── scatter ───────────────────────────────────────────────────────────

    @staticmethod
    def _extract_scatter(trace: go.Scatter) -> ScatterTraceConfig:
        """Convert a ``go.Scatter`` with markers-only to ``ScatterTraceConfig``."""
        color = ""
        marker_size = 8
        marker_symbol = "circle"
        marker_line_width = 0.0
        marker_line_color = ""

        if trace.marker:
            color = _normalize_color(trace.marker.color) or ""
            if trace.marker.size is not None:
                marker_size = int(trace.marker.size)
            if trace.marker.symbol:
                marker_symbol = str(trace.marker.symbol)
            if hasattr(trace.marker, "line") and trace.marker.line:
                bw = getattr(trace.marker.line, "width", None)
                if bw is not None:
                    marker_line_width = float(bw)
                bc = getattr(trace.marker.line, "color", None)
                if bc is not None:
                    marker_line_color = _normalize_color(bc) or ""

        return ScatterTraceConfig(
            name=str(getattr(trace, "name", "") or ""),
            x=_to_list(trace.x),
            y=[float(v) if v is not None else 0.0 for v in _to_list(trace.y)],
            yaxis=_extract_yaxis(trace),
            color=color,
            opacity=float(getattr(trace, "opacity", 1.0) or 1.0),
            visible=bool(getattr(trace, "visible", True)),
            show_in_legend=bool(getattr(trace, "showlegend", True)),
            legendgroup=str(getattr(trace, "legendgroup", "") or ""),
            marker_symbol=marker_symbol,
            marker_size=marker_size,
            marker_line_width=marker_line_width,
            marker_line_color=marker_line_color,
            error_y=_extract_error_y(trace),
        )

    # ── histogram ─────────────────────────────────────────────────────────

    @staticmethod
    def _extract_histogram(trace: go.Histogram) -> HistogramTraceConfig:
        """Convert a ``go.Histogram`` to ``HistogramTraceConfig``."""
        color = ""
        if trace.marker:
            color = _normalize_color(trace.marker.color) or ""

        nbins = int(getattr(trace, "nbinsx", 20) or 20)

        return HistogramTraceConfig(
            name=str(getattr(trace, "name", "") or ""),
            x=_to_list(trace.x),
            y=[],
            color=color,
            opacity=float(getattr(trace, "opacity", 1.0) or 1.0),
            visible=bool(getattr(trace, "visible", True)),
            show_in_legend=bool(getattr(trace, "showlegend", True)),
            nbins=nbins,
        )


# ── module-level helpers ──────────────────────────────────────────────────────


def _to_list(val: Any) -> List[Any]:
    """Coerce trace data to a plain list."""
    if val is None:
        return []
    if hasattr(val, "tolist"):
        return val.tolist()  # type: ignore[no-any-return]
    return list(val) if not isinstance(val, list) else val


def _normalize_color(color: Any) -> Optional[str]:
    """Convert Plotly ``rgb()/rgba()/hex`` to a matplotlib hex string."""
    if not color or not isinstance(color, str):
        return None
    color = color.strip()
    m = re.match(
        r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*[\d.]+)?\s*\)",
        color,
    )
    if m:
        return "#{:02x}{:02x}{:02x}".format(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return str(color)


def _extract_yaxis(trace: Any) -> Literal["y", "y2"]:
    """Determine which Y-axis a trace targets."""
    raw = getattr(trace, "yaxis", "y") or "y"
    return "y2" if raw == "y2" else "y"


def _extract_error_y(trace: Any) -> Optional[List[float]]:
    """Extract error bar values if present."""
    ey = getattr(trace, "error_y", None)
    if ey is None:
        return None
    arr = getattr(ey, "array", None)
    if arr is None:
        return None
    raw = _to_list(arr)
    if not raw:
        return None
    return [float(v) if v is not None else 0.0 for v in raw]


def _infer_bar_width_from_list(trace: Any, x_num: List[float]) -> float:
    """Determine bar width from trace metadata or x-spacing."""
    if hasattr(trace, "width") and trace.width is not None:
        return float(trace.width)
    if len(x_num) > 1:
        spacings = [x_num[i + 1] - x_num[i] for i in range(len(x_num) - 1)]
        pos = [s for s in spacings if s > 0.1]
        if pos:
            return min(pos) * 0.8
    return 0.8
