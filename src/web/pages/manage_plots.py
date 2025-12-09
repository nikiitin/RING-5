"""Manage plots page using modern plot class hierarchy."""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Import plot classes
from src.plotting import PlotFactory, PlotRenderer, BasePlot

# Import functions from main app for delegation
import app as main_app


def apply_shapers(data, shapers_config):
    """Delegate to main app's apply_shapers function."""
    return main_app.apply_shapers(data, shapers_config)


def configure_shaper(shaper_type, data, shaper_id, existing_config):
    """Delegate to main app's configure_shaper function."""
    return main_app.configure_shaper(shaper_type, data, shaper_id, existing_config)


def initialize_session_state():
    """Initialize session state for plots management."""
    if 'plots_objects' not in st.session_state:
        st.session_state.plots_objects = []
    if 'plot_counter' not in st.session_state:
        st.session_state.plot_counter = 0
    if 'current_plot_id' not in st.session_state:
        st.session_state.current_plot_id = None
    
    # Migrate old plots to new format if needed
    if 'plots' in st.session_state and not st.session_state.plots_objects:
        migrate_old_plots()


def migrate_old_plots():
    """Migrate old dictionary-based plots to new class-based format."""
    for old_plot in st.session_state.plots:
        try:
            plot = PlotFactory.create_plot(
                plot_type=old_plot.get('plot_type', 'bar'),
                plot_id=old_plot['id'],
                name=old_plot['name']
            )
            plot.pipeline = old_plot.get('pipeline', [])
            plot.pipeline_counter = old_plot.get('pipeline_counter', 0)
            plot.processed_data = old_plot.get('processed_data')
            plot.config = old_plot.get('plot_config', {})
            plot.legend_mappings_by_column = old_plot.get('legend_mappings_by_column', {})
            plot.legend_mappings = old_plot.get('legend_mappings', {})
            
            st.session_state.plots_objects.append(plot)
        except Exception as e:
            st.error(f"Failed to migrate plot '{old_plot.get('name')}': {e}")
    
    # Clear old plots after migration
    if st.session_state.plots_objects:
        st.session_state.plots = []


def show_manage_plots_page():
    """Main interface for managing multiple plots with pipelines."""
    st.markdown("## Manage Plots")
    st.markdown("Create and configure multiple plots with independent data processing pipelines.")
    
    initialize_session_state()
    
    # Create new plot
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        new_plot_name = st.text_input(
            "New plot name",
            value=f"Plot {st.session_state.plot_counter + 1}",
            key="new_plot_name"
        )
    with col2:
        plot_type = st.selectbox(
            "Plot type",
            options=PlotFactory.get_available_plot_types(),
            key="new_plot_type"
        )
    with col3:
        if st.button("➕ Create Plot", width="stretch"):
            plot = PlotFactory.create_plot(
                plot_type=plot_type,
                plot_id=st.session_state.plot_counter,
                name=new_plot_name
            )
            st.session_state.plots_objects.append(plot)
            st.session_state.plot_counter += 1
            st.session_state.current_plot_id = plot.plot_id
            st.rerun()
    
    if not st.session_state.plots_objects:
        st.warning("No plots yet. Create a plot to get started!")
        return
    
    # Plot selection tabs
    plot_names = [p.name for p in st.session_state.plots_objects]
    selected_tab = st.radio("Select Plot", plot_names, horizontal=True, key="plot_selector")
    
    plot_idx = plot_names.index(selected_tab)
    current_plot = st.session_state.plots_objects[plot_idx]
    st.session_state.current_plot_id = current_plot.plot_id
    
    # Plot management
    render_plot_management(current_plot, plot_idx)
    
    # Data pipeline
    st.markdown("---")
    render_data_pipeline(current_plot)
    
    # Plot configuration
    if current_plot.processed_data is not None:
        st.markdown("---")
        render_plot_configuration(current_plot)
    
    # Workspace management
    st.markdown("---")
    render_workspace_management()


