"""
Variable Editor Component for RING-5.
Handles rendering and interaction for defining parser variables (scalars, vectors, distributions).
"""

from typing import Any, Dict, List, Optional

import streamlit as st

from src.web.facade import BackendFacade


class VariableEditor:
    """Component for editing parser variables."""

    @classmethod
    def render(
        cls,
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

        for idx, var in enumerate(variables):
            # Ensure ID exists
            var_id = var.get("_id", f"fallback_{idx}")
            
            # Common fields (Name, Alias, Type)
            var_name, var_alias, var_type, should_delete = cls._render_common_fields(
                idx, var, var_id
            )

            if should_delete:
                deleted_indices.append(idx)
                continue

            var_config = {"name": var_name, "type": var_type, "_id": var_id}
            if var_alias:
                var_config["alias"] = var_alias

            # Type-specific configuration
            if var_type == "vector":
                cls._render_vector_config(
                    var_config, var, var_id, available_variables, stats_path, stats_pattern
                )
            elif var_type == "distribution":
                cls._render_distribution_config(var_config, var, var_id)
            elif var_type == "configuration":
                cls._render_configuration_config(var_config, var, var_id)

            updated_vars.append(var_config)

        # Add Variable Section
        cls._render_add_variable_section(variables, available_variables)

        return updated_vars

    @staticmethod
    def _render_common_fields(idx: int, var: Dict[str, Any], var_id: str):
        """Render common variable fields (Name, Alias, Type)."""
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

        with col1:
            var_name = st.text_input(
                f"Variable {idx+1} Name",
                value=var.get("name", ""),
                key=f"var_name_{var_id}",
                label_visibility="collapsed",
                placeholder="stats.name",
            )

        with col2:
            var_alias = st.text_input(
                f"Alias {idx+1}",
                value=var.get("alias", ""),
                key=f"var_alias_{var_id}",
                label_visibility="collapsed",
                placeholder="Alias (Optional)",
            )

        with col3:
            current_type = var.get("type", "scalar")
            options = ["scalar", "vector", "distribution", "configuration"]
            
            if current_type not in options:
                current_type = "scalar"
                
            var_type = st.selectbox(
                f"Type {idx+1}",
                options=options,
                index=options.index(current_type),
                key=f"var_type_{var_id}",
                label_visibility="collapsed",
            )

        with col4:
            delete_clicked = st.button("X", key=f"delete_var_{var_id}")

        return var_name, var_alias, var_type, delete_clicked

    @classmethod
    def _render_vector_config(
        cls,
        var_config: Dict[str, Any],
        original_var: Dict[str, Any],
        var_id: str,
        available_variables: Optional[List[Dict[str, Any]]],
        stats_path: Optional[str],
        stats_pattern: str,
    ):
        """Render configuration for vector variables."""
        var_name = var_config["name"]
        st.markdown(f"**Vector Configuration for `{var_name}`:**")
        st.info(
            "Vectors require entries to be specified. "
            "You can manually search for entries, or use the **Deep Scan** feature below "
            "to automatically find them in your stats files."
        )

        # 1. Determine discovered entries
        discovered_entries = []
        if available_variables:
            for v in available_variables:
                if v["name"] == var_name and "entries" in v:
                    discovered_entries = v["entries"]
                    break

        # 2. Determine entry mode options
        options = ["Manual Entry Names", "Vector Statistics"]
        if discovered_entries:
            options.insert(0, "Select from Discovered Entries")

        current_mode_index = 0
        if original_var.get("useSpecialMembers", False):
            if "Vector Statistics" in options:
                current_mode_index = options.index("Vector Statistics")
            else:
                current_mode_index = 1 # Fallback
        
        entry_mode = st.radio(
            "How to specify vector entries:",
            options=options,
            index=current_mode_index,
            key=f"entry_mode_{var_id}",
            horizontal=True,
        )

        # 3. Handle Deep Scan
        cls._handle_deep_scan(
            var_name, 
            var_id, 
            entry_mode, 
            discover_entries_available=bool(discovered_entries), 
            stats_path=stats_path, 
            stats_pattern=stats_pattern
        )

        # 4. Render selected mode inputs
        if entry_mode == "Select from Discovered Entries":
            cls._render_vector_discovered_selection(var_config, original_var, var_id, discovered_entries)
        
        elif entry_mode == "Manual Entry Names":
            cls._render_vector_manual_entry(var_config, original_var, var_id)
            
        else:  # Vector Statistics mode
            cls._render_vector_statistics_selection(var_config, original_var, var_id)

    @staticmethod
    def _handle_deep_scan(
        var_name: str, 
        var_id: str, 
        entry_mode: str, 
        discover_entries_available: bool, 
        stats_path: Optional[str], 
        stats_pattern: str
    ):
        """Handle deep scan logic and button."""
        if not stats_path:
            return

        should_show_scan = (
            entry_mode == "Select from Discovered Entries"
            or (not discover_entries_available and entry_mode == "Manual Entry Names")
        )

        if should_show_scan:
            if st.button(
                f"Deep Scan Entries for '{var_name}'",
                key=f"deep_scan_{var_id}",
                help="Scan ALL stats files to find all possible entries for this vector.",
            ):
                with st.spinner(f"Scanning all files for {var_name}..."):
                    facade = BackendFacade()
                    all_entries = facade.scan_vector_entries(
                        stats_path, var_name, stats_pattern
                    )

                    if all_entries:
                        # Update session state available variables
                        if "available_variables" in st.session_state and st.session_state.available_variables:
                            for v in st.session_state.available_variables:
                                if v["name"] == var_name:
                                    v["entries"] = all_entries
                                    break
                                    
                        st.success(f"Found {len(all_entries)} entries!")
                        st.rerun()
                    else:
                        st.warning("No entries found.")

    @staticmethod
    def _render_vector_discovered_selection(
        var_config: Dict[str, Any], 
        original_var: Dict[str, Any], 
        var_id: str, 
        discovered_entries: List[str]
    ):
        """Render multiselect for discovered vector entries."""
        current_entries = original_var.get("vectorEntries", [])
        if isinstance(current_entries, str):
            current_entries = [e.strip() for e in current_entries.split(",") if e.strip()]

        # Filter defaults to ensure they exist in discovered list
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
            st.success(f"Will extract {len(selected_entries)} entries")
        else:
            st.warning("Please select at least one entry")

    @staticmethod
    def _render_vector_manual_entry(
        var_config: Dict[str, Any], 
        original_var: Dict[str, Any], 
        var_id: str
    ):
        """Render text input for manual vector entries."""
        default_entries = original_var.get("vectorEntries", "")
        if isinstance(default_entries, list):
            default_entries = ", ".join(default_entries)

        vector_entries_input = st.text_input(
            "Vector entries (comma-separated)",
            value=default_entries,
            key=f"vector_entries_{var_id}",
            placeholder="e.g., cpu0, cpu1, cpu2 or bank0, bank1, bank2",
            help="Enter the exact names of vector entries as they appear in stats.txt",
        )

        if vector_entries_input.strip():
            entries = [e.strip() for e in vector_entries_input.split(",") if e.strip()]
            var_config["vectorEntries"] = entries
            var_config["useSpecialMembers"] = False
            st.success(
                f"Will extract {len(entries)} entries: "
                f"{', '.join(entries[:3])}{'...' if len(entries) > 3 else ''}"
            )
        else:
            st.warning("Please enter at least one vector entry name")

    @staticmethod
    def _render_vector_statistics_selection(
        var_config: Dict[str, Any], 
        original_var: Dict[str, Any], 
        var_id: str
    ):
        """Render checkboxes for vector statistics."""
        st.markdown("**Select statistics to extract from the vector:**")
        col_stat1, col_stat2 = st.columns(2)
        
        current_entries = original_var.get("vectorEntries", [])

        with col_stat1:
            extract_total = st.checkbox("total (sum)", value="total" in current_entries, key=f"stat_total_{var_id}")
            extract_mean = st.checkbox("mean (arithmetic)", value="mean" in current_entries, key=f"stat_mean_{var_id}")
            extract_gmean = st.checkbox("gmean (geometric)", value="gmean" in current_entries, key=f"stat_gmean_{var_id}")

        with col_stat2:
            extract_samples = st.checkbox("samples (count)", value="samples" in current_entries, key=f"stat_samples_{var_id}")
            extract_stdev = st.checkbox("stdev (standard deviation)", value="stdev" in current_entries, key=f"stat_stdev_{var_id}")

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
            st.success(f"Will extract statistics: {', '.join(special_members)}")
        else:
            st.warning("Please select at least one statistic to extract")

    @staticmethod
    def _render_distribution_config(var_config: Dict[str, Any], original_var: Dict[str, Any], var_id: str):
        """Render configuration for distribution variables."""
        var_name = var_config["name"]
        st.markdown(f"**Distribution Configuration for `{var_name}`:**")

        col_min, col_max = st.columns(2)
        with col_min:
            min_val = st.number_input(
                "Minimum value", value=original_var.get("minimum", 0), key=f"dist_min_{var_id}"
            )
        with col_max:
            max_val = st.number_input(
                "Maximum value", value=original_var.get("maximum", 100), key=f"dist_max_{var_id}"
            )

        var_config["minimum"] = min_val
        var_config["maximum"] = max_val

    @staticmethod
    def _render_configuration_config(var_config: Dict[str, Any], original_var: Dict[str, Any], var_id: str):
        """Render configuration for configuration variables."""
        var_name = var_config["name"]
        st.markdown(f"**Configuration for `{var_name}`:**")

        on_empty = st.text_input(
            "Default value (if not found)",
            value=original_var.get("onEmpty", "None"),
            key=f"config_onempty_{var_id}",
            help="Value to use if the configuration variable is not found in stats",
        )
        var_config["onEmpty"] = on_empty

    @staticmethod
    def _render_add_variable_section(variables: List[Dict[str, Any]], available_variables: Optional[List[Dict[str, Any]]]):
        """Render the 'Add Variable' section with search and manual add options."""
        st.markdown("---")
        st.markdown("### Add Variable")

        col_add1, col_add2 = st.columns([3, 1])

        with col_add1:
            if available_variables:
                options = [f"{v['name']} ({v['type']})" for v in available_variables]
                selected_option = st.selectbox(
                    "Search available variables",
                    options=[""] + options,
                    key="var_search_box",
                    help="Type to search for variables found in your stats files",
                )

                if selected_option:
                    name = selected_option.split(" (")[0]
                    var_type = selected_option.split(" (")[1][:-1]

                    if st.button("Add Selected", key="add_selected_var"):
                        variables.append({"name": name, "type": var_type})
                        st.rerun()
            else:
                st.info("Scan stats files to enable variable search.")

        with col_add2:
            if st.button("+ Add Manual", key="add_manual_var"):
                variables.append({"name": "new_variable", "type": "scalar"})
                st.rerun()
