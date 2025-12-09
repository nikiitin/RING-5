"""
RING-5 Reusable UI Components
Common UI elements used across the application.
"""
import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any
import datetime


class UIComponents:
    """Collection of reusable UI components."""
    
    @staticmethod
    def show_data_preview(data: pd.DataFrame, title: str = "Data Preview", rows: int = 20):
        """
        Display a data preview with statistics.
        
        Args:
            data: DataFrame to preview
            title: Title for the preview section
            rows: Number of rows to show
        """
        st.markdown(f"### {title}")
        st.dataframe(data.head(rows), width='stretch')
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Rows", len(data))
        with col2:
            st.metric("Columns", len(data.columns))
        with col3:
            numeric_cols = data.select_dtypes(include=['number']).columns
            st.metric("Numeric Columns", len(numeric_cols))
        with col4:
            categorical_cols = data.select_dtypes(include=['object']).columns
            st.metric("Categorical Columns", len(categorical_cols))
    
    @staticmethod
    def show_column_details(data: pd.DataFrame):
        """
        Display detailed column information in an expander.
        
        Args:
            data: DataFrame to analyze
        """
        with st.expander("Column Details"):
            col_info = pd.DataFrame({
                'Column': data.columns,
                'Type': data.dtypes.astype(str),
                'Non-Null': data.count(),
                'Null': data.isnull().sum(),
                'Unique': [data[col].nunique() for col in data.columns]
            })
            st.dataframe(col_info, width='stretch')
    
    @staticmethod
    def file_info_card(file_info: Dict[str, Any], index: int):
        """
        Display a file information card with actions.
        
        Args:
            file_info: Dictionary with file information
            index: Unique index for the card
            
        Returns:
            Tuple of (load_clicked, preview_clicked, delete_clicked)
        """
        modified_time = datetime.datetime.fromtimestamp(file_info['modified'])
        
        with st.expander(f"{file_info['name']} ({file_info['size'] / 1024:.1f} KB)", 
                        expanded=(index == 0)):
            st.text(f"Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                load_clicked = st.button("Load This File", key=f"load_{index}")
            
            with col2:
                preview_clicked = st.button("Preview", key=f"preview_{index}")
            
            with col3:
                delete_clicked = st.button("Delete", key=f"delete_{index}")
            
            return load_clicked, preview_clicked, delete_clicked
    
    @staticmethod
    def config_info_card(config_info: Dict[str, Any], index: int):
        """
        Display a configuration information card with actions.
        
        Args:
            config_info: Dictionary with config information
            index: Unique index for the card
            
        Returns:
            Tuple of (load_clicked, delete_clicked)
        """
        modified_time = datetime.datetime.fromtimestamp(config_info['modified'])
        
        with st.expander(f"{config_info['name']}", expanded=(index == 0)):
            st.text(f"Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.text(f"Description: {config_info['description']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                load_clicked = st.button("Load This Configuration", key=f"load_cfg_{index}")
            
            with col2:
                delete_clicked = st.button("Delete", key=f"delete_cfg_{index}")
            
            return load_clicked, delete_clicked
    
    @staticmethod
    def progress_display(step: int, total_steps: int, message: str):
        """
        Display a progress indicator.
        
        Args:
            step: Current step number
            total_steps: Total number of steps
            message: Status message
        """
        progress = step / total_steps
        st.progress(progress)
        st.text(message)
    
    @staticmethod
    def variable_editor(variables: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Display an editor for parser variables.
        
        Args:
            variables: List of variable configurations
            
        Returns:
            Updated list of variables
        """
        st.markdown("**Current Variables:**")
        
        updated_vars = []
        deleted_indices = []
        
        for idx, var in enumerate(variables):
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                var_name = st.text_input(
                    f"Variable {idx+1} Name",
                    value=var.get("name", ""),
                    key=f"var_name_{idx}",
                    label_visibility="collapsed"
                )
            
            with col2:
                var_type = st.selectbox(
                    f"Type {idx+1}",
                    options=["scalar", "vector", "distribution", "configuration"],
                    index=["scalar", "vector", "distribution", "configuration"].index(
                        var.get("type", "scalar")),
                    key=f"var_type_{idx}",
                    label_visibility="collapsed"
                )
            
            with col3:
                if st.button("X", key=f"delete_var_{idx}"):
                    deleted_indices.append(idx)
            
            if idx not in deleted_indices:
                updated_vars.append({"name": var_name, "type": var_type})
        
        return updated_vars
    
    @staticmethod
    def add_variable_button() -> bool:
        """
        Display an add variable button.
        
        Returns:
            True if button was clicked
        """
        col1, col2 = st.columns([1, 4])
        with col1:
            return st.button("+ Add Variable", width='stretch')
        return False
    
    @staticmethod
    def sidebar_info():
        """Display sidebar information about RING-5."""
        st.markdown("### About RING-5")
        st.info("""
        **Pure Python** implementation for gem5 data analysis.
        
        - Parse gem5 stats OR upload CSV  
        - No R dependencies  
        - Interactive configuration  
        - Real-time visualization  
        - Professional plots
        """)
    
    @staticmethod
    def navigation_menu() -> str:
        """
        Display navigation menu and return selected page.
        
        Returns:
            Selected page name
        """
        return st.radio(
            "Navigation",
            [
                "Data Source",
                "Upload Data",
                "Data Managers",
                "Configure Pipeline",
                "Generate Plots",
                "Results",
                "Load Configuration"
            ],
            label_visibility="collapsed"
        )
    
    @staticmethod
    def clear_data_button() -> bool:
        """
        Display clear data button.
        
        Returns:
            True if button was clicked
        """
        return st.button("Clear All Data", width='stretch')
    
    @staticmethod
    def download_buttons(data: pd.DataFrame, prefix: str = "processed_data"):
        """
        Display download buttons for different formats.
        
        Args:
            data: DataFrame to download
            prefix: Filename prefix
        """
        import tempfile
        
        st.markdown("### Download Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv_data = data.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"{prefix}.csv",
                mime="text/csv",
                width='stretch'
            )
        
        with col2:
            json_data = data.to_json(orient='records', indent=2).encode('utf-8')
            st.download_button(
                label="Download JSON",
                data=json_data,
                file_name=f"{prefix}.json",
                mime="application/json",
                width='stretch'
            )
        
        with col3:
            excel_buffer = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            data.to_excel(excel_buffer.name, index=False, engine='openpyxl')
            with open(excel_buffer.name, 'rb') as f:
                excel_data = f.read()
            
            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name=f"{prefix}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch'
            )
