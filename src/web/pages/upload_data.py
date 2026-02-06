"""
RING-5 Upload Data Page
Page for uploading CSV data directly.
"""

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.pages.ui.components.upload_components import UploadComponents


class UploadDataPage:
    """Handles CSV data upload and preview."""

    def __init__(self, api: ApplicationAPI):
        """Initialize the upload page."""
        self.api = api

    def render(self) -> None:
        """Render the upload data page."""
        # Check if parser mode and data already loaded
        if self.api.state_manager.is_using_parser():
            if self.api.state_manager.has_data():
                UploadComponents.render_parsed_data_preview(self.api)
                return
            else:
                st.warning("Please parse gem5 stats first in **Data Source** page!")
                return

        # CSV upload mode
        st.markdown("## Step 2: Upload Your Data")

        tab1, tab2 = st.tabs(["Upload CSV File", "Paste Data"])

        with tab1:
            UploadComponents.render_file_upload_tab(self.api)

        with tab2:
            UploadComponents.render_paste_data_tab(self.api)
