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
            # Type-specific configuration
            if var_type == "vector":
                cls.render_vector_config(
                    var_config, var, var_id, available_variables, stats_path, stats_pattern
                )
            elif var_type == "distribution":
                cls.render_distribution_config(var_config, var, var_id, stats_path, stats_pattern)
            elif var_type == "histogram":
                cls.render_histogram_config(
                    var_config, var, var_id, available_variables, stats_path, stats_pattern
                )
            elif var_type == "configuration":
                cls.render_configuration_config(var_config, var, var_id)

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
            options = ["scalar", "vector", "distribution", "histogram", "configuration"]

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
    def render_histogram_config(
        cls,
        var_config: Dict[str, Any],
        original_var: Dict[str, Any],
        var_id: str,
        available_variables: Optional[List[Dict[str, Any]]],
        stats_path: Optional[str],
        stats_pattern: str,
    ):
        """Render configuration for histogram variables."""
        var_name = var_config.get("name", "")
        if var_name:
            st.markdown(f"**Histogram Configuration for `{var_name}`:**")

        st.info(
            "Histograms require buckets (ranges) to be specified. "
            "You can use **Deep Scan** to find all range buckets found across all simulations."
        )

        discovered_entries = []
        if available_variables:
            for v in available_variables:
                if v["name"] == var_name and "entries" in v:
                    discovered_entries = v["entries"]
                    break

        options = ["Manual Entry Names", "Histogram Statistics"]
        if discovered_entries:
            options.insert(0, "Select from Discovered Entries")

        current_mode_index = 0
        if original_var.get("useSpecialMembers", False):
            if "Histogram Statistics" in options:
                current_mode_index = options.index("Histogram Statistics")
            else:
                current_mode_index = 1

        entry_mode = st.radio(
            "How to specify histogram entries:",
            options=options,
            index=current_mode_index,
            key=f"hist_entry_mode_{var_id}",
            horizontal=True,
        )

        cls._handle_deep_scan(
            var_name,
            var_id,
            entry_mode,
            discover_entries_available=bool(discovered_entries),
            stats_path=stats_path,
            stats_pattern=stats_pattern,
            var_type="histogram",
        )

        # Target Buckets Configuration (Rebinning)
        st.write("---")
        enable_rebin = st.checkbox(
            "Normalize to Fixed Buckets (Rebinning)",
            value=original_var.get("enableRebin", False),
            key=f"hist_rebin_{var_id}",
            help="Normalizes histograms with inconsistent bucket ranges across simulations",
        )

        if enable_rebin:
            c1, c2 = st.columns(2)
            with c1:
                bins = st.number_input(
                    "Target Buckets",
                    min_value=1,
                    max_value=1000,
                    value=int(original_var.get("bins", 10)),
                    key=f"hist_bins_{var_id}",
                )
            with c2:
                max_range = st.number_input(
                    "Max Range",
                    min_value=1.0,
                    value=float(original_var.get("max_range", 1024.0)),
                    key=f"hist_max_range_{var_id}",
                )
            var_config["bins"] = bins
            var_config["max_range"] = max_range
            original_var["enableRebin"] = True
            original_var["bins"] = bins
            original_var["max_range"] = max_range

        if entry_mode == "Select from Discovered Entries":
            cls._render_vector_discovered_selection(
                var_config, original_var, var_id, discovered_entries
            )
        elif entry_mode == "Manual Entry Names":
            cls._render_vector_manual_entry(var_config, original_var, var_id)
        else:
            cls._render_distribution_statistics_selection(var_config, original_var, var_id)

    @classmethod
    def render_vector_config(
        cls,
        var_config: Dict[str, Any],
        original_var: Dict[str, Any],
        var_id: str,
        available_variables: Optional[List[Dict[str, Any]]],
        stats_path: Optional[str],
        stats_pattern: str,
    ):
        """Render configuration for vector variables."""
        var_name = var_config.get("name", "")
        # Header is optional or can be external
        if var_name:
            st.markdown(f"**Vector Configuration for `{var_name}`:**")

        st.info(
            "Vectors require entries to be specified. "
            "You can manually search for entries, or use the **Deep Scan** feature below "
            "to automatically find them in your stats files."
        )

        discovered_entries = []
        if available_variables:
            for v in available_variables:
                if v["name"] == var_name and "entries" in v:
                    discovered_entries = v["entries"]
                    break

        options = ["Manual Entry Names", "Vector Statistics"]
        if discovered_entries:
            options.insert(0, "Select from Discovered Entries")

        current_mode_index = 0
        if original_var.get("useSpecialMembers", False):
            if "Vector Statistics" in options:
                current_mode_index = options.index("Vector Statistics")
            else:
                current_mode_index = 1  # Fallback

        entry_mode = st.radio(
            "How to specify vector entries:",
            options=options,
            index=current_mode_index,
            key=f"entry_mode_{var_id}",
            horizontal=True,
        )

        cls._handle_deep_scan(
            var_name,
            var_id,
            entry_mode,
            discover_entries_available=bool(discovered_entries),
            stats_path=stats_path,
            stats_pattern=stats_pattern,
        )

        if entry_mode == "Select from Discovered Entries":
            cls._render_vector_discovered_selection(
                var_config, original_var, var_id, discovered_entries
            )

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
        stats_pattern: str,
        var_type: str = "vector",
    ):
        """Handle deep scan logic and button."""
        if not stats_path:
            return

        is_distribution = var_type == "distribution"

        if is_distribution:
            should_show_scan = True
            btn_label = f"Deep Scan Range for '{var_name}'"
            help_text = (
                "Scan ALL stats files to find the total min/max bucket range for this distribution."
            )
        else:
            should_show_scan = entry_mode == "Select from Discovered Entries" or (
                not discover_entries_available and entry_mode == "Manual Entry Names"
            )
            btn_label = f"Deep Scan Entries for '{var_name}'"
            help_text = "Scan ALL stats files to find all possible entries for this variable."

        if should_show_scan:
            if st.button(
                btn_label,
                key=f"deep_scan_{var_id}",
                help=help_text,
            ):
                with st.spinner(f"Scanning all files for {var_name}..."):
                    facade = BackendFacade()

                    if is_distribution:
                        result = facade.scan_distribution_range(stats_path, var_name, stats_pattern)
                        if result and (
                            result["minimum"] is not None or result["maximum"] is not None
                        ):
                            # Update session state if possible, though number_input value is local
                            st.success(f"Found range: {result['minimum']} to {result['maximum']}")
                            # Store in session state for number_input default usage
                            st.session_state[f"dist_range_result_{var_id}"] = result
                            st.rerun()
                        else:
                            st.warning("No distribution data found.")
                    else:
                        all_entries = facade.scan_entries_for_variable(
                            stats_path, var_name, stats_pattern
                        )

                        if all_entries:
                            # Update session state available variables
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

    @staticmethod
    def _render_vector_discovered_selection(
        var_config: Dict[str, Any],
        original_var: Dict[str, Any],
        var_id: str,
        discovered_entries: List[str],
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
        var_config: Dict[str, Any], original_var: Dict[str, Any], var_id: str
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
        var_config: Dict[str, Any], original_var: Dict[str, Any], var_id: str
    ):
        """Render checkboxes for vector statistics."""
        st.markdown("**Select statistics to extract from the vector:**")
        col_stat1, col_stat2 = st.columns(2)

        current_entries = original_var.get("vectorEntries", [])

        with col_stat1:
            extract_total = st.checkbox(
                "total (sum)", value="total" in current_entries, key=f"stat_total_{var_id}"
            )
            extract_mean = st.checkbox(
                "mean (arithmetic)", value="mean" in current_entries, key=f"stat_mean_{var_id}"
            )
            extract_gmean = st.checkbox(
                "gmean (geometric)", value="gmean" in current_entries, key=f"stat_gmean_{var_id}"
            )

        with col_stat2:
            extract_samples = st.checkbox(
                "samples (count)", value="samples" in current_entries, key=f"stat_samples_{var_id}"
            )
            extract_stdev = st.checkbox(
                "stdev (standard deviation)",
                value="stdev" in current_entries,
                key=f"stat_stdev_{var_id}",
            )

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

    @classmethod
    def render_distribution_config(
        cls,
        var_config: Dict[str, Any],
        original_var: Dict[str, Any],
        var_id: str,
        stats_path: Optional[str],
        stats_pattern: str,
    ):
        """Render configuration for distribution variables."""
        var_name = var_config.get("name", "")
        if var_name:
            st.markdown(f"**Distribution Configuration for `{var_name}`:**")

        # Range inputs with potential deep-scan overrides
        range_result = st.session_state.get(f"dist_range_result_{var_id}", {})
        default_min = range_result.get("minimum", original_var.get("minimum", 0))
        default_max = range_result.get("maximum", original_var.get("maximum", 100))

        col_min, col_max = st.columns(2)
        with col_min:
            min_val = st.number_input("Minimum value", value=default_min, key=f"dist_min_{var_id}")
        with col_max:
            max_val = st.number_input("Maximum value", value=default_max, key=f"dist_max_{var_id}")

        var_config["minimum"] = min_val
        var_config["maximum"] = max_val

        cls._handle_deep_scan(
            var_name,
            var_id,
            "",
            False,
            stats_path,
            stats_pattern,
            var_type="distribution",
        )

        st.write("")
        cls._render_distribution_statistics_selection(var_config, original_var, var_id)

    @staticmethod
    def _render_distribution_statistics_selection(
        var_config: Dict[str, Any], original_var: Dict[str, Any], var_id: str
    ):
        """Render checkboxes for distribution statistics."""
        st.markdown("**Extract additional statistics:**")
        col_stat1, col_stat2 = st.columns(2)

        current_stats = original_var.get("statistics", [])

        with col_stat1:
            extract_mean = st.checkbox(
                "mean", value="mean" in current_stats, key=f"dist_stat_mean_{var_id}"
            )
            extract_stdev = st.checkbox(
                "stdev", value="stdev" in current_stats, key=f"dist_stat_stdev_{var_id}"
            )
            extract_samples = st.checkbox(
                "samples", value="samples" in current_stats, key=f"dist_stat_samples_{var_id}"
            )
            extract_underflows = st.checkbox(
                "underflows",
                value="underflows" in current_stats,
                key=f"dist_stat_underflows_{var_id}",
            )

        with col_stat2:
            extract_total = st.checkbox(
                "total", value="total" in current_stats, key=f"dist_stat_total_{var_id}"
            )
            extract_gmean = st.checkbox(
                "gmean", value="gmean" in current_stats, key=f"dist_stat_gmean_{var_id}"
            )
            extract_overflows = st.checkbox(
                "overflows", value="overflows" in current_stats, key=f"dist_stat_overflows_{var_id}"
            )

        selected_stats = []
        if extract_mean:
            selected_stats.append("mean")
        if extract_stdev:
            selected_stats.append("stdev")
        if extract_samples:
            selected_stats.append("samples")
        if extract_total:
            selected_stats.append("total")
        if extract_gmean:
            selected_stats.append("gmean")
        if extract_underflows:
            selected_stats.append("underflows")
        if extract_overflows:
            selected_stats.append("overflows")

        if selected_stats:
            var_config["statistics"] = selected_stats

    @staticmethod
    def render_configuration_config(
        var_config: Dict[str, Any], original_var: Dict[str, Any], var_id: str
    ):
        """Render configuration for configuration variables."""
        var_name = var_config.get("name", "")
        if var_name:
            st.markdown(f"**Configuration for `{var_name}`:**")

        on_empty = st.text_input(
            "Default value (if not found)",
            value=original_var.get("onEmpty", "None"),
            key=f"config_onempty_{var_id}",
            help="Value to use if the configuration variable is not found in stats",
        )
        var_config["onEmpty"] = on_empty

    @staticmethod
    def _render_add_variable_section(
        variables: List[Dict[str, Any]], available_variables: Optional[List[Dict[str, Any]]]
    ):
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
