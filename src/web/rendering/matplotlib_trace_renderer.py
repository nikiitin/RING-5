"""
Matplotlib trace renderer — draws ``TraceConfig`` instances on matplotlib axes.

This module is the **engine-agnostic** trace renderer for the matplotlib
connector.  It reads from ``TraceConfig`` sub-classes (``BarTraceConfig``,
``LineTraceConfig``, ``ScatterTraceConfig``, ``HistogramTraceConfig``,
``HeatmapTraceConfig``) and draws the equivalent matplotlib artists.

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
    HeatmapTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)
from src.web.rendering._heatmap_utils import is_dark_cell
from src.web.rendering._render_result import MatplotlibRenderResult

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
        bargap: float = 0.2,
        bargroupgap: float = 0.0,
        bar_border_width: float = 0.0,
        heatmap_vmin: float | None = None,
        heatmap_vmax: float | None = None,
    ) -> MatplotlibRenderResult:
        """Render all traces onto *ax*.

        Args:
            traces: Ordered list of ``TraceConfig`` instances to draw.
            ax: The matplotlib axes to draw on.
            barmode: Bar arrangement mode (``"group"`` or ``"stack"``).
            palette_colors: Resolved palette hex colours.  When supplied,
                each trace is coloured ``palette_colors[idx]`` instead of
                using the colour embedded in the ``TraceConfig``.  This
                ensures the user-selected palette is respected.
            bargap: Gap between bar groups (0.0–1.0).
            bargroupgap: Gap between bars within a group (0.0–1.0).
            bar_border_width: Border width around each bar (stacked).

        Secondary-Y traces (``yaxis='y2'``) are rendered on a twin axis
        created via ``ax.twinx()``, stored as ``ax._ring5_twin``.

        Returns:
            A ``MatplotlibRenderResult`` with trace count and heatmap metadata.
        """
        # Collect bar traces for stacking computation
        bar_specs: list[BarTraceConfig] = [t for t in traces if isinstance(t, BarTraceConfig)]

        # Secondary Y handling
        has_secondary = any(t.yaxis == "y2" for t in traces)
        ax2: Axes | None = None
        if has_secondary:
            ax2 = ax.twinx()
            cast(Any, ax)._ring5_twin = ax2

        result = MatplotlibRenderResult()
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
                        bargap=bargap,
                        bargroupgap=bargroupgap,
                        bar_border_width=bar_border_width,
                    )
                    result.trace_count += 1
                elif isinstance(trace, LineTraceConfig):
                    MatplotlibTraceRenderer._draw_line(
                        trace,
                        target,
                        override_color=override_color,
                    )
                    result.trace_count += 1
                elif isinstance(trace, ScatterTraceConfig):
                    MatplotlibTraceRenderer._draw_scatter(
                        trace,
                        target,
                        override_color=override_color,
                    )
                    result.trace_count += 1
                elif isinstance(trace, HistogramTraceConfig):
                    MatplotlibTraceRenderer._draw_histogram(
                        trace,
                        target,
                        override_color=override_color,
                    )
                    result.trace_count += 1
                elif isinstance(trace, HeatmapTraceConfig):
                    MatplotlibTraceRenderer._draw_heatmap(
                        trace,
                        target,
                        result,
                        vmin=heatmap_vmin,
                        vmax=heatmap_vmax,
                    )
                    result.trace_count += 1
                else:
                    logger.warning(
                        "Unknown TraceConfig type: %s",
                        type(trace).__name__,
                    )
            except Exception:
                logger.exception("Failed to render trace %s", trace.name)

        return result

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
        bargap: float = 0.2,
        bargroupgap: float = 0.0,
        bar_border_width: float = 0.0,
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
            x_pos, eff_bar_width = _compute_categorical_positions(
                spec, bar_idx, bar_specs, barmode, bargap, bargroupgap
            )
            is_categorical = True

        props: dict[str, Any] = {}
        if eff_bar_width is not None:
            props["width"] = eff_bar_width

        # Bar border: controls visual separation between stacked items
        if bar_border_width > 0:
            props["edgecolor"] = "white"
            props["linewidth"] = bar_border_width
        else:
            props["edgecolor"] = "none"
            props["linewidth"] = 0

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
            ax.xaxis.set_ticks(base_positions)
            if not categorical_labels:
                categorical_labels.extend(str(v) for v in spec.x)
            ax.xaxis.set_ticklabels(categorical_labels)

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
        # Markers: honour show_markers/marker_symbol/marker_size so the matplotlib
        # engine matches Plotly's "lines+markers" mode (dot-lines, dual-axis dots).
        if spec.show_markers:
            props["marker"] = _MARKER_MAP.get(spec.marker_symbol, "o")
            if spec.marker_size:
                props["markersize"] = float(spec.marker_size)

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

    # ── heatmap ─────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_heatmap(
        spec: HeatmapTraceConfig,
        ax: Axes,
        result: MatplotlibRenderResult,
        vmin: float | None = None,
        vmax: float | None = None,
    ) -> None:
        """Draw a heatmap from its ``HeatmapTraceConfig``.

        Uses ``ax.pcolormesh()`` so the output is pure vector graphics,
        enabling PGF/TikZ export without raster-image errors.
        """
        if not spec.z:
            return

        # Build z-matrix replacing None with NaN
        z_array = np.array(
            [[float(v) if v is not None else np.nan for v in row] for row in spec.z],
            dtype=float,
        )

        # Map Plotly colorscale names to matplotlib equivalents.
        # Palette-derived colorscales arrive as [[pos, hex], ...] lists;
        # string names use the static lookup table.
        cmap: Any
        if isinstance(spec.colorscale, list):
            from matplotlib.colors import LinearSegmentedColormap

            hex_colors = [str(pair[1]) for pair in spec.colorscale]
            cmap = LinearSegmentedColormap.from_list("custom_palette", hex_colors)
        else:
            cmap = _COLORSCALE_MAP.get(spec.colorscale.lower(), spec.colorscale)

        # pcolormesh draws vector quadrilaterals (PGF-safe) instead of a
        # raster bitmap (imshow).  Explicit edge arrays make each cell span
        # one unit so that cell centres sit at (col + 0.5, row + 0.5).
        n_rows, n_cols = z_array.shape
        mesh_kwargs: dict[str, Any] = {
            "cmap": cmap,
            "shading": "flat",
        }
        if vmin is not None:
            mesh_kwargs["vmin"] = vmin
        if vmax is not None:
            mesh_kwargs["vmax"] = vmax
        im = ax.pcolormesh(
            np.arange(n_cols + 1),
            np.arange(n_rows + 1),
            z_array,
            **mesh_kwargs,
        )
        ax.invert_yaxis()  # row 0 at top, matching matrix convention
        ax.set_aspect("auto")
        result.heatmap_image = im

        if spec.col_labels:
            result.heatmap_col_labels = spec.col_labels
        if spec.row_labels:
            result.heatmap_row_labels = spec.row_labels

        # Cell annotations — placed at cell centres (col+0.5, row+0.5)
        if spec.show_values and spec.text:
            font_size = spec.text_font_size or 8
            for i, text_row in enumerate(spec.text):
                for j, cell_text in enumerate(text_row):
                    if cell_text:
                        if spec.text_color_mode == "custom":
                            color = spec.text_color
                        else:
                            dark = is_dark_cell(z_array, i, j)  # type: ignore[arg-type]
                            color = "white" if dark else "black"
                        ax.text(
                            j + 0.5,
                            i + 0.5,
                            cell_text,
                            ha="center",
                            va="center",
                            fontsize=font_size,
                            color=color,
                        )

        # Totals separator lines
        if spec.totals_position and spec.totals_count > 0:
            if spec.totals_position == "right" and n_cols > 1:
                # Vertical line before the totals column
                x_pos = n_cols - spec.totals_count
                ax.axvline(x=x_pos, color="black", linewidth=2, zorder=5)
            elif spec.totals_position == "top" and n_rows > 1:
                # Horizontal line below the totals row (first row)
                y_pos = spec.totals_count
                ax.axhline(y=y_pos, color="black", linewidth=2, zorder=5)


# ── module-level helpers ──────────────────────────────────────────────────────

_COLORSCALE_MAP: dict[str, str] = {
    "viridis": "viridis",
    "viridis_r": "viridis_r",
    "plasma": "plasma",
    "plasma_r": "plasma_r",
    "inferno": "inferno",
    "inferno_r": "inferno_r",
    "magma": "magma",
    "magma_r": "magma_r",
    "cividis": "cividis",
    "cividis_r": "cividis_r",
    "blues": "Blues",
    "blues_r": "Blues_r",
    "reds": "Reds",
    "reds_r": "Reds_r",
    "greens": "Greens",
    "greens_r": "Greens_r",
    "ylgnbu": "YlGnBu",
    "ylgnbu_r": "YlGnBu_r",
    "rdbu": "RdBu",
    "rdbu_r": "RdBu_r",
    "hot": "hot",
    "hot_r": "hot_r",
    "ylorrd": "YlOrRd",
    "ylorrd_r": "YlOrRd_r",
    "rdylgn": "RdYlGn",
    "rdylgn_r": "RdYlGn_r",
}


_DASH_MAP: dict[str, str] = {
    "dash": "--",
    "dot": ":",
    "dashdot": "-.",
    "longdash": "--",
    "longdashdot": "-.",
    "solid": "-",
}

# Plotly marker-symbol names -> matplotlib marker codes. Keeps the matplotlib
# engine's markers consistent with the Plotly path (which uses "lines+markers").
_MARKER_MAP: dict[str, str] = {
    "circle": "o",
    "square": "s",
    "diamond": "D",
    "cross": "+",
    "x": "x",
    "triangle-up": "^",
    "triangle-down": "v",
    "star": "*",
}


def _compute_categorical_positions(
    spec: BarTraceConfig,
    bar_idx: int,
    bar_specs: list[BarTraceConfig],
    barmode: str,
    bargap: float = 0.2,
    bargroupgap: float = 0.0,
) -> tuple[list[float], float]:
    """Compute bar x-positions for categorical data when not pre-filled.

    For stacked bars all traces share the same integer positions.
    For grouped bars each trace is offset so bars sit side by side.

    Args:
        bargap: Gap between bar groups (0.0–1.0).  A value of 0.2 means
            20% of the available space between integer ticks is empty.
        bargroupgap: Gap between bars within a group (0.0–1.0).

    Returns:
        A tuple of (x_positions, effective_bar_width).
    """
    n_categories = len(spec.x)
    base = list(range(n_categories))

    # Available width for one group = 1.0 - bargap
    group_width = max(0.05, 1.0 - bargap)

    if barmode == "stack":
        return ([float(b) for b in base], group_width)

    # Grouped: distribute traces around each integer tick
    n_traces = len(bar_specs)
    if n_traces <= 1:
        return ([float(b) for b in base], group_width)

    # Each bar gets (group_width / n_traces) minus inner gap
    bar_w = group_width / n_traces
    if bargroupgap > 0:
        bar_w = bar_w * (1.0 - bargroupgap)

    # Ensure minimum visible width
    bar_w = max(0.01, bar_w)

    # Total span occupied by all bars + inner gaps
    step = group_width / n_traces
    start_offset = -(n_traces - 1) * step / 2
    offset = start_offset + bar_idx * step
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
