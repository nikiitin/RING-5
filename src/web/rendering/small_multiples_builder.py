"""UI-free small-multiples rendering for both figure engines."""

from __future__ import annotations

import copy
from collections.abc import Sequence

import pandas as pd
import plotly.graph_objects as go

from src.core.models.visualization.dashboard_spec import DashboardSpec
from src.core.models.visualization.small_multiples_spec import FacetPanel, SmallMultiplesSpec
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.rendering.dashboard_builder import DashboardEngine, DashboardFigure, render_dashboard


def _panel_rows(
    data: pd.DataFrame,
    facet_columns: tuple[str, ...],
    panel: FacetPanel,
) -> pd.DataFrame:
    """Return a defensive subset for one exact facet combination."""
    mask = pd.Series(True, index=data.index, dtype=bool)
    for column, value in zip(facet_columns, panel.values):
        mask &= data[column].isna() if value is None else data[column].eq(value).fillna(False)
    return data.loc[mask].copy(deep=True)


def _facet_views(plot: BasePlot, spec: SmallMultiplesSpec) -> list[BasePlot]:
    """Create transient plot views without changing the registered source plot."""
    if plot.processed_data is None:
        raise ValueError(f"Plot '{plot.name}' has no processed data.")
    missing = [column for column in spec.facet_columns if column not in plot.processed_data.columns]
    if missing:
        raise ValueError(
            "Small-multiples facet columns are no longer available: " + ", ".join(missing)
        )

    views: list[BasePlot] = []
    for index, panel in enumerate(spec.panels):
        rows = _panel_rows(plot.processed_data, spec.facet_columns, panel)
        if rows.empty:
            raise ValueError(f"Small-multiples panel '{panel.title}' no longer has matching rows.")
        view = copy.copy(plot)
        view.plot_id = index
        view.name = panel.title
        view.config = copy.deepcopy(plot.config)
        view.processed_data = rows
        view.source_data = None
        view.last_generated_fig = None
        view.last_traces = None
        view.last_figure_cache_key = None
        views.append(view)
    return views


def _match_all_plotly_axes(figure: go.Figure, spec: SmallMultiplesSpec) -> None:
    """Link every compatible facet axis, including panels in different rows."""
    if spec.shared_xaxes:
        xaxes = list(figure.select_xaxes())
        if xaxes:
            reference = str(xaxes[0].plotly_name).replace("axis", "")
            xaxes[0].matches = None
            for axis in xaxes[1:]:
                axis.matches = reference
    if spec.shared_yaxes:
        yaxes = list(figure.select_yaxes())
        groups = (
            [axis for axis in yaxes if not axis.overlaying],
            [axis for axis in yaxes if axis.overlaying],
        )
        for axes in groups:
            if axes:
                reference = str(axes[0].plotly_name).replace("axis", "")
                axes[0].matches = None
                for axis in axes[1:]:
                    axis.matches = reference


def render_small_multiples(
    plots: Sequence[BasePlot],
    spec: SmallMultiplesSpec,
    *,
    engine: DashboardEngine = "plotly",
) -> DashboardFigure:
    # [impl->req~ring5.plots.small-multiples~1]
    """Render one registered plot repeatedly for every resolved facet panel."""
    by_id = {plot.plot_id: plot for plot in plots}
    plot = by_id.get(spec.plot_id)
    if plot is None:
        raise ValueError(f"Small multiples references unknown plot ID: {spec.plot_id}.")

    views = _facet_views(plot, spec)
    dashboard = DashboardSpec(
        plot_ids=tuple(view.plot_id for view in views),
        rows=spec.rows,
        columns=spec.columns,
        panel_titles=tuple(panel.title for panel in spec.panels),
        title=spec.title,
        width=spec.width,
        height=spec.height,
        shared_xaxes=spec.shared_xaxes,
        shared_yaxes=spec.shared_yaxes,
        shared_legend=spec.shared_legend,
        x_title=spec.x_title,
        y_title=spec.y_title,
    )
    figure = render_dashboard(views, dashboard, engine=engine)
    if isinstance(figure, go.Figure):
        _match_all_plotly_axes(figure, spec)
    return figure


__all__ = ["render_small_multiples"]
