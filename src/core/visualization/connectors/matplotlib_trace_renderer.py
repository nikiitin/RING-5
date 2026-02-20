"""
Matplotlib trace renderer — draws ``TraceConfig`` instances on matplotlib axes.

This module is the **engine-agnostic** trace renderer for the matplotlib
connector.  It reads from ``TraceConfig`` sub-classes (``BarTraceConfig``,
``LineTraceConfig``, ``ScatterTraceConfig``, ``HistogramTraceConfig``) and
draws the equivalent matplotlib artists.

**No Plotly dependency** — this module does not import or reference
``plotly.graph_objects`` or any Plotly types.

Design notes:
    * **Stateless** — all methods are ``@staticmethod``.
    * **No styling** — only draws data; layout/style is handled by
      ``FigureSpecToMatplotlib.apply()``.
    * **Pre-computed positions** — bar positions, widths, offsets are
      read directly from ``BarTraceConfig``; no grouping math here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from matplotlib.axes import Axes

from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)

logger = logging.getLogger(__name__)


class MatplotlibTraceRenderer:
    """Draw ``TraceConfig`` instances on a matplotlib ``Axes``.

    This replaces the previous implementation that read from Plotly
    ``go.Figure`` objects.  All trace data now comes from engine-agnostic
    ``TraceConfig`` dataclasses.
    """

    # ── public API ────────────────────────────────────────────────────────

    @staticmethod
    def render(
        traces: List[TraceConfig],
        ax: Axes,
        barmode: str = "group",
        palette_colors: Optional[List[str]] = None,
    ) -> int:
        """Render all traces onto *ax*.

        Args:
            traces: Ordered list of ``TraceConfig`` instances to draw.
            ax: The matplotlib axes to draw on.
            barmode: Bar arrangement mode (``"group"`` or ``"stack"``).
            palette_colors: Resolved palette hex colours.  When supplied,
                each trace is coloured ``palette_colors[idx]`` instead of
                using the colour embedded in the ``TraceConfig``.  This
                ensures the user-selected palette is respected.

        Secondary-Y traces (``yaxis='y2'``) are rendered on a twin axis
        created via ``ax.twinx()``, stored as ``ax._ring5_twin``.

        Returns:
            Number of traces successfully rendered.
        """
        # Collect bar traces for stacking computation
        bar_specs: List[BarTraceConfig] = [t for t in traces if isinstance(t, BarTraceConfig)]

        # Secondary Y handling
        has_secondary = any(t.yaxis == "y2" for t in traces)
        ax2: Optional[Axes] = None
        if has_secondary:
            ax2 = ax.twinx()
            ax._ring5_twin = ax2  # type: ignore[attr-defined]

        count = 0
        categorical_labels: List[str] = []

        for idx, trace in enumerate(traces):
            is_secondary = trace.yaxis == "y2"
            target = ax2 if (is_secondary and ax2 is not None) else ax

            # Override trace colour with palette when provided
            override_color: Optional[str] = None
            if palette_colors:
                override_color = palette_colors[idx % len(palette_colors)]

            try:
                if isinstance(trace, BarTraceConfig):
                    bar_idx = bar_specs.index(trace)
                    MatplotlibTraceRenderer._draw_bar(
                        trace,
                        target,
                        bar_idx,
                        bar_specs,
                        barmode,
                        categorical_labels,
                        override_color=override_color,
                    )
                    count += 1
                elif isinstance(trace, LineTraceConfig):
                    MatplotlibTraceRenderer._draw_line(
                        trace,
                        target,
                        override_color=override_color,
                    )
                    count += 1
                elif isinstance(trace, ScatterTraceConfig):
                    MatplotlibTraceRenderer._draw_scatter(
                        trace,
                        target,
                        override_color=override_color,
                    )
                    count += 1
                elif isinstance(trace, HistogramTraceConfig):
                    MatplotlibTraceRenderer._draw_histogram(
                        trace,
                        target,
                        override_color=override_color,
                    )
                    count += 1
                else:
                    logger.warning(
                        "Unknown TraceConfig type: %s",
                        type(trace).__name__,
                    )
            except Exception:
                logger.exception("Failed to render trace %s", trace.name)

        return count

    # ── bar ────────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_bar(
        spec: BarTraceConfig,
        ax: Axes,
        bar_idx: int,
        bar_specs: List[BarTraceConfig],
        barmode: str,
        categorical_labels: List[str],
        override_color: Optional[str] = None,
    ) -> None:
        """Draw a single bar trace from its ``BarTraceConfig``."""
        color = override_color or spec.color or None
        is_categorical = bool(spec.x) and isinstance(spec.x[0], str)

        if is_categorical:
            if not categorical_labels:
                categorical_labels.extend(str(v) for v in spec.x)

            if barmode == "stack":
                bottom = _stack_bottom(bar_idx, bar_specs)
                ax.bar(
                    spec.x_positions,
                    spec.y,
                    bottom=bottom,
                    label=spec.name,
                    color=color,
                    width=spec.bar_width,
                    edgecolor="white",
                    linewidth=0.5,
                )
            else:
                ax.bar(
                    spec.x_positions,
                    spec.y,
                    label=spec.name,
                    color=color,
                    width=spec.bar_width,
                    edgecolor="white",
                    linewidth=0.5,
                )

            if bar_idx == 0:
                base_positions = list(range(len(spec.x)))
                ax.set_xticks(base_positions)
                ax.set_xticklabels(categorical_labels)
        elif barmode == "stack":
            bottom = _stack_bottom_numeric(bar_idx, bar_specs, spec.x_positions)
            ax.bar(
                spec.x_positions,
                spec.y,
                bottom=bottom,
                label=spec.name,
                color=color,
                width=spec.bar_width,
                edgecolor="white",
                linewidth=0.5,
            )
        else:
            ax.bar(
                spec.x_positions,
                spec.y,
                label=spec.name,
                color=color,
                width=spec.bar_width,
            )

    # ── line ───────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_line(
        spec: LineTraceConfig,
        ax: Axes,
        override_color: Optional[str] = None,
    ) -> None:
        """Draw a single line trace from its ``LineTraceConfig``."""
        props: Dict[str, Any] = {}
        color = override_color or spec.color
        if color:
            props["color"] = color
        if spec.line_width:
            props["linewidth"] = spec.line_width
        if spec.line_dash:
            props["linestyle"] = _DASH_MAP.get(spec.line_dash, "-")
        ax.plot(spec.x, spec.y, label=spec.name, **props)

    # ── scatter ────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_scatter(
        spec: ScatterTraceConfig,
        ax: Axes,
        override_color: Optional[str] = None,
    ) -> None:
        """Draw a single scatter trace from its ``ScatterTraceConfig``."""
        props: Dict[str, Any] = {}
        color = override_color or spec.color
        if color:
            props["color"] = color
        if spec.marker_size:
            props["s"] = spec.marker_size
        ax.scatter(spec.x, spec.y, label=spec.name, **props)

    # ── histogram ──────────────────────────────────────────────────────────

    @staticmethod
    def _draw_histogram(
        spec: HistogramTraceConfig,
        ax: Axes,
        override_color: Optional[str] = None,
    ) -> None:
        """Draw a single histogram trace from its ``HistogramTraceConfig``."""
        props: Dict[str, Any] = {}
        color = override_color or spec.color
        if color:
            props["color"] = color
        ax.hist(spec.x, bins=spec.nbins, label=spec.name, **props)


# ── module-level helpers ──────────────────────────────────────────────────────

_DASH_MAP: Dict[str, str] = {
    "dash": "--",
    "dot": ":",
    "dashdot": "-.",
    "longdash": "--",
    "longdashdot": "-.",
    "solid": "-",
}


def _stack_bottom(
    bar_idx: int,
    bar_specs: List[BarTraceConfig],
) -> List[float]:
    """Compute cumulative bottom for stacked bars."""
    n_positions = len(bar_specs[bar_idx].y) if bar_specs else 0
    bottom = [0.0] * n_positions
    for prev in bar_specs[:bar_idx]:
        for i, v in enumerate(prev.y):
            if i < n_positions:
                bottom[i] += float(v) if v is not None else 0.0
    return bottom


def _stack_bottom_numeric(
    bar_idx: int,
    bar_specs: List[BarTraceConfig],
    x_positions: List[float],
) -> List[float]:
    """Compute cumulative bottom for numeric-axis stacked bars."""
    bottom = [0.0] * len(x_positions)
    for prev in bar_specs[:bar_idx]:
        for i, xi in enumerate(x_positions):
            for j, pxi in enumerate(prev.x_positions):
                if abs(xi - pxi) < 1e-6 and j < len(prev.y):
                    bottom[i] += float(prev.y[j]) if prev.y[j] is not None else 0.0
                    break
    return bottom
