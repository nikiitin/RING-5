"""
RING-5 Data Source Page
Page for selecting and configuring data sources.
"""

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.components.data_source.data_source_components import DataSourceComponents


class DataSourcePage:
    """Handles the data source selection and parser configuration."""

    def __init__(self, api: ApplicationAPI):
        """Initialize the data source page."""
        self.api = api

    def render(self) -> None:
        """Render the data source page."""
        # [impl->req~ring5.ingestion.source-modes~1]
        st.markdown("## Step 1: Choose Data Source")

        # Determine selected simulator for dynamic labels
        simulators = ApplicationAPI.available_simulators()
        selected_sim = self.api.state_manager.get_simulator()
        if selected_sim not in simulators:
            selected_sim = simulators[0] if simulators else "gem5"
        sim_info = ApplicationAPI.get_simulator_info(selected_sim)
        sim_label = sim_info.display_name

        parse_label = f"Parse {sim_label} Stats Files"

        st.info(f"""
        **RING-5 supports three data input methods:**

        - **{parse_label}**: For raw simulator output ({sim_info.file_pattern} files)
        - **Upload Data or Portfolio**: Review CSV, JSON, Excel, or a RING-5 portfolio
        - **Load from Recent**: Quick access to previously parsed CSV files
        """)

        data_source_options = [
            parse_label,
            "Upload data or portfolio",
            "Load from Recent",
        ]
        choice = st.segmented_control(
            "Select your data source:",
            data_source_options,
            default=data_source_options[0],
            key="data_source_choice",
        )

        if choice == parse_label:
            if not self.api.state_manager.is_using_parser():
                self.api.state_manager.set_use_parser(True)
            DataSourceComponents.render_parser_config(self.api)
        elif choice == "Load from Recent":
            DataSourceComponents.render_csv_pool(self.api)
        else:
            if self.api.state_manager.is_using_parser():
                self.api.state_manager.set_use_parser(False)
            st.success(
                "Upload mode selected — validation and review happen before workspace changes."
            )
            DataSourceComponents.render_browser_upload(self.api)
