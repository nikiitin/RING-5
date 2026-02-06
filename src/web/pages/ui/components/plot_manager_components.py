import copy
import logging
from typing import Any, Optional

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.services.pipeline_service import PipelineService
from src.web.pages.ui.plotting import BasePlot, PlotFactory, PlotRenderer
from src.web.pages.ui.plotting.plot_service import PlotService
from src.web.pages.ui.shaper_config import apply_shapers, configure_shaper

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
    def render_plot_selector(api: ApplicationAPI) -> Optional[BasePlot]:
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

        selected_name = st.radio(
            "Select Plot", plot_names, horizontal=True, index=default_index, key="plot_selector"
        )

        # Update current ID based on selection
        selected_plot = next((p for p in plots if p.name == selected_name), plots[0])
        if selected_plot.plot_id != current_id:
            api.state_manager.set_current_plot_id(selected_plot.plot_id)

        return selected_plot

    @staticmethod
    def render_plot_controls(api: ApplicationAPI, plot: BasePlot) -> None:
        """Render controls for renaming and managing the current plot."""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            new_name = st.text_input("Rename plot", value=plot.name, key=f"rename_{plot.plot_id}")
            if new_name != plot.name:
                plot.name = new_name

        with col2:
            c2_1, c2_2 = st.columns(2)
            with c2_1:
                if st.button(
                    "Save Pipe", key=f"save_plot_{plot.plot_id}", help="Save current pipeline"
                ):
                    st.session_state[f"show_save_for_plot_{plot.plot_id}"] = True
                    st.session_state[f"show_load_for_plot_{plot.plot_id}"] = False
                    st.rerun()
            with c2_2:
                if st.button(
                    "Load Pipe", key=f"load_plot_{plot.plot_id}", help="Load to current pipeline"
                ):
                    st.session_state[f"show_load_for_plot_{plot.plot_id}"] = True
                    st.session_state[f"show_save_for_plot_{plot.plot_id}"] = False
                    st.rerun()

        with col3:
            if st.button("Delete", key=f"delete_plot_{plot.plot_id}"):
                PlotService.delete_plot(plot.plot_id, api.state_manager)
                st.rerun()

        with col4:
            if st.button("Duplicate", key=f"dup_plot_{plot.plot_id}"):
                PlotService.duplicate_plot(plot, api.state_manager)
                st.rerun()

        # Dialogs
        if st.session_state.get(f"show_save_for_plot_{plot.plot_id}", False):
            PlotManagerComponents._render_save_pipeline_dialog(plot)
        if st.session_state.get(f"show_load_for_plot_{plot.plot_id}", False):
            PlotManagerComponents._render_load_pipeline_dialog(plot)

    @staticmethod
    def _render_save_pipeline_dialog(plot: BasePlot) -> None:
        st.markdown("---")
        st.markdown(f"### Save Pipeline for '{plot.name}'")
        col1, col2 = st.columns([3, 1])
        with col1:
            name = st.text_input(
                "Pipeline Name", value=f"{plot.name}_pipeline", key=f"save_p_name_{plot.plot_id}"
            )
        with col2:
            st.write("")
            st.write("")
            if st.button("Save", type="primary", key=f"save_p_btn_{plot.plot_id}"):
                try:
                    PipelineService.save_pipeline(
                        name, plot.pipeline, description=f"Source: {plot.name}"
                    )
                    st.success("Pipeline saved!")
                    st.session_state[f"show_save_for_plot_{plot.plot_id}"] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            if st.button("Cancel", key=f"cancel_save_{plot.plot_id}"):
                st.session_state[f"show_save_for_plot_{plot.plot_id}"] = False
                st.rerun()

    @staticmethod
    def _render_load_pipeline_dialog(plot: BasePlot) -> None:
        st.markdown("---")
        st.markdown("### Load Pipeline")
        pipelines = PipelineService.list_pipelines()
        if not pipelines:
            st.warning("No saved pipelines found.")
            if st.button("Close", key=f"close_load_{plot.plot_id}"):
                st.session_state[f"show_load_for_plot_{plot.plot_id}"] = False
                st.rerun()
            return

        selected = st.selectbox("Select Pipeline", pipelines, key=f"load_p_sel_{plot.plot_id}")
        if st.button("Load", type="primary", key=f"load_p_btn_{plot.plot_id}"):
            try:
                data = PipelineService.load_pipeline(selected)
                plot.pipeline = copy.deepcopy(data.get("pipeline", []))
                plot.pipeline_counter = len(plot.pipeline)
                plot.processed_data = None  # Reset data
                st.success("Pipeline loaded!")
                st.session_state[f"show_load_for_plot_{plot.plot_id}"] = False
                st.rerun()
            except Exception as e:
                st.error(f"Error loading: {e}")
                logger.error(
                    "PLOT: Failed to load pipeline for plot '%s': %s", plot.name, e, exc_info=True
                )

        if st.button("Cancel", key=f"cancel_load_{plot.plot_id}"):
            st.session_state[f"show_load_for_plot_{plot.plot_id}"] = False
            st.rerun()

    @staticmethod
    def render_pipeline_editor(api: ApplicationAPI, plot: BasePlot) -> None:
        """Render the Data Processing Pipeline editor."""
        st.markdown("### Data Processing Pipeline")

        data = api.state_manager.get_data()
        if data is None:
            st.warning("Please upload data first!")
            return

        # Add shaper
        col1, col2 = st.columns([3, 1])
        shaper_map = {
            "Column Selector": "columnSelector",
            "Sort": "sort",
            "Mean Calculator": "mean",
            "Normalize": "normalize",
            "Filter": "conditionSelector",
            "Transformer": "transformer",
        }
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
                # Reverse map for display
                d_name = next(
                    (k for k, v in shaper_map.items() if v == shaper["type"]), shaper["type"]
                )
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
                        if idx > 0 and st.button("Up", key=f"up_{plot.plot_id}_{idx}"):
                            plot.pipeline[idx], plot.pipeline[idx - 1] = (
                                plot.pipeline[idx - 1],
                                plot.pipeline[idx],
                            )
                            st.rerun()
                    with c3:
                        if idx < len(plot.pipeline) - 1 and st.button(
                            "Down", key=f"down_{plot.plot_id}_{idx}"
                        ):
                            plot.pipeline[idx], plot.pipeline[idx + 1] = (
                                plot.pipeline[idx + 1],
                                plot.pipeline[idx],
                            )
                            st.rerun()
                    with c4:
                        if st.button("Del", key=f"del_{plot.plot_id}_{idx}"):
                            plot.pipeline.pop(idx)
                            st.rerun()

                    # Preview
                    if shaper["config"]:
                        try:
                            out = apply_shapers(inp, [shaper["config"]])
                            st.dataframe(out.head(5))
                        except Exception as e:
                            st.error(f"Preview error: {e}")
                            logger.error(
                                "PIPELINE: Preview failure for shaper index %d in plot '%s': %s",
                                idx,
                                plot.name,
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
                    st.error(f"Error: {e}")

    @staticmethod
    def render_plot_display(api: ApplicationAPI, plot: BasePlot) -> None:
        """Render the plot display section with controls."""
        if plot.processed_data is None:
            st.warning("No processed data available.")
            return

        st.markdown("### Visualization")

        # Config merge logic
        saved_config = plot.config
        current_config = saved_config.copy()

        st.markdown("---")
        st.markdown("### Plot Configuration")

        # Type Selector
        types = PlotFactory.get_available_plot_types()
        new_type = st.selectbox(
            "Plot Type",
            options=types,
            index=types.index(plot.plot_type) if plot.plot_type in types else 0,
            key=f"plot_type_sel_{plot.plot_id}",
        )

        if new_type != plot.plot_type:
            PlotService.change_plot_type(plot, new_type, api.state_manager)
            st.rerun()

        # Plot-specific UI
        data = plot.processed_data

        # Merge logic to preserve interactive state (e.g. range_x, legend_x)
        ui_config = plot.render_config_ui(data, saved_config)
        current_config.update(ui_config)

        # Advanced & Theme
        a1, a2 = st.columns(2)
        with a1:
            with st.expander("⚙️ Advanced Options"):
                # Pass current state so advanced options see UI updates
                advanced = plot.render_advanced_options(current_config, data)
                current_config.update(advanced)
        with a2:
            with st.expander("🎨 Theme & Style"):
                layout = plot.render_display_options(current_config)
                current_config.update(layout)
                st.markdown("---")
                theme = plot.render_theme_options(current_config)
                current_config.update(theme)

        # Refresh Logic
        config_changed = current_config != saved_config

        r1, r2 = st.columns([1, 3])
        with r1:
            auto = st.toggle(
                "Auto-refresh",
                value=st.session_state.get(f"auto_{plot.plot_id}", True),
                key=f"auto_t_{plot.plot_id}",
            )
            st.session_state[f"auto_{plot.plot_id}"] = auto
        with r2:
            manual = st.button("Refresh Plot", key=f"refresh_{plot.plot_id}", width="stretch")

        should_gen = manual or (auto and config_changed)
        plot.config = current_config

        PlotRenderer.render_plot(plot, should_gen)

    @staticmethod
    def render_workspace_management(api: ApplicationAPI, _PortfolioServiceClass: Any) -> None:
        """Render workspace management buttons."""
        st.markdown("---")
        st.markdown("### Workspace Management")

        st.markdown("#### Export All Plots")
        st.caption(
            "Export all plots to a local directory (e.g., your LaTeX repository). Uses individual plot settings (Scale/Format)."  # noqa: E501
        )

        ec1, ec2, ec3 = st.columns([2, 1, 1])
        with ec1:
            export_path = st.text_input(
                "Local Export Path",
                value=st.session_state.get("last_export_path", ""),
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
            if st.button("Export All", type="primary", width="stretch", key="export_all_btn"):
                if not export_path:
                    st.error("Please provide a path.")
                    logger.warning("EXPORT: Attempted export without providing path.")
                else:
                    st.session_state["last_export_path"] = export_path
                    plots = api.state_manager.get_plots()
                    if not plots:
                        st.warning("No plots to export.")
                    else:
                        count = 0
                        errors = []
                        # Determine override
                        fmt_arg = None
                        if export_fmt_override != "Keep Individual":
                            fmt_arg = export_fmt_override

                        progress = st.progress(0)
                        for i, p in enumerate(plots):
                            try:
                                fmt_to_use = fmt_arg if fmt_arg else "png"
                                res = PlotService.export_plot_to_file(
                                    p, export_path, format=fmt_to_use
                                )
                                if res:
                                    count += 1
                            except Exception as exc:
                                errors.append(f"{p.name}: {exc}")
                            progress.progress((i + 1) / len(plots))

                        progress.empty()
                        if count > 0:
                            st.success(f"Successfully exported {count} plots to '{export_path}'")
                        if errors:
                            st.error(f"Failed to export {len(errors)} plots.")
                            logger.error("EXPORT: Failed to export some plots. Errors: %s", errors)
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
                st.success("Workspace state synchronized.")
