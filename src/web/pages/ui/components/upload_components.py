"""
Upload Components - UI for File and Data Upload.

Provides Streamlit components for uploading and ingesting data: CSV file upload,
paste data, and CSV preview functionality.
"""

import tempfile
from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.pages.ui.components.data_components import DataComponents


class UploadComponents:
    """UI Components for the Upload Data Page."""

    @staticmethod
    def render_parsed_data_preview(api: ApplicationAPI) -> None:
        """Render preview if data is already parsed/loaded."""
        st.markdown("## Step 2: Parsed Data Preview")

        st.success("Data loaded from parser!")

        data = api.state_manager.get_data()
        if data is not None:
            DataComponents.show_data_preview(data)
            DataComponents.show_column_details(data)

        st.info("Proceed to **Configure Pipeline** to process your data")

    @staticmethod
    def render_file_upload_tab(api: ApplicationAPI) -> None:
        """Render the file upload interface."""
        st.markdown("### Upload gem5 Statistics CSV")
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv", "txt"],
            help="Upload your gem5 statistics file (CSV format)",
        )

        if uploaded_file:
            try:
                # Create temp directory
                if not api.state_manager.get_temp_dir():
                    api.state_manager.set_temp_dir(tempfile.mkdtemp())

                # Save file
                temp_dir = api.state_manager.get_temp_dir()
                if not temp_dir:
                    raise RuntimeError("Failed to create temporary directory")

                csv_path = Path(temp_dir) / uploaded_file.name
                with open(csv_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Load data using the public ApplicationAPI CSV-loading method.
                # ApplicationAPI exposes load_data(...), which stores the DataFrame
                # in the state manager; we then retrieve it from there.
                api.load_data(str(csv_path))
                data = api.state_manager.get_data()
                if data is None:
                    raise ValueError("Data failed to load from CSV via ApplicationAPI.")

                st.success(f"Successfully loaded {len(data)} rows × {len(data.columns)} columns!")

                DataComponents.show_data_preview(data)
                DataComponents.show_column_details(data)

            except Exception as e:
                st.error(f"Error loading file: {e}")

    @staticmethod
    def render_paste_data_tab(api: ApplicationAPI) -> None:
        """Render the paste data interface."""
        st.markdown("### Paste CSV Data")
        csv_text = st.text_area(
            "Paste your CSV data here",
            height=200,
            help="Paste CSV data (comma or whitespace separated)",
        )

        if csv_text and st.button("Load Data"):
            try:
                try:
                    data = pd.read_csv(StringIO(csv_text))
                except Exception:
                    data = pd.read_csv(StringIO(csv_text), sep=r"\s+")

                api.state_manager.set_data(data)
                st.success(f"Successfully loaded {len(data)} rows × {len(data.columns)} columns!")
                st.dataframe(data.head(10), width="stretch")

            except Exception as e:
                st.error(f"Error parsing data: {e}")
