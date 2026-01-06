"""
RING-5 Reusable UI Components
Common UI elements used across the application.
"""

import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.web.facade import BackendFacade


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
        st.dataframe(data.head(rows), width="stretch")

        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Rows", len(data))
        with col2:
            st.metric("Columns", len(data.columns))
        with col3:
            numeric_cols = data.select_dtypes(include=["number"]).columns
            st.metric("Numeric Columns", len(numeric_cols))
        with col4:
            categorical_cols = data.select_dtypes(include=["object"]).columns
            st.metric("Categorical Columns", len(categorical_cols))

    @staticmethod
    def show_column_details(data: pd.DataFrame):
        """
        Display detailed column information in an expander.

        Args:
            data: DataFrame to analyze
        """
        with st.expander("Column Details"):
            col_info = pd.DataFrame(
                {
                    "Column": data.columns,
                    "Type": data.dtypes.astype(str),
                    "Non-Null": data.count(),
                    "Null": data.isnull().sum(),
                    "Unique": [data[col].nunique() for col in data.columns],
                }
            )
            st.dataframe(col_info, width="stretch")

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
        modified_time = datetime.datetime.fromtimestamp(file_info["modified"])

        with st.expander(
            f"{file_info['name']} ({file_info['size'] / 1024:.1f} KB)", expanded=(index == 0)
        ):
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
        modified_time = datetime.datetime.fromtimestamp(config_info["modified"])

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
    def variable_editor(
        variables: List[Dict[str, Any]],
        available_variables: Optional[List[Dict[str, Any]]] = None,
        stats_path: Optional[str] = None,
        stats_pattern: str = "stats.txt",
    ) -> List[Dict[str, Any]]:
        """
        Display an editor for parser variables.

        Args:
            variables: List of variable configurations
            available_variables: Optional list of discovered variables from stats files
            stats_path: Optional path to stats files (for deep scanning)
            stats_pattern: Optional pattern for stats files

        Returns:
            Updated list of variable configurations
        """
        st.markdown("**Current Variables:**")

        updated_vars = []
        deleted_indices = []

        updated_vars = []
        deleted_indices = []

        for idx, var in enumerate(variables):
            # Ensure ID exists (fallback if StateManager didn't catch it for some reason)
            var_id = var.get("_id", f"fallback_{idx}")
            
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

            with col1:
                var_name = st.text_input(
                    f"Variable {idx+1} Name",
                    value=var.get("name", ""),
                    key=f"var_name_{var_id}",
                    label_visibility="collapsed",
                    placeholder="stats.name"
                )
                
            with col2:
                var_alias = st.text_input(
                    f"Alias {idx+1}",
                    value=var.get("alias", ""),
                    key=f"var_alias_{var_id}",
                    label_visibility="collapsed",
                    placeholder="Alias (Optional)"
                )

            with col3:
                var_type = st.selectbox(
                    f"Type {idx+1}",
                    options=["scalar", "vector", "distribution", "configuration"],
                    index=["scalar", "vector", "distribution", "configuration"].index(
                        var.get("type", "scalar")
                    ),
                    key=f"var_type_{var_id}",
                    label_visibility="collapsed",
                )

            with col4:
                if st.button("X", key=f"delete_var_{var_id}"):
                    deleted_indices.append(idx)

            if idx not in deleted_indices:
                var_config = {"name": var_name, "type": var_type, "_id": var_id}
                if var_alias:
                    var_config["alias"] = var_alias

                # Type-specific configuration
                if var_type == "vector":
                    st.markdown(f"**Vector Configuration for `{var_name}`:**")
                    st.info(
                        "ℹ️ Vectors require entries to be specified. "
                        "You can manually search for entries, or use the **Deep Scan** feature below "
                        "to automatically find them in your stats files."
                    )

                    # Check if we have discovered entries for this variable
                    discovered_entries = []
                    if available_variables:
                        for v in available_variables:
                            if v["name"] == var_name and "entries" in v:
                                discovered_entries = v["entries"]
                                break

                    # Choice: manual entries or statistics
                    options = ["Manual Entry Names", "Vector Statistics"]
                    if discovered_entries:
                        options.insert(0, "Select from Discovered Entries")

                    # Add Deep Scan option if stats path is available
                    if stats_path and not discovered_entries:
                        # If no entries found yet (or incomplete), allow scanning
                        pass

                    entry_mode = st.radio(
                        "How to specify vector entries:",
                        options=options,
                        index=(
                            0
                            if not var.get("useSpecialMembers", False)
                            else (
                                options.index("Vector Statistics")
                                if "Vector Statistics" in options
                                else 1
                            )
                        ),
                        key=f"entry_mode_{var_id}",
                        horizontal=True,
                    )

                    # Deep Scan Button
                    if (
                        stats_path
                        and entry_mode == "Select from Discovered Entries"
                        or (
                            stats_path
                            and not discovered_entries
                            and entry_mode == "Manual Entry Names"
                        )
                    ):
                        if st.button(
                            f"Deep Scan Entries for '{var_name}'",
                            key=f"deep_scan_{var_id}",
                            help="Scan ALL stats files to find all possible entries "
                            "for this vector.",
                        ):
                            with st.spinner(f"Scanning all files for {var_name}..."):
                                facade = BackendFacade()
                                if stats_path is None:
                                    raise ValueError("stats_path cannot be None")
                                if var_name is None:
                                    raise ValueError("var_name cannot be None")
                                all_entries = facade.scan_vector_entries(
                                    stats_path, var_name, stats_pattern
                                )

                                if all_entries:
                                    # Update session state logic remains same...
                                    if (
                                        "available_variables" in st.session_state
                                        and st.session_state.available_variables
                                    ):
                                        for v in st.session_state.available_variables:
                                            if v["name"] == var_name:
                                                v["entries"] = all_entries
                                                break

                                    st.success(f"Found {len(all_entries)} entries!")
                                    st.rerun()
                                else:
                                    st.warning("No entries found.")

                    if entry_mode == "Select from Discovered Entries":
                        # Multiselect for discovered entries
                        current_entries = var.get("vectorEntries", [])
                        if isinstance(current_entries, str):
                            current_entries = [
                                e.strip() for e in current_entries.split(",") if e.strip()
                            ]

                        # Filter current entries to only those in discovered list to avoid errors
                        valid_defaults = [e for e in current_entries if e in discovered_entries]

                        selected_entries = st.multiselect(
                            "Select entries to extract:",
                            options=discovered_entries,
                            default=valid_defaults,
                            key=f"vector_entries_select_{var_id}",
                        )

                        if selected_entries:
                            var_config["vectorEntries"] = selected_entries
                            var_config["useSpecialMembers"] = False
                            st.success(f"✓ Will extract {len(selected_entries)} entries")
                        else:
                            st.warning("⚠️ Please select at least one entry")

                    elif entry_mode == "Manual Entry Names":
                        # Manual vector entries input
                        default_entries = var.get("vectorEntries", "")
                        if isinstance(default_entries, list):
                            default_entries = ", ".join(default_entries)

                        vector_entries_input = st.text_input(
                            "Vector entries (comma-separated)",
                            value=default_entries,
                            key=f"vector_entries_{var_id}",
                            placeholder="e.g., cpu0, cpu1, cpu2 or bank0, bank1, bank2",
                            help="Enter the exact names of vector entries as they appear in "
                            "stats.txt (e.g., 'cpu0', 'cpu1.data', 'bank0')",
                        )

                        if vector_entries_input.strip():
                            # Parse comma-separated entries
                            entries = [
                                e.strip() for e in vector_entries_input.split(",") if e.strip()
                            ]
                            var_config["vectorEntries"] = entries
                            var_config["useSpecialMembers"] = False
                            st.success(
                                f"✓ Will extract {len(entries)} entries: "
                                f"{', '.join(entries[:3])}{'...' if len(entries) > 3 else ''}"
                            )
                        else:
                            st.warning("⚠️ Please enter at least one vector entry name")

                    else:  # Vector Statistics mode
                        st.markdown("**Select statistics to extract from the vector:**")

                        col_stat1, col_stat2 = st.columns(2)

                        with col_stat1:
                            extract_total = st.checkbox(
                                "total (sum of all entries)",
                                value="total" in var.get("vectorEntries", []),
                                key=f"stat_total_{var_id}",
                            )
                            extract_mean = st.checkbox(
                                "mean (arithmetic mean)",
                                value="mean" in var.get("vectorEntries", []),
                                key=f"stat_mean_{var_id}",
                            )
                            extract_gmean = st.checkbox(
                                "gmean (geometric mean)",
                                value="gmean" in var.get("vectorEntries", []),
                                key=f"stat_gmean_{var_id}",
                            )

                        with col_stat2:
                            extract_samples = st.checkbox(
                                "samples (count)",
                                value="samples" in var.get("vectorEntries", []),
                                key=f"stat_samples_{var_id}",
                            )
                            extract_stdev = st.checkbox(
                                "stdev (standard deviation)",
                                value="stdev" in var.get("vectorEntries", []),
                                key=f"stat_stdev_{var_id}",
                            )

                        # Build list of selected statistics
                        special_members = []
                        if extract_total:
                            special_members.append("total")
                        if extract_mean:
                            special_members.append("mean")
                        if extract_gmean:
                            special_members.append("gmean")
                        if extract_samples:
                            special_members.append("samples")
                        if extract_stdev:
                            special_members.append("stdev")

                        if special_members:
                            var_config["vectorEntries"] = special_members
                            var_config["useSpecialMembers"] = True
                            st.success(f"✓ Will extract statistics: {', '.join(special_members)}")
                        else:
                            st.warning("⚠️ Please select at least one statistic to extract")

                elif var_type == "distribution":
                    st.markdown(f"**Distribution Configuration for `{var_name}`:**")

                    col_min, col_max = st.columns(2)
                    with col_min:
                        min_val = st.number_input(
                            "Minimum value", value=var.get("minimum", 0), key=f"dist_min_{var_id}"
                        )
                    with col_max:
                        max_val = st.number_input(
                            "Maximum value", value=var.get("maximum", 100), key=f"dist_max_{var_id}"
                        )

                    var_config["minimum"] = min_val
                    var_config["maximum"] = max_val

                elif var_type == "configuration":
                    st.markdown(f"**Configuration for `{var_name}`:**")

                    on_empty = st.text_input(
                        "Default value (if not found)",
                        value=var.get("onEmpty", "None"),
                        key=f"config_onempty_{var_id}",
                        help="Value to use if the configuration variable is not found in stats",
                    )
                    var_config["onEmpty"] = on_empty

                # Ensure vectorEntries is present for vector types, even if empty
                if var_type == "vector":
                    if "vectorEntries" not in var_config:
                        # Try to preserve existing entries if available in the input var
                        if "vectorEntries" in var:
                            var_config["vectorEntries"] = var["vectorEntries"]
                        else:
                            var_config["vectorEntries"] = []
                        st.write(f"DEBUG: Added missing vectorEntries for {var_name}")
                    else:
                        pass # Debug message removed to reduce clutter

                updated_vars.append(var_config)

        # Add Variable Section
        st.markdown("---")
        st.markdown("### Add Variable")

        col_add1, col_add2 = st.columns([3, 1])

        with col_add1:
            if available_variables:
                # Create options list: "name (type)"
                options = [f"{v['name']} ({v['type']})" for v in available_variables]
                selected_option = st.selectbox(
                    "Search available variables",
                    options=[""] + options,
                    key="var_search_box",
                    help="Type to search for variables found in your stats files",
                )

                if selected_option:
                    # Parse back
                    name = selected_option.split(" (")[0]
                    var_type = selected_option.split(" (")[1][:-1]

                    if st.button("Add Selected", key="add_selected_var"):
                        # If vector, try to pre-populate all entries if available?
                        # Or just let the user select them.
                        # Let's just add the variable, the editor will show the entries.
                        variables.append({"name": name, "type": var_type})
                        st.rerun()
            else:
                st.info("Scan stats files to enable variable search.")

        with col_add2:
            if st.button("+ Add Manual", key="add_manual_var"):
                variables.append({"name": "new_variable", "type": "scalar"})
                st.rerun()

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
            return st.button("+ Add Variable", width="stretch")
        return False

    @staticmethod
    def sidebar_info():
        """Display sidebar information about RING-5."""
        st.markdown("### About RING-5")
        st.info(
            """
        **Pure Python** implementation for gem5 data analysis.

        - Parse gem5 stats OR upload CSV
        - No R dependencies
        - Interactive configuration
        - Real-time visualization
        - Professional plots
        """
        )

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
                "Load Configuration",
            ],
            label_visibility="collapsed",
        )

    @staticmethod
    def clear_data_button() -> bool:
        """
        Display clear data button.

        Returns:
            True if button was clicked
        """
        return st.button("Clear All Data", width="stretch")

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
            csv_data = data.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"{prefix}.csv",
                mime="text/csv",
                width="stretch",
            )

        with col2:
            json_data = data.to_json(orient="records", indent=2).encode("utf-8")
            st.download_button(
                label="Download JSON",
                data=json_data,
                file_name=f"{prefix}.json",
                mime="application/json",
                width="stretch",
            )

        with col3:
            excel_buffer = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            data.to_excel(excel_buffer.name, index=False, engine="openpyxl")
            with open(excel_buffer.name, "rb") as f:
                excel_data = f.read()

            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name=f"{prefix}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
