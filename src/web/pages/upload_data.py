"""
RING-5 Upload Data Page
Page for uploading CSV data directly.
"""

import tempfile
from io import StringIO
from pathlib import Path

import streamlit as st

from ..components import UIComponents
from ..facade import BackendFacade
from ..state_manager import StateManager
from ..styles import AppStyles


class UploadDataPage:
    """Handles CSV data upload and preview."""

    def __init__(self, facade: BackendFacade):
        """Initialize the upload page."""
        self.facade = facade

    def render(self):
        """Render the upload data page."""
        # Check if parser mode and data already loaded
        if StateManager.is_using_parser():
            if StateManager.has_data():
                st.markdown(
                    AppStyles.step_header("Step 2: Parsed Data Preview"), unsafe_allow_html=True
                )
                st.success("Data loaded from parser!")

                data = StateManager.get_data()
                UIComponents.show_data_preview(data)
                UIComponents.show_column_details(data)

                st.info("Proceed to **Configure Pipeline** to process your data")
                return
            else:
                st.warning("Please parse gem5 stats first in **Data Source** page!")
                return

        # CSV upload mode
        st.markdown(AppStyles.step_header("Step 2: Upload Your Data"), unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["Upload CSV File", "Paste Data"])

        with tab1:
            self._show_file_upload()

        with tab2:
            self._show_paste_data()

    def _show_file_upload(self):
        """Show file upload interface."""
        st.markdown("### Upload gem5 Statistics CSV")
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv", "txt"],
            help="Upload your gem5 statistics file (CSV format)",
        )

        if uploaded_file:
            try:
                # Create temp directory
                if not StateManager.get_temp_dir():
                    StateManager.set_temp_dir(tempfile.mkdtemp())

                # Save file
                csv_path = Path(StateManager.get_temp_dir()) / uploaded_file.name
                with open(csv_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Load data
                data = self.facade.load_csv_file(str(csv_path))
                StateManager.set_data(data)
                StateManager.set_csv_path(str(csv_path))

                st.success(f"Successfully loaded {len(data)} rows × {len(data.columns)} columns!")

                UIComponents.show_data_preview(data)
                UIComponents.show_column_details(data)

            except Exception as e:
                st.error(f"Error loading file: {e}")

    def _show_paste_data(self):
        """Show paste data interface."""
        st.markdown("### Paste CSV Data")
        csv_text = st.text_area(
            "Paste your CSV data here",
            height=200,
            help="Paste CSV data (comma or whitespace separated)",
        )

        if csv_text and st.button("Load Data"):
            try:
                import pandas as pd

                try:
                    data = pd.read_csv(StringIO(csv_text))
                except Exception:
                    data = pd.read_csv(StringIO(csv_text), sep=r"\s+")

                StateManager.set_data(data)
                st.success(f"Successfully loaded {len(data)} rows × {len(data.columns)} columns!")
                st.dataframe(data.head(10), width="stretch")

            except Exception as e:
                st.error(f"Error parsing data: {e}")
