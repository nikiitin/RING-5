"""UI-free rendering of multi-plot dashboards for both figure engines."""

from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any, Literal, cast

import plotly.graph_objects as go
from matplotlib.figure import Figure as MplFigure
from plotly.subplots import make_subplots

from src.core.models.visualization.dashboard_spec import DashboardSpec
from src.core.models.visualization.trace_config import HeatmapTraceConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.pages.ui.plotting.base_plot import BasePlot, _relabel_traces
from src.web.rendering.config_builder import ConfigSpecBuilder, enrich_from_traces
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_figure_builder import (
    _drop_dual_axis_title_annotations,
    apply_dual_axis,
)
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer

DashboardEngine = Literal["plotly", "matplotlib"]
DashboardFigure = go.Figure | MplFigure

_AXIS_LAYOUT_KEYS = frozenset(
    {
        "anchor",
        "domain",
        "matches",
        "overlaying",
        "position",
        "scaleanchor",
        "scaleratio",
    }
)


def render_dashboard(
    plots: Sequence[BasePlot],
    spec: DashboardSpec,
    *,
    engine: DashboardEngine = "plotly",
) -> DashboardFigure:
    # [impl->req~ring5.plots.multi-panel-dashboard~1]
    """Render registered plots into the dashboard's configured grid."""
    by_id = {plot.plot_id: plot for plot in plots}
    missing = [plot_id for plot_id in spec.plot_ids if plot_id not in by_id]
    if missing:
        raise ValueError(
            "Dashboard plots are no longer available: " + ", ".join(map(str, missing)) + "."
        )
    selected = [by_id[plot_id] for plot_id in spec.plot_ids]
    without_data = [plot.name for plot in selected if plot.processed_data is None]
    if without_data:
        raise ValueError("Dashboard plots have no processed data: " + ", ".join(without_data) + ".")
    if engine == "plotly":
        return _render_plotly_dashboard(selected, spec)
    if engine == "matplotlib":
        return _render_matplotlib_dashboard(selected, spec)
    raise ValueError("Unknown dashboard engine. Choose 'plotly' or 'matplotlib'.")


def _has_nested_subplots(fig: go.Figure) -> bool:
    """Return whether a child figure already assigns traces beyond x/y/y2."""
    return any(
        (getattr(trace, "xaxis", None) not in (None, "x"))
        or (getattr(trace, "yaxis", None) not in (None, "y", "y2"))
        for trace in fig.data
    )


def _axis_props(axis: Any, *, omit_title: bool) -> dict[str, Any]:
    """Copy child-axis styling without overwriting the dashboard domains."""
    props = dict(axis.to_plotly_json()) if axis is not None else {}
    for key in _AXIS_LAYOUT_KEYS:
        props.pop(key, None)
    if omit_title:
        props.pop("title", None)
    return props


def _trace_axis_ref(axis: Any) -> str:
    name = str(axis.plotly_name)
    return name.replace("axis", "")


def _paper_value(value: Any, domain: Sequence[float]) -> Any:
    if not isinstance(value, (int, float)):
        return value
    return float(domain[0]) + float(value) * (float(domain[1]) - float(domain[0]))


def _map_ref(
    item: dict[str, Any],
    *,
    coordinate: str,
    target_primary: str,
    target_secondary: str | None,
    domain: Sequence[float],
) -> None:
    """Map one annotation/shape reference from child space into panel space."""
    ref_key = f"{coordinate}ref"
    source_ref = str(item.get(ref_key, coordinate))
    value_keys = (coordinate,) if coordinate in item else (f"{coordinate}0", f"{coordinate}1")
    if source_ref == "paper":
        item[ref_key] = "paper"
        for value_key in value_keys:
            if value_key in item:
                item[value_key] = _paper_value(item[value_key], domain)
        return

    suffix = " domain" if source_ref.endswith(" domain") else ""
    bare_ref = source_ref.removesuffix(" domain")
    target = target_secondary if (bare_ref.endswith("2") and target_secondary) else target_primary
    item[ref_key] = f"{target}{suffix}"


