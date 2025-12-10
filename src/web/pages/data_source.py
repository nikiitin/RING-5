"""
RING-5 Data Source Page
Page for selecting and configuring data sources.
"""

import tempfile
from pathlib import Path

import streamlit as st

from ..components import UIComponents
from ..facade import BackendFacade
from ..state_manager import StateManager
from ..styles import AppStyles


class DataSourcePage:
    """Handles the data source selection and parser configuration."""

    def __init__(self, facade: BackendFacade):
        """
        Initialize the data source page.

        Args:
            facade: Backend facade instance
        """
        self.facade = facade

    def render(self):
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
            self._show_parser_configuration()
        elif choice == "Load from Recent":
            self._show_csv_pool()
        else:
            StateManager.set_use_parser(False)
            st.success("CSV mode selected. Proceed to **Upload Data** to upload your CSV file.")

    def _show_csv_pool(self):
        """Display and manage the CSV pool."""
        st.markdown("---")
        st.markdown("### Recent CSV Files")

        # Reload pool
        csv_pool = self.facade.load_csv_pool()
        StateManager.set_csv_pool(csv_pool)

        if not csv_pool:
            st.warning("No CSV files in the pool yet. Parse some gem5 stats to populate this list.")
            return

        st.info(f"Found {len(csv_pool)} CSV file(s) in the pool")

        for idx, csv_info in enumerate(csv_pool):
            csv_path = Path(csv_info["path"])

            if not csv_path.exists():
                st.error(f"File no longer exists: {csv_info['name']}")
                continue

            load_clicked, preview_clicked, delete_clicked = UIComponents.file_info_card(
                csv_info, idx
            )

            if load_clicked:
                try:
                    data = self.facade.load_csv_file(str(csv_path))
                    StateManager.set_data(data)
                    StateManager.set_csv_path(str(csv_path))
                    StateManager.set_use_parser(False)
                    st.success(f"Loaded {len(data)} rows!")

                    # Show data preview
                    UIComponents.show_data_preview(data, "Loaded CSV Preview")
                    UIComponents.show_column_details(data)
                    st.info("Data loaded! Proceed to **Configure Pipeline** to process it.")
                except Exception as e:
                    st.error(f"Error loading file: {e}")

            if preview_clicked:
                try:
                    preview_data = self.facade.load_csv_file(str(csv_path))
                    st.dataframe(preview_data.head(5))
                except Exception as e:
                    st.error(f"Error previewing file: {e}")

            if delete_clicked:
                if self.facade.delete_from_csv_pool(str(csv_path)):
                    st.success("File deleted!")
                    st.rerun()
                else:
                    st.error("Error deleting file")

    def _show_parser_configuration(self):
        """Display parser configuration interface."""
        st.markdown("---")
        st.markdown("### gem5 Stats Parser Configuration")

        st.markdown("#### File Location")

        col1, col2 = st.columns(2)

        with col1:
            stats_path = st.text_input(
                "Stats directory path",
                value="/path/to/gem5/stats",
                help="Directory containing gem5 stats files (can include subdirectories)",
            )

        with col2:
            stats_pattern = st.text_input(
                "File pattern",
                value="stats.txt",
                help="Filename pattern to search for (e.g., stats.txt, *.txt)",
            )

        # Compression option
        st.markdown("#### Remote Filesystem Optimization")

        compress_data = st.checkbox(
            "Enable compression (for remote/SSHFS filesystems)",
            value=False,
            help="Compress and copy stats files locally for faster processing.",
        )

        if compress_data:
            st.info(
                """
            **Compression Mode Enabled:**

            Stats files will be copied and compressed locally for faster processing.
            """
            )

        # Variables configuration
        st.markdown("#### Variables to Extract")

        st.markdown(
            """
        Define which variables to extract from gem5 stats files:
        - **Scalar**: Single numeric values (e.g., simTicks, IPC)
        - **Vector**: Arrays of values with specified entries (e.g., cache miss breakdown by CPU)
          - Specify entry names like: `cpu0, cpu1, cpu2`
          - Or use statistics: `total, mean, samples, stdev, gmean`
        - **Distribution**: Statistical distributions with min/max range
        - **Configuration**: Metadata (benchmark name, config ID, seed)

        **Note:** For vector statistics (total, mean, etc.), use the special members feature in the
        vector configuration.
        """
        )

        # Variable editor
        variables = StateManager.get_parse_variables()
        updated_vars = UIComponents.variable_editor(variables)
        StateManager.set_parse_variables(updated_vars)

        # Add variable button
        if UIComponents.add_variable_button():
            variables.append({"name": "new_variable", "type": "scalar"})
            StateManager.set_parse_variables(variables)
            st.rerun()

        # Preview configuration
        st.markdown("#### Configuration Preview")

        parse_config = {
            "parser": "gem5_stats",
            "statsPath": stats_path,
            "statsPattern": stats_pattern,
            "compress": compress_data,
            "variables": StateManager.get_parse_variables(),
        }

        st.json(parse_config)

        # Parse button
        st.markdown("---")

        if st.button("Parse gem5 Stats Files", type="primary", width="stretch"):
            self._run_parser(stats_path, stats_pattern, compress_data)

    def _run_parser(self, stats_path: str, stats_pattern: str, compress: bool):
        """
        Run the parser with progress tracking.

        Args:
            stats_path: Base directory with stats files
            stats_pattern: File pattern to match
            compress: Enable compression
        """
        # Validate inputs
        if not stats_path or stats_path == "/path/to/gem5/stats":
            st.error("Please specify a valid stats directory path!")
            return

        if not Path(stats_path).exists():
            st.error(f"Directory not found: {stats_path}")
            return

        # Find files
        files_found = self.facade.find_stats_files(stats_path, stats_pattern)

        if len(files_found) == 0:
            st.warning("No files found matching pattern")
            return

        st.info(f"Found {len(files_found)} files to parse")

        # Create temp directory
        if not StateManager.get_temp_dir():
            StateManager.set_temp_dir(tempfile.mkdtemp())

        output_dir = StateManager.get_temp_dir()
        if output_dir is None:
            st.error("Failed to create temporary directory")
            return

        # Create progress containers
        progress_container = st.container()

        with progress_container:
            st.markdown("### Processing Progress")
            overall_progress = st.progress(0)
            status_text = st.empty()
            file_details = st.empty()

            # Progress callback
            def update_progress(step, progress, message):
                overall_progress.progress(progress)
                status_text.text(message)
                if step == 3:
                    file_details.text(f"Processing {len(files_found)} files...")

            try:
                csv_path = self.facade.parse_gem5_stats(
                    stats_path=stats_path,
                    stats_pattern=stats_pattern,
                    compress=compress,
                    variables=StateManager.get_parse_variables(),
                    output_dir=output_dir,
                    progress_callback=update_progress,
                )

                if csv_path and Path(csv_path).exists():
                    # Add to pool
                    self.facade.add_to_csv_pool(csv_path)

                    # Load data
                    data = self.facade.load_csv_file(csv_path)
                    StateManager.set_data(data)
                    StateManager.set_csv_path(csv_path)

                    st.success(f"Successfully parsed {len(data)} rows! CSV saved to pool.")
                    UIComponents.show_data_preview(data, "Parsed Data Preview")
                    st.info("Data ready! Proceed to **Configure Pipeline**")
                else:
                    st.error("Parser did not generate CSV file")

            except Exception as e:
                st.error(f"Error during parsing: {e}")
                import traceback

                st.code(traceback.format_exc())
