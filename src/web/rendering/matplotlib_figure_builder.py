"""Native Matplotlib figure allocation and shared panel drawing.

Resolved styling and neutral traces feed the same panel drawing routine in standalone
figures and dashboards. All-heatmap results without a secondary axis use one subplot
row per heatmap, with shared or per-trace colorbars.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import plotly.graph_objects as go
from matplotlib.axes import Axes
from matplotlib.figure import Figure as MplFigure

from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.trace_build_result import (
    RuleLine,
    SeparatorLine,
    ShadedRegion,
    TraceBuildResult,
)
from src.core.models.visualization.trace_config import HeatmapTraceConfig, TraceConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering._heatmap_utils import compute_nice_range, compute_z_extent
from src.web.rendering._connector_protocol import (
    uses_heatmap_panels,
    validate_annotation_types,
    validate_trace_types,
)
from src.web.rendering._render_result import MatplotlibRenderResult
from src.web.rendering.config_builder import (
    ConfigSpecBuilder,
    PlotlyFigureSpecBuilder,
    enrich_from_traces,
)
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer
from src.web.rendering.figure_preparation import PreparedFigure


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


def build_matplotlib_figure(
    plotly_fig: go.Figure,
    config: dict[str, Any],
    plot_type: str,
    traces: list[TraceConfig] | None = None,
    separator_lines: list[SeparatorLine] | None = None,
    shaded_regions: list[ShadedRegion] | None = None,
    rule_lines: list[RuleLine] | None = None,
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
        rule_lines: Category super-group span rules from the trace build.

    Returns:
        ``(figure, resolved_spec)`` — the spec is what PGF export needs
        for the LaTeX preamble.

    Raises:
        Whatever the connectors raise; the partially built figure is
        closed first (no pyplot registration leak on failure).
    """
    traces = traces or []

    # 1. Build and resolve FigureConfig (enriched from the styled plotly fig)
    spec = ConfigSpecBuilder.from_config(config, plot_type)
    PlotlyFigureSpecBuilder.enrich_from_plotly(spec, plotly_fig)
    spec = resolve_config(spec)
    result = TraceBuildResult(
        traces=traces,
        separator_lines=separator_lines or [],
        shaded_regions=shaded_regions or [],
        rule_lines=rule_lines or [],
        secondary_y=any(trace.yaxis == "y2" for trace in traces),
    )
    return _assemble_matplotlib_figure(PreparedFigure(config, result, spec))


