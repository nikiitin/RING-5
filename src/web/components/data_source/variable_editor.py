"""
Variable Editor Component for RING-5.
Handles rendering and interaction for defining parser variables (scalars, vectors, distributions).
"""

import uuid
from concurrent.futures import Future, as_completed

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import ScannedVariable
from src.core.models.data_models import ParseVariableConfig, ScannedVariableDict
from src.web.components.common.filtered_selector import filtered_multiselect, filtered_selectbox
from src.web.components.data_source.pattern_index_selector import PatternIndexSelector


class VariableEditor:
    """Component for editing parser variables."""

    @classmethod
    def render(
        cls,
        api: ApplicationAPI,
        variables: list[ParseVariableConfig],
        available_variables: list[ScannedVariableDict] | None = None,
        stats_path: str | None = None,
        stats_pattern: str = "stats.txt",
    ) -> list[ParseVariableConfig]:
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
        # Ensure all variables have IDs (mutate in-place)
        for var in variables:
            if "_id" not in var:
                var["_id"] = api.data_services.generate_variable_id()

        st.markdown("**Current Variables:**")

        updated_vars: list[ParseVariableConfig] = []
        deleted_indices: list[int] = []

        for idx, var in enumerate(variables):
            # Get ID (should exist after ensuring IDs above)
            var_id = var.get("_id", f"fallback_{idx}")

            # Common fields (Name, Alias, Type)
            var_name, var_alias, var_type, should_delete = cls._render_common_fields(
                idx, var, var_id
            )

            if should_delete:
                deleted_indices.append(idx)
                continue

            var_config: ParseVariableConfig = {"name": var_name, "type": var_type, "_id": var_id}
            if var_alias:
                var_config["alias"] = var_alias

            # Type-specific configuration
            if var_type == "vector":
                cls.render_vector_config(
                    api, var_config, var, var_id, available_variables, stats_path, stats_pattern
                )
            elif var_type == "distribution":
                cls.render_distribution_config(
                    api, var_config, var, var_id, stats_path, stats_pattern
                )
            elif var_type == "histogram":
                cls.render_histogram_config(
                    api, var_config, var, var_id, available_variables, stats_path, stats_pattern
                )
            elif var_type == "configuration":
                cls.render_configuration_config(var_config, var, var_id)

            # Pattern index selection for ALL variable types (scalars included)
            if PatternIndexSelector.is_pattern_variable(var_name):
                cls._render_pattern_index_for_variable(api, var_config, var, var_id)

            updated_vars.append(var_config)

        # Add Variable Section
        cls._render_add_variable_section(variables, available_variables)

        return updated_vars

    @staticmethod
    def _render_common_fields(
        idx: int, var: ParseVariableConfig, var_id: str
    ) -> tuple[str, str, str, bool]:
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
            delete_clicked = st.button("X", key=f"delete_var_{var_id}", type="tertiary")

        return var_name, var_alias, var_type, delete_clicked

    @classmethod
    def _render_pattern_index_for_variable(
        cls,
        api: ApplicationAPI,
        var_config: ParseVariableConfig,
        original_var: ParseVariableConfig,
        var_id: str,
    ) -> None:
        """
        Render PatternIndexSelector for any pattern variable type.

        When a user selects specific indices, ``keepIndices`` is set to
        ``True`` and ``parsed_ids`` is populated with the filtered list.
        This applies to scalars, vectors, distributions, and histograms.
        """
        var_name = var_config.get("name", "")
        scanned_vars = api.state_manager.get_scanned_variables() or []
        pattern_indices: list[str] | None = None

        for v in scanned_vars:
            if v["name"] == var_name and "pattern_indices" in v:
                pattern_indices = v["pattern_indices"]
                break

        if not pattern_indices:
            return

        current_selection = original_var.get("patternSelection", None)
        use_filter, pattern_filtered = PatternIndexSelector.render_selector(
            var_name, pattern_indices, var_id, current_selection
        )

        if use_filter:
            var_config["patternSelection"] = pattern_filtered
            var_config["parsed_ids"] = pattern_filtered
            var_config["keepIndices"] = True
        else:
            var_config["keepIndices"] = False

    @classmethod
    def render_histogram_config(
        cls,
        api: ApplicationAPI,
        var_config: ParseVariableConfig,
        original_var: ParseVariableConfig,
        var_id: str,
        available_variables: list[ScannedVariableDict] | None,
        stats_path: str | None,
        stats_pattern: str,
    ) -> None:
        """Render configuration for histogram variables."""
        var_name = var_config.get("name", "")
        if var_name:
            st.markdown(f"**Histogram Configuration for `{var_name}`:**")

        st.info(
            "Histograms require buckets (ranges) to be specified. "
            "You can use **Deep Scan** to find all range buckets found across all simulations."
        )

        discovered_entries: list[str] = []
        if available_variables:
            for v in available_variables:
                if v["name"] == var_name and "entries" in v:
                    discovered_entries = v["entries"]
                    break

        # Parsing mode — always available: statistics, optionally bucket entries
        hist_parse_options = [
            "Statistics Only",
            "Bucket Entries Only",
            "Bucket Entries + Statistics",
        ]
        hist_default = (
            hist_parse_options[0]
            if original_var.get("statisticsOnly", True)
            else (
                hist_parse_options[1]
                if not original_var.get("statistics", [])
                else hist_parse_options[2]
            )
        )
        parse_mode = st.segmented_control(
            "Parsing mode:",
            options=hist_parse_options,
            default=hist_default,
            key=f"hist_parse_mode_{var_id}",
            help=(
                "Statistics Only: Parse mean, stdev, etc. without individual buckets. "
                "Bucket Entries Only: Parse histogram bucket frequencies. "
                "Bucket Entries + Statistics: Parse both."
            ),
        )

        wants_statistics = parse_mode in ("Statistics Only", "Bucket Entries + Statistics")
        wants_entries = parse_mode in ("Bucket Entries Only", "Bucket Entries + Statistics")

        var_config["statisticsOnly"] = parse_mode == "Statistics Only"

        # Statistics selection (always visible when stats requested)
        if wants_statistics:
            cls._render_distribution_statistics_selection(var_config, original_var, var_id)

        # Bucket entry selection (only when entries requested)
        if wants_entries:
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

            entry_options = ["Manual Entry Names"]
            if discovered_entries:
                entry_options.insert(0, "Select from Discovered Entries")

            entry_mode = st.pills(
                "How to specify histogram entries:",
                options=entry_options,
                default=entry_options[0],
                key=f"hist_entry_mode_{var_id}",
            )

            cls._handle_deep_scan(
                api,
                var_name,
                var_id,
                entry_mode or entry_options[0],
                discover_entries_available=bool(discovered_entries),
                stats_path=stats_path,
                stats_pattern=stats_pattern,
                var_type="histogram",
            )

            if entry_mode == "Select from Discovered Entries":
                cls._render_vector_discovered_selection(
                    api, var_config, original_var, var_id, discovered_entries
                )
            else:
                cls._render_vector_manual_entry(api, var_config, original_var, var_id)

    @classmethod
    def render_vector_config(
        cls,
        api: ApplicationAPI,
        var_config: ParseVariableConfig,
        original_var: ParseVariableConfig,
        var_id: str,
        available_variables: list[ScannedVariableDict] | None,
        stats_path: str | None,
        stats_pattern: str,
    ) -> None:
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

        discovered_entries: list[str] = []
        if available_variables:
            for v in available_variables:
                if v["name"] == var_name and "entries" in v:
                    discovered_entries = v["entries"]
                    break

        # Parsing mode — always available: statistics, optionally entries
        vec_parse_options = ["Statistics Only", "Entries Only", "Entries + Statistics"]
        vec_default = (
            vec_parse_options[0]
            if original_var.get("statisticsOnly", False)
            else (
                vec_parse_options[1]
                if not original_var.get("useSpecialMembers", False)
                and not original_var.get("statisticsOnly", False)
                else vec_parse_options[2]
            )
        )
        parse_mode = st.segmented_control(
            "Parsing mode:",
            options=vec_parse_options,
            default=vec_default,
            key=f"vec_parse_mode_{var_id}",
            help=(
                "Statistics Only: Parse total, mean, stdev, etc. without "
                "individual entries. Entries Only: Parse selected entries. "
                "Entries + Statistics: Parse both entries and statistics."
            ),
        )

        wants_statistics = parse_mode in ("Statistics Only", "Entries + Statistics")
        wants_entries = parse_mode in ("Entries Only", "Entries + Statistics")

        var_config["statisticsOnly"] = parse_mode == "Statistics Only"

        # Statistics selection (always visible when stats requested)
        if wants_statistics:
            cls._render_vector_statistics_selection(var_config, original_var, var_id)

        # Entry selection (only when entries requested)
        if wants_entries:
            entry_options = ["Manual Entry Names"]
            if discovered_entries:
                entry_options.insert(0, "Select from Discovered Entries")

            entry_mode = st.pills(
                "How to specify entries:",
                options=entry_options,
                default=entry_options[0],
                key=f"entry_mode_{var_id}",
            )

            cls._handle_deep_scan(
                api,
                var_name,
                var_id,
                entry_mode or entry_options[0],
                discover_entries_available=bool(discovered_entries),
                stats_path=stats_path,
                stats_pattern=stats_pattern,
            )

            if entry_mode == "Select from Discovered Entries":
                cls._render_vector_discovered_selection(
                    api, var_config, original_var, var_id, discovered_entries
                )
            else:
                cls._render_vector_manual_entry(api, var_config, original_var, var_id)

    @classmethod
    def _handle_deep_scan(
        cls,
        api: ApplicationAPI,
        var_name: str,
        var_id: str,
        entry_mode: str,
        discover_entries_available: bool,
        stats_path: str | None,
        stats_pattern: str,
        var_type: str = "vector",
    ) -> None:
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
            if st.button(btn_label, key=f"deep_scan_{var_id}", help=help_text):
                try:
                    futures = api.submit_scan_async(stats_path, stats_pattern, limit=-1)
                    cls._show_scan_dialog(api, var_name, var_id, futures, is_distribution)
                except Exception as e:
                    st.exception(e)

    @classmethod
    @st.dialog("Deep Scan", dismissible=True)
    def _show_scan_dialog(
        cls,
        api: ApplicationAPI,
        var_name: str,
        var_id: str,
        futures: list[Future[list[ScannedVariable]]],
        is_distribution: bool,
    ) -> None:
        """Blocking dialog for async scanning using futures."""
        st.write(f"Variable: `{var_name}`")
        st.write(f"Scanning {len(futures)} files...")
        progress_bar = st.progress(0, text="Starting scan...")

        results: list[list[ScannedVariable]] = []
        errors: list[str] = []
        completed = 0
        total = len(futures)

        try:
            for future in as_completed(futures):
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception as e:
                    errors.append(str(e))

                completed += 1
                if total > 0:
                    pct = min(completed / total, 1.0)
                    progress_bar.progress(pct, text=f"Scanned {completed}/{total} files")
        except KeyboardInterrupt:
            st.warning("Scan interrupted.")
            return

        if errors:
            st.warning(f"Encountered {len(errors)} errors during scan.")

        if not results:
            st.warning("No results found.")
            return

        # Aggregate results with status container
        with st.status("Processing scan results...", expanded=True) as status:
            st.write("Aggregating scan data...")
            snapshot = api.finalize_scan(results)
            snapshot_dicts = [sv.to_dict() for sv in snapshot]

            # Process results based on type
            if is_distribution:
                st.write("Computing distribution range...")
                global_min, global_max = api.data_services.aggregate_distribution_range(
                    snapshot_dicts, var_name
                )

                if global_min is not None or global_max is not None:
                    st.session_state[f"dist_range_result_{var_id}"] = {
                        "minimum": global_min,
                        "maximum": global_max,
                    }
                    status.update(
                        label=f"Range found: [{global_min}, {global_max}]",
                        state="complete",
                        expanded=False,
                    )
                    st.success(f"Final Range: [{global_min}, {global_max}]")
                else:
                    status.update(label="No distribution data found", state="error")
                    st.warning(f"No distribution data found matching '{var_name}'.")
            else:
                st.write("Discovering entries...")
                # Aggregate entries using VariableServicesAPI
                filtered_entries = api.data_services.aggregate_discovered_entries(
                    snapshot_dicts, var_name
                )

                if filtered_entries:
                    st.write(f"Updating {len(filtered_entries)} entries...")
                    scanned_vars = api.state_manager.get_scanned_variables() or []
                    # Delegate update logic to VariableService (Layer B)
                    updated_vars = api.data_services.update_scanned_entries(
                        scanned_vars, var_name, filtered_entries
                    )
                    api.state_manager.set_scanned_variables(updated_vars)
                    status.update(
                        label=f"Discovered {len(filtered_entries)} entries",
                        state="complete",
                        expanded=False,
                    )
                    st.success(f"Discovered {len(filtered_entries)} unique entries!")
                else:
                    status.update(label="No entries found", state="error")
                    st.warning(f"No valid entries found matching '{var_name}'.")

        # Release completed futures to free memory (~70MB for 252 files).
        from src.core.application_api import ApplicationAPI

        ApplicationAPI.cancel_pending_scans()

        if st.button("Close", key=f"finish_{var_id}"):
            st.rerun()

    @classmethod
    def _render_vector_discovered_selection(
        cls,
        api: ApplicationAPI,
        var_config: ParseVariableConfig,
        original_var: ParseVariableConfig,
        var_id: str,
        discovered_entries: list[str],
    ) -> None:
        """Render multiselect for discovered vector entries."""
        # Filter internal statistics using variable services
        filtered_entries = api.data_services.filter_internal_stats(discovered_entries)

        # Continue with normal entry selection
        current_entries = original_var.get("vectorEntries", [])
        if isinstance(current_entries, str):
            current_entries = api.data_services.parse_comma_separated_entries(current_entries)

        # Filter defaults to ensure they exist in discovered list
        valid_defaults = [e for e in current_entries if e in filtered_entries]

        selected_entries = filtered_multiselect(
            "Select entries to extract:",
            options=filtered_entries,
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
        api: ApplicationAPI,
        var_config: ParseVariableConfig,
        original_var: ParseVariableConfig,
        var_id: str,
    ) -> None:
        """Render text input for manual vector entries."""
        default_entries = original_var.get("vectorEntries", "")
        if isinstance(default_entries, list):
            default_entries = api.data_services.format_entries_as_string(default_entries)

        vector_entries_input = st.text_input(
            "Vector entries (comma-separated)",
            value=default_entries,
            key=f"vector_entries_{var_id}",
            placeholder="e.g., cpu0, cpu1, cpu2 or bank0, bank1, bank2",
            help="Enter the exact names of vector entries as they appear in stats.txt",
        )

        if vector_entries_input.strip():
            entries = api.data_services.parse_comma_separated_entries(vector_entries_input)
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
        var_config: ParseVariableConfig, original_var: ParseVariableConfig, var_id: str
    ) -> None:
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

        special_members: list[str] = []
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
        api: ApplicationAPI,
        var_config: ParseVariableConfig,
        original_var: ParseVariableConfig,
        var_id: str,
        stats_path: str | None,
        stats_pattern: str,
    ) -> None:
        """Render configuration for distribution variables."""
        var_name = var_config.get("name", "")
        if var_name:
            st.markdown(f"**Distribution Configuration for `{var_name}`:**")

        # Parsing mode — statistics are always available, bucket entries optional
        dist_parse_options = [
            "Statistics Only",
            "Bucket Entries Only",
            "Bucket Entries + Statistics",
        ]
        dist_default = (
            dist_parse_options[0]
            if original_var.get("statisticsOnly", True)
            else (
                dist_parse_options[1]
                if not original_var.get("statistics", [])
                else dist_parse_options[2]
            )
        )
        parse_mode = st.segmented_control(
            "Parsing mode:",
            options=dist_parse_options,
            default=dist_default,
            key=f"dist_parse_mode_{var_id}",
            help=(
                "Statistics Only: Parse mean, stdev, etc. without individual buckets. "
                "Bucket Entries Only: Parse distribution bucket frequencies. "
                "Bucket Entries + Statistics: Parse both."
            ),
        )

        wants_statistics = parse_mode in ("Statistics Only", "Bucket Entries + Statistics")
        wants_entries = parse_mode in ("Bucket Entries Only", "Bucket Entries + Statistics")

        var_config["statisticsOnly"] = parse_mode == "Statistics Only"

        # Statistics selection (always visible when stats requested)
        if wants_statistics:
            cls._render_distribution_statistics_selection(var_config, original_var, var_id)

        # Range inputs only needed when parsing bucket entries
        if wants_entries:
            st.write("---")
            st.markdown("**Bucket Range:**")

            range_result = st.session_state.get(f"dist_range_result_{var_id}", {})
            default_min = range_result.get("minimum", original_var.get("minimum", 0))
            default_max = range_result.get("maximum", original_var.get("maximum", 100))

            col_min, col_max = st.columns(2)
            with col_min:
                min_val = st.number_input(
                    "Minimum value", value=default_min, key=f"dist_min_{var_id}"
                )
            with col_max:
                max_val = st.number_input(
                    "Maximum value", value=default_max, key=f"dist_max_{var_id}"
                )

            var_config["minimum"] = min_val
            var_config["maximum"] = max_val

            cls._handle_deep_scan(
                api,
                var_name,
                var_id,
                "",
                False,
                stats_path,
                stats_pattern,
                var_type="distribution",
            )

    @staticmethod
    def _render_distribution_statistics_selection(
        var_config: ParseVariableConfig, original_var: ParseVariableConfig, var_id: str
    ) -> None:
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

        selected_stats: list[str] = []
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
        var_config: ParseVariableConfig, original_var: ParseVariableConfig, var_id: str
    ) -> None:
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
        variables: list[ParseVariableConfig],
        available_variables: list[ScannedVariableDict] | None,
    ) -> None:
        """Render the 'Add Variable' section with search and manual add options."""
        st.markdown("---")
        st.markdown("### Add Variable")

        col_add1, col_add2 = st.columns([3, 1])

        with col_add1:
            if available_variables:
                options = [f"{v['name']} ({v['type']})" for v in available_variables]
                selected_option = filtered_selectbox(
                    "Search available variables",
                    options=options,
                    key="var_search_box",
                    help="Type to search for variables found in your stats files",
                )

                if selected_option:
                    name = selected_option.split(" (")[0]
                    var_type = selected_option.split(" (")[1][:-1]

                    if st.button("Add Selected", key="add_selected_var"):
                        new_var: ParseVariableConfig = {
                            "name": name,
                            "type": var_type,
                            "_id": str(uuid.uuid4()),
                        }
                        # Mutate in-place for Streamlit state management
                        variables.append(new_var)
                        st.rerun()
            else:
                st.info("Scan stats files to enable variable search.")

        with col_add2:
            if st.button("+ Add Manual", key="add_manual_var"):
                manual_var: ParseVariableConfig = {
                    "name": "new_variable",
                    "type": "scalar",
                    "_id": str(uuid.uuid4()),
                }
                # Mutate in-place for Streamlit state management
                variables.append(manual_var)
                st.rerun()
