"""
RING-5 Data Source Page
Page for selecting and configuring data sources.
"""

import streamlit as st

from src.web.facade import BackendFacade
from src.web.state_manager import StateManager
from src.web.styles import AppStyles
from src.web.ui.components.data_source_components import DataSourceComponents


class DataSourcePage:
    """Handles the data source selection and parser configuration."""

    def __init__(self, facade: BackendFacade):
        """Initialize the data source page."""
        self.facade = facade

    def render(self) -> None:
        """Render the data source page."""
        st.markdown(AppStyles.step_header("Step 1: Choose Data Source"), unsafe_allow_html=True)

        st.info(
            """
        **RING-5 supports two data input methods:**

        - **Parse gem5 Stats Files**: For raw gem5 output (stats.txt files)
        - **Upload CSV Directly**: If you already have parsed CSV data
        - **Load from Recent**: Quick access to previously parsed CSV files
        """
        )

        choice = st.radio(
            "Select your data source:",
            ["Parse gem5 Stats Files", "I already have CSV data", "Load from Recent"],
            key="data_source_choice",
        )

        if choice == "Parse gem5 Stats Files":
            StateManager.set_use_parser(True)
            DataSourceComponents.render_parser_config(self.facade)
        elif choice == "Load from Recent":
            DataSourceComponents.render_csv_pool(self.facade)
        else:
            StateManager.set_use_parser(False)
            st.success("CSV mode selected. Proceed to **Upload Data** to upload your CSV file.")