def build_matplotlib_figure_from_traces(
    config: dict[str, Any],
    plot_type: str,
    result: Any,
) -> tuple[MplFigure, FigureConfig]:
    """Build a fully styled matplotlib figure straight from a ``TraceBuildResult``.

    The spec is built from configuration and neutral trace metadata before native
    figure allocation. This direct trace consumer does not construct a Plotly figure.

    Args:
        config: The plot's config dict.
        plot_type: Registry key (``bar``, ``grouped_stacked_bar``, …).
        result: The ``TraceBuildResult`` from ``plot.create_traces`` (post legend relabel).

    Returns:
        ``(figure, resolved_spec)`` — the spec is what PGF export needs.
    """
    spec = ConfigSpecBuilder.from_config(config, plot_type)
    enrich_from_traces(spec, result)
    spec = resolve_config(spec)
    return _assemble_matplotlib_figure(PreparedFigure(config, result, spec))


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

    y2 = spec.axes.y2 if spec.axes is not None else None
    if y2 is not None:
        twin.set_yscale(y2.scale)
        if y2.range is not None:
            twin.set_ylim(*y2.range)
        if y2.tick_values is not None:
            twin.set_yticks([float(value) for value in y2.tick_values], y2.tick_text)
        elif y2.dtick is not None and y2.dtick > 0 and y2.scale == "linear":
            from matplotlib.ticker import MultipleLocator

            twin.yaxis.set_major_locator(MultipleLocator(y2.dtick))
        on_left = y2.tick_side == "left"
        twin.tick_params(
            axis="y",
            left=on_left and y2.show_ticks,
            right=not on_left and y2.show_ticks,
            labelleft=on_left and y2.show_tick_labels,
            labelright=not on_left and y2.show_tick_labels,
            pad=y2.tick_pad,
            labelrotation=y2.tick_angle,
            colors=y2.tick_font_color or y2.axis_color,
        )
        if y2.show_grid:
            twin.yaxis.grid(
                True,
                color=y2.grid_color,
                linewidth=y2.grid_width,
                linestyle=FigureSpecToMatplotlib._map_dash_style(y2.grid_dash),
                alpha=y2.grid_alpha,
            )
        else:
            twin.yaxis.grid(False)
        twin.yaxis.label.set_color(y2.axis_color)
        twin.yaxis.labelpad = y2.label_standoff if y2.label_standoff >= 0 else y2.label_pad
        twin.yaxis.label.set_y(y2.label_position + y2.title_vshift / 100.0)
        twin.spines["right"].set_color(y2.axis_line_color or y2.axis_color)
        twin.spines["right"].set_linewidth(y2.axis_line_width)
        for text in twin.get_yticklabels():
            if font_family:
                text.set_fontfamily(font_family)

    # Explicit right-axis range + tick font (matches the Plotly y2 handling).
    rng = config.get("range_y2")
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        twin.set_ylim(float(rng[0]), float(rng[1]))
    if typo is not None and typo.font_size_y2ticks > 0:
        twin.tick_params(axis="y", labelsize=typo.font_size_y2ticks)

    primary = getattr(twin, "_ring5_primary", None)
    if primary is not None and config.get("unified_legend", True):
        handles, labels = primary.get_legend_handles_labels()
        right_handles, right_labels = twin.get_legend_handles_labels()
        if handles or right_handles:
            # Reuse the primary legend's complete positioning and typography contract.
            FigureSpecToMatplotlib._apply_legends(
                spec, primary, extra_handles=(right_handles, right_labels)
            )
        return

    # A legend for the right-axis (twin) series — matplotlib's primary legend on the
    # base axes only sees the left-axis handles. Position/style are configurable via
    # the legend2_* keys (emitted by DualAxisOpts.legend); when none are given it
    # falls back to the historic upper-right placement.
    handles, labels = twin.get_legend_handles_labels()
    if handles:
        legend_kwargs: dict[str, Any] = {}
        dx, dy = config.get("legend2_x"), config.get("legend2_y")
        if dx is not None and dy is not None:
            legend_kwargs["loc"] = FigureSpecToMatplotlib._anchor_to_mpl_loc(
                str(config.get("legend2_anchor_x", "left")),
                str(config.get("legend2_anchor_y", "top")),
            )
            legend_kwargs["bbox_to_anchor"] = (float(dx), float(dy))
        else:
            legend_kwargs["loc"] = "upper right"
        ncols = config.get("legend2_ncols")
        if ncols is not None:
            legend_kwargs["ncol"] = max(1, int(ncols))
        bg = config.get("legend2_bgcolor")
        if bg:
            legend_kwargs["facecolor"] = str(bg)
        ba = config.get("legend2_bgalpha")
        if ba is not None:
            legend_kwargs["framealpha"] = float(ba)
        elif bg:
            legend_kwargs["framealpha"] = 1.0  # opaque when an explicit bg is set
        else:
            legend_kwargs["framealpha"] = 0.85
        bc = config.get("legend2_border_color")
        if bc:
            legend_kwargs["edgecolor"] = str(bc)
        dfs = config.get("legend2_font_size")
        size = (
            float(dfs)
            if dfs is not None
            else (
                float(typo.font_size_legend2)
                if (typo is not None and typo.font_size_legend2 > 0)
                else None
            )
        )
        prop: dict[str, Any] = {}
        if font_family:
            prop["family"] = font_family
        if size is not None:
            # fontsize is ignored when prop is given — fold it into prop.
            if prop:
                prop["size"] = size
            else:
                legend_kwargs["fontsize"] = size
        if prop:
            legend_kwargs["prop"] = prop
        iw = config.get("legend2_itemwidth")
        if iw is not None and size:
            legend_kwargs["handlelength"] = float(iw) / float(size)
        htp = config.get("legend2_handletextpad")
        if htp is not None:
            legend_kwargs["handletextpad"] = float(htp)
        leg = twin.legend(handles, labels, **legend_kwargs)
        if leg is not None:
            leg.set_zorder(10)


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