def _copy_panel_decorations(
    dashboard: go.Figure,
    child: go.Figure,
    *,
    target_x: Any,
    target_y: Any,
    target_y2: Any | None,
) -> None:
    """Copy data- and paper-space annotations/shapes into one panel domain."""
    x_ref = _trace_axis_ref(target_x)
    y_ref = _trace_axis_ref(target_y)
    y2_ref = _trace_axis_ref(target_y2) if target_y2 is not None else None
    x_domain = cast(Sequence[float], target_x.domain)
    y_domain = cast(Sequence[float], target_y.domain)

    for source in child.layout.annotations or ():
        annotation = dict(source.to_plotly_json())
        _map_ref(
            annotation,
            coordinate="x",
            target_primary=x_ref,
            target_secondary=None,
            domain=x_domain,
        )
        _map_ref(
            annotation,
            coordinate="y",
            target_primary=y_ref,
            target_secondary=y2_ref,
            domain=y_domain,
        )
        dashboard.add_annotation(annotation)

    for source in child.layout.shapes or ():
        shape = dict(source.to_plotly_json())
        _map_ref(
            shape,
            coordinate="x",
            target_primary=x_ref,
            target_secondary=None,
            domain=x_domain,
        )
        _map_ref(
            shape,
            coordinate="y",
            target_primary=y_ref,
            target_secondary=y2_ref,
            domain=y_domain,
        )
        dashboard.add_shape(shape)


