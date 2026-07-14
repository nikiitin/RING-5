"""
Data Source Components - UI for Data Ingestion and Parsing.

Provides Streamlit components for simulator statistics parsing: CSV pool management,
parser configuration, variable selection, and data preview.
"""

import logging
import tempfile
import uuid
from concurrent.futures import TimeoutError as FuturesTimeoutError
from concurrent.futures import as_completed
from pathlib import Path
from typing import Any, cast

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.common.security_limits import MAX_SCAN_FILES, SCAN_BATCH_TIMEOUT_SECONDS
from src.core.common.utils import validate_web_stats_path
from src.core.models import ParseBatchResult, ScanFileResult, ScanResult
from src.core.models.data_models import ParseVariableConfig, ScannedVariableDict
from src.web.components.common.card_components import CardComponents
from src.web.components.common.data_components import DataComponents
from src.web.components.common.filtered_selector import filtered_selectbox
from src.web.components.data_source.variable_editor import VariableEditor

logger = logging.getLogger(__name__)


class DataSourceComponents:
    """UI Components for the Data Source Page."""

    @staticmethod
    def render_csv_pool(api: ApplicationAPI) -> None:
        """Display and manage the CSV pool."""
        st.markdown("---")
        st.markdown("### Recent CSV Files")

        # Use cached pool from state; only load from disk when cache is empty.
        csv_pool = api.state_manager.get_csv_pool()
        if not csv_pool:
            csv_pool = api.load_csv_pool()
            api.state_manager.set_csv_pool(csv_pool)

        if not csv_pool:
            st.warning("No CSV files in the pool yet. Parse some stats to populate this list.")
            return

        st.info(f"Found {len(csv_pool)} CSV file(s) in the pool")

        for idx, csv_info in enumerate(csv_pool):
            csv_path = Path(csv_info["path"])

            if not csv_path.exists():
                st.error(f"File no longer exists: {csv_info['name']}")
                logger.warning("CSV POOL: File not found on disk: %s", csv_info["path"])
                continue

            load_clicked, preview_clicked, delete_clicked = CardComponents.file_info_card(
                csv_info, idx
            )

            if load_clicked:
                try:
                    data = api.load_csv_file(str(csv_path))
                    api.state_manager.set_data(data)
                    api.state_manager.set_csv_path(str(csv_path))
                    api.state_manager.set_use_parser(False)
                    st.success(f"Loaded {len(data)} rows!")

                    # Show data preview
                    DataComponents.show_data_preview(data, "Loaded CSV Preview")
                    DataComponents.show_column_details(data)
                    st.info("Data loaded! Proceed to **Configure Pipeline** to process it.")
                except Exception as e:
                    st.exception(e)
                    logger.error(
                        "CSV POOL: Failed to load CSV file '%s': %s", csv_path, e, exc_info=True
                    )

            if preview_clicked:
                try:
                    preview_data = api.load_csv_file(str(csv_path))
                    st.dataframe(preview_data.head(5))
                except Exception as e:
                    st.exception(e)

            if delete_clicked:
                if api.delete_from_csv_pool(str(csv_path)):
                    st.toast("File deleted!", icon="🗑️")
                    st.rerun()
                else:
                    st.error("Error deleting file")
                    logger.error("CSV POOL: Failed to delete metadata for: %s", csv_path)

    @staticmethod
    def render_parser_config(api: ApplicationAPI) -> None:
        """Display parser configuration interface."""
        # Get simulator info for dynamic labels
        selected_sim = api.state_manager.get_simulator()
        sim_info = ApplicationAPI.get_simulator_info(selected_sim)
        sim_label = sim_info.display_name

        st.markdown("---")

        # Simulator backend selector (pills navigation)
        simulators = ApplicationAPI.available_simulator_info()
        sim_names = [s.name for s in simulators]
        sim_display = {s.name: f":material/memory: {s.display_name}" for s in simulators}
        chosen: str | None = st.pills(
            "Simulator",
            options=sim_names,
            format_func=lambda x: sim_display.get(x, str(x)),
            selection_mode="single",
            default=selected_sim if selected_sim in sim_names else sim_names[0],
            key="simulator_selector",
        )
        if chosen and chosen != selected_sim:
            api.state_manager.set_simulator(chosen)
            st.rerun()

        st.markdown(f"### {sim_label} Stats Parser Configuration")

        # The entire parser config section (file inputs, strategy radio,
        # variable editor, scan button, config preview) is wrapped in a
        # single @st.fragment so that typing in text inputs or changing the
        # strategy radio only reruns this fragment — NOT the full page.
        @st.fragment
        def _parser_config_fragment() -> None:
            st.markdown("#### File Location")
            col1, col2 = st.columns(2)
            with col1:
                current_path = api.state_manager.get_stats_path()
                stats_path = st.text_input(
                    "Stats directory path",
                    value=current_path,
                    help=(
                        f"Directory containing {sim_label} stats files "
                        "(can include subdirectories)"
                    ),
                    key="stats_path_input",
                )
                if stats_path != current_path:
                    api.state_manager.set_stats_path(stats_path)

            with col2:
                current_pattern = api.state_manager.get_stats_pattern()
                stats_pattern = st.text_input(
                    "File pattern",
                    value=current_pattern,
                    help="Filename pattern to search for (e.g., stats.txt, *.txt)",
                    key="stats_pattern_input",
                )
                if stats_pattern != current_pattern:
                    api.state_manager.set_stats_pattern(stats_pattern)

            st.markdown("#### Parsing Strategy")
            current_strategy = api.state_manager.get_parser_strategy()
            # Strategies come from the simulator's registry contract
            strategies = sim_info.parsing_strategies
            strategy_options = {s.name: s.display_name for s in strategies}
            strategy_help = {s.name: s.description for s in strategies}

            # Fall back to first strategy if current is not in options
            if current_strategy not in strategy_options:
                current_strategy = strategies[0].name

            selected_strategy = st.segmented_control(
                "Select ingestion strategy:",
                options=list(strategy_options.keys()),
                format_func=lambda x: strategy_options[x],
                default=current_strategy,
                help=strategy_help.get(current_strategy, ""),
                key="parser_strategy_selector",
            )

            if selected_strategy and selected_strategy != current_strategy:
                api.state_manager.set_parser_strategy(selected_strategy)

            # Variables configuration
            st.markdown("#### Variables to Extract")
            st.markdown(f"""
            Define which variables to extract from {sim_label} stats files:
            - **Scalar**: Single numeric values (e.g., simTicks, IPC)
            - **Vector**: Arrays of values with specified entries
            - **Distribution**: Statistical distributions with min/max range
            - **Configuration**: Metadata (benchmark name, config ID, seed)
            """)

            # Scanner UI
            col_scan1, _col_scan2 = st.columns([1, 3])
            with col_scan1:
                deep_scan = st.checkbox(
                    f"Deep Scan (up to {MAX_SCAN_FILES} files)",
                    help="Scan a bounded sample of files for variables (slower)",
                )
                if st.button("🔍 Quick Scan", help="Scan files to auto-discover variables"):
                    try:
                        scan_limit = MAX_SCAN_FILES if deep_scan else 10
                        scan_label = "Deep" if deep_scan else "Quick"
                        with st.status(f"{scan_label} scanning...", expanded=True) as status:
                            st.write("Submitting scan tasks...")
                            safe_stats_path = str(validate_web_stats_path(stats_path))
                            scan_futures = api.submit_scan_async(
                                safe_stats_path, stats_pattern, limit=scan_limit
                            )
                            st.write(f"Scanning {len(scan_futures)} files...")
                            scan_results: list[ScanFileResult] = []
                            total_futures = len(scan_futures)
                            try:
                                completed = as_completed(
                                    scan_futures, timeout=SCAN_BATCH_TIMEOUT_SECONDS
                                )
                                for i, future in enumerate(completed):
                                    scan_results.append(future.result())
                                    st.write(f"Scanned {i + 1}/{total_futures} files...")
                            except FuturesTimeoutError as exc:
                                for future in scan_futures:
                                    future.cancel()
                                raise TimeoutError(
                                    "Scan batch exceeded the five-minute limit."
                                ) from exc
                            st.write("Aggregating patterns...")
                            scan_result: ScanResult = api.finalize_scan(scan_results)
                            found_vars = scan_result.variables
                            scanned_vars_dicts = [v.to_dict() for v in found_vars]
                            api.state_manager.set_scanned_variables(scanned_vars_dicts)
                            for failure in scan_result.failures:
                                st.warning(f"Scan failed for {failure.file_path}: {failure.error}")
                            status.update(
                                label=f"Scan complete — {len(found_vars)} variables found",
                                state="complete",
                                expanded=False,
                            )

                        if scan_result.failures:
                            st.toast(
                                f"⚠️ Scan finished with {len(scan_result.failures)} file "
                                f"error(s); found {len(found_vars)} variables.",
                                icon="⚠️",
                            )
                        else:
                            st.toast(
                                f"✅ Scan complete! Found {len(found_vars)} variables.",
                                icon="🔍",
                            )
                        # Release completed futures to free memory (~70MB for 252 files).
                        # Settled-only: never abort another browser session's live scan.
                        api.release_settled_scans()
                        st.rerun()
                    except Exception as e:
                        st.exception(e)
                        logger.error(
                            "SCANNER: Quick scan failed at %r: %s",
                            str(stats_path).replace("\n", ""),
                            e,
                            exc_info=True,
                        )

            scanned_vars: list[ScannedVariableDict] = api.state_manager.get_scanned_variables()
            if scanned_vars:
                st.success(
                    f"Scanner found {len(scanned_vars)} variables. "
                    "Use 'Add Variable' to select them."
                )

            # Variable editor
            variables = api.state_manager.get_parse_variables()
            updated_vars = VariableEditor.render(
                api,
                variables,
                available_variables=scanned_vars,
                stats_path=stats_path,
                stats_pattern=stats_pattern,
            )
            # Only persist when the editor actually changed something to
            # avoid redundant logging + state writes on every rerun.
            if updated_vars != variables:
                api.state_manager.set_parse_variables(updated_vars)

            # Add variable button
            if st.button(
                "➕ Add Variable", help="Add a new variable manually or from scanned list"
            ):
                DataSourceComponents.variable_config_dialog(api)

            # Preview configuration
            st.markdown("#### Configuration Preview")
            parse_config: dict[str, Any] = {
                "parser": selected_sim,
                "statsPath": stats_path,
                "statsPattern": stats_pattern,
                "strategy": api.state_manager.get_parser_strategy(),
                "variables": api.state_manager.get_parse_variables(),
            }
            st.json(parse_config)

        _parser_config_fragment()

        # Parse button — sits outside the fragment so that clicking it causes
        # a full rerun (other page sections can react). Read widget values
        # from session_state because locals from the fragment are not in scope.
        st.markdown("---")
        if st.button(f"Parse {sim_label} Stats Files", type="primary", use_container_width=True):
            _stats_path = st.session_state.get(
                "stats_path_input", api.state_manager.get_stats_path()
            )
            _stats_pattern = st.session_state.get(
                "stats_pattern_input", api.state_manager.get_stats_pattern()
            )
            if not _stats_path:
                st.error("Please specify a stats directory path.")
            else:
                try:
                    safe_stats_path = str(validate_web_stats_path(str(_stats_path)))
                    # Reset state for new run only after validating the source path.
                    output_dir = tempfile.mkdtemp()
                    api.state_manager.set_temp_dir(output_dir)
                    batch = api.submit_parse_async(
                        safe_stats_path,
                        _stats_pattern,
                        api.state_manager.get_parse_variables(),
                        output_dir,
                        scanned_vars=api.state_manager.get_scanned_variables(),
                        strategy_type=api.state_manager.get_parser_strategy(),
                    )
                    DataSourceComponents._show_parse_dialog(api, batch, output_dir)
                except Exception as e:
                    st.exception(e)
                    logger.error("UI: Parsing submission failed: %s", e, exc_info=True)

    @staticmethod
    @st.dialog("Add Variable")
    def variable_config_dialog(api: ApplicationAPI) -> None:
        """Dialog to add a new variable."""
        scanned_vars = api.state_manager.get_scanned_variables() or []

        # 1. Method Selection
        method = st.pills(
            "Addition Method",
            ["Search Scanned Variables", "Manual Entry"],
            default="Search Scanned Variables",
            label_visibility="collapsed",
        )

        name = ""
        var_type = "scalar"
        selected_scanned_var = None
        idx = None

        # 2. Input/Selection Logic
        if method == "Search Scanned Variables":
            if not scanned_vars:
                st.warning("No variables scanned yet. Run 'Scan for Variables' first.")
            else:

                def format_func(v: ScannedVariableDict) -> str:
                    label = f"{v['name']} ({v['type']})"
                    if v["type"] == "vector" and "entries" in v:
                        label += f" [{len(v['entries'])} items]"
                    count = v.get("count", 0)
                    if count > 1:
                        label += f" (Grouped {count}x)"
                    return label

                str_options = [format_func(scanned_vars[i]) for i in range(len(scanned_vars))]
                st.markdown("##### Search Variable")
                selected_label = filtered_selectbox(
                    "Search by name...",
                    str_options,
                    key="dialog_select_var_idx",
                    placeholder="Type to search...",
                )
                idx = str_options.index(selected_label) if selected_label else None

                if idx is not None:
                    selected_scanned_var = scanned_vars[idx]
                    name = selected_scanned_var["name"]
                    var_type = selected_scanned_var["type"]

        else:  # Manual Entry
            st.markdown("##### Variable Details")
            manual_name = st.text_input("Variable Name", key="dialog_manual_name")
            if manual_name:
                name = manual_name
            type_options = ["scalar", "vector", "distribution", "configuration"]
            var_type = st.selectbox("Type", type_options, key="dialog_manual_type")

        # 3. Dynamic Configuration Form
        if method == "Search Scanned Variables" and idx is None:
            st.info("Start typing in the search box above to find a variable.")
        else:
            st.markdown("---")
            st.markdown(f"**Configuration: {var_type.upper()}**")

            if method == "Search Scanned Variables":
                name = st.text_input("Name", value=name, key="dialog_final_name")

            config: ParseVariableConfig = {"name": name, "type": var_type, "_id": ""}
            temp_id = "dialog_new_var"
            defaults: ParseVariableConfig = cast(
                ParseVariableConfig,
                (
                    selected_scanned_var
                    if selected_scanned_var
                    else {"name": "", "type": "", "entries": []}
                ),
            )

            if var_type == "vector":
                VariableEditor.render_vector_config(
                    api=api,
                    var_config=config,
                    original_var=defaults,
                    var_id=temp_id,
                    available_variables=scanned_vars,
                    stats_path=api.state_manager.get_stats_path(),
                    stats_pattern=api.state_manager.get_stats_pattern(),
                )
            elif var_type == "distribution":
                VariableEditor.render_distribution_config(
                    api=api,
                    var_config=config,
                    original_var=defaults,
                    var_id=temp_id,
                    stats_path=api.state_manager.get_stats_path(),
                    stats_pattern=api.state_manager.get_stats_pattern(),
                )
            elif var_type == "configuration":
                VariableEditor.render_configuration_config(
                    var_config=config, original_var=defaults, var_id=temp_id
                )

            with st.expander("Advanced Options"):
                repeat = st.number_input(
                    "Repeat Count",
                    min_value=1,
                    value=1,
                    help="If variable repeats in strict sequence (Perl parser specific)",
                    key="adv_repeat",
                )
                repeat_int = int(repeat)
                if repeat_int > 1:
                    config["repeat"] = str(repeat_int)

            st.write("")
            if st.button("Add to Configuration", type="primary", use_container_width=True):
                if not name:
                    st.error("Variable name is required.")
                elif var_type == "vector" and not config.get("vectorEntries"):
                    st.error("Vector variables require at least one entry.")
                else:
                    # Build new variable from config + dialog fields
                    config["name"] = name
                    config["type"] = var_type
                    config["_id"] = str(uuid.uuid4())
                    new_var: ParseVariableConfig = config
                    current_vars = api.state_manager.get_parse_variables()
                    if api.data_services.has_variable_with_name(current_vars, name):
                        st.warning(f"Variable '{name}' already exists.")
                    else:
                        current_vars.append(new_var)
                        api.state_manager.set_parse_variables(current_vars)
                        st.toast(f"Added '{name}'!", icon="✅")
                        st.rerun()

    @staticmethod
    @st.dialog("Parsing Stats", dismissible=True)
    def _show_parse_dialog(api: ApplicationAPI, batch: ParseBatchResult, output_dir: str) -> None:
        """Render the parsing progress dialog using blocking futures."""
        futures = batch.futures
        st.write(f"Processing {len(futures)} files...")
        progress_bar = st.progress(0, text="Starting...")
        status_text = st.empty()

        results: list[Any] = []
        errors: list[str] = []

        completed_count = 0
        total = len(futures)

        try:
            for future in as_completed(futures):
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception as e:
                    errors.append(str(e))

                completed_count += 1
                if total > 0:
                    pct = min(completed_count / total, 1.0)
                    progress_bar.progress(pct, text=f"Processed {completed_count}/{total}")

        except KeyboardInterrupt:
            # Fallback if something interrupts
            for f in futures:
                f.cancel()
            st.warning("Parsing interrupted.")
            return

        if errors:
            st.error(f"Encountered {len(errors)} errors during parsing.")
            with st.expander("Show Errors"):
                for err in errors:
                    st.write(err)

        if not results and not errors:
            st.warning("No results generated.")
            return

        status_text.empty()

        with st.status("Finalizing results...", expanded=True) as status:
            _loaded_data: Any = None
            _parse_failed = False
            try:
                st.write("Generating CSV output...")
                strategy = api.state_manager.get_parser_strategy()
                csv_path = api.finalize_parsing(
                    output_dir,
                    results,
                    strategy_type=strategy,
                    var_names=batch.var_names,
                )
                if csv_path and Path(csv_path).exists():
                    st.write("Adding to data pool...")
                    pool_path = api.add_to_csv_pool(csv_path)
                    st.write("Loading data into session...")
                    data = api.load_csv_file(pool_path)
                    api.state_manager.set_data(data)
                    api.state_manager.set_csv_path(pool_path)
                    _loaded_data = data
                    status.update(
                        label=f"Complete — {len(data)} rows loaded",
                        state="complete",
                        expanded=False,
                    )
                else:
                    _parse_failed = True
                    status.update(label="Failed", state="error")
                    st.error("Failed to generate final CSV.")
            except Exception as e:
                _parse_failed = True
                status.update(label="Error", state="error")
                st.exception(e)

        # Success message and close button OUTSIDE the status block
        # so they remain visible when the status collapses.
        if _loaded_data is not None and not _parse_failed:
            st.success(f"Done! Generated {len(_loaded_data)} rows.")
            DataComponents.show_missing_data_notice(_loaded_data)
            if st.button("Close & Reload", key="finish_parse_futures_btn"):
                st.rerun()
