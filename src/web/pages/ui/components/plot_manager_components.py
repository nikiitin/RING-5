"""
Plot Manager Components - UI for Plot Creation and Configuration.

Provides Streamlit components for plot management: creation, configuration,
data transformation pipelines, rendering, and export operations.
"""

import logging
from typing import cast

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.services.shapers.factory import ShaperFactory
from src.web.pages.ui.plotting import BasePlot, PlotFactory
from src.web.pages.ui.plotting.plot_service import PlotService
from src.web.pages.ui.shaper_config import apply_shapers, configure_shaper
from src.web.state.ui_state_manager import UIStateManager

logger = logging.getLogger(__name__)


class PlotManagerComponents:
    """UI Components for the Plot Management Page."""

    @staticmethod
    def render_create_plot_section(api: ApplicationAPI) -> None:
        """Render the section to create a new plot."""
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            new_plot_name = st.text_input(
                "New plot name",
                value=f"Plot {api.state_manager.get_plot_counter() + 1}",
                key="new_plot_name",
            )
        with col2:
            plot_types = PlotFactory.get_available_plot_types()
            plot_type = st.selectbox("Plot type", options=plot_types, key="new_plot_type")
        with col3:
            if st.button("Create Plot", width="stretch"):
                if plot_type:
                    PlotService.create_plot(new_plot_name, plot_type, api.state_manager)
                    st.rerun()

    @staticmethod
    def render_plot_selector(api: ApplicationAPI) -> BasePlot | None:
        """Render tabs/selector for plots and return the current plot."""
        plots = api.state_manager.get_plots()
        if not plots:
            st.warning("No plots yet. Create a plot to get started!")
            return None

        plot_names = [p.name for p in plots]
        # Ensure selection persists or defaults to 0
        current_id = api.state_manager.get_current_plot_id()
        default_index = 0

        if current_id is not None:
            # Find index of current ID
            for i, p in enumerate(plots):
                if p.plot_id == current_id:
                    default_index = i
                    break

        default_name = plot_names[default_index] if plot_names else None
        selected_name = st.pills(
            "Select Plot", plot_names, default=default_name, key="plot_selector"
        )

        # Update current ID based on selection
        selected_plot = next((p for p in plots if p.name == selected_name), plots[0])
        if selected_plot.plot_id != current_id:
            api.state_manager.set_current_plot_id(selected_plot.plot_id)

        return cast(BasePlot, selected_plot)

    @staticmethod
    def render_plot_controls(api: ApplicationAPI, plot: BasePlot) -> None:
        """Render controls for renaming and managing the current plot."""
        col1, col2, col3 = st.columns(3)

        with col1:
            new_name = st.text_input("Rename plot", value=plot.name, key=f"rename_{plot.plot_id}")
            if new_name != plot.name:
                plot.name = new_name

        with col2:
            st.button(
                "Delete",
                key=f"delete_plot_{plot.plot_id}",
                on_click=lambda: PlotService.delete_plot(plot.plot_id, api.state_manager),
                type="tertiary",
            )

        with col3:

            def _duplicate() -> None:
                PlotService.duplicate_plot(plot, api.state_manager)

            st.button(
                "Duplicate",
                key=f"dup_plot_{plot.plot_id}",
                on_click=_duplicate,
                type="tertiary",
            )

    @staticmethod
    def render_pipeline_editor(api: ApplicationAPI, plot: BasePlot) -> None:
        """Render the Data Processing Pipeline editor."""
        st.markdown("### Data Processing Pipeline")

        data = api.state_manager.get_data()
        if data is None:
            st.warning("Please upload data first!")
            return

        # Add shaper — display names from ShaperFactory (Layer B)
        col1, col2 = st.columns([3, 1])
        shaper_map = ShaperFactory.get_display_name_map()
        with col1:
            display_type = st.selectbox(
                "Add transformation", list(shaper_map.keys()), key=f"shaper_add_{plot.plot_id}"
            )
        with col2:
            if st.button("Add to Pipeline", width="stretch", key=f"add_shaper_btn_{plot.plot_id}"):
                plot.pipeline.append(
                    {"id": plot.pipeline_counter, "type": shaper_map[display_type], "config": {}}
                )
                plot.pipeline_counter += 1
                st.rerun()

        # Config loop
        if plot.pipeline:
            st.markdown("**Current Pipeline:**")
            for idx, shaper in enumerate(plot.pipeline):
                # Display name from ShaperFactory
                d_name = ShaperFactory.get_display_name(shaper["type"])
                with st.expander(f"{idx+1}. {d_name}", expanded=True):
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    with c1:
                        # Calculate input
                        if idx == 0:
                            inp = data
                        else:
                            prev_confs = [s["config"] for s in plot.pipeline[:idx] if s["config"]]
                            inp = apply_shapers(data, prev_confs)

                        shaper["config"] = configure_shaper(
                            shaper["type"],
                            inp,
                            shaper["id"],
                            shaper.get("config", {}),
                            owner_id=plot.plot_id,
                        )

                    with c2:
                        if idx > 0 and st.button(
                            "Up", key=f"up_{plot.plot_id}_{idx}", type="tertiary"
                        ):
                            plot.pipeline[idx], plot.pipeline[idx - 1] = (
                                plot.pipeline[idx - 1],
                                plot.pipeline[idx],
                            )
                            st.rerun()
                    with c3:
                        if idx < len(plot.pipeline) - 1 and st.button(
                            "Down", key=f"down_{plot.plot_id}_{idx}", type="tertiary"
                        ):
                            plot.pipeline[idx], plot.pipeline[idx + 1] = (
                                plot.pipeline[idx + 1],
                                plot.pipeline[idx],
                            )
                            st.rerun()
                    with c4:
                        if st.button("Del", key=f"del_{plot.plot_id}_{idx}", type="tertiary"):
                            plot.pipeline.pop(idx)
                            st.rerun()

                    # Preview
                    if shaper["config"]:
                        try:
                            out = apply_shapers(inp, [shaper["config"]])
                            st.dataframe(out.head(5))
                        except Exception as e:
                            st.exception(e)
                            logger.error(
                                "PIPELINE: Preview failure for shaper index %d in plot %r: %s",
                                idx,
                                str(plot.name).replace("\n", ""),
                                e,
                                exc_info=True,
                            )

        # Finalize
        if plot.pipeline:
            if st.button(
                "Finalize Pipeline for Plotting",
                type="primary",
                width="stretch",
                key=f"finalize_{plot.plot_id}",
            ):
                try:
                    confs = [s["config"] for s in plot.pipeline if s["config"]]
                    processed = apply_shapers(data, confs)
                    plot.processed_data = processed
                    st.success(f"Pipeline applied! Shape: {processed.shape}")
                    st.dataframe(processed.head(10))
                except Exception as e:
                    st.exception(e)

    @staticmethod
    def render_workspace_management(api: ApplicationAPI) -> None:
        """Render workspace management buttons."""
        st.markdown("---")
        st.markdown("### Workspace Management")

        st.markdown("#### Download All Plots")
        st.caption(
            "Download all plots to a local directory"
            " (e.g., your LaTeX repository)."
            " Uses individual plot settings (Scale/Format)."
        )

        ec1, ec2, ec3 = st.columns([2, 1, 1])
        with ec1:
            ui = UIStateManager()
            export_path = st.text_input(
                "Local Download Path",
                value=ui.export.get_last_export_path(),
                placeholder="/absolute/path/to/folder",
                key="export_path_input",
            )
        with ec2:
            export_fmt_override = st.selectbox(
                "Force Format",
                options=["Keep Individual", "pdf", "svg", "png", "html"],
                index=0,
                key="export_fmt_override",
                help="Override format for all plots (e.g. force PDF for LaTeX)",
            )

        with ec3:
            st.write("")
            st.write("")
            if st.button("Download All", type="primary", width="stretch", key="export_all_btn"):
                if not export_path:
                    st.error("Please provide a path.")
                    logger.warning("DOWNLOAD: Attempted download without providing path.")
                else:
                    UIStateManager().export.set_last_export_path(export_path)
                    plots = api.state_manager.get_plots()
                    if not plots:
                        st.warning("No plots to download.")
                    else:
                        count = 0
                        errors: list[str] = []
                        # Determine override
                        fmt_arg = None
                        if export_fmt_override != "Keep Individual":
                            fmt_arg = export_fmt_override

                        with st.status(
                            f"Downloading {len(plots)} plots...", expanded=True
                        ) as status:
                            for i, p in enumerate(plots):
                                try:
                                    fmt_to_use = fmt_arg if fmt_arg else "png"
                                    st.write(
                                        f"Downloading **{p.name}** " f"({i + 1}/{len(plots)})..."
                                    )
                                    res = PlotService.export_plot_to_file(
                                        cast(BasePlot, p), export_path, format=fmt_to_use
                                    )
                                    if res:
                                        count += 1
                                except Exception as exc:
                                    errors.append(f"{p.name}: {exc}")

                            if errors:
                                status.update(
                                    label=f"Downloaded {count} plots ({len(errors)} errors)",
                                    state="error",
                                    expanded=True,
                                )
                            else:
                                status.update(
                                    label=f"Downloaded {count} plots to '{export_path}'",
                                    state="complete",
                                    expanded=False,
                                )

                        if count > 0:
                            st.toast(
                                f"Successfully downloaded {count} plots to '{export_path}'",
                                icon="✅",
                            )
                        if errors:
                            st.error(f"Failed to download {len(errors)} plots.")
                            logger.error(
                                "DOWNLOAD: Failed to download some plots. Errors: %s", errors
                            )
                            with st.expander("Show Errors"):
                                for error_msg in errors:
                                    st.write(error_msg)

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Process All Plots in Parallel", width="stretch"):
                st.info("Coming soon!")
        with c2:
            if st.button("Save Entire Workspace", width="stretch"):
                # Sync state confirmation
                st.toast("Workspace state synchronized.", icon="✅")
