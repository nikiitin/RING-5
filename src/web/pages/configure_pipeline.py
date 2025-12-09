"""
RING-5 Configure Pipeline Page
Dynamic, reorderable pipeline configuration with live previews.
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional

from ..state_manager import StateManager
from ..facade import BackendFacade
from ..components import UIComponents
from ..styles import AppStyles


class ConfigurePipelinePage:
    """Handles dynamic pipeline configuration with previews."""
    
    def __init__(self, facade: BackendFacade):
        """Initialize the configure page."""
        self.facade = facade
    
    def render(self):
        """Render the pipeline configuration page."""
        if not StateManager.has_data():
            st.warning("Please upload data first!")
            return
        
        st.markdown(AppStyles.step_header("Step 3: Configure Processing Pipeline"), 
                   unsafe_allow_html=True)
        
        st.info("""
        **Build your data processing pipeline:**
        
        - Add multiple shapers in any order
        - Reorder steps with ↑/↓ buttons
        - Preview transformations at each step
        - Supported shapers: Column Selector, Normalizer, Mean Calculator, Sort
        """)
        
        # Initialize pipeline in session state
        if 'pipeline' not in st.session_state:
            st.session_state.pipeline = []
        
        # Show current pipeline
        self._show_pipeline_editor()
        
        # Add new shaper
        st.markdown("---")
        self._show_add_shaper_section()
        
        # Apply pipeline
        st.markdown("---")
        self._show_apply_section()
    
    def _show_pipeline_editor(self):
        """Display the pipeline editor with reordering capabilities."""
        st.markdown("### Current Pipeline")
        
        pipeline = st.session_state.pipeline
        
        if not pipeline:
            st.info("No shapers in pipeline yet. Add one below.")
            return
        
        # Display each shaper with controls
        for idx, shaper in enumerate(pipeline):
            with st.expander(f"Step {idx + 1}: {self._get_shaper_display_name(shaper)}", 
                           expanded=True):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.json(shaper)
                
                with col2:
                    if idx > 0:
                        if st.button("↑", key=f"up_{idx}"):
                            pipeline[idx], pipeline[idx-1] = pipeline[idx-1], pipeline[idx]
                            st.rerun()
                
                with col3:
                    if idx < len(pipeline) - 1:
                        if st.button("↓", key=f"down_{idx}"):
                            pipeline[idx], pipeline[idx+1] = pipeline[idx+1], pipeline[idx]
                            st.rerun()
                
                with col4:
                    if st.button("🗑", key=f"delete_{idx}"):
                        pipeline.pop(idx)
                        st.rerun()
                
                # Show preview of this step
                if st.checkbox(f"Preview after step {idx + 1}", key=f"preview_{idx}"):
                    self._show_step_preview(idx)
    
    def _show_step_preview(self, step_index: int):
        """Show preview after applying shapers up to this step."""
        st.markdown("#### Transformation Preview")
        
        try:
            # Apply all shapers up to and including this step
            data = StateManager.get_data()
            shapers_to_apply = st.session_state.pipeline[:step_index + 1]
            
            result = self.facade.apply_shapers(data.copy(), shapers_to_apply)
            
            st.markdown(f"**Result after {step_index + 1} step(s):**")
            st.dataframe(result.head(10), width='stretch')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", len(result))
            with col2:
                st.metric("Columns", len(result.columns))
            with col3:
                st.metric("Original Rows", len(data))
            
        except Exception as e:
            st.error(f"Error previewing transformation: {e}")
    
    def _show_add_shaper_section(self):
        """Show section to add new shapers."""
        st.markdown("### Add Shaper")
        
        shaper_type = st.selectbox(
            "Select shaper type",
            ["Column Selector", "Normalizer", "Mean Calculator", "Sort"],
            key="new_shaper_type"
        )
        
        if shaper_type == "Column Selector":
            self._add_column_selector()
        elif shaper_type == "Normalizer":
            self._add_normalizer()
        elif shaper_type == "Mean Calculator":
            self._add_mean_calculator()
        elif shaper_type == "Sort":
            self._add_sort()
    
    def _add_column_selector(self):
        """Add column selector configuration."""
        st.markdown("#### Column Selector Configuration")
        
        data = StateManager.get_data()
        selected_columns = st.multiselect(
            "Select columns to keep",
            options=data.columns.tolist(),
            key="col_selector_cols"
        )
        
        if st.button("Add Column Selector", key="add_col_selector"):
            if selected_columns:
                shaper = {
                    'type': 'columnSelector',
                    'columns': selected_columns
                }
                st.session_state.pipeline.append(shaper)
                st.success("Column Selector added to pipeline!")
                st.rerun()
            else:
                st.warning("Please select at least one column")
    
    def _add_normalizer(self):
        """Add normalizer configuration."""
        st.markdown("#### Normalizer Configuration")
        
        data = StateManager.get_data()
        numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        
        col1, col2 = st.columns(2)
        
        with col1:
            normalize_vars = st.multiselect(
                "Variables to normalize",
                options=numeric_cols,
                key="norm_vars"
            )
            
            normalizer_column = st.selectbox(
                "Normalizer column",
                options=categorical_cols,
                key="norm_col"
            )
        
        with col2:
            if normalizer_column:
                normalizer_value = st.selectbox(
                    "Baseline value",
                    options=data[normalizer_column].unique().tolist(),
                    key="norm_val"
                )
                
                group_by = st.multiselect(
                    "Group by",
                    options=categorical_cols,
                    key="norm_group"
                )
        
        if st.button("Add Normalizer", key="add_normalizer"):
            if normalize_vars and normalizer_column and normalizer_value and group_by:
                shaper = {
                    'type': 'normalize',
                    'normalizeVars': normalize_vars,
                    'normalizerColumn': normalizer_column,
                    'normalizerValue': normalizer_value,
                    'groupBy': group_by
                }
                st.session_state.pipeline.append(shaper)
                st.success("Normalizer added to pipeline!")
                st.rerun()
            else:
                st.warning("Please fill all fields")
    
    def _add_mean_calculator(self):
        """Add mean calculator configuration."""
        st.markdown("#### Mean Calculator Configuration")
        
        data = StateManager.get_data()
        numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            mean_algorithm = st.selectbox(
                "Mean type",
                options=['arithmean', 'geomean', 'harmean'],
                key="mean_algo"
            )
        
        with col2:
            mean_vars = st.multiselect(
                "Variables",
                options=numeric_cols,
                key="mean_vars"
            )
        
        with col3:
            grouping_column = st.selectbox(
                "Group by",
                options=categorical_cols,
                key="mean_group"
            )
        
        replacing_column = st.selectbox(
            "Replacing column",
            options=categorical_cols,
            key="mean_replace"
        )
        
        if st.button("Add Mean Calculator", key="add_mean"):
            if mean_vars and grouping_column and replacing_column:
                shaper = {
                    'type': 'mean',
                    'meanAlgorithm': mean_algorithm,
                    'meanVars': mean_vars,
                    'groupingColumn': grouping_column,
                    'replacingColumn': replacing_column
                }
                st.session_state.pipeline.append(shaper)
                st.success("Mean Calculator added to pipeline!")
                st.rerun()
            else:
                st.warning("Please fill all fields")
    
    def _add_sort(self):
        """Add sort configuration."""
        st.markdown("#### Sort Configuration")
        
        data = StateManager.get_data()
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        
        sort_column = st.selectbox(
            "Column to sort",
            options=categorical_cols,
            key="sort_col"
        )
        
        if sort_column:
            unique_values = data[sort_column].unique().tolist()
            
            sort_order = st.text_area(
                "Custom order (one value per line)",
                value='\n'.join(unique_values),
                height=150,
                key="sort_order"
            )
            
            if st.button("Add Sort", key="add_sort"):
                order_list = [line.strip() for line in sort_order.split('\n') if line.strip()]
                if order_list:
                    shaper = {
                        'type': 'sort',
                        'order_dict': {sort_column: order_list}
                    }
                    st.session_state.pipeline.append(shaper)
                    st.success("Sort added to pipeline!")
                    st.rerun()
                else:
                    st.warning("Please provide sort order")
    
    def _show_apply_section(self):
        """Show apply and save buttons."""
        st.markdown("### Apply Pipeline")
        
        # Show complete pipeline preview
        if st.session_state.pipeline:
            with st.expander("View Complete Pipeline Configuration"):
                st.json({'shapers': st.session_state.pipeline})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Apply Pipeline", type="primary", width='stretch'):
                self._apply_pipeline()
        
        with col2:
            if st.button("Save Pipeline Configuration", width='stretch'):
                self._save_pipeline()
        
        with col3:
            if st.button("Clear Pipeline", width='stretch'):
                st.session_state.pipeline = []
                st.success("Pipeline cleared!")
                st.rerun()
    
    def _apply_pipeline(self):
        """Apply the complete pipeline."""
        if not st.session_state.pipeline:
            st.warning("Pipeline is empty!")
            return
        
        try:
            data = StateManager.get_data()
            processed_data = self.facade.apply_shapers(data.copy(), st.session_state.pipeline)
            StateManager.set_processed_data(processed_data)
            StateManager.update_config('shapers', st.session_state.pipeline)
            
            st.success("Pipeline applied successfully!")
            
            st.markdown("### Final Result")
            UIComponents.show_data_preview(processed_data, "Processed Data")
            
            st.info("Proceed to **Results** to download or **Generate Plots** to visualize!")
            
        except Exception as e:
            st.error(f"Error applying pipeline: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    def _save_pipeline(self):
        """Save the current pipeline configuration."""
        if not st.session_state.pipeline:
            st.warning("Pipeline is empty!")
            return
        
        st.markdown("---")
        st.markdown("### Save Pipeline Configuration")
        
        config_name = st.text_input("Configuration name", value="my_pipeline", key="save_name")
        config_description = st.text_area("Description", 
                                         value="My custom pipeline", 
                                         key="save_desc")
        
        if st.button("Save Now", key="save_now"):
            try:
                config_path = self.facade.save_configuration(
                    name=config_name,
                    description=config_description,
                    shapers_config=st.session_state.pipeline,
                    csv_path=StateManager.get_csv_path()
                )
                
                # Reload configs
                StateManager.set_saved_configs(self.facade.load_saved_configs())
                
                st.success(f"Pipeline configuration saved successfully!")
            except Exception as e:
                st.error(f"Error saving configuration: {e}")
    
    def _get_shaper_display_name(self, shaper: Dict[str, Any]) -> str:
        """Get a friendly display name for a shaper."""
        shaper_type = shaper.get('type', 'unknown')
        
        if shaper_type == 'columnSelector':
            cols = shaper.get('columns', [])
            return f"Column Selector ({len(cols)} columns)"
        elif shaper_type == 'normalize':
            return f"Normalizer ({shaper.get('normalizerColumn', 'unknown')})"
        elif shaper_type == 'mean':
            return f"Mean Calculator ({shaper.get('meanAlgorithm', 'unknown')})"
        elif shaper_type == 'sort':
            return "Sort"
        else:
            return shaper_type
