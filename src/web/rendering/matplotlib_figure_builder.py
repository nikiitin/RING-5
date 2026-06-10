"""One matplotlib figure builder — the single render sequence, UI-free.

Both consumers of the matplotlib engine build their figures here:
``ChartDisplayComponent`` (which adds the Streamlit display + session
caching around it) and the public ``ring5`` package (headless). Keeping
one implementation is what guarantees the app preview and a headless
export of the same plot are the same figure.

The sequence (after the engine-agnostic traces and the styled plotly
figure exist): build ``FigureConfig`` from the plot config → enrich it
from the styled plotly figure (tick vals/text, annotations, barmode,
legend3) → resolve sentinels → create the figure → render traces → apply
the styling pipeline → draw layout shapes → dual-axis twin fix-up.
Multi-heatmap traces branch to one subplot row per heatmap with shared or
per-trace colorbars.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from matplotlib.axes import Axes
from matplotlib.figure import Figure as MplFigure

from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.trace_build_result import SeparatorLine, ShadedRegion
from src.core.models.visualization.trace_config import HeatmapTraceConfig, TraceConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering._heatmap_utils import compute_nice_range, compute_z_extent
from src.web.rendering._render_result import MatplotlibRenderResult
from src.web.rendering.config_builder import ConfigSpecBuilder, PlotlyFigureSpecBuilder
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer


def build_matplotlib_figure(
    plotly_fig: go.Figure,
    config: dict[str, Any],
    plot_type: str,
    traces: list[TraceConfig] | None = None,
    separator_lines: list[SeparatorLine] | None = None,
    shaded_regions: list[ShadedRegion] | None = None,
) -> tuple[MplFigure, FigureConfig]:
    """Build a fully styled matplotlib figure from a styled plotly figure.

    Args:
        plotly_fig: The STYLED plotly figure (``create_figure`` +
            ``apply_common_layout``) — the enrichment source for tick
            values/labels, annotations, barmode and legend3.
        config: The plot's config dict.
        plot_type: Registry key (``bar``, ``heatmap``, …).
        traces: Engine-agnostic traces (``plot.last_traces.traces``).
        separator_lines: Bar-group separators from the trace build.
        shaded_regions: Alternate-shading bands from the trace build.

    Returns:
        ``(figure, resolved_spec)`` — the spec is what PGF export needs
        for the LaTeX preamble.

    Raises:
        Whatever the connectors raise; the partially built figure is
        closed first (no pyplot registration leak on failure).
    """
    import matplotlib.pyplot as plt

    traces = traces or []

    # 1. Build and resolve FigureConfig (enriched from the styled plotly fig)
    spec = ConfigSpecBuilder.from_config(config, plot_type)
    PlotlyFigureSpecBuilder.enrich_from_plotly(spec, plotly_fig)
    spec = resolve_config(spec)

    # 2a. Multi-heatmap: one subplot row per heatmap trace
    heatmap_traces = [t for t in traces if isinstance(t, HeatmapTraceConfig)]
    if len(heatmap_traces) > 1:
        return _build_multi_heatmap(heatmap_traces, spec), spec

    # 3. Blank figure + 4. traces + 5. styling + 5b. layout shapes
    mpl_fig, ax = FigureSpecToMatplotlib.create_figure(spec)
    try:
        render_result = MatplotlibTraceRenderer.render(
            traces,
            ax,
            barmode=spec.barmode,
            palette_colors=spec.color_palette or None,
            bargap=spec.dimensions.bargap,
            bargroupgap=spec.dimensions.bargroupgap,
            bar_border_width=float(config.get("bar_border_width", 0.0)),
        )
        FigureSpecToMatplotlib.apply(spec, ax, render_result)
        FigureSpecToMatplotlib.draw_layout_shapes(ax, separator_lines or [], shaded_regions or [])

        # 5c. Dual-axis parity: right-axis title + legend on the twin
        twin = getattr(ax, "_ring5_twin", None)
        if twin is not None:
            apply_dual_axis(twin, config, spec)
    except Exception:
        plt.close(mpl_fig)
        raise

    return mpl_fig, spec


def apply_dual_axis(twin: Axes, config: dict[str, Any], spec: FigureConfig) -> None:
    """Give the matplotlib twin (right) axis its Y-title and a legend.

    matplotlib already renders right-axis traces on the twin; this fills
    the remaining gap so dual-axis charts match Plotly (secondary title +
    right-axis series in a legend).
    """
    typo = spec.typography
    font_family = spec.font_family

    ylabel_right = config.get("ylabel_right")
    if ylabel_right:
        label_kwargs: dict[str, Any] = {}
        if typo is not None and typo.font_size_y2label > 0:
            label_kwargs["fontsize"] = typo.font_size_y2label
        if typo is not None and typo.bold_y2label:
            label_kwargs["fontweight"] = "bold"
        # These artists are created after the connector's rc_context
        # exits, so the family must be set explicitly.
        if font_family:
            label_kwargs["fontfamily"] = font_family
        twin.set_ylabel(str(ylabel_right), **label_kwargs)

    # A legend for the right-axis (twin) series — matplotlib's primary
    # legend on the base axes only sees the left-axis handles.
    handles, labels = twin.get_legend_handles_labels()
    if handles:
        legend_kwargs: dict[str, Any] = {"loc": "upper right", "framealpha": 0.85}
        prop: dict[str, Any] = {}
        if font_family:
            prop["family"] = font_family
        if typo is not None and typo.font_size_legend2 > 0:
            # fontsize is ignored when prop is given — fold it into prop.
            if prop:
                prop["size"] = typo.font_size_legend2
            else:
                legend_kwargs["fontsize"] = typo.font_size_legend2
        if prop:
            legend_kwargs["prop"] = prop
        twin.legend(handles, labels, **legend_kwargs)


def _build_multi_heatmap(
    heatmap_traces: list[HeatmapTraceConfig],
    spec: FigureConfig,
) -> MplFigure:
    """One subplot row per heatmap trace, with shared or per-trace colorbars."""
    import matplotlib.pyplot as plt

    n = len(heatmap_traces)
    mpl_fig, axes_list = FigureSpecToMatplotlib.create_multi_figure(spec, n)

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

    try:
        render_results: list[MatplotlibRenderResult] = []
        for i, trace in enumerate(heatmap_traces):
            ax = axes_list[i]
            # Per-trace range when not shared
            if shared:
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
            FigureSpecToMatplotlib.apply(spec, ax, render_result=None)
            ax.set_title(trace.name)

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
