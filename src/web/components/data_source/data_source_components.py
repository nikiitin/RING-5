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

import pandas as pd
import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.common.security_limits import (
    MAX_BROWSER_UPLOAD_BYTES,
    MAX_SCAN_FILES,
    PARSER_PLAYGROUND_TIMEOUT_SECONDS,
    SCAN_BATCH_TIMEOUT_SECONDS,
)
from src.core.common.utils import allowed_web_stats_roots, validate_web_stats_path
from src.core.models import (
    BrowserUpload,
    HttpSource,
    ImportColumnCorrection,
    ImportOptions,
    ImportPreview,
    ParserPlaygroundBatchResult,
    ScanFileResult,
    ScanResult,
    S3Source,
    SshSource,
)
from src.core.models.data_models import ParseVariableConfig, ScannedVariableDict
from src.core.models.import_models import ImportColumnType
from src.core.models.browser_upload_models import BrowserUploadRequest
from src.core.models.remote_source_models import RemoteSource, RemoteSourcePolicy
from src.web.components.common.card_components import CardComponents
from src.web.components.common.data_components import DataComponents
from src.web.components.common.filtered_selector import filtered_selectbox
from src.web.components.data_source.parse_job_status import (
    get_visible_parse_job,
    remember_parse_job,
    render_parse_job_panel,
)
from src.web.components.data_source.variable_editor import VariableEditor

logger = logging.getLogger(__name__)

_IMPORT_PREVIEW_PATH_KEY = "data_source.import_preview_path"
_REMOTE_INSPECTION_KEY = "data_source.remote_inspection"


