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
from collections.abc import Sequence
from typing import Any, cast

import numpy as np
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
        traces: Sequence[TraceConfig],
        ax: Axes,
        barmode: str = "group",
        palette_colors: Sequence[str] | None = None,
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
        bar_specs: list[BarTraceConfig] = [t for t in traces if isinstance(t, BarTraceConfig)]

        # Secondary Y handling
        has_secondary = any(t.yaxis == "y2" for t in traces)
        ax2: Axes | None = None
        if has_secondary:
            ax2 = ax.twinx()
            cast(Any, ax)._ring5_twin = ax2

        count = 0
        categorical_labels: list[str] = []

        for idx, trace in enumerate(traces):
            is_secondary = trace.yaxis == "y2"
            target = ax2 if (is_secondary and ax2 is not None) else ax

            # Override trace colour with palette when provided
            override_color: str | None = None
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
        bar_specs: list[BarTraceConfig],
        barmode: str,
        categorical_labels: list[str],
        override_color: str | None = None,
    ) -> None:
        """Draw a single bar trace from its ``BarTraceConfig``."""
        color = override_color or spec.color or None
        is_categorical = bool(spec.x) and isinstance(spec.x[0], str)

        # 2) Compute standard x-positions and effective bar width
        if spec.x_positions:
            # Pre-filled numeric axis (e.g., histogram overlay)
            x_pos = spec.x_positions
            eff_bar_width = spec.bar_width
            is_categorical = False
        else:
            # Categorical string axis
            x_pos, eff_bar_width = _compute_categorical_positions(spec, bar_idx, bar_specs, barmode)
            is_categorical = True

        props: dict[str, Any] = {}
        if eff_bar_width is not None:
            props["width"] = eff_bar_width
        props["edgecolor"] = "white"
        props["linewidth"] = 0.5

        # 3) Sanitize y-values (None -> np.nan)
        y_clean = [float(v) if v is not None else np.nan for v in spec.y]

        # 4) Compute stacking bottom
        if barmode == "stack" and bar_idx > 0:
            if is_categorical:
                bottom = _stack_bottom(bar_idx, bar_specs)
            else:
                bottom = _stack_bottom_numeric(bar_idx, bar_specs, x_pos)
            props["bottom"] = bottom

        # 5) Render
        color = override_color or spec.color
        if color:
            props["color"] = color

        ax.bar(x_pos, y_clean, label=spec.name, **props)

        if is_categorical and bar_idx == 0:
            base_positions = list(range(len(spec.x)))
            ax.set_xticks(base_positions)
            if not categorical_labels:
                categorical_labels.extend(str(v) for v in spec.x)
            ax.set_xticklabels(categorical_labels)

    # ── line ───────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_line(
        spec: LineTraceConfig,
        ax: Axes,
        override_color: str | None = None,
    ) -> None:
        """Draw a single line trace from its ``LineTraceConfig``."""
        props: dict[str, Any] = {}
        color = override_color or spec.color
        if color:
            props["color"] = color
        if spec.line_width:
            props["linewidth"] = spec.line_width
        if spec.line_dash:
            props["linestyle"] = _DASH_MAP.get(spec.line_dash, "-")

        y_clean = [float(v) if v is not None else np.nan for v in spec.y]
        ax.plot(spec.x, y_clean, label=spec.name, **props)

    # ── scatter ────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_scatter(
        spec: ScatterTraceConfig,
        ax: Axes,
        override_color: str | None = None,
    ) -> None:
        """Draw a single scatter trace from its ``ScatterTraceConfig``."""
        props: dict[str, Any] = {}
        color = override_color or spec.color
        if color:
            props["color"] = color
        if spec.marker_size:
            props["s"] = spec.marker_size

        y_clean = [float(v) if v is not None else np.nan for v in spec.y]
        ax.scatter(spec.x, y_clean, label=spec.name, **props)

    # ── histogram ──────────────────────────────────────────────────────────

    @staticmethod
    def _draw_histogram(
        spec: HistogramTraceConfig,
        ax: Axes,
        override_color: str | None = None,
    ) -> None:
        """Draw a single histogram trace from its ``HistogramTraceConfig``."""
        props: dict[str, Any] = {}
        color = override_color or spec.color
        if color:
            props["color"] = color

        x_clean = [float(v) if v is not None else np.nan for v in spec.x]
        ax.hist(x_clean, bins=spec.nbins, label=spec.name, **props)


# ── module-level helpers ──────────────────────────────────────────────────────

_DASH_MAP: dict[str, str] = {
    "dash": "--",
    "dot": ":",
    "dashdot": "-.",
    "longdash": "--",
    "longdashdot": "-.",
    "solid": "-",
}


def _compute_categorical_positions(
    spec: BarTraceConfig,
    bar_idx: int,
    bar_specs: list[BarTraceConfig],
    barmode: str,
) -> tuple[list[float], float]:
    """Compute bar x-positions for categorical data when not pre-filled.

    For stacked bars all traces share the same integer positions.
    For grouped bars each trace is offset so bars sit side by side.

    Returns:
        A tuple of (x_positions, effective_bar_width). It is structurally
        important that we DO NOT mutate spec.bar_width directly.
    """
    n_categories = len(spec.x)
    base = list(range(n_categories))

    if barmode == "stack":
        return ([float(b) for b in base], spec.bar_width)

    # Grouped: distribute traces around each integer tick
    n_traces = len(bar_specs)
    if n_traces <= 1:
        return ([float(b) for b in base], spec.bar_width)

    total_width = spec.bar_width * n_traces
    # Keep total group width ≤ 0.9 to avoid overlap between categories
    if total_width > 0.9:
        bar_w = 0.9 / n_traces
    else:
        bar_w = spec.bar_width

    start_offset = -(n_traces - 1) * bar_w / 2
    offset = start_offset + bar_idx * bar_w
    return ([float(b) + offset for b in base], bar_w)


def _stack_bottom(
    bar_idx: int,
    bar_specs: list[BarTraceConfig],
) -> list[float]:
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
    bar_specs: list[BarTraceConfig],
    x_positions: list[float],
) -> list[float]:
    """Compute cumulative bottom for numeric-axis stacked bars."""
    bottom = [0.0] * len(x_positions)
    for prev in bar_specs[:bar_idx]:
        prev_positions = prev.x_positions if prev.x_positions else [float(v) for v in prev.x]
        for i, xi in enumerate(x_positions):
            for j, pxi in enumerate(prev_positions):
                if abs(xi - pxi) < 1e-6 and j < len(prev.y):
                    bottom[i] += float(prev.y[j]) if prev.y[j] is not None else 0.0
                    break
    return bottom