def _render_plotly_dashboard(plots: Sequence[BasePlot], spec: DashboardSpec) -> go.Figure:
    child_figures: list[go.Figure] = []
    secondary_flags: list[bool] = []
    for plot in plots:
        child = plot.create_figure(cast(Any, plot.processed_data), plot.config)
        child = plot.apply_common_layout(child, plot.config)
        if _has_nested_subplots(child):
            raise ValueError(
                f"Plot '{plot.name}' already contains nested subplots and cannot be placed "
                "inside a dashboard panel."
            )
        child_figures.append(child)
        secondary_flags.append(any(getattr(trace, "yaxis", None) == "y2" for trace in child.data))

    cells: list[list[dict[str, str | bool | int | float] | None]] = []
    for row in range(spec.rows):
        cells.append(
            [
                {
                    "secondary_y": (
                        secondary_flags[row * spec.columns + column]
                        if row * spec.columns + column < len(secondary_flags)
                        else False
                    )
                }
                for column in range(spec.columns)
            ]
        )
    subplot_titles = list(spec.panel_titles) + [""] * (
        spec.rows * spec.columns - len(spec.panel_titles)
    )
    dashboard = make_subplots(
        rows=spec.rows,
        cols=spec.columns,
        specs=cells,
        subplot_titles=subplot_titles,
        shared_xaxes=spec.shared_xaxes,
        shared_yaxes=spec.shared_yaxes,
        horizontal_spacing=min(0.12, 0.18 / spec.columns),
        vertical_spacing=min(0.16, 0.24 / spec.rows),
    )

    legend_names: set[str] = set()
    inferred_x_title = ""
    inferred_y_title = ""
    for index, child in enumerate(child_figures):
        row, column = divmod(index, spec.columns)
        row += 1
        column += 1
        panel_legend = "legend" if index == 0 else f"legend{index + 1}"

        for source_trace in child.data:
            trace = copy.deepcopy(source_trace)
            secondary = getattr(trace, "yaxis", None) == "y2"
            trace.update(xaxis=None, yaxis=None)
            if spec.shared_legend:
                name = str(getattr(trace, "name", ""))
                originally_visible = getattr(trace, "showlegend", None) is not False
                trace.showlegend = originally_visible and name not in legend_names
                if originally_visible:
                    legend_names.add(name)
            else:
                trace.legend = panel_legend
            dashboard.add_trace(trace, row=row, col=column, secondary_y=secondary)

        target = cast(Any, dashboard.get_subplot(row, column))
        target_x, target_y = target.xaxis, target.yaxis
        target_yaxes = list(dashboard.select_yaxes(row=row, col=column))
        target_y2 = target_yaxes[1] if len(target_yaxes) > 1 else None

        source_x = child.layout.xaxis
        source_y = child.layout.yaxis
        source_y2 = getattr(child.layout, "yaxis2", None)
        target_x.update(_axis_props(source_x, omit_title=spec.shared_xaxes))
        target_y.update(_axis_props(source_y, omit_title=spec.shared_yaxes))
        if target_y2 is not None and source_y2 is not None:
            target_y2.update(_axis_props(source_y2, omit_title=False))

        if not inferred_x_title and source_x.title and source_x.title.text:
            inferred_x_title = str(source_x.title.text)
        if not inferred_y_title and source_y.title and source_y.title.text:
            inferred_y_title = str(source_y.title.text)
        _copy_panel_decorations(
            dashboard,
            child,
            target_x=target_x,
            target_y=target_y,
            target_y2=target_y2,
        )

        if not spec.shared_legend:
            domain_x = cast(Sequence[float], target_x.domain)
            domain_y = cast(Sequence[float], target_y.domain)
            dashboard.update_layout(
                {
                    panel_legend: {
                        "x": float(domain_x[1]) - 0.01,
                        "y": float(domain_y[1]) - 0.01,
                        "xanchor": "right",
                        "yanchor": "top",
                        "bgcolor": "rgba(255,255,255,0.8)",
                    }
                }
            )

    dashboard.update_layout(
        title={"text": spec.title, "x": 0.5, "xanchor": "center"},
        width=spec.width,
        height=spec.height,
        paper_bgcolor=child_figures[0].layout.paper_bgcolor or "white",
        plot_bgcolor=child_figures[0].layout.plot_bgcolor or "white",
        font=child_figures[0].layout.font,
        margin={
            "l": 72,
            "r": 36,
            "t": 84 if spec.title else 56,
            "b": 110 if (spec.shared_legend and (spec.x_title or inferred_x_title)) else 82,
        },
    )
    if spec.shared_legend:
        dashboard.update_layout(
            legend={
                "orientation": "h",
                "x": 0.5,
                "xanchor": "center",
                "y": -0.08,
                "yanchor": "top",
            }
        )

    x_title = spec.x_title or (inferred_x_title if spec.shared_xaxes else "")
    y_title = spec.y_title or (inferred_y_title if spec.shared_yaxes else "")
    if x_title:
        dashboard.add_annotation(
            text=x_title,
            x=0.5,
            y=-0.16 if spec.shared_legend else -0.10,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
    if y_title:
        dashboard.add_annotation(
            text=y_title,
            x=-0.07,
            y=0.5,
            xref="paper",
            yref="paper",
            textangle=-90,
            showarrow=False,
        )
    return dashboard


def _render_matplotlib_dashboard(plots: Sequence[BasePlot], spec: DashboardSpec) -> MplFigure:
    # [impl->req~ring5.figure.accessible-themes~1]
    from src.core.services.managers.semantic_metadata_service import SemanticMetadataService
    from src.core.services.visualization.accessibility_service import AccessibilityService
    import matplotlib.pyplot as plt

    figure, raw_axes = plt.subplots(
        nrows=spec.rows,
        ncols=spec.columns,
        figsize=(spec.width / 96.0, spec.height / 96.0),
        dpi=96,
        squeeze=False,
        sharex=spec.shared_xaxes,
        sharey=spec.shared_yaxes,
    )
    axes = list(raw_axes.flat)
    first_figure_spec: Any = None
    try:
        for index, (plot, panel_title) in enumerate(zip(plots, spec.panel_titles)):
            ax = axes[index]
            plot.config = SemanticMetadataService.enrich_figure_config(
                cast(Any, plot.processed_data), plot.config
            )
            plot.config = AccessibilityService.apply_defaults(plot.config, plot.plot_type)
            result = plot.create_traces(cast(Any, plot.processed_data), plot.config)
            result = AccessibilityService.apply_non_color_encodings(result, plot.config)
            result = _relabel_traces(result, plot.config.get("legend_labels"))
            plot.last_traces = result
            if sum(isinstance(trace, HeatmapTraceConfig) for trace in result.traces) > 1:
                raise ValueError(
                    f"Plot '{plot.name}' already contains nested heatmap panels and cannot "
                    "be placed inside a dashboard panel."
                )

            figure_spec = ConfigSpecBuilder.from_config(plot.config, plot.plot_type)
            enrich_from_traces(figure_spec, result)
            figure_spec = resolve_config(figure_spec)
            _drop_dual_axis_title_annotations(figure_spec, plot.config)
            if first_figure_spec is None:
                first_figure_spec = figure_spec

            render_result = MatplotlibTraceRenderer.render(
                list(result.traces),
                ax,
                barmode=figure_spec.barmode,
                palette_colors=figure_spec.color_palette or None,
                bargap=figure_spec.dimensions.bargap,
                bargroupgap=figure_spec.dimensions.bargroupgap,
                bar_border_width=float(plot.config.get("bar_border_width", 0.0)),
            )
            FigureSpecToMatplotlib.apply(
                figure_spec,
                ax,
                render_result,
                apply_margins=False,
            )
            FigureSpecToMatplotlib.draw_layout_shapes(
                ax,
                list(result.separator_lines),
                list(result.shaded_regions),
                list(result.rule_lines),
            )
            twin = getattr(ax, "_ring5_twin", None)
            if twin is not None:
                apply_dual_axis(twin, plot.config, figure_spec)
            ax.set_title(panel_title)
            if spec.shared_xaxes:
                ax.set_xlabel("")
            if spec.shared_yaxes:
                ax.set_ylabel("")

        for ax in axes[len(plots) :]:
            ax.set_axis_off()

        if spec.shared_legend:
            handles_by_label: dict[str, Any] = {}
            for ax in axes[: len(plots)]:
                candidates = [ax]
                twin = getattr(ax, "_ring5_twin", None)
                if twin is not None:
                    candidates.append(twin)
                for candidate in candidates:
                    handles, labels = candidate.get_legend_handles_labels()
                    for handle, label in zip(handles, labels):
                        if label and not label.startswith("_"):
                            handles_by_label.setdefault(label, handle)
                    legend = candidate.get_legend()
                    if legend is not None:
                        legend.remove()
            if handles_by_label:
                legend_prop = (
                    {"family": first_figure_spec.font_family}
                    if first_figure_spec and first_figure_spec.font_family
                    else None
                )
                figure.legend(
                    list(handles_by_label.values()),
                    list(handles_by_label),
                    loc="lower center",
                    ncol=min(4, len(handles_by_label)),
                    bbox_to_anchor=(0.5, 0.01),
                    prop=legend_prop,
                )

        font_kwargs = (
            {"fontfamily": first_figure_spec.font_family}
            if first_figure_spec and first_figure_spec.font_family
            else {}
        )
        if spec.title:
            figure.suptitle(spec.title, **font_kwargs)
        inferred_x = str(plots[0].config.get("xlabel", "")) if spec.shared_xaxes else ""
        inferred_y = str(plots[0].config.get("ylabel", "")) if spec.shared_yaxes else ""
        if spec.x_title or inferred_x:
            figure.supxlabel(spec.x_title or inferred_x, **font_kwargs)
        if spec.y_title or inferred_y:
            figure.supylabel(spec.y_title or inferred_y, **font_kwargs)
        if first_figure_spec and first_figure_spec.paper_bgcolor:
            figure.patch.set_facecolor(first_figure_spec.paper_bgcolor)
        figure.subplots_adjust(
            left=0.08,
            right=0.97,
            top=0.90 if spec.title else 0.95,
            bottom=0.14 if spec.shared_legend else 0.09,
            wspace=0.26,
            hspace=0.36,
        )
        figure._ring5_spec = first_figure_spec  # type: ignore[attr-defined]
        return figure
    except Exception:
        plt.close(figure)
        raise


__all__ = ["DashboardEngine", "DashboardFigure", "render_dashboard"]
