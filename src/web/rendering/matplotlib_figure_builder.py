"""Native Matplotlib figure allocation and shared panel drawing.

Resolved styling and neutral traces feed the same panel drawing routine in standalone
figures and dashboards. All-heatmap results without a secondary axis use one subplot
row per heatmap, with shared or per-trace colorbars.
"""

from __future__ import annotations

from dataclasses import replace

from matplotlib.axes import Axes
from matplotlib.figure import Figure as MplFigure

from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.trace_config import HeatmapTraceConfig
from src.web.rendering._matplotlib_lock import serialized_matplotlib
from src.web.rendering._heatmap_utils import compute_nice_range, compute_z_extent
from src.web.rendering._connector_protocol import (
    uses_heatmap_panels,
    validate_annotation_types,
    validate_trace_types,
)
from src.web.rendering._render_result import MatplotlibRenderResult
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer
from src.web.rendering.figure_preparation import PreparedFigure


@serialized_matplotlib
def draw_matplotlib_axes(
    prepared: PreparedFigure, ax: Axes, *, apply_margins: bool = True
) -> MatplotlibRenderResult:
    """Draw one prepared panel without preparing, resolving or allocating another figure.

    Args:
        prepared: Neutral traces and resolved styling for this panel.
        ax: Axes owned by the standalone or dashboard figure.
        apply_margins: Apply standalone figure margins; dashboards own their grid margins.

    Returns:
        Native rendering context, including categorical positions and legend handles.
    """
    result, spec = prepared.trace_result, prepared.spec
    validate_trace_types(result.traces)
    validate_annotation_types(result.annotations)
    validate_annotation_types(spec.annotations)
    rendered = MatplotlibTraceRenderer.render(
        result.traces,
        ax,
        barmode=spec.barmode,
        palette_colors=spec.color_palette or None,
        bargap=spec.dimensions.bargap,
        bargroupgap=spec.dimensions.bargroupgap,
        bar_border_width=float(prepared.config.get("bar_border_width", 0.0)),
        category_order=spec.axes.x.category_order,
    )
    FigureSpecToMatplotlib.apply(spec, ax, rendered, apply_margins=apply_margins)
    FigureSpecToMatplotlib.draw_layout_shapes(
        ax, result.separator_lines, result.shaded_regions, result.rule_lines
    )
    return rendered


@serialized_matplotlib
def build_matplotlib_figure_from_prepared(
    prepared: PreparedFigure,
) -> tuple[MplFigure, FigureConfig]:
    """Allocate and draw a native figure from its already resolved preparation.

    Args:
        prepared: The single neutral preparation of the registered plot.

    Returns:
        Native figure and the exact resolved specification used to render it.
    """
    # [impl->req~ring5.render.matplotlib~1]
    return _assemble_matplotlib_figure(prepared)


def _assemble_matplotlib_figure(
    prepared: PreparedFigure,
) -> tuple[MplFigure, FigureConfig]:
    """Choose native facet geometry, then draw the prepared traces and styling."""
    result, spec = prepared.trace_result, prepared.spec
    validate_trace_types(result.traces)
    validate_annotation_types(result.annotations)
    validate_annotation_types(spec.annotations)

    import matplotlib.pyplot as plt

    # 2a. Multi-heatmap: one subplot row per heatmap trace
    heatmap_traces = [t for t in result.traces if isinstance(t, HeatmapTraceConfig)]
    if uses_heatmap_panels(result):
        return _build_multi_heatmap(heatmap_traces, spec), spec

    # 3. Blank figure + 4. traces + 5. styling + 5b. layout shapes
    mpl_fig, ax = FigureSpecToMatplotlib.create_figure(spec)
    try:
        draw_matplotlib_axes(prepared, ax)
    except Exception:
        plt.close(mpl_fig)
        raise

    return mpl_fig, spec


def _build_multi_heatmap(
    heatmap_traces: list[HeatmapTraceConfig],
    spec: FigureConfig,
) -> MplFigure:
    """One subplot row per heatmap trace, with shared or per-trace colorbars."""
    import matplotlib.pyplot as plt

    n = len(heatmap_traces)

    # Compute shared vmin/vmax from ColorbarConfig
    cbar_cfg = spec.legends[0].colorbar if spec.legends else None
    if (
        cbar_cfg
        and cbar_cfg.range_mode == "manual"
        and cbar_cfg.zmin is not None
        and cbar_cfg.zmax is not None
    ):
        vmin, vmax = float(cbar_cfg.zmin), float(cbar_cfg.zmax)
    else:
        raw_min, raw_max = compute_z_extent(heatmap_traces)
        nticks = cbar_cfg.nticks if cbar_cfg else 5
        vmin, vmax, _ = compute_nice_range(raw_min, raw_max, nticks)

    shared = cbar_cfg.shared if cbar_cfg else True
    mpl_fig, axes_list = FigureSpecToMatplotlib.create_multi_figure(spec, n)

    try:
        render_results: list[MatplotlibRenderResult] = []
        for i, trace in enumerate(heatmap_traces):
            ax = axes_list[i]
            # Per-trace range when not shared
            if shared or (cbar_cfg is not None and cbar_cfg.range_mode == "manual"):
                t_vmin, t_vmax = vmin, vmax
            else:
                t_min, t_max = compute_z_extent([trace])
                nticks = cbar_cfg.nticks if cbar_cfg else 5
                t_vmin, t_vmax, _ = compute_nice_range(t_min, t_max, nticks)

            rr = MatplotlibTraceRenderer.render(
                [trace],
                ax,
                heatmap_vmin=t_vmin,
                heatmap_vmax=t_vmax,
            )
            render_results.append(rr)

            # Apply styling per-axes (skip colorbar — handled below)
            FigureSpecToMatplotlib.apply(spec, ax, render_result=replace(rr, heatmap_image=None))
            ax.set_title(trace.name)
            if i < n - 1:
                ax.set_xlabel("")
                ax.tick_params(axis="x", labelbottom=False, labeltop=False)

        FigureSpecToMatplotlib.apply_multi_heatmap_colorbars(
            spec,
            mpl_fig,
            axes_list,
            render_results,
        )
    except Exception:
        plt.close(mpl_fig)
        raise

    return mpl_fig
