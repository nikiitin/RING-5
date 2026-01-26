"""
RING-5 Upload Data Page
Page for uploading CSV data directly.
"""

import streamlit as st

from src.web.facade import BackendFacade
from src.web.state_manager import StateManager
from src.web.styles import AppStyles
from src.web.ui.components.upload_components import UploadComponents


class UploadDataPage:
    """Handles CSV data upload and preview."""

    def __init__(self, facade: BackendFacade):
        """Initialize the upload page."""
        self.facade = facade

    def render(self) -> None:
        """Render the upload data page."""
        # Check if parser mode and data already loaded
        if StateManager.is_using_parser():
            if StateManager.has_data():
                UploadComponents.render_parsed_data_preview()
                return
            else:
                st.warning("Please parse gem5 stats first in **Data Source** page!")
                return

        # CSV upload mode
        st.markdown(AppStyles.step_header("Step 2: Upload Your Data"), unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["Upload CSV File", "Paste Data"])

        with tab1:
            UploadComponents.render_file_upload_tab(self.facade)

        with tab2:
            UploadComponents.render_paste_data_tab()