class DataSourceComponents:
    """UI Components for the Data Source Page."""

    @staticmethod
    def render_browser_upload(api: ApplicationAPI) -> None:
        # [impl->req~ring5.ingestion.browser-upload~1]
        """Validate a browser upload and route it through review or restore confirmation."""
        st.markdown("### Upload data, a portfolio, or a portable bundle")
        st.caption(
            "Files stay out of the workspace until validation finishes and you explicitly "
            "confirm loading or restoration."
        )
        origin = st.segmented_control(
            "Source location",
            options=["This computer", "Remote source"],
            default="This computer",
            key="data_source.upload_origin",
        )
        if origin == "Remote source":
            DataSourceComponents.render_remote_source(api)
            return
        interpretation_labels: dict[str, BrowserUploadRequest] = {
            "Auto detect": "auto",
            "Dataset": "dataset",
            "RING-5 portfolio": "portfolio",
            "Portable bundle": "bundle",
        }
        interpretation = st.selectbox(
            "Interpret upload as",
            options=list(interpretation_labels),
            help=(
                "Use an explicit choice when JSON could be records or a portfolio, "
                "or when selecting a portable bundle."
            ),
            key="data_source.browser_upload_interpretation",
        )
        uploaded = st.file_uploader(
            "Choose CSV, JSON, Excel, RING-5 portfolio, or portable bundle",
            type=["csv", "json", "xlsx", "ring5-bundle"],
            max_upload_size=MAX_BROWSER_UPLOAD_BYTES // (1024 * 1024),
            help=(
                "CSV and tabular JSON/Excel files enter the normal import review. "
                "Modern .xlsx workbooks use their first visible sheet."
            ),
            key="data_source.browser_upload",
        )
        if uploaded is None:
            st.info(
                "Choose a file up to 64 MiB. Accepted names end in .csv, .json, .xlsx, "
                "or .ring5-bundle."
            )
            return

        try:
            inspection = api.inspect_browser_upload(
                uploaded.name,
                uploaded.type or "",
                uploaded.getvalue(),
                interpretation_labels[interpretation],
            )
        except (OSError, TypeError, UnicodeError, ValueError) as exc:
            st.error(f"Upload validation failed: {exc}")
            return

        DataSourceComponents._show_validated_upload(api, inspection)

    @staticmethod
    def render_remote_source(api: ApplicationAPI) -> None:
        # [impl->req~ring5.ingestion.remote-sources~1]
        """Collect adapter configuration without retaining remote credentials."""
        st.markdown("#### Fetch an authorized remote source")
        policy = RemoteSourcePolicy.from_environment()
        if policy.allowed_hosts:
            st.caption("Authorized hosts: " + ", ".join(policy.allowed_hosts))
        else:
            st.warning(
                "Remote access is disabled. Set RING5_ALLOWED_REMOTE_HOSTS on the server "
                "to an explicit comma-separated host allowlist."
            )

        adapter = st.selectbox(
            "Remote adapter",
            options=["HTTPS", "SSH", "S3-compatible"],
            key="data_source.remote_adapter",
        )
        with st.form("data_source.remote_form", clear_on_submit=True):
            file_name = st.text_input(
                "Downloaded filename override (optional)",
                help=(
                    "Use when the remote URL or object key does not end in .csv, .json, "
                    ".xlsx, or .ring5-bundle."
                ),
            )
            source: RemoteSource
            if adapter == "HTTPS":
                url = st.text_input("HTTPS URL")
                bearer_token = st.text_input("Bearer token (optional)", type="password")
                source = HttpSource(
                    url=url,
                    file_name=file_name.strip() or None,
                    bearer_token=bearer_token or None,
                )
            elif adapter == "SSH":
                host = st.text_input("SSH host")
                username = st.text_input("SSH username (optional)")
                port = int(st.number_input("SSH port", min_value=1, max_value=65_535, value=22))
                remote_path = st.text_input("Absolute remote file path")
                identity_file = st.text_input(
                    "Server-side identity file (optional)",
                    help="Leave empty to use the server process's SSH agent and configuration.",
                )
                source = SshSource(
                    host=host,
                    path=remote_path,
                    username=username or None,
                    port=port,
                    identity_file=identity_file or None,
                    file_name=file_name.strip() or None,
                )
            else:
                endpoint = st.text_input("S3-compatible HTTPS endpoint")
                bucket = st.text_input("Bucket")
                key = st.text_input("Object key")
                region = st.text_input("Region", value="us-east-1")
                access_key = st.text_input("Access key (optional)", type="password")
                secret_key = st.text_input("Secret key (optional)", type="password")
                session_token = st.text_input("Session token (optional)", type="password")
                source = S3Source(
                    endpoint=endpoint,
                    bucket=bucket,
                    key=key,
                    region=region,
                    access_key=access_key or None,
                    secret_key=secret_key or None,
                    session_token=session_token or None,
                    file_name=file_name.strip() or None,
                )
            submitted = st.form_submit_button(
                ":material/cloud_download: Fetch and validate",
                type="primary",
                disabled=not policy.allowed_hosts,
                width="stretch",
            )

        if submitted:
            try:
                st.session_state[_REMOTE_INSPECTION_KEY] = api.fetch_remote_source(source, policy)
            except (OSError, TypeError, UnicodeError, ValueError) as exc:
                st.error(f"Remote source validation failed: {exc}")
                st.session_state.pop(_REMOTE_INSPECTION_KEY, None)

        inspection = st.session_state.get(_REMOTE_INSPECTION_KEY)
        if isinstance(inspection, BrowserUpload):
            DataSourceComponents._show_validated_upload(api, inspection)

    @staticmethod
    def _show_validated_upload(api: ApplicationAPI, inspection: BrowserUpload) -> None:
        """Present one validated local or remote upload and its confirmation path."""

        kind_label = {
            "csv": "CSV dataset",
            "json": "JSON dataset",
            "excel": "Excel dataset",
            "portfolio": "RING-5 portfolio",
            "bundle": "RING-5 portable bundle",
        }[inspection.kind]
        st.success(f"Validated {kind_label}: {inspection.file_name}")
        if inspection.origin_display:
            st.caption(f"Fetched from `{inspection.origin_display}`")
        size_col, type_col, digest_col = st.columns(3)
        size_col.metric("Upload size", f"{inspection.size_bytes / 1024:.1f} KiB")
        type_col.metric("Detected type", kind_label)
        digest_col.metric("SHA-256", f"{inspection.source_sha256[:12]}…")

        if inspection.kind == "bundle":
            # [impl->req~ring5.portfolio.portable-bundles~1]
            info = inspection.bundle_info
            if info is None:
                st.error("Validated bundle did not provide an artifact summary.")
                return
            st.markdown("#### Review portable bundle restoration")
            status = info.portfolio_integrity.status
            st.write(
                {
                    "Bundle": info.name,
                    "Portfolio schema": info.portfolio_schema_version,
                    "Sources recorded": info.source_count,
                    "Pinned requirements": info.requirement_count,
                    "Dataset snapshot": (
                        info.dataset_snapshot.name if info.dataset_snapshot else "Not included"
                    ),
                    "Generated results": len(info.result_names),
                    "Portfolio integrity": status.replace("-", " ").title(),
                }
            )
            if info.result_names:
                st.caption("Included results: " + ", ".join(info.result_names))
            bundle_signing_key: str | None = None
            require_signature = status == "signature-unverified"
            if info.portfolio_integrity.key_id:
                st.caption(f"Signing key ID: `{info.portfolio_integrity.key_id}`")
            if require_signature:
                bundle_signing_key = (
                    st.text_input(
                        "Bundle portfolio signing secret",
                        type="password",
                        key=f"data_source.bundle_secret.{inspection.source_sha256}",
                        help="Used only for this restore; the secret is not stored.",
                    )
                    or None
                )
            st.warning(
                "Restoring replaces the current workspace with the bundled portfolio. "
                "Included snapshots and generated results are validated but are not written "
                "to server storage."
            )
            if st.button(
                ":material/package_2: Restore portable bundle",
                type="primary",
                width="stretch",
                key=f"data_source.restore_bundle.{inspection.source_sha256}",
                disabled=require_signature and bundle_signing_key is None,
            ):
                try:
                    report = api.restore_browser_portfolio_bundle(
                        inspection,
                        signing_key=bundle_signing_key,
                        require_signature=require_signature,
                    )
                    if report.complete:
                        st.toast("Portable bundle restored.", icon="✅")
                    else:
                        st.toast("Bundle restored with reported omissions.", icon="⚠️")
                    st.rerun(scope="app")
                except (OSError, TypeError, UnicodeError, ValueError) as exc:
                    st.error(f"Portable bundle restoration failed: {exc}")
            return

        if inspection.kind == "portfolio":
            st.markdown("#### Review portfolio restoration")
            integrity_labels = {
                "legacy-unverified": "Legacy — no manifest",
                "checksum-valid": "Checksums match — unsigned",
                "signature-unverified": "Checksums match — signature needs secret",
                "signature-valid": "Checksums and signature verified",
                "modified": "Modified",
                "signature-invalid": "Signature invalid",
                "invalid-manifest": "Invalid manifest",
            }
            integrity_status = inspection.portfolio_integrity_status
            st.write(
                {
                    "Schema version": inspection.portfolio_schema_version,
                    "Plots": inspection.portfolio_plot_count,
                    "Contains data": "Yes" if inspection.portfolio_has_data else "No",
                    "Integrity": (
                        integrity_labels.get(integrity_status, "Not reported")
                        if integrity_status is not None
                        else "Not reported"
                    ),
                }
            )
            portfolio_signing_key: str | None = None
            require_signature = inspection.portfolio_integrity_status == "signature-unverified"
            if inspection.portfolio_signing_key_id:
                st.caption(f"Signing key ID: `{inspection.portfolio_signing_key_id}`")
            if require_signature:
                portfolio_signing_key = (
                    st.text_input(
                        "Portfolio signing secret",
                        type="password",
                        key=f"data_source.portfolio_secret.{inspection.source_sha256}",
                        help="Used only for this restore; the secret is not stored.",
                    )
                    or None
                )
            st.warning(
                "Restoring replaces the current workspace with the uploaded portfolio. "
                "The upload has been validated but no state has changed yet."
            )
            if st.button(
                ":material/settings_backup_restore: Restore uploaded portfolio",
                type="primary",
                width="stretch",
                key=f"data_source.restore_upload.{inspection.source_sha256}",
                disabled=require_signature and portfolio_signing_key is None,
            ):
                try:
                    report = api.restore_browser_portfolio(
                        inspection,
                        signing_key=portfolio_signing_key,
                        require_signature=require_signature,
                    )
                    if report.complete:
                        st.toast("Uploaded portfolio restored.", icon="✅")
                    else:
                        st.toast("Portfolio restored with reported omissions.", icon="⚠️")
                    st.rerun(scope="app")
                except (OSError, TypeError, UnicodeError, ValueError) as exc:
                    st.error(f"Portfolio restoration failed: {exc}")
            return

        row_count = inspection.row_count if inspection.row_count is not None else 0
        detail = f"{row_count:,} source row(s) · {len(inspection.columns)} column(s)"
        if inspection.sheet_name:
            detail += f" · worksheet {inspection.sheet_name!r}"
        st.caption(detail)
        if inspection.import_path is None:
            st.error("Validated dataset did not produce a reviewable table.")
            return
        DataSourceComponents.render_import_preview(api, inspection.import_path)

    @staticmethod
    def render_csv_pool(api: ApplicationAPI) -> None:
        """Display and manage the CSV pool."""
        # [impl->req~ring5.ingestion.csv-pool~1]
        # [impl->req~ring5.ingestion.import-preview~1]
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

        requested_preview: str | None = None
        for idx, csv_info in enumerate(csv_pool):
            csv_path = Path(csv_info["path"])

            if not csv_path.exists():
                st.error(f"File no longer exists: {csv_info['name']}")
                logger.warning("CSV POOL: File not found on disk: %s", csv_info["path"])
                continue

            load_clicked, preview_clicked, delete_clicked = CardComponents.file_info_card(
                csv_info, idx
            )

            if load_clicked or preview_clicked:
                requested_preview = str(csv_path)
                st.session_state[_IMPORT_PREVIEW_PATH_KEY] = requested_preview

            if delete_clicked:
                if api.delete_from_csv_pool(str(csv_path)):
                    st.toast("File deleted!", icon="🗑️")
                    st.rerun()
                else:
                    st.error("Error deleting file")
                    logger.error("CSV POOL: Failed to delete metadata for: %s", csv_path)

        preview_path = requested_preview or st.session_state.get(_IMPORT_PREVIEW_PATH_KEY)
        if isinstance(preview_path, str):
            available_paths = {str(Path(entry["path"])) for entry in csv_pool}
            if preview_path in available_paths and Path(preview_path).exists():
                DataSourceComponents.render_import_preview(api, preview_path)
            else:
                st.session_state.pop(_IMPORT_PREVIEW_PATH_KEY, None)

    @staticmethod
    def render_import_preview(api: ApplicationAPI, file_path: str) -> None:
        # [impl->req~ring5.ingestion.import-preview~1]
        """Render detected structure, corrections, row outcomes, and reviewed loading."""
        st.markdown("---")
        st.markdown("### Review tabular import")
        st.caption(
            "Inspect the detected format and row outcomes. Corrections are applied to the "
            "preview before any data enters the workspace."
        )

        encoding_labels: dict[str, str | None] = {
            "Auto detect": None,
            "UTF-8": "utf-8",
            "UTF-8 with BOM": "utf-8-sig",
            "Windows-1252": "cp1252",
            "Latin-1": "latin-1",
        }
        delimiter_labels: dict[str, str | None] = {
            "Auto detect": None,
            "Comma (,)": ",",
            "Semicolon (;)": ";",
            "Tab": "\t",
            "Pipe (|)": "|",
        }
        format_col, delimiter_col, header_col = st.columns(3)
        with format_col:
            encoding_label = st.selectbox(
                "Text encoding",
                options=list(encoding_labels),
                key="data_source.import_encoding",
            )
        with delimiter_col:
            delimiter_label = st.selectbox(
                "Delimiter",
                options=list(delimiter_labels),
                key="data_source.import_delimiter",
            )
        with header_col:
            header_row = int(
                st.number_input(
                    "Header row",
                    min_value=1,
                    max_value=100,
                    value=1,
                    key="data_source.import_header_row",
                )
            )
        trim_whitespace = st.checkbox(
            "Trim surrounding whitespace",
            value=True,
            key="data_source.import_trim",
        )
        missing_text = st.text_input(
            "Missing-value tokens (comma-separated)",
            value=",NA,N/A,null,None",
            key="data_source.import_null_values",
        )
        preview_rows = int(
            st.number_input(
                "Accepted rows to display",
                min_value=1,
                max_value=500,
                value=50,
                key="data_source.import_preview_rows",
            )
        )
        null_values = tuple(value.strip() for value in missing_text.split(","))

        try:
            base_options = ImportOptions(
                encoding=encoding_labels[encoding_label],
                delimiter=delimiter_labels[delimiter_label],
                header_row=header_row,
                trim_whitespace=trim_whitespace,
                null_values=null_values,
                preview_rows=preview_rows,
            )
            base_preview = api.preview_import(file_path, base_options)
            type_table = pd.DataFrame(
                {
                    "Column": [column.name for column in base_preview.columns],
                    "Inferred": [column.inferred_type.title() for column in base_preview.columns],
                    "Import as": ["Auto" for _column in base_preview.columns],
                    "Allows missing": [column.nullable for column in base_preview.columns],
                }
            )
            edited_types = st.data_editor(
                type_table,
                hide_index=True,
                width="stretch",
                disabled=["Column", "Inferred", "Allows missing"],
                column_config={
                    "Import as": st.column_config.SelectboxColumn(
                        options=["Auto", "Text", "Integer", "Number", "Boolean", "Datetime"],
                        required=True,
                    )
                },
                key=f"data_source.import_types.{base_preview.source_sha256}",
            )
            corrections = tuple(
                ImportColumnCorrection(
                    str(row["Column"]),
                    cast(ImportColumnType, str(row["Import as"]).lower()),
                )
                for row in edited_types.to_dict("records")
                if str(row["Import as"]) != "Auto"
            )
            options = ImportOptions(
                encoding=base_options.encoding,
                delimiter=base_options.delimiter,
                header_row=base_options.header_row,
                trim_whitespace=base_options.trim_whitespace,
                null_values=base_options.null_values,
                column_types=corrections,
                preview_rows=base_options.preview_rows,
            )
            preview = api.preview_import(file_path, options) if corrections else base_preview
        except Exception as exc:
            st.exception(exc)
            return

        DataSourceComponents._show_import_preview_result(api, preview)

    @staticmethod
    def _show_import_preview_result(api: ApplicationAPI, preview: ImportPreview) -> None:
        """Present one corrected preview and its explicit load action."""
        delimiter_name = {",": "comma", ";": "semicolon", "\t": "tab", "|": "pipe"}[
            preview.delimiter
        ]
        st.info(
            f"Detected **{preview.encoding}** text with a **{delimiter_name}** delimiter · "
            f"SHA-256 `{preview.source_sha256[:12]}…`"
        )
        accepted_col, rejected_col, total_col = st.columns(3)
        accepted_col.metric("Accepted rows", preview.accepted_row_count)
        rejected_col.metric("Rejected rows", preview.rejected_row_count)
        total_col.metric("Total rows", preview.total_row_count)

        st.markdown("#### Accepted-row preview")
        accepted_table = pd.DataFrame(
            preview.rows,
            columns=[column.name for column in preview.columns],
        )
        st.dataframe(accepted_table, width="stretch", hide_index=True)
        if preview.preview_truncated:
            st.caption(
                f"Showing {len(preview.rows)} of {preview.accepted_row_count} accepted rows."
            )

        if preview.rejected_row_count:
            st.markdown("#### Rejected rows")
            st.warning(
                f"{preview.rejected_row_count} row(s) will not be loaded. "
                "Correct their source values or adjust the reviewed types."
            )
            st.dataframe(
                pd.DataFrame(
                    {
                        "Line": [row.line_number for row in preview.rejected_rows],
                        "Reason": [row.reason for row in preview.rejected_rows],
                        "Source values": [" | ".join(row.values) for row in preview.rejected_rows],
                    }
                ),
                width="stretch",
                hide_index=True,
            )
            if preview.rejection_details_truncated:
                st.caption(
                    f"Showing {len(preview.rejected_rows)} of "
                    f"{preview.rejected_row_count} rejected rows."
                )
        else:
            st.success("Every data row is accepted by the reviewed import settings.")

        load_col, close_col = st.columns(2)
        with load_col:
            if st.button(
                ":material/download: Load accepted rows",
                type="primary",
                disabled=preview.accepted_row_count == 0,
                width="stretch",
                key="data_source.import_load",
            ):
                try:
                    data = api.load_import_preview(preview)
                    st.success(f"Loaded {len(data)} reviewed rows!")
                    DataComponents.show_data_preview(data, "Loaded import preview")
                    DataComponents.show_column_details(data)
                    st.info("Data loaded! Proceed to **Configure Pipeline** to process it.")
                except Exception as exc:
                    st.exception(exc)
        with close_col:
            if st.button(
                "Close review",
                width="stretch",
                key="data_source.import_close",
            ):
                st.session_state.pop(_IMPORT_PREVIEW_PATH_KEY, None)
                st.rerun()

    @staticmethod
    def render_parser_config(api: ApplicationAPI) -> None:
        """Display parser configuration interface."""
        # [impl->req~ring5.ingestion.parser-playground~1]
        # [impl->req~ring5.ingestion.incremental-parsing~1]
        # [impl->req~ring5.ingestion.scan-presets-progress~1]
        # [impl->req~ring5.ingestion.web-path-authorization~1]
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

        render_parse_job_panel(api)

        incremental_enabled = st.checkbox(
            "Reuse unchanged simulator files",
            value=True,
            help=(
                "Fingerprint all matching inputs, parse only new or changed files, and remove "
                "rows whose source files were deleted. The cache stays beside the generated "
                "CSV and is invalidated when parser settings change."
            ),
            key="parser_incremental_enabled",
        )

        # The entire parser config section (file inputs, strategy radio,
        # variable editor, scan button, config preview) is wrapped in a
        # single @st.fragment so that typing in text inputs or changing the
        # strategy radio only reruns this fragment — NOT the full page.
        @st.fragment
        def _parser_config_fragment() -> None:
            st.markdown("#### File Location")
            allowed_roots = ", ".join(str(root) for root in allowed_web_stats_roots())
            st.caption(f"Allowed statistics roots: {allowed_roots}")
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
                "incremental": incremental_enabled,
                "variables": api.state_manager.get_parse_variables(),
            }
            st.json(parse_config)

        _parser_config_fragment()

        # Actions sit outside the fragment so their dialogs can own the complete
        # async lifecycle. Read widget values from session_state because locals
        # from the fragment are not in scope.
        st.markdown("---")
        visible_job = get_visible_parse_job(api)
        test_col, parse_col = st.columns(2)
        with test_col:
            test_configuration = st.button(
                ":material/science: Test configuration",
                help="Run the real parser on up to three matching files without loading data.",
                width="stretch",
                key="parser_test_configuration",
                disabled=visible_job is not None and visible_job.status.is_active,
            )
        with parse_col:
            parse_configuration = st.button(
                f"Parse {sim_label} Stats Files",
                type="primary",
                width="stretch",
                disabled=visible_job is not None,
                help=(
                    "Retry, load, or dismiss the current parse attempt first."
                    if visible_job is not None
                    else None
                ),
            )

        if test_configuration:
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
                    session_dir = api.state_manager.get_temp_dir()
                    if not session_dir:
                        session_dir = tempfile.mkdtemp(prefix="ring5-session-")
                        api.state_manager.set_temp_dir(session_dir)
                    output_path = Path(session_dir) / "parser_playground"
                    output_path.mkdir(parents=True, exist_ok=True)
                    playground_batch = api.submit_parser_playground_async(
                        safe_stats_path,
                        str(_stats_pattern),
                        api.state_manager.get_parse_variables(),
                        str(output_path),
                        scanned_vars=api.state_manager.get_scanned_variables(),
                        strategy_type=api.state_manager.get_parser_strategy(),
                    )
                    DataSourceComponents._show_parser_playground_dialog(api, playground_batch)
                except Exception as exc:
                    st.exception(exc)

        if parse_configuration:
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
                    incremental = bool(st.session_state.get("parser_incremental_enabled", True))
                    snapshot = api.submit_parse_job(
                        safe_stats_path,
                        str(_stats_pattern),
                        api.state_manager.get_parse_variables(),
                        scanned_vars=api.state_manager.get_scanned_variables(),
                        strategy_type=api.state_manager.get_parser_strategy(),
                        simulator=selected_sim,
                        incremental=incremental,
                    )
                    remember_parse_job(snapshot)
                    st.toast("Parsing started in the background.", icon="⏳")
                    st.rerun()
                except Exception as e:
                    st.exception(e)
                    logger.error("UI: Parsing submission failed: %s", e, exc_info=True)

    @staticmethod
    @st.dialog("Parser configuration test", dismissible=True)
    def _show_parser_playground_dialog(
        api: ApplicationAPI,
        batch: ParserPlaygroundBatchResult,
    ) -> None:
        # [impl->req~ring5.ingestion.parser-playground~1]
        """Show bounded real-parser output without loading or retaining it."""
        futures = batch.futures
        st.write(
            f"Testing {len(futures)} of {batch.matched_file_count} matching files "
            "in lexical order."
        )
        progress = st.progress(0, text="Starting parser workers...")
        errors: list[str] = []
        try:
            for completed_count, future in enumerate(
                as_completed(futures, timeout=PARSER_PLAYGROUND_TIMEOUT_SECONDS), start=1
            ):
                try:
                    future.result()
                except Exception as exc:
                    errors.append(str(exc))
                progress.progress(
                    completed_count / len(futures),
                    text=f"Processed {completed_count}/{len(futures)} sampled files",
                )
        except FuturesTimeoutError:
            cancelled = sum(future.cancel() for future in futures if not future.done())
            st.error(
                "Configuration test exceeded the two-minute limit; cancellation was requested "
                f"for unfinished work ({cancelled} pending task(s) cancelled)."
            )
            return

        if errors:
            st.error(f"The sampled parser run encountered {len(errors)} error(s).")
            with st.expander("Show parser errors"):
                for error in errors:
                    st.write(error)
            return

        try:
            ordered_results = [future.result() for future in futures]
            result = api.finalize_parser_playground(batch, ordered_results)
        except Exception as exc:
            st.exception(exc)
            return

        matched_col, sampled_col, columns_col = st.columns(3)
        matched_col.metric("Matching files", result.matched_file_count)
        sampled_col.metric("Files tested", len(result.sampled_files))
        columns_col.metric("Output columns", len(result.columns))

        with st.expander("Sampled files", expanded=False):
            for file_path in result.sampled_files:
                st.code(file_path, language=None)

        st.markdown("#### Sample output")
        st.dataframe(
            pd.DataFrame(result.rows, columns=result.columns),
            hide_index=True,
            width="stretch",
        )
        if result.missing_variables:
            st.warning("Missing sampled values: " + ", ".join(result.missing_variables))
        for diagnostic in result.diagnostics:
            st.caption(diagnostic)
        if result.ready_for_full_parse:
            st.success("Ready for a full parse.")
        else:
            st.warning("Review the diagnostics before starting a full parse.")

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
            if st.button("Add to Configuration", type="primary", width="stretch"):
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
