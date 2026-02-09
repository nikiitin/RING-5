"""
Data Source Components - UI for Data Ingestion and Parsing.

Provides Streamlit components for gem5 statistics parsing: CSV pool management,
parser configuration, variable selection, and data preview.
"""

import logging
import tempfile
import uuid
from concurrent.futures import as_completed
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.parsing.models import ScannedVariable
from src.web.pages.ui.components.card_components import CardComponents
from src.web.pages.ui.components.data_components import DataComponents
from src.web.pages.ui.components.variable_editor import VariableEditor

logger = logging.getLogger(__name__)


class DataSourceComponents:
    """UI Components for the Data Source Page."""

    @staticmethod
    def render_csv_pool(api: ApplicationAPI) -> None:
        """Display and manage the CSV pool."""
        st.markdown("---")
        st.markdown("### Recent CSV Files")

        # Reload pool
        csv_pool = api.load_csv_pool()
        api.state_manager.set_csv_pool(csv_pool)

        if not csv_pool:
            st.warning("No CSV files in the pool yet. Parse some gem5 stats to populate this list.")
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
                    st.error(f"Error loading file: {e}")
                    logger.error(
                        "CSV POOL: Failed to load CSV file '%s': %s", csv_path, e, exc_info=True
                    )

            if preview_clicked:
                try:
                    preview_data = api.load_csv_file(str(csv_path))
                    st.dataframe(preview_data.head(5))
                except Exception as e:
                    st.error(f"Error previewing file: {e}")

            if delete_clicked:
                if api.delete_from_csv_pool(str(csv_path)):
                    st.success("File deleted!")
                    st.rerun()
                else:
                    st.error("Error deleting file")
                    logger.error("CSV POOL: Failed to delete metadata for: %s", csv_path)

    @staticmethod
    def render_parser_config(api: ApplicationAPI) -> None:
        """Display parser configuration interface."""
        st.markdown("---")
        st.markdown("### gem5 Stats Parser Configuration")

        st.markdown("#### File Location")
        col1, col2 = st.columns(2)
        with col1:
            # Use StateManager for persistence
            current_path = api.state_manager.get_stats_path()
            stats_path = st.text_input(
                "Stats directory path",
                value=current_path,
                help="Directory containing gem5 stats files (can include subdirectories)",
                key="stats_path_input",
            )
            # Explicitly set state to ensure persistence across reruns
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
        strategy_options = {
            "simple": "Simple (stats.txt only)",
            "config_aware": "Config-Aware (Integrates config.ini)",
        }

        selected_strategy = st.radio(
            "Select ingestion strategy:",
            options=list(strategy_options.keys()),
            format_func=lambda x: strategy_options[x],
            index=list(strategy_options.keys()).index(current_strategy),
            help="Config-Aware strategy allows extracting metadata from simulation config files.",
            key="parser_strategy_selector",
        )

        if selected_strategy != current_strategy:
            api.state_manager.set_parser_strategy(selected_strategy)

        # Variables configuration
        st.markdown("#### Variables to Extract")
        st.markdown("""
        Define which variables to extract from gem5 stats files:
        - **Scalar**: Single numeric values (e.g., simTicks, IPC)
        - **Vector**: Arrays of values with specified entries
        - **Distribution**: Statistical distributions with min/max range
        - **Configuration**: Metadata (benchmark name, config ID, seed)
        """)

        # Scanner UI
        col_scan1, col_scan2 = st.columns([1, 3])
        with col_scan1:
            deep_scan = st.checkbox(
                "Deep Scan (check all files)", help="Scan ALL files for variables (slower)"
            )
            if st.button("🔍 Quick Scan", help="Scan files to auto-discover variables"):
                try:
                    # Submit async scan with limit based on checkbox
                    scan_limit = -1 if deep_scan else 10
                    with st.spinner(f"{'Deep' if deep_scan else 'Quick'} scanning..."):
                        scan_futures = api.submit_scan_async(
                            stats_path, stats_pattern, limit=scan_limit
                        )
                        # Wait for scan to complete
                        scan_results = [f.result() for f in scan_futures]
                        # Process and store results - returns List[ScannedVariable]
                        scanned_vars_result: List[ScannedVariable] = api.finalize_scan(scan_results)
                        # Convert to dict format for StateManager
                        scanned_vars_dicts = [v.to_dict() for v in scanned_vars_result]
                        api.state_manager.set_scanned_variables(scanned_vars_dicts)

                    st.success(f"✅ Scan complete! Found {len(scanned_vars_result)} variables.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Scan failed: {e}")
                    logger.error(
                        "SCANNER: Quick scan failed at %r: %s",
                        str(stats_path).replace("\n", ""),
                        e,
                        exc_info=True,
                    )

        scanned_vars: List[Dict[str, Any]] = api.state_manager.get_scanned_variables()
        if scanned_vars:
            st.success(
                f"Scanner found {len(scanned_vars)} variables. Use 'Add Variable' to select them."
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
        api.state_manager.set_parse_variables(updated_vars)

        # Add variable button
        if st.button("➕ Add Variable", help="Add a new variable manually or from scanned list"):
            DataSourceComponents.variable_config_dialog(api)

        # Preview configuration
        st.markdown("#### Configuration Preview")
        parse_config = {
            "parser": "gem5_stats",
            "statsPath": stats_path,
            "statsPattern": stats_pattern,
            "strategy": api.state_manager.get_parser_strategy(),
            "variables": api.state_manager.get_parse_variables(),
        }
        st.json(parse_config)

        # Parse button
        st.markdown("---")
        if st.button("Parse gem5 Stats Files", type="primary", use_container_width=True):
            if not stats_path:
                st.error("Please specify a stats directory path.")
            else:
                # Reset state for new run
                output_dir = tempfile.mkdtemp()
                api.state_manager.set_temp_dir(output_dir)

                try:
                    futures = api.submit_parse_async(
                        stats_path,
                        stats_pattern,
                        api.state_manager.get_parse_variables(),
                        output_dir,
                        scanned_vars=api.state_manager.get_scanned_variables(),
                        strategy_type=api.state_manager.get_parser_strategy(),
                    )
                    DataSourceComponents._show_parse_dialog(api, futures, output_dir)
                except Exception as e:
                    st.error(f"Failed to submit parsing job: {e}")
                    logger.error("UI: Parsing submission failed: %s", e, exc_info=True)

    @staticmethod
    @st.dialog("Add Variable")
    def variable_config_dialog(api: ApplicationAPI) -> None:
        """Dialog to add a new variable."""
        scanned_vars = api.state_manager.get_scanned_variables() or []

        # 1. Method Selection
        method = st.radio(
            "Addition Method",
            ["Search Scanned Variables", "Manual Entry"],
            horizontal=True,
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

                def format_func(v: Any) -> str:
                    label = f"{v['name']} ({v['type']})"
                    if v["type"] == "vector" and "entries" in v:
                        label += f" [{len(v['entries'])} items]"
                    if "count" in v and v["count"] > 1:
                        label += f" (Grouped {v['count']}x)"
                    return label

                options = range(len(scanned_vars))
                st.markdown("##### Search Variable")
                idx = st.selectbox(
                    "Search by name...",
                    options,
                    format_func=lambda i: format_func(scanned_vars[i]),
                    key="dialog_select_var_idx",
                    placeholder="Type to search...",
                    index=None,
                )

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

            config = {}
            temp_id = "dialog_new_var"
            defaults = selected_scanned_var if selected_scanned_var else {}

            config["name"] = name

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
                repeat_int = int(repeat) if repeat is not None else 1
                if repeat_int > 1:
                    config["repeat"] = str(repeat_int)

            st.write("")
            if st.button("Add to Configuration", type="primary", use_container_width=True):
                if not name:
                    st.error("Variable name is required.")
                elif var_type == "vector" and not config.get("vectorEntries"):
                    st.error("Vector variables require at least one entry.")
                else:
                    new_var = {
                        "name": name,
                        "type": var_type,
                        "id": None,
                        "_id": str(uuid.uuid4()),
                        **config,
                    }
                    current_vars = api.state_manager.get_parse_variables()
                    if any(v["name"] == name for v in current_vars):
                        st.warning(f"Variable '{name}' already exists.")
                    else:
                        current_vars.append(new_var)
                        api.state_manager.set_parse_variables(current_vars)
                        st.success(f"Added '{name}'!")
                        st.rerun()

    @staticmethod
    @st.dialog("Parsing gem5 Stats", dismissible=True)
    def _show_parse_dialog(api: ApplicationAPI, futures: List[Any], output_dir: str) -> None:
        """Render the parsing progress dialog using blocking futures."""
        st.write(f"Processing {len(futures)} files...")
        progress_bar = st.progress(0, text="Starting...")
        status_text = st.empty()

        results = []
        errors = []

        # User defined rule: "futures could be asked for only once... use these in the UI"
        completed_count = 0
        total = len(futures)

        # Note: We cannot easily use a 'Stop' button inside a blocking loop in Streamlit
        # without some trickery, but we can check a session state flag or just rely on
        # the user closing the dialog (which might not kill threads, but user said "call cancel_parse").  # noqa: E501
        # If we block here, `st.button` inside the loop won't work well.
        # However, `as_completed` is an iterator. We can iterate it.

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

        status_text.text("Finalizing CSV...")

        try:
            strategy = api.state_manager.get_parser_strategy()
            csv_path = api.finalize_parsing(output_dir, results, strategy_type=strategy)
            if csv_path and Path(csv_path).exists():
                pool_path = api.add_to_csv_pool(csv_path)
                data = api.load_csv_file(pool_path)
                api.state_manager.set_data(data)
                api.state_manager.set_csv_path(pool_path)
                st.success(f"Done! Generated {len(data)} rows.")
                if st.button("Close & Reload", key="finish_parse_futures_btn"):
                    st.rerun()
            else:
                st.error("Failed to generate final CSV.")
        except Exception as e:
            st.error(f"Finalization failed: {e}")