def render_plot_management(plot: BasePlot, plot_idx: int):
    """Render plot management controls."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        new_name = st.text_input(
            "Rename plot",
            value=plot.name,
            key=f"rename_{plot.plot_id}"
        )
        if new_name != plot.name:
            plot.name = new_name
    
    with col2:
        if st.button("📥 Load Config", key=f"load_plot_{plot.plot_id}"):
            st.session_state[f'show_load_for_plot_{plot.plot_id}'] = True
            st.rerun()
    
    with col3:
        if st.button("🗑️ Delete", key=f"delete_plot_{plot.plot_id}"):
            st.session_state.plots_objects.pop(plot_idx)
            st.rerun()
    
    with col4:
        if st.button("📋 Duplicate", key=f"dup_plot_{plot.plot_id}"):
            import copy
            new_plot = copy.deepcopy(plot)
            new_plot.plot_id = st.session_state.plot_counter
            new_plot.name = f"{plot.name} (copy)"
            # Clear non-serializable data
            new_plot.last_generated_fig = None
            st.session_state.plots_objects.append(new_plot)
            st.session_state.plot_counter += 1
            st.rerun()
    
    # Show load dialog if requested
    if st.session_state.get(f'show_load_for_plot_{plot.plot_id}', False):
        render_load_config_dialog(plot)


def render_load_config_dialog(plot: BasePlot):
    """Render dialog for loading saved configurations."""
    st.markdown("---")
    st.markdown("### Load Pipeline Configuration")
    
    from pathlib import Path
    RING5_DATA_DIR = Path.home() / '.ring5'
    CONFIGS_DIR = RING5_DATA_DIR / 'configs'
    
    if CONFIGS_DIR.exists():
        config_files = list(CONFIGS_DIR.glob("*.json"))
        if config_files:
            config_names = [c.stem for c in config_files]
            selected_config = st.selectbox(
                "Select configuration",
                config_names,
                key=f"load_config_select_{plot.plot_id}"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Load", type="primary", key=f"confirm_load_{plot.plot_id}"):
                    import json
                    config_path = CONFIGS_DIR / f"{selected_config}.json"
                    with open(config_path, 'r') as f:
                        loaded_config = json.load(f)
                    
                    if 'pipeline' in loaded_config:
                        pipeline = loaded_config['pipeline']
                        pipeline_counter = loaded_config.get('pipeline_counter', len(pipeline))
                        plot.pipeline = pipeline
                        plot.pipeline_counter = pipeline_counter
                        st.success(f"Loaded configuration: {selected_config}")
                        st.session_state[f'show_load_for_plot_{plot.plot_id}'] = False
                        st.rerun()
            
            with col2:
                if st.button("Cancel", key=f"cancel_load_{plot.plot_id}"):
                    st.session_state[f'show_load_for_plot_{plot.plot_id}'] = False
                    st.rerun()
        else:
            st.info("No saved configurations found.")
    else:
        st.info("No saved configurations found.")


def render_data_pipeline(plot: BasePlot):
    """Render data pipeline configuration."""
    st.markdown("### Data Processing Pipeline")
    
    if st.session_state.data is None:
        st.warning("Please load data first from the Data Manager page.")
        return
    
    # Add shaper to pipeline
    col1, col2 = st.columns([3, 1])
    with col1:
        shaper_types = ['Column Selector', 'Sort', 'Mean Calculator', 'Normalize', 'Filter']
        selected_shaper = st.selectbox(
            "Add transformation",
            shaper_types,
            key=f"shaper_type_{plot.plot_id}"
        )
    
    with col2:
        if st.button("Add to Pipeline", width="stretch", key=f"add_shaper_{plot.plot_id}"):
            plot.pipeline.append({
                'id': plot.pipeline_counter,
                'type': selected_shaper,
                'config': {}
            })
            plot.pipeline_counter += 1
            st.rerun()
    
    # Display and configure pipeline
    if plot.pipeline:
        st.markdown("**Current Pipeline:**")
        
        for idx, shaper in enumerate(plot.pipeline):
            with st.expander(f"{idx + 1}. {shaper['type']}", expanded=True):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    # Get input data for this shaper
                    if idx == 0:
                        input_data = st.session_state.data
                    else:
                        prev_configs = [s['config'] for s in plot.pipeline[:idx] if s['config']]
                        input_data = apply_shapers(st.session_state.data, prev_configs)
                    
                    # Configure shaper
                    shaper['config'] = configure_shaper(
                        shaper['type'],
                        input_data,
                        shaper['id'],
                        shaper.get('config', {})
                    )
                
                with col2:
                    if idx > 0 and st.button("↑", key=f"up_{plot.plot_id}_{idx}"):
                        plot.pipeline[idx], plot.pipeline[idx-1] = plot.pipeline[idx-1], plot.pipeline[idx]
                        st.rerun()
                
                with col3:
                    if idx < len(plot.pipeline) - 1 and st.button("↓", key=f"down_{plot.plot_id}_{idx}"):
                        plot.pipeline[idx], plot.pipeline[idx+1] = plot.pipeline[idx+1], plot.pipeline[idx]
                        st.rerun()
                
                with col4:
                    if st.button("🗑️", key=f"del_{plot.plot_id}_{idx}"):
                        plot.pipeline.pop(idx)
                        st.rerun()
                
                # Show preview
                if shaper['config']:
                    try:
                        output_data = apply_shapers(input_data, [shaper['config']])
                        st.dataframe(output_data.head(5))
                    except Exception as e:
                        st.error(f"Preview error: {e}")
    
    # Finalize pipeline
    if plot.pipeline:
        if st.button(
            "Finalize Pipeline for Plotting",
            type="primary",
            width="stretch",
            key=f"apply_{plot.plot_id}"
        ):
            try:
                shapers_config = [s['config'] for s in plot.pipeline if s['config']]
                processed_data = apply_shapers(st.session_state.data, shapers_config)
                plot.processed_data = processed_data
                st.success(f"Pipeline applied! Data shape: {processed_data.shape}")
                st.dataframe(processed_data.head(10))
            except Exception as e:
                st.error(f"Error applying pipeline: {e}")


def render_plot_configuration(plot: BasePlot):
    """Render plot configuration and visualization."""
    st.markdown("### Plot Configuration")
    
    data = plot.processed_data
    saved_config = plot.config
    
    # Plot type selector
    plot_types = PlotFactory.get_available_plot_types()
    plot_type_idx = plot_types.index(plot.plot_type) if plot.plot_type in plot_types else 0
    
    new_plot_type = st.selectbox(
        "Plot Type",
        options=plot_types,
        index=plot_type_idx,
        key=f"plot_type_{plot.plot_id}"
    )
    
    # If plot type changed, create new plot instance
    if new_plot_type != plot.plot_type:
        new_plot = PlotFactory.create_plot(new_plot_type, plot.plot_id, plot.name)
        new_plot.pipeline = plot.pipeline
        new_plot.pipeline_counter = plot.pipeline_counter
        new_plot.processed_data = plot.processed_data
        new_plot.config = {}  # Reset config when type changes
        
        # Replace in session state
        plot_idx = st.session_state.plots_objects.index(plot)
        st.session_state.plots_objects[plot_idx] = new_plot
        st.rerun()
        return
    
    # Render plot-specific configuration
    current_config = plot.render_config_ui(data, saved_config)
    
    # Advanced Options - in an expander
    with st.expander("⚙️ Advanced Options", expanded=False):
        # Advanced display options (legend, error bars, download)
        advanced_config = plot.render_advanced_options(saved_config)
        current_config.update(advanced_config)
        
        st.markdown("---")
        st.markdown("#### Legend Label Customization")
        legend_labels = PlotRenderer.render_legend_customization(plot, data, current_config)
        if legend_labels:
            current_config['legend_labels'] = legend_labels
    
    # Check if config changed (for auto-refresh)
    config_changed = current_config != saved_config
    
    # Auto-refresh toggle
    col1, col2 = st.columns([1, 3])
    with col1:
        auto_refresh = st.toggle(
            "Auto-refresh plot",
            value=st.session_state.get(f'auto_refresh_{plot.plot_id}', True),
            key=f"auto_refresh_toggle_{plot.plot_id}"
        )
        st.session_state[f'auto_refresh_{plot.plot_id}'] = auto_refresh
    
    with col2:
        manual_generate = st.button(
            "🔄 Refresh Plot",
            type="secondary",
            width="stretch",
            key=f"generate_{plot.plot_id}"
        )
    
    # Determine if we should generate
    should_generate = manual_generate or (auto_refresh and config_changed)
    
    # Store config
    plot.config = current_config
    
    # Render the plot
    PlotRenderer.render_plot(plot, should_generate)


def render_workspace_management():
    """Render workspace-level management controls."""
    st.markdown("### Workspace Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Process All Plots in Parallel", width="stretch"):
            st.info("Parallel processing feature coming soon!")
    
    with col2:
        if st.button("💾 Save Entire Workspace", width="stretch"):
            # Convert plot objects to dictionaries for saving
            plots_data = [plot.to_dict() for plot in st.session_state.plots_objects]
            # Store in old format for compatibility
            st.session_state.plots = plots_data
            st.success("Workspace synchronized for saving")


# Main entry point
if __name__ == "__main__":
    show_manage_plots_page()
