"""Manage plots page with delegation to main app functions."""
import streamlit as st
import plotly.express as px
import pandas as pd


# Import functions from main app for delegation
import sys
from pathlib import Path

# Add parent directory to path to import app
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import app as main_app


def apply_shapers(data, shapers_config):
    """Delegate to main app's apply_shapers function."""
    return main_app.apply_shapers(data, shapers_config)


def configure_shaper(shaper_type, data, shaper_id, existing_config):
    """Delegate to main app's configure_shaper function."""
    return main_app.configure_shaper(shaper_type, data, shaper_id, existing_config)


def show_manage_plots_page():
    """Main interface for managing multiple plots with pipelines."""
    st.markdown("## Manage Plots")
    st.markdown("Create and configure multiple plots with independent data processing pipelines.")
    
    # Initialize plots if needed
    if 'plots' not in st.session_state:
        st.session_state.plots = []
    if 'plot_counter' not in st.session_state:
        st.session_state.plot_counter = 0
    if 'current_plot_id' not in st.session_state:
        st.session_state.current_plot_id = None
    
    # Create new plot
    col1, col2 = st.columns([2, 1])
    with col1:
        new_plot_name = st.text_input("New plot name", value=f"Plot {st.session_state.plot_counter + 1}", key="new_plot_name")
    with col2:
        if st.button("➕ Create Plot", width="stretch"):
            st.session_state.plots.append({
                'id': st.session_state.plot_counter,
                'name': new_plot_name,
                'pipeline': [],
                'pipeline_counter': 0,
                'plot_type': 'bar',
                'plot_config': {},
                'processed_data': None
            })
            st.session_state.plot_counter += 1
            st.session_state.current_plot_id = st.session_state.plot_counter - 1
            st.rerun()
    
    if not st.session_state.plots:
        st.warning("No plots yet. Create a plot to get started!")
        return
    
    # Plot selection tabs
    plot_names = [p['name'] for p in st.session_state.plots]
    selected_tab = st.radio("Select Plot", plot_names, horizontal=True, key="plot_selector")
    
    plot_idx = plot_names.index(selected_tab)
    current_plot = st.session_state.plots[plot_idx]
    st.session_state.current_plot_id = current_plot['id']
    
    # Plot management
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        new_name = st.text_input("Rename plot", value=current_plot['name'], key=f"rename_{current_plot['id']}")
        if new_name != current_plot['name']:
            current_plot['name'] = new_name
    
    with col2:
        if st.button("📥 Load Config to This Plot", key=f"load_plot_{current_plot['id']}"):
            st.session_state[f'show_load_for_plot_{current_plot["id"]}'] = True
            st.rerun()
    
    with col3:
        if st.button("🗑️ Delete This Plot", key=f"delete_plot_{current_plot['id']}"):
            st.session_state.plots.pop(plot_idx)
            st.rerun()
    
    with col4:
        if st.button("📋 Duplicate Plot", key=f"dup_plot_{current_plot['id']}"):
            import copy
            new_plot = copy.deepcopy(current_plot)
            new_plot['id'] = st.session_state.plot_counter
            new_plot['name'] = f"{current_plot['name']} (copy)"
            st.session_state.plots.append(new_plot)
            st.session_state.plot_counter += 1
            st.rerun()
    
    # Show load dialog for this plot if requested
    if st.session_state.get(f'show_load_for_plot_{current_plot["id"]}', False):
        st.markdown("---")
        st.markdown("### Load Pipeline Configuration")
        
        from pathlib import Path
        RING5_DATA_DIR = Path.home() / '.ring5'
        CONFIG_DIR = RING5_DATA_DIR / 'configs'
        
        if CONFIG_DIR.exists():
            config_files = list(CONFIG_DIR.glob("*.json"))
            if config_files:
                config_names = [c.stem for c in config_files]
                selected_config = st.selectbox("Select configuration", config_names, key=f"load_config_select_{current_plot['id']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Load Pipeline Only", key=f"load_pipeline_{current_plot['id']}"):
                        try:
                            import json
                            config_path = CONFIG_DIR / f"{selected_config}.json"
                            with open(config_path, 'r') as f:
                                config_data = json.load(f)
                            
                            # Load just the pipeline
                            if 'pipeline' in config_data:
                                pipeline = config_data['pipeline']
                                pipeline_counter = 0
                                for s in pipeline:
                                    s['id'] = pipeline_counter
                                    pipeline_counter += 1
                                
                                current_plot['pipeline'] = pipeline
                                current_plot['pipeline_counter'] = pipeline_counter
                                
                                st.success(f"Loaded pipeline with {len(pipeline)} shapers")
                                st.session_state[f'show_load_for_plot_{current_plot["id"]}'] = False
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                
                with col2:
                    if st.button("Cancel", key=f"cancel_load_{current_plot['id']}"):
                        st.session_state[f'show_load_for_plot_{current_plot["id"]}'] = False
                        st.rerun()
            else:
                st.warning("No saved configurations found")
        else:
            st.warning("No configurations directory found")
    
    # Pipeline configuration
    st.markdown("---")
    st.markdown("### Data Processing Pipeline")
    
    if st.session_state.data is None:
        st.warning("Please load data first from the Data Source page")
        return
    
    # Add shaper to pipeline
    col1, col2 = st.columns([3, 1])
    with col1:
        shaper_types = ['Column Selector', 'Sort', 'Mean Calculator', 'Normalize', 'Filter']
        selected_shaper = st.selectbox("Add shaper to pipeline", shaper_types, key=f"shaper_select_{current_plot['id']}")
    with col2:
        if st.button("Add to Pipeline", width="stretch", key=f"add_shaper_{current_plot['id']}"):
            current_plot['pipeline'].append({
                'type': selected_shaper,
                'config': None,
                'id': current_plot['pipeline_counter']
            })
            current_plot['pipeline_counter'] += 1
            st.rerun()
    
    # Display and configure pipeline
    if current_plot['pipeline']:
        st.markdown("#### Pipeline Steps")
        
        for idx, shaper in enumerate(current_plot['pipeline']):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    with st.expander(f"**{idx + 1}. {shaper['type']}**", expanded=False):
                        # Get data from previous step or original data
                        if idx == 0:
                            input_data = st.session_state.data.copy()
                        else:
                            try:
                                prev_shapers = [s['config'] for s in current_plot['pipeline'][:idx] if s['config']]
                                input_data = apply_shapers(st.session_state.data.copy(), prev_shapers)
                            except:
                                input_data = st.session_state.data.copy()
                        
                        st.caption(f"Input: {len(input_data)} rows, {len(input_data.columns)} columns")
                        
                        # Configure this shaper
                        shaper['config'] = configure_shaper(shaper['type'], input_data, shaper['id'], shaper.get('config', {}))
                    
                    # Execute this shaper speculatively if configured
                    if shaper.get('config'):
                        try:
                            output_data = apply_shapers(input_data, [shaper['config']])
                            st.caption(f"✓ Output: {len(output_data)} rows, {len(output_data.columns)} columns")
                            with st.expander("Preview output", expanded=False):
                                st.dataframe(output_data.head(5))
                        except Exception as e:
                            st.caption(f"⚠️ Configuration incomplete or error: {str(e)}")
                
                with col2:
                    if idx > 0:
                        if st.button("Up", key=f"up_{current_plot['id']}_{idx}"):
                            current_plot['pipeline'][idx], current_plot['pipeline'][idx-1] = \
                                current_plot['pipeline'][idx-1], current_plot['pipeline'][idx]
                            st.rerun()
                
                with col3:
                    if idx < len(current_plot['pipeline']) - 1:
                        if st.button("Down", key=f"down_{current_plot['id']}_{idx}"):
                            current_plot['pipeline'][idx], current_plot['pipeline'][idx+1] = \
                                current_plot['pipeline'][idx+1], current_plot['pipeline'][idx]
                            st.rerun()
                
                with col4:
                    if st.button("Delete", key=f"delete_{current_plot['id']}_{idx}"):
                        current_plot['pipeline'].pop(idx)
                        st.rerun()
    
    # Finalize pipeline button
    if current_plot['pipeline']:
        if st.button("Finalize Pipeline for Plotting", type="primary", width="stretch", key=f"apply_{current_plot['id']}"):
            with st.spinner("Finalizing pipeline..."):
                try:
                    shapers_config = [s['config'] for s in current_plot['pipeline'] if s['config']]
                    processed_data = apply_shapers(st.session_state.data.copy(), shapers_config)
                    current_plot['processed_data'] = processed_data
                    # Clear cached figure so it regenerates with new data
                    if 'last_generated_fig' in current_plot:
                        del current_plot['last_generated_fig']
                    st.success(f"Pipeline finalized! {len(processed_data)} rows, {len(processed_data.columns)} columns ready for plotting.")
                    st.dataframe(processed_data.head(10))
                except Exception as e:
                    st.error(f"Error processing data: {e}")
    
    st.markdown("---")
    
    # Plot configuration
    if current_plot['processed_data'] is not None:
        st.markdown("### Plot Configuration")
        
        data = current_plot['processed_data']
        
        # Get saved config if it exists
        saved_config = current_plot.get('plot_config', {})
        
        # Plot type selector
        plot_types = ['bar', 'grouped_bar', 'grouped_stacked_bar', 'line', 'scatter']
        plot_type_default = current_plot.get('plot_type', 'bar')
        plot_type_idx = plot_types.index(plot_type_default) if plot_type_default in plot_types else 0
        
        plot_type = st.selectbox(
            "Plot Type",
            options=plot_types,
            index=plot_type_idx,
            key=f"plot_type_{current_plot['id']}"
        )
        
        # Update plot type in the plot configuration
        current_plot['plot_type'] = plot_type
        
        col1, col2 = st.columns(2)
        
        with col1:
            numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
            
            # Use saved values as index if available
            x_default_idx = 0
            if saved_config.get('x') and saved_config['x'] in (categorical_cols + numeric_cols):
                x_default_idx = (categorical_cols + numeric_cols).index(saved_config['x'])
            
            x_column = st.selectbox("X-axis", options=categorical_cols + numeric_cols,
                                   index=x_default_idx,
                                   key=f"x_{current_plot['id']}")
            
            y_default_idx = 0
            if saved_config.get('y') and saved_config['y'] in numeric_cols:
                y_default_idx = numeric_cols.index(saved_config['y'])
            
            y_column = st.selectbox("Y-axis", options=numeric_cols,
                                   index=y_default_idx,
                                   key=f"y_{current_plot['id']}")
            
            if plot_type == 'grouped_bar':
                group_default_idx = 0
                if saved_config.get('group') and saved_config['group'] in categorical_cols:
                    group_default_idx = categorical_cols.index(saved_config['group'])
                
                group_column = st.selectbox("Group by", options=categorical_cols,
                                           index=group_default_idx,
                                           key=f"group_{current_plot['id']}")
                stack_column = None
            elif plot_type == 'grouped_stacked_bar':
                group_default_idx = 0
                if saved_config.get('group') and saved_config['group'] in categorical_cols:
                    group_default_idx = categorical_cols.index(saved_config['group'])
                
                group_column = st.selectbox("Group by (x-axis groups)", options=categorical_cols,
                                           index=group_default_idx,
                                           key=f"group_{current_plot['id']}")
                
                stack_default_idx = 0
                if saved_config.get('stack') and saved_config['stack'] in categorical_cols:
                    stack_default_idx = categorical_cols.index(saved_config['stack'])
                
                stack_column = st.selectbox("Stack by (within groups)", options=categorical_cols,
                                           index=stack_default_idx,
                                           key=f"stack_{current_plot['id']}")
            else:
                group_column = None
                stack_column = None
            
            color_options = [None] + categorical_cols
            color_default_idx = 0
            if saved_config.get('color') and saved_config['color'] in categorical_cols:
                color_default_idx = color_options.index(saved_config['color'])
            
            color_column = st.selectbox("Color by (optional)", options=color_options,
                                       index=color_default_idx,
                                       key=f"color_{current_plot['id']}")
        
        with col2:
            default_title = saved_config.get('title', f"{y_column} by {x_column}")
            title = st.text_input("Title", value=default_title, 
                                 key=f"title_{current_plot['id']}")
            
            default_xlabel = saved_config.get('xlabel', x_column)
            xlabel = st.text_input("X-label", value=default_xlabel, key=f"xlabel_{current_plot['id']}")
            
            default_ylabel = saved_config.get('ylabel', y_column)
            ylabel = st.text_input("Y-label", value=default_ylabel, key=f"ylabel_{current_plot['id']}")
            
            default_width = saved_config.get('width', 800)
            width = st.slider("Width (px)", 400, 1600, default_width, key=f"width_{current_plot['id']}")
            
            default_height = saved_config.get('height', 600)
            height = st.slider("Height (px)", 300, 1200, default_height, key=f"height_{current_plot['id']}")
        
        # Advanced options
        with st.expander("Advanced Options"):
            col1, col2 = st.columns(2)
            
            with col1:
                default_legend_title = saved_config.get('legend_title', '')
                legend_title = st.text_input("Legend Title", value=default_legend_title, key=f"legend_title_{current_plot['id']}")
                
                default_error_bars = saved_config.get('show_error_bars', False)
                show_error_bars = st.checkbox("Show Error Bars (if .sd columns exist)", value=default_error_bars, 
                                             key=f"error_bars_{current_plot['id']}")
            
            with col2:
                download_formats = ['html', 'png', 'pdf']
                default_format_idx = 0
                if saved_config.get('download_format') in download_formats:
                    default_format_idx = download_formats.index(saved_config['download_format'])
                
                download_format = st.selectbox("Download Format", options=download_formats,
                                              index=default_format_idx,
                                              key=f"download_fmt_{current_plot['id']}")
            
            # Legend labels customization
            if color_column or (plot_type == 'grouped_bar' and group_column) or (plot_type == 'grouped_stacked_bar' and stack_column):
                if plot_type == 'grouped_bar':
                    legend_col = group_column
                elif plot_type == 'grouped_stacked_bar':
                    legend_col = stack_column
                else:
                    legend_col = color_column
                unique_vals = data[legend_col].unique().tolist() if legend_col else []
                
                st.markdown("**Custom Legend Labels**")
                st.caption("Customize the legend labels for each value (leave blank to keep original)")
                
                # Initialize per-column legend mappings storage if not exists
                if 'legend_mappings_by_column' not in current_plot:
                    current_plot['legend_mappings_by_column'] = {}
                
                # Get existing mappings for THIS specific column
                existing_mappings_for_column = current_plot['legend_mappings_by_column'].get(legend_col, {})
                
                # Fallback to old legend_mappings or saved_config for backward compatibility
                if not existing_mappings_for_column:
                    # Try legacy legend_mappings first
                    if current_plot.get('legend_mappings'):
                        existing_mappings_for_column = current_plot.get('legend_mappings', {})
                    # Then try saved_config
                    elif saved_config.get('legend_labels'):
                        existing_mappings_for_column = saved_config.get('legend_labels', {})
                
                # Create individual text inputs for each unique value
                legend_labels = {}
                num_cols = min(3, len(unique_vals))
                cols = st.columns(num_cols)
                
                for idx, val in enumerate(unique_vals):
                    col_idx = idx % num_cols
                    with cols[col_idx]:
                        # Get existing mapping for this value in this column
                        default_value = existing_mappings_for_column.get(str(val), str(val))
                        custom_label = st.text_input(
                            f"`{val}`",
                            value=default_value,
                            key=f"legend_label_{current_plot['id']}_{legend_col}_{val}",
                            label_visibility="visible"
                        )
                        # Only add to mapping if user provided a value
                        if custom_label and custom_label.strip():
                            legend_labels[str(val)] = custom_label.strip()
                        else:
                            legend_labels[str(val)] = str(val)
                
                # Store mappings for THIS column specifically
                current_plot['legend_mappings_by_column'][legend_col] = legend_labels
                
                # Also update the global legend_mappings for backward compatibility
                current_plot['legend_mappings'] = legend_labels
            else:
                legend_labels = None
        
        # Build current configuration for comparison
        current_config = {
            'type': plot_type,
            'x': x_column,
            'y': y_column,
            'group': group_column,
            'stack': stack_column if plot_type == 'grouped_stacked_bar' else None,
            'color': color_column,
            'title': title,
            'xlabel': xlabel,
            'ylabel': ylabel,
            'width': width,
            'height': height,
            'legend_title': legend_title,
            'show_error_bars': show_error_bars,
            'download_format': download_format,
            'legend_labels': legend_labels
        }
        
        # Check if configuration has changed (for auto-refresh)
        config_changed = current_plot.get('plot_config') != current_config
        
        # Auto-generate plot when configuration changes or on manual request
        manual_generate = st.button("🔄 Refresh Plot", type="secondary", width="stretch", 
                                    key=f"gen_{current_plot['id']}")
        
        # Enable auto-refresh toggle
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption("💡 Auto-refresh: Plot updates automatically when you change any setting")
        with col2:
            auto_refresh = st.toggle("Auto-refresh", value=True, key=f"auto_refresh_{current_plot['id']}")
        
        # Generate plot automatically or manually
        should_generate = manual_generate or (auto_refresh and config_changed)
        
        if should_generate or current_plot.get('last_generated_fig') is not None:
            try:
                # Only regenerate if needed
                if should_generate:
                    # Check for error bars
                    y_error = None
                    if show_error_bars:
                        sd_col = f"{y_column}.sd"
                        if sd_col in data.columns:
                            y_error = sd_col
                    
                    if plot_type == 'bar':
                        fig = px.bar(data, x=x_column, y=y_column, color=color_column,
                                    error_y=y_error,
                                    title=title, labels={x_column: xlabel, y_column: ylabel})
                    elif plot_type == 'grouped_bar':
                        fig = px.bar(data, x=x_column, y=y_column, color=group_column,
                                    error_y=y_error,
                                    barmode='group', title=title, 
                                    labels={x_column: xlabel, y_column: ylabel})
                    elif plot_type == 'grouped_stacked_bar':
                        # Create grouped stacked bar using both group and stack dimensions
                        fig = px.bar(data, x=group_column, y=y_column, color=stack_column,
                                    error_y=y_error,
                                    barmode='group', title=title,
                                    labels={group_column: xlabel, y_column: ylabel},
                                    facet_col=x_column if x_column != group_column else None)
                    elif plot_type == 'line':
                        fig = px.line(data, x=x_column, y=y_column, color=color_column,
                                     error_y=y_error,
                                     title=title, labels={x_column: xlabel, y_column: ylabel})
                    elif plot_type == 'scatter':
                        fig = px.scatter(data, x=x_column, y=y_column, color=color_column,
                                        error_y=y_error,
                                        title=title, labels={x_column: xlabel, y_column: ylabel})
                    
                    fig.update_layout(width=width, height=height, hovermode='closest')
                    fig.update_traces(hovertemplate='<b>%{x}</b><br>%{y:.4f}<extra></extra>')
                    
                    # Update legend
                    if legend_title:
                        fig.update_layout(legend_title_text=legend_title)
                    
                    if legend_labels:
                        # Use the mapping dictionary directly
                        fig.for_each_trace(lambda t: t.update(name=legend_labels.get(t.name, t.name)))
                    
                    # Store the figure and config
                    current_plot['last_generated_fig'] = fig
                    current_plot['plot_config'] = current_config
                else:
                    # Use cached figure
                    fig = current_plot.get('last_generated_fig')
                
                # Display the plot
                st.plotly_chart(fig)
                
                # Download button
                import plotly.io as pio
                if download_format == 'html':
                    # Export as interactive HTML (no extra dependencies needed)
                    html_str = pio.to_html(fig, include_plotlyjs=True)
                    st.download_button(
                        label="Download Interactive HTML",
                        data=html_str,
                        file_name=f"{current_plot['name']}.html",
                        mime="text/html"
                    )
                elif download_format in ['png', 'pdf']:
                    try:
                        # Convert plotly figure to static image using matplotlib backend
                        import matplotlib.pyplot as plt
                        import matplotlib.backends.backend_pdf as pdf_backend
                        import io
                        
                        # Extract data from plotly figure
                        fig_data = fig.to_dict()
                        
                        # Create matplotlib figure
                        mpl_fig = plt.figure(figsize=(width/100, height/100))
                        
                        # Handle grouped bar charts
                        if plot_type == 'grouped_bar' and group_column:
                            import numpy as np
                            x_categories = data[x_column].unique()
                            groups = data[group_column].unique()
                            x_pos = np.arange(len(x_categories))
                            bar_width = 0.8 / len(groups)
                            
                            for idx, group in enumerate(groups):
                                group_data = data[data[group_column] == group]
                                y_vals = [group_data[group_data[x_column] == cat][y_column].values[0] if cat in group_data[x_column].values else 0 for cat in x_categories]
                                offset = (idx - len(groups)/2 + 0.5) * bar_width
                                label = legend_labels.get(str(group), str(group)) if legend_labels else str(group)
                                plt.bar(x_pos + offset, y_vals, bar_width, label=label, alpha=0.8)
                            
                            plt.xticks(x_pos, x_categories, rotation=45, ha='right')
                        else:
                            # Regular plots
                            for trace in fig_data['data']:
                                if trace['type'] in ['bar', 'scatter']:
                                    x_data = trace.get('x', [])
                                    y_data = trace.get('y', [])
                                    label = trace.get('name', '')
                                    
                                    if trace['type'] == 'bar':
                                        plt.bar(x_data, y_data, label=label, alpha=0.8)
                                    else:  # scatter/line
                                        mode = trace.get('mode', 'markers')
                                        if 'lines' in mode:
                                            plt.plot(x_data, y_data, label=label, marker='o')
                                        else:
                                            plt.scatter(x_data, y_data, label=label)
                            
                            plt.xticks(rotation=45, ha='right')
                        
                        plt.xlabel(xlabel if xlabel else x_column)
                        plt.ylabel(ylabel if ylabel else y_column)
                        plt.title(title if title else current_plot['name'])
                        if legend_title:
                            plt.legend(title=legend_title)
                        else:
                            plt.legend()
                        plt.tight_layout()
                        
                        # Save to bytes
                        buf = io.BytesIO()
                        if download_format == 'pdf':
                            plt.savefig(buf, format='pdf', bbox_inches='tight')
                            mime = 'application/pdf'
                            label = 'Download PDF'
                            filename = f"{current_plot['name']}.pdf"
                        else:
                            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                            mime = 'image/png'
                            label = 'Download PNG'
                            filename = f"{current_plot['name']}.png"
                        
                        buf.seek(0)
                        plt.close()
                        
                        st.download_button(
                            label=label,
                            data=buf,
                            file_name=filename,
                            mime=mime
                        )
                    except Exception as e:
                        st.error(f"Export failed: {e}. Please use HTML format instead.")
            except Exception as e:
                st.error(f"Error generating plot: {e}")
                # Clear cached figure on error
                if 'last_generated_fig' in current_plot:
                    del current_plot['last_generated_fig']
    
    # Batch process all plots
    st.markdown("---")
    st.markdown("### Workspace Operations")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚀 Process All Plots in Parallel", width="stretch"):
            process_all_plots_parallel()
    
    with col2:
        if st.button("💾 Save Entire Workspace", width="stretch"):
            st.session_state.show_save_dialog = True
            st.rerun()
    
    with col3:
        if st.button("📥 Load Workspace", width="stretch"):
            st.session_state.show_load_workspace = True
            st.rerun()
    
    # Show save dialog if flag is set
    if st.session_state.get('show_save_dialog', False):
        from app import show_save_config_dialog
        show_save_config_dialog()
        if st.button("Cancel Save"):
            st.session_state.show_save_dialog = False
            st.rerun()
    
    # Show load workspace dialog
    if st.session_state.get('show_load_workspace', False):
        from app import show_load_workspace_dialog
        show_load_workspace_dialog()
        if st.button("Cancel Load"):
            st.session_state.show_load_workspace = False
            st.rerun()


def process_all_plots_parallel():
    """Process all plots in parallel using ThreadPoolExecutor."""
    plots_to_process = [p for p in st.session_state.plots if p['pipeline']]
    
    if not plots_to_process:
        st.warning("No plots with pipelines to process!")
        return
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with st.spinner(f"Processing {len(plots_to_process)} plots in parallel..."):
        def process_plot(plot):
            try:
                shapers_config = [s['config'] for s in plot['pipeline'] if s['config']]
                processed_data = apply_shapers(st.session_state.data.copy(), shapers_config)
                plot['processed_data'] = processed_data
                return plot['name'], len(processed_data), None
            except Exception as e:
                return plot['name'], 0, str(e)
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(process_plot, plot): plot for plot in plots_to_process}
            results = []
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Show results
        success_count = sum(1 for _, _, error in results if error is None)
        st.success(f"Processed {success_count}/{len(results)} plots successfully!")
        
        for name, rows, error in results:
            if error:
                st.error(f"{name}: {error}")
            else:
                st.info(f"{name}: {rows} rows ready")
