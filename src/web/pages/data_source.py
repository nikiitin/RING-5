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

        # Scanner UI
        col_scan1, col_scan2 = st.columns([1, 3])
        with col_scan1:
            if st.button("🔍 Scan for Variables", help="Scan files to auto-discover variables"):
                with st.spinner("Scanning stats files..."):
                    # Use facade to scan
                    scanned_vars = self.facade.scan_stats_variables_with_grouping(
                        stats_path, stats_pattern
                    )
                    StateManager.set_scanned_variables(scanned_vars)
                    st.rerun()

        # Display Scanned Variables Summary if any
        scanned_vars = StateManager.get_scanned_variables()
        if scanned_vars:
            st.success(f"Scanner found {len(scanned_vars)} variables. Use 'Add Variable' to select them.")

        # Variable editor
        variables = StateManager.get_parse_variables()
        updated_vars = UIComponents.variable_editor(variables)
        StateManager.set_parse_variables(updated_vars)

        # Add variable button
        if st.button("➕ Add Variable", help="Add a new variable manually or from scanned list"):
            self._variable_config_dialog()

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

    @st.dialog("Add Variable")
    def _variable_config_dialog(self):
        """Dialog to add a new variable."""
        scanned_vars = StateManager.get_scanned_variables() or []
        
        # 1. Method Selection
        method = st.radio("Addition Method", ["Search Scanned Variables", "Manual Entry"], horizontal=True, label_visibility="collapsed")
        
        name = ""
        var_type = "scalar"
        selected_scanned_var = None
        
        # 2. Input/Selection Logic
        if method == "Search Scanned Variables":
            if not scanned_vars:
                st.warning("No variables scanned yet. Run 'Scan for Variables' first.")
            else:
                # Format options for selectbox
                def format_func(v):
                    label = f"{v['name']} ({v['type']})"
                    if v['type'] == 'vector' and 'entries' in v:
                        label += f" [{len(v['entries'])} items]"
                    if 'count' in v and v['count'] > 1:
                        label += f" (Grouped {v['count']}x)"
                    return label
                
                # Use index to handle dict objects
                options = range(len(scanned_vars))
                
                st.markdown("##### Search Variable")
                idx = st.selectbox(
                    "Search by name...", 
                    options, 
                    format_func=lambda i: format_func(scanned_vars[i]),
                    key="dialog_select_var_idx",
                    placeholder="Type to search...",
                    index=None, # Allow empty initial state
                )
                
                if idx is not None:
                    selected_scanned_var = scanned_vars[idx]
                    name = selected_scanned_var["name"]
                    var_type = selected_scanned_var["type"]
        
        else: # Manual Entry
            st.markdown("##### Variable Details")
            manual_name = st.text_input("Variable Name", key="dialog_manual_name")
            if manual_name:
                name = manual_name
            
            # Type selection
            type_options = ["scalar", "vector", "distribution", "configuration"]
            var_type = st.selectbox("Type", type_options, key="dialog_manual_type")

        # 3. Dynamic Configuration Form
        # Only show if we have a name (or are in manual mode and can type one)
        
        if method == "Search Scanned Variables" and idx is None:
            st.info("Start typing in the search box above to find a variable.")
        else:
            st.markdown("---")
            st.markdown(f"**Configuration: {var_type.upper()}**")
            
            # Allow editing name even if selected from list? Usually yes, but keep it simple.
            if method == "Search Scanned Variables":
                name = st.text_input("Name", value=name, key="dialog_final_name")

            config = {}
            
            if var_type == "vector":
                st.markdown("###### Vector Configuration")
                st.caption("Select sub-items to extract:")
                
                # Container for selections
                selected_entries = []
                
                # A. Standard Stats
                standard_stats = ["total", "mean", "stdev", "samples", "gmean"]
                sel_stats = st.multiselect(
                    "Standard Statistics", 
                    standard_stats, 
                    default=["total", "mean"],
                    key="vec_stats"
                )
                selected_entries.extend(sel_stats)
                
                # B. Scanned Entries (if available)
                if selected_scanned_var and "entries" in selected_scanned_var:
                    found_entries = selected_scanned_var["entries"]
                    if found_entries:
                        sel_found = st.multiselect(
                            "Available Fields (from scan)", 
                            found_entries,
                            key="vec_found"
                        )
                        selected_entries.extend(sel_found)
                
                # C. Custom Entries
                custom_text = st.text_input(
                    "Custom Entries (comma separated)", 
                    placeholder="e.g. cpu0, cpu1",
                    key="vec_custom"
                )
                if custom_text:
                    custom_items = [x.strip() for x in custom_text.split(",") if x.strip()]
                    selected_entries.extend(custom_items)
                
                # Combine unique entries
                final_entries = list(dict.fromkeys(selected_entries)) # Remove dups keying order
                
                if final_entries:
                    st.success(f"Selected Entries: {', '.join(final_entries)}")
                    config["vectorEntries"] = ", ".join(final_entries)
                else:
                    st.warning("Please select at least one entry.")

                
            elif var_type == "distribution":
                col_min, col_max = st.columns(2)
                with col_min:
                    d_min = st.number_input("Minimum", value=-10, key="dist_min")
                with col_max:
                    d_max = st.number_input("Maximum", value=100, key="dist_max")
                config["minimum"] = d_min
                config["maximum"] = d_max
                
            elif var_type == "configuration":
                on_empty = st.text_input("On Empty Value", value="None", key="conf_empty")
                config["onEmpty"] = on_empty
                
            # Optional Repeat stuff (Advanced)
            with st.expander("Advanced Options"):
                 repeat = st.number_input("Repeat Count", min_value=1, value=1, help="If variable repeats in strict sequence (Perl parser specific)", key="adv_repeat")
                 if repeat > 1:
                    config["repeat"] = repeat

            st.write("") # Spacer
            if st.button("Add to Configuration", type="primary", use_container_width=True):
                if not name:
                    st.error("Variable name is required.")
                elif var_type == "vector" and not config.get("vectorEntries"):
                    st.error("Vector variables require at least one entry.")
                else:
                    # Construct Entry
                    import uuid
                    new_var = {
                        "name": name,
                        "type": var_type,
                        "id": None, # Parser ID - backend generated usually, but we use name as ID for parser config
                        "_id": str(uuid.uuid4()), # UI ID
                        **config
                    }
                    
                    # Update Session State
                    current_vars = StateManager.get_parse_variables()
                    # Check duplicate
                    if any(v["name"] == name for v in current_vars):
                        st.warning(f"Variable '{name}' already exists.")
                    else:
                        current_vars.append(new_var)
                        StateManager.set_parse_variables(current_vars)
                        st.success(f"Added '{name}'!")
                        st.rerun()

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
        current_temp = StateManager.get_temp_dir()
        if not current_temp or not Path(current_temp).exists():
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
