"""Human-first Streamlit composer for multi-panel dashboards."""

from __future__ import annotations

from typing import Any, cast

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import streamlit as st
from matplotlib.figure import Figure as MplFigure

from src.core.application_api import ApplicationAPI
from src.core.common.utils import sanitize_filename
from src.core.models.visualization.dashboard_spec import DashboardSpec
from src.core.models.visualization.engine import EngineMode
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.rendering.dashboard_builder import render_dashboard
from src.web.rendering.engine_manager import EngineManager
from src.web.rendering.figure_export import (
    MatplotlibFormat,
    PlotlyFormat,
    get_matplotlib_extension,
    get_matplotlib_mime,
    get_plotly_extension,
    get_plotly_mime,
    matplotlib_download_bytes,
    plotly_download_bytes,
)

_FIGURE_KEY = "dashboard.composer.figure"
_SPEC_KEY = "dashboard.composer.spec"
_ENGINE_KEY = "dashboard.composer.rendered_engine"


class DashboardComposer:
    """Compose, preview, and export a grid from the current plot workspace."""

    def __init__(self, api: ApplicationAPI) -> None:
        self._api = api

    def render(self) -> None:
        # [impl->req~ring5.plots.multi-panel-dashboard~1]
        """Render the complete dashboard workflow."""
        with st.expander(":material/dashboard: Multi-panel dashboard", expanded=False):
            st.caption(
                "Combine existing plots into one figure. Panel order follows the plot list below; "
                "edit a source plot, then rebuild to refresh its panel."
            )
            plots = cast(list[BasePlot], self._api.state_manager.get_plots())
            if len(plots) < 2:
                st.info("Create at least two plots to build a dashboard.")
                return

            by_id = {plot.plot_id: plot for plot in plots}
            selected_ids = st.multiselect(
                "Panels",
                options=list(by_id),
                default=list(by_id)[:2],
                format_func=lambda plot_id: f"{by_id[plot_id].name} · {by_id[plot_id].plot_type}",
                key="dashboard.composer.panels",
                help="Panels appear left-to-right, then top-to-bottom, in this order.",
            )
            if len(selected_ids) < 2:
                st.info("Select at least two panels.")
                return

            title = st.text_input(
                "Dashboard title", value="Analysis dashboard", key="dashboard.composer.title"
            )
            grid_col, width_col, height_col = st.columns(3)
            maximum_columns = min(6, len(selected_ids))
            columns_key = "dashboard.composer.columns"
            saved_columns = st.session_state.get(columns_key)
            if isinstance(saved_columns, int) and saved_columns > maximum_columns:
                st.session_state[columns_key] = maximum_columns
            with grid_col:
                columns = int(
                    st.number_input(
                        "Columns",
                        min_value=1,
                        max_value=maximum_columns,
                        value=min(2, len(selected_ids)),
                        step=1,
                        key=columns_key,
                    )
                )
            rows = (len(selected_ids) + columns - 1) // columns
            with width_col:
                width = int(
                    st.number_input(
                        "Width (px)",
                        min_value=320,
                        max_value=5000,
                        value=1200,
                        step=40,
                        key="dashboard.composer.width",
                    )
                )
            with height_col:
                height = int(
                    st.number_input(
                        "Height (px)",
                        min_value=240,
                        max_value=5000,
                        value=max(480, rows * 420),
                        step=40,
                        key="dashboard.composer.height",
                    )
                )
            st.caption(f"Grid: {rows} row{'s' if rows != 1 else ''} × {columns} columns")

            share_x_col, share_y_col, legend_col = st.columns(3)
            with share_x_col:
                shared_xaxes = st.toggle(
                    "Share X axis", value=False, key="dashboard.composer.share_x"
                )
            with share_y_col:
                shared_yaxes = st.toggle(
                    "Share Y axis", value=False, key="dashboard.composer.share_y"
                )
            with legend_col:
                shared_legend = st.toggle(
                    "One shared legend", value=True, key="dashboard.composer.share_legend"
                )

            label_x_col, label_y_col = st.columns(2)
            with label_x_col:
                x_title = st.text_input(
                    "Shared X title",
                    value="",
                    key="dashboard.composer.x_title",
                    disabled=not shared_xaxes,
                )
            with label_y_col:
                y_title = st.text_input(
                    "Shared Y title",
                    value="",
                    key="dashboard.composer.y_title",
                    disabled=not shared_yaxes,
                )

            engine_choice = st.pills(
                "Engine",
                options=["plotly", "matplotlib"],
                default=EngineManager.get_engine(),
                format_func=lambda value: (
                    "Interactive Plotly" if value == "plotly" else "Publication Matplotlib"
                ),
                key="dashboard.composer.engine",
            )
            engine = cast(EngineMode, engine_choice or EngineManager.get_engine())

            try:
                current_spec = self._api.create_dashboard(
                    selected_ids,
                    title=title,
                    rows=rows,
                    columns=columns,
                    width=width,
                    height=height,
                    shared_xaxes=shared_xaxes,
                    shared_yaxes=shared_yaxes,
                    shared_legend=shared_legend,
                    x_title=x_title,
                    y_title=y_title,
                )
            except ValueError as exc:
                st.error(str(exc))
                return

            if st.button(
                ":material/grid_view: Build dashboard",
                type="primary",
                width="stretch",
                key="dashboard.composer.build",
            ):
                old_figure = st.session_state.get(_FIGURE_KEY)
                if isinstance(old_figure, MplFigure):
                    plt.close(old_figure)
                st.session_state.pop(_FIGURE_KEY, None)
                st.session_state.pop(_SPEC_KEY, None)
                st.session_state.pop(_ENGINE_KEY, None)
                try:
                    figure = render_dashboard(plots, current_spec, engine=engine)
                except Exception as exc:
                    st.exception(exc)
                else:
                    EngineManager.set_engine(engine)
                    st.session_state[_FIGURE_KEY] = figure
                    st.session_state[_SPEC_KEY] = current_spec
                    st.session_state[_ENGINE_KEY] = engine

            rendered_figure = st.session_state.get(_FIGURE_KEY)
            rendered_spec = st.session_state.get(_SPEC_KEY)
            rendered_engine = st.session_state.get(_ENGINE_KEY)
            if rendered_figure is None or not isinstance(rendered_spec, DashboardSpec):
                return
            if rendered_spec != current_spec or rendered_engine != engine:
                st.info("Settings changed. Build the dashboard again to update the preview.")

            if isinstance(rendered_figure, go.Figure):
                st.plotly_chart(
                    rendered_figure,
                    config={"responsive": False, "displaylogo": False},
                    width="content",
                    key="dashboard.composer.plotly_preview",
                )
            elif isinstance(rendered_figure, MplFigure):
                st.pyplot(rendered_figure)
            self._render_export(rendered_figure, rendered_spec)

    @staticmethod
    def _render_export(figure: Any, spec: DashboardSpec) -> None:
        """Offer one download containing every dashboard panel."""
        with st.expander(":material/download: Download whole dashboard", expanded=True):
            stem = sanitize_filename(spec.title) if spec.title.strip() else "dashboard"
            if isinstance(figure, go.Figure):
                plotly_fmt = st.pills(
                    "Format",
                    options=["html", "png", "svg", "pdf"],
                    default="html",
                    key="dashboard.composer.plotly_format",
                )
                if plotly_fmt is None:
                    return
                typed_plotly_fmt = cast(PlotlyFormat, plotly_fmt)

                def generate_plotly() -> bytes:
                    return plotly_download_bytes(
                        figure,
                        typed_plotly_fmt,
                        width=spec.width,
                        height=spec.height,
                    )

                st.download_button(
                    f"Download complete {plotly_fmt.upper()}",
                    data=generate_plotly,
                    file_name=f"{stem}{get_plotly_extension(typed_plotly_fmt)}",
                    mime=get_plotly_mime(typed_plotly_fmt),
                    on_click="ignore",
                    width="stretch",
                    key="dashboard.composer.plotly_download",
                )
                return

            if isinstance(figure, MplFigure):
                mpl_fmt = st.pills(
                    "Format",
                    options=["pdf", "pgf", "png", "svg"],
                    default="pdf",
                    key="dashboard.composer.matplotlib_format",
                )
                if mpl_fmt is None:
                    return
                typed_mpl_fmt = cast(MatplotlibFormat, mpl_fmt)
                data = matplotlib_download_bytes(
                    figure,
                    typed_mpl_fmt,
                    spec=getattr(figure, "_ring5_spec", None),
                )
                st.download_button(
                    f"Download complete {mpl_fmt.upper()}",
                    data=data,
                    file_name=f"{stem}{get_matplotlib_extension(typed_mpl_fmt)}",
                    mime=get_matplotlib_mime(typed_mpl_fmt),
                    width="stretch",
                    key="dashboard.composer.matplotlib_download",
                )


__all__ = ["DashboardComposer"]
