import streamlit as st
import pandas as pd
from typing import Optional, List, Any
import copy
from src.plotting import BasePlot, PlotFactory, PlotRenderer
from src.web.state_manager import StateManager
from src.web.ui.shaper_config import apply_shapers, configure_shaper
from src.web.services.pipeline_service import PipelineService
from src.web.services.plot_service import PlotService

class PlotManagerComponents:
    """UI Components for the Plot Management Page."""

    @staticmethod
    def render_create_plot_section():
        """Render the section to create a new plot."""
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            new_plot_name = st.text_input(
                "New plot name", 
                value=f"Plot {StateManager.get_plot_counter() + 1}", 
                key="new_plot_name"
            )
        with col2:
            plot_types = PlotFactory.get_available_plot_types()
            plot_type = st.selectbox(
                "Plot type", 
                options=plot_types, 
                key="new_plot_type"
            )
        with col3:
            if st.button("Create Plot", width="stretch"):
                if plot_type:
                    PlotService.create_plot(new_plot_name, plot_type)
                    st.rerun()

    @staticmethod
    def render_plot_selector() -> Optional[BasePlot]:
        """Render tabs/selector for plots and return the current plot."""
        plots = StateManager.get_plots()
        if not plots:
            st.warning("No plots yet. Create a plot to get started!")
            return None

        plot_names = [p.name for p in plots]
        # Ensure selection persists or defaults to 0
        current_id = StateManager.get_current_plot_id()
        default_index = 0
        
        if current_id is not None:
             # Find index of current ID
             for i, p in enumerate(plots):
                 if p.plot_id == current_id:
                     default_index = i
                     break
        
        selected_name = st.radio(
            "Select Plot", 
            plot_names, 
            horizontal=True, 
            index=default_index,
            key="plot_selector"
        )
        
        # Update current ID based on selection
        selected_plot = next((p for p in plots if p.name == selected_name), plots[0])
        if selected_plot.plot_id != current_id:
            StateManager.set_current_plot_id(selected_plot.plot_id)
            
        return selected_plot

    @staticmethod
    def render_plot_controls(plot: BasePlot):
        """Render controls for renaming and managing the current plot."""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            new_name = st.text_input("Rename plot", value=plot.name, key=f"rename_{plot.plot_id}")
            if new_name != plot.name:
                plot.name = new_name

        with col2:
            c2_1, c2_2 = st.columns(2)
            with c2_1:
                if st.button("Save Pipe", key=f"save_plot_{plot.plot_id}", help="Save current pipeline"):
                    st.session_state[f"show_save_for_plot_{plot.plot_id}"] = True
                    st.session_state[f"show_load_for_plot_{plot.plot_id}"] = False
                    st.rerun()
            with c2_2:
                if st.button("Load Pipe", key=f"load_plot_{plot.plot_id}", help="Load to current pipeline"):
                    st.session_state[f"show_load_for_plot_{plot.plot_id}"] = True
                    st.session_state[f"show_save_for_plot_{plot.plot_id}"] = False
                    st.rerun()

        with col3:
            if st.button("Delete", key=f"delete_plot_{plot.plot_id}"):
                PlotService.delete_plot(plot.plot_id)
                st.rerun()

        with col4:
            if st.button("Duplicate", key=f"dup_plot_{plot.plot_id}"):
                PlotService.duplicate_plot(plot)
                st.rerun()

        # Dialogs
        if st.session_state.get(f"show_save_for_plot_{plot.plot_id}", False):
            PlotManagerComponents._render_save_pipeline_dialog(plot)
        if st.session_state.get(f"show_load_for_plot_{plot.plot_id}", False):
             PlotManagerComponents._render_load_pipeline_dialog(plot)

    @staticmethod
    def _render_save_pipeline_dialog(plot: BasePlot):
        st.markdown("---")
        st.markdown(f"### Save Pipeline for '{plot.name}'")
        col1, col2 = st.columns([3, 1])
        with col1:
             name = st.text_input("Pipeline Name", value=f"{plot.name}_pipeline", key=f"save_p_name_{plot.plot_id}")
        with col2:
             st.write("")
             st.write("")
             if st.button("Save", type="primary", key=f"save_p_btn_{plot.plot_id}"):
                 try:
                     PipelineService.save_pipeline(name, plot.pipeline, description=f"Source: {plot.name}")
                     st.success("Pipeline saved!")
                     st.session_state[f"show_save_for_plot_{plot.plot_id}"] = False
                     st.rerun()
                 except Exception as e:
                     st.error(f"Error: {e}")
             if st.button("Cancel", key=f"cancel_save_{plot.plot_id}"):
                 st.session_state[f"show_save_for_plot_{plot.plot_id}"] = False
                 st.rerun()

    @staticmethod
    def _render_load_pipeline_dialog(plot: BasePlot):
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
                plot.processed_data = None # Reset data
                st.success("Pipeline loaded!")
                st.session_state[f"show_load_for_plot_{plot.plot_id}"] = False
                st.rerun()
            except Exception as e:
                st.error(f"Error loading: {e}")
                
        if st.button("Cancel", key=f"cancel_load_{plot.plot_id}"):
            st.session_state[f"show_load_for_plot_{plot.plot_id}"] = False
            st.rerun()

    @staticmethod
    def render_pipeline_editor(plot: BasePlot):
        """Render the Data Processing Pipeline editor."""
        st.markdown("### Data Processing Pipeline")
        
        data = StateManager.get_data()
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
             display_type = st.selectbox("Add transformation", list(shaper_map.keys()), key=f"shaper_add_{plot.plot_id}")
        with col2:
             if st.button("Add to Pipeline", width="stretch", key=f"add_shaper_btn_{plot.plot_id}"):
                 plot.pipeline.append({
                     "id": plot.pipeline_counter,
                     "type": shaper_map[display_type],
                     "config": {}
                 })
                 plot.pipeline_counter += 1
                 st.rerun()

        # Config loop
        if plot.pipeline:
             st.markdown("**Current Pipeline:**")
             for idx, shaper in enumerate(plot.pipeline):
                 # Reverse map for display
                 d_name = next((k for k, v in shaper_map.items() if v == shaper["type"]), shaper["type"])
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
                             shaper["type"], inp, shaper["id"], shaper.get("config", {}), owner_id=plot.plot_id
                         )
                     
                     with c2:
                         if idx > 0 and st.button("Up", key=f"up_{plot.plot_id}_{idx}"):
                             plot.pipeline[idx], plot.pipeline[idx-1] = plot.pipeline[idx-1], plot.pipeline[idx]
                             st.rerun()
                     with c3:
                         if idx < len(plot.pipeline)-1 and st.button("Down", key=f"down_{plot.plot_id}_{idx}"):
                             plot.pipeline[idx], plot.pipeline[idx+1] = plot.pipeline[idx+1], plot.pipeline[idx]
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

        # Finalize
        if plot.pipeline:
            if st.button("Finalize Pipeline for Plotting", type="primary", width="stretch", key=f"finalize_{plot.plot_id}"):
                try:
                    confs = [s["config"] for s in plot.pipeline if s["config"]]
                    processed = apply_shapers(data, confs)
                    plot.processed_data = processed
                    st.success(f"Pipeline applied! Shape: {processed.shape}")
                    st.dataframe(processed.head(10))
                except Exception as e:
                     st.error(f"Error: {e}")

    @staticmethod
    def render_plot_display(plot: BasePlot):
        """Render the plot configuration and the plot itself."""
        if plot.processed_data is None:
             st.warning("No processed data available.")
             return

        st.markdown("---")
        st.markdown("### Plot Configuration")

        # Type Selector
        types = PlotFactory.get_available_plot_types()
        new_type = st.selectbox(
            "Plot Type", 
            options=types, 
            index=types.index(plot.plot_type) if plot.plot_type in types else 0,
            key=f"plot_type_sel_{plot.plot_id}"
        )
        
        if new_type != plot.plot_type:
            PlotService.change_plot_type(plot, new_type)
            st.rerun()
        
        # Plot-specific UI
        data = plot.processed_data
        saved_config = plot.config
        current_config = plot.render_config_ui(data, saved_config)
        
        # Advanced & Theme
        a1, a2 = st.columns(2)
        with a1:
            with st.expander("⚙️ Advanced Options"):
                 merged = saved_config.copy()
                 merged.update(current_config)
                 advanced = plot.render_advanced_options(merged, data)
                 current_config.update(advanced)
        with a2:
             with st.expander("🎨 Theme & Style"):
                 layout = plot.render_display_options(saved_config)
                 current_config.update(layout)
                 st.markdown("---")
                 theme = plot.render_theme_options(saved_config)
                 current_config.update(theme)

        # Refresh Logic
        config_changed = current_config != saved_config
        
        r1, r2 = st.columns([1, 3])
        with r1:
             auto = st.toggle("Auto-refresh", value=st.session_state.get(f"auto_{plot.plot_id}", True), key=f"auto_t_{plot.plot_id}")
             st.session_state[f"auto_{plot.plot_id}"] = auto
        with r2:
             manual = st.button("Refresh Plot", key=f"refresh_{plot.plot_id}", width="stretch")
        
        should_gen = manual or (auto and config_changed)
        plot.config = current_config
        
        PlotRenderer.render_plot(plot, should_gen)

    @staticmethod
    def render_workspace_management(PortfolioServiceClass):
        """Render workspace management buttons."""
        st.markdown("---")
        st.markdown("### Workspace Management")
        c1, c2 = st.columns(2)
        with c1:
             if st.button("Process All Plots in Parallel", width="stretch"):
                 st.info("Coming soon!")
        with c2:
             if st.button("Save Entire Workspace", width="stretch"):
                  # Use PortfolioService to save? 
                  # Actually the old behavior was sync only.
                  # But 'Save Entire Workspace' usually implies persistence.
                  # The user said "not persisting... save... load".
                  # The button in manage_plots just syncs to `st.session_state.plots` list.
                  # We should maintain that behavior or improve it.
                  # Let's keep the sync behavior for now as Portfolio Page does the real file saving.
                  plots = StateManager.get_plots()
                  # We simply confirm they are in state (they are, since we use get_plots/set_plots).
                  # Maybe this button is redundant now?
                  st.success("Workspace state synchronized.")
