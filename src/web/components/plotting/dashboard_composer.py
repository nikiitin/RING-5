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
from src.core.models.visualization.linked_selection_spec import LinkedSelectionSpec
from src.web.components.plotting.interactive_plot import interactive_plotly_chart
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
from src.web.rendering.linked_selection import (
    apply_linked_selection,
    selection_values_from_event,
)

_FIGURE_KEY = "dashboard.composer.figure"
_SPEC_KEY = "dashboard.composer.spec"
_ENGINE_KEY = "dashboard.composer.rendered_engine"
_SELECTION_VALUES_KEY = "dashboard.composer.selection.values"
_SELECTION_EVENT_KEY = "dashboard.composer.selection.event"
_SELECTION_CONFIG_KEY = "dashboard.composer.selection.config"
_SELECTION_GENERATION_KEY = "dashboard.composer.selection.generation"


class DashboardComposer:
    """Compose, preview, and export a grid from the current plot workspace."""

    def __init__(self, api: ApplicationAPI) -> None:
        self._api = api

    def render(self) -> None:
        # [impl->req~ring5.plots.multi-panel-dashboard~1]
        # [impl->req~ring5.figure.panel-composition~1]
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
                "Common figure title",
                value="Analysis dashboard",
                key="dashboard.composer.title",
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

            publication_options: dict[str, Any] = {}
            publication_layout = st.toggle(
                "Publication layout",
                value=False,
                key="dashboard.composer.publication_layout",
                help=(
                    "Add panel identifiers and captions, then control the exact normalized "
                    "gap between panels."
                ),
            )
            if publication_layout:
                label_mode = st.pills(
                    "Panel labels",
                    options=["automatic", "custom", "none"],
                    default="automatic",
                    format_func=lambda value: value.capitalize(),
                    key="dashboard.composer.panel_label_mode",
                    help="Automatic labels use the publication convention (a), (b), and so on.",
                )
                panel_labels: Any = None
                if label_mode == "automatic":
                    panel_labels = "auto"
                elif label_mode == "custom":
                    panel_labels = self._panel_lines(
                        st.text_area(
                            "Custom panel labels (one per line)",
                            value="",
                            key="dashboard.composer.panel_labels",
                        ),
                        len(selected_ids),
                    )

                panel_captions = self._panel_lines(
                    st.text_area(
                        "Panel captions (one per line)",
                        value="",
                        key="dashboard.composer.panel_captions",
                        help="Keep a blank line for a panel that does not need a caption.",
                    ),
                    len(selected_ids),
                )
                horizontal_gap_col, vertical_gap_col = st.columns(2)
                horizontal_maximum = self._maximum_gap_percent(columns)
                vertical_maximum = self._maximum_gap_percent(rows)
                for key, maximum in (
                    ("dashboard.composer.horizontal_spacing", horizontal_maximum),
                    ("dashboard.composer.vertical_spacing", vertical_maximum),
                ):
                    saved_gap = st.session_state.get(key)
                    if isinstance(saved_gap, int) and saved_gap > maximum:
                        st.session_state[key] = maximum
                with horizontal_gap_col:
                    horizontal_gap = st.slider(
                        "Horizontal gap (%)",
                        min_value=0,
                        max_value=horizontal_maximum,
                        value=min(6, horizontal_maximum),
                        key="dashboard.composer.horizontal_spacing",
                    )
                with vertical_gap_col:
                    vertical_gap = st.slider(
                        "Vertical gap (%)",
                        min_value=0,
                        max_value=vertical_maximum,
                        value=min(10, vertical_maximum),
                        key="dashboard.composer.vertical_spacing",
                    )
                publication_options = {
                    "panel_labels": panel_labels,
                    "panel_captions": panel_captions,
                    "horizontal_spacing": horizontal_gap / 100,
                    "vertical_spacing": vertical_gap / 100,
                }

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

            link_enabled = st.toggle(
                "Link panel selections",
                value=False,
                disabled=engine != "plotly",
                key="dashboard.composer.link_enabled",
                help="Box- or lasso-select visible values in one panel to update every panel.",
            )
            linked_spec: LinkedSelectionSpec | None = None
            if link_enabled and engine == "plotly":
                link_axis_col, link_mode_col = st.columns(2)
                with link_axis_col:
                    link_axis = st.pills(
                        "Relate values on",
                        options=["x", "y"],
                        default="x",
                        format_func=lambda value: f"{value.upper()} axis",
                        key="dashboard.composer.link_axis",
                    )
                with link_mode_col:
                    link_mode = st.pills(
                        "Linked behavior",
                        options=["highlight", "filter"],
                        default="highlight",
                        format_func=lambda value: value.capitalize(),
                        key="dashboard.composer.link_mode",
                    )
                try:
                    linked_spec = self._api.create_linked_selection(
                        selected_ids,
                        axis=cast(Any, link_axis or "x"),
                        mode=cast(Any, link_mode or "highlight"),
                    )
                except ValueError as exc:
                    st.error(str(exc))
                    return
                st.caption(
                    "Use box or lasso selection in any panel. Clear the selection to restore "
                    "the complete dashboard. Source plot data is never changed."
                )
            elif _SELECTION_CONFIG_KEY in st.session_state:
                self._clear_linked_selection()

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
                    **publication_options,
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
                self._clear_linked_selection()
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
                applicable_link = (
                    linked_spec
                    if linked_spec is not None
                    and tuple(linked_spec.plot_ids) == tuple(rendered_spec.plot_ids)
                    else None
                )
                self._render_plotly_preview(rendered_figure, applicable_link)
            elif isinstance(rendered_figure, MplFigure):
                st.pyplot(rendered_figure)
            self._render_export(rendered_figure, rendered_spec)

    @staticmethod
    def _panel_lines(value: str, panel_count: int) -> tuple[str, ...]:
        """Align human-entered lines while retaining intentional interior blanks."""
        if not value:
            return ("",) * panel_count
        return tuple(value.split("\n"))

    @staticmethod
    def _maximum_gap_percent(panel_count: int) -> int:
        """Return a safe, readable spacing limit for the current grid dimension."""
        if panel_count <= 1:
            return 20
        return min(20, 99 // (panel_count - 1))

    @staticmethod
    def _clear_linked_selection() -> None:
        """Clear transient selection values without touching plot or dataset state."""
        generation = st.session_state.get(_SELECTION_GENERATION_KEY, 0)
        st.session_state.pop(_SELECTION_VALUES_KEY, None)
        st.session_state.pop(_SELECTION_EVENT_KEY, None)
        st.session_state.pop(_SELECTION_CONFIG_KEY, None)
        st.session_state[_SELECTION_GENERATION_KEY] = generation + 1

    @staticmethod
    def _render_plotly_preview(
        figure: go.Figure,
        linked_spec: LinkedSelectionSpec | None,
    ) -> None:
        # [impl->req~ring5.plots.linked-selections~1]
        """Render a normal preview or consume linked box/lasso events."""
        if linked_spec is None:
            st.plotly_chart(
                figure,
                config={"responsive": False, "displaylogo": False},
                width="content",
                key="dashboard.composer.plotly_preview",
            )
            return

        identity = (linked_spec.plot_ids, linked_spec.axis, linked_spec.mode)
        if st.session_state.get(_SELECTION_CONFIG_KEY) != identity:
            DashboardComposer._clear_linked_selection()
            st.session_state[_SELECTION_CONFIG_KEY] = identity

        values = tuple(st.session_state.get(_SELECTION_VALUES_KEY, ()))
        display_figure = apply_linked_selection(figure, linked_spec, values)
        display_figure.update_layout(dragmode="select")

        if values:
            shown = ", ".join(str(value) for value in values[:5])
            if len(values) > 5:
                shown += f", +{len(values) - 5} more"
            status_col, clear_col = st.columns([4, 1])
            with status_col:
                st.caption(f"Linked {linked_spec.axis.upper()} selection: {shown}")
            with clear_col:
                if st.button(
                    "Clear selection",
                    width="stretch",
                    key="dashboard.composer.clear_selection",
                ):
                    DashboardComposer._clear_linked_selection()
                    st.rerun()
                    return

        event = interactive_plotly_chart(
            display_figure,
            config={
                "responsive": False,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["select2d", "lasso2d"],
            },
            key=(
                f"dashboard.linked.{linked_spec.axis}.{linked_spec.mode}."
                f"{st.session_state.get(_SELECTION_GENERATION_KEY, 0)}"
            ),
            capture_selection=True,
        )
        if not event or event.get("kind") != "selection":
            return
        if event == st.session_state.get(_SELECTION_EVENT_KEY):
            return
        st.session_state[_SELECTION_EVENT_KEY] = event
        st.session_state[_SELECTION_VALUES_KEY] = selection_values_from_event(
            event, linked_spec.axis
        )
        st.rerun()

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
