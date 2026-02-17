"""
Matplotlib trace renderer — converts Plotly traces to matplotlib artists.

This module bridges the gap between the Plotly-based ``FigureEngine``
(which produces ``go.Figure`` objects) and the Matplotlib canvas.  It
iterates over every trace in a Plotly figure and draws the equivalent
matplotlib artist (bar, line, scatter) on the provided ``Axes``.

Design notes:
    * **Stateless** — all methods are ``@staticmethod``.
    * **No styling** — only draws data; layout/style is handled by
      ``FigureSpecToMatplotlib.apply()``.
    * **Colour-safe** — normalises Plotly ``rgb()/rgba()/hex`` to
      matplotlib-compatible hex strings.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import plotly.graph_objects as go
from matplotlib.axes import Axes

logger = logging.getLogger(__name__)


class MatplotlibTraceRenderer:
    """Convert Plotly traces to matplotlib artists on an ``Axes``."""

    # ── public API ────────────────────────────────────────────────────────

    @staticmethod
    def render(plotly_fig: go.Figure, ax: Axes) -> int:
        """Render all traces from *plotly_fig* onto *ax*.

        Secondary-Y traces (``yaxis='y2'``) are rendered on a twin axis
        created via ``ax.twinx()``, stored as ``ax._ring5_twin``.

        Returns:
            Number of traces successfully converted.
        """
        bar_traces: List[go.Bar] = [t for t in plotly_fig.data if t.type == "bar"]
        barmode: str = getattr(plotly_fig.layout, "barmode", "group") or "group"

        # Secondary Y handling
        has_secondary = any(getattr(t, "yaxis", None) == "y2" for t in plotly_fig.data)
        ax2: Optional[Axes] = None
        if has_secondary:
            ax2 = ax.twinx()
            ax._ring5_twin = ax2  # type: ignore[attr-defined]

        count = 0
        categorical_labels: List[str] = []

        for idx, trace in enumerate(plotly_fig.data):
            is_secondary = getattr(trace, "yaxis", None) == "y2"
            target = ax2 if (is_secondary and ax2 is not None) else ax
            try:
                if trace.type == "bar":
                    MatplotlibTraceRenderer._draw_bar(
                        trace, target, idx, bar_traces, barmode, categorical_labels
                    )
                    count += 1
                elif trace.type == "scatter":
                    mode = str(trace.mode or "lines")
                    if "markers" in mode and "lines" not in mode:
                        MatplotlibTraceRenderer._draw_scatter(trace, target)
                    else:
                        MatplotlibTraceRenderer._draw_line(trace, target)
                    count += 1
                elif trace.type == "histogram":
                    MatplotlibTraceRenderer._draw_histogram(trace, target)
                    count += 1
                else:
                    logger.warning("Unsupported trace type: %s", trace.type)
            except Exception:
                logger.exception("Failed to convert trace %s", trace.name)

        return count

    # ── bar ────────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_bar(
        trace: go.Bar,
        ax: Axes,
        trace_idx: int,
        bar_traces: List[go.Bar],
        barmode: str,
        categorical_labels: List[str],
    ) -> None:
        x = _to_list(trace.x)
        y = _to_list(trace.y)
        color = _normalize_color(trace.marker.color if trace.marker else None)
        n_bars = len(bar_traces)

        is_categorical = bool(x) and isinstance(x[0], str)

        if is_categorical:
            if not categorical_labels:
                categorical_labels.extend(str(v) for v in x)

            n_pos = len(x)
            positions = list(range(n_pos))

            if barmode == "stack":
                bottom = _stack_bottom(trace_idx, bar_traces, n_pos)
                ax.bar(
                    positions,
                    y,
                    bottom=bottom,
                    label=trace.name or "",
                    color=color,
                    width=0.8,
                    edgecolor="white",
                    linewidth=0.5,
                )
            else:
                if n_bars > 1:
                    bw = 0.8 / n_bars
                    offset = -0.4 + (trace_idx + 0.5) * bw
                    xp = [p + offset for p in positions]
                else:
                    bw = 0.8
                    xp = [float(p) for p in positions]
                ax.bar(
                    xp,
                    y,
                    label=trace.name or "",
                    color=color,
                    width=bw,
                    edgecolor="white",
                    linewidth=0.5,
                )

            if trace_idx == 0:
                ax.set_xticks(positions)
                ax.set_xticklabels(categorical_labels)
        elif barmode == "stack":
            x_num = [float(v) for v in x]
            bottom = _stack_bottom_numeric(trace_idx, bar_traces, x_num)
            bw = _infer_bar_width(trace, x_num)
            ax.bar(
                x_num,
                y,
                bottom=bottom,
                label=trace.name or "",
                color=color,
                width=bw,
                edgecolor="white",
                linewidth=0.5,
            )
        else:
            ax.bar(x, y, label=trace.name or "", color=color, width=0.8)

    # ── line ───────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_line(trace: go.Scatter, ax: Axes) -> None:
        x = _to_list(trace.x)
        y = _to_list(trace.y)
        props: Dict[str, Any] = {}
        if trace.line:
            c = _normalize_color(trace.line.color)
            if c:
                props["color"] = c
            if trace.line.width:
                props["linewidth"] = trace.line.width
            if trace.line.dash:
                props["linestyle"] = _DASH_MAP.get(trace.line.dash, "-")
        ax.plot(x, y, label=trace.name or "", **props)

    # ── scatter ────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_scatter(trace: go.Scatter, ax: Axes) -> None:
        x = _to_list(trace.x)
        y = _to_list(trace.y)
        props: Dict[str, Any] = {}
        if trace.marker:
            c = _normalize_color(trace.marker.color)
            if c:
                props["color"] = c
            if trace.marker.size:
                props["s"] = trace.marker.size
        ax.scatter(x, y, label=trace.name or "", **props)

    # ── histogram ──────────────────────────────────────────────────────────

    @staticmethod
    def _draw_histogram(trace: go.Histogram, ax: Axes) -> None:
        x = _to_list(trace.x)
        props: Dict[str, Any] = {}
        if trace.marker:
            c = _normalize_color(trace.marker.color)
            if c:
                props["color"] = c
        nbins = trace.nbinsx if trace.nbinsx else 20
        ax.hist(x, bins=nbins, label=trace.name or "", **props)


# ── module-level helpers ──────────────────────────────────────────────────────

_DASH_MAP: Dict[str, str] = {
    "dash": "--",
    "dot": ":",
    "dashdot": "-.",
    "longdash": "--",
    "longdashdot": "-.",
    "solid": "-",
}


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


def _stack_bottom(
    trace_idx: int,
    bar_traces: List[go.Bar],
    n_positions: int,
) -> List[float]:
    """Compute cumulative bottom for categorical stacked bars."""
    bottom = [0.0] * n_positions
    for prev in bar_traces[:trace_idx]:
        prev_y = _to_list(prev.y)
        for i, v in enumerate(prev_y):
            if i < n_positions:
                bottom[i] += float(v) if v is not None else 0.0
    return bottom


def _stack_bottom_numeric(
    trace_idx: int,
    bar_traces: List[go.Bar],
    x_positions: List[float],
) -> List[float]:
    """Compute cumulative bottom for numeric-axis stacked bars."""
    bottom = [0.0] * len(x_positions)
    for prev in bar_traces[:trace_idx]:
        px = [float(v) for v in _to_list(prev.x)]
        py = _to_list(prev.y)
        for i, xi in enumerate(x_positions):
            for j, pxi in enumerate(px):
                if abs(xi - pxi) < 1e-6 and j < len(py):
                    bottom[i] += float(py[j]) if py[j] is not None else 0.0
                    break
    return bottom


def _infer_bar_width(trace: go.Bar, x_num: List[float]) -> float:
    """Determine bar width from trace metadata or x-spacing."""
    if hasattr(trace, "width") and trace.width is not None:
        return float(trace.width)
    if len(x_num) > 1:
        spacings = [x_num[i + 1] - x_num[i] for i in range(len(x_num) - 1)]
        pos = [s for s in spacings if s > 0.1]
        if pos:
            return min(pos) * 0.8
    return 0.8
