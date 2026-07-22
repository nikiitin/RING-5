"""Human-first builder for reproducible HTML and PDF analysis reports."""

from __future__ import annotations

from typing import Literal, cast

import pandas as pd
import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.common.utils import sanitize_filename
from src.core.models import AnalysisReport, ReportFigure
from src.core.services.environment_metadata_service import EnvironmentMetadataService
from src.core.services.report_service import ReportService
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.rendering.report_builder import render_report

_BYTES_KEY = "report.composer.bytes"
_NAME_KEY = "report.composer.name"
_FORMAT_KEY = "report.composer.format"
_SIGNATURE_KEY = "report.composer.signature"


class ReportComposer:
    """Build and download a report from the current workspace."""

    def __init__(self, api: ApplicationAPI) -> None:
        """Store the session-scoped application facade."""
        self._api = api

    def render(self) -> None:
        # [impl->req~ring5.export.batch-reports~1]
        # [impl->req~ring5.export.interactive-gallery~1]
        """Render selected figures, narrative, table, and metadata controls."""
        with st.expander(":material/article: Analysis report", expanded=False):
            st.caption(
                "Package selected figures with plain-language findings, inspectable data, "
                "source provenance, and the exact execution environment."
            )
            plots = cast(list[BasePlot], self._api.state_manager.get_plots())
            if not plots:
                st.info("Create at least one plot before building a report.")
                return

            by_id = {plot.plot_id: plot for plot in plots}
            selected_ids = st.multiselect(
                "Report figures",
                options=list(by_id),
                default=list(by_id)[: min(2, len(by_id))],
                format_func=lambda plot_id: f"{by_id[plot_id].name} · {by_id[plot_id].plot_type}",
                key="report.composer.figures",
            )
            title = st.text_input(
                "Report title", value="Analysis report", key="report.composer.title"
            )
            narrative_heading = st.text_input(
                "Narrative heading", value="Summary", key="report.composer.narrative_heading"
            )
            narrative_text = st.text_area(
                "Narrative text",
                value="",
                placeholder="Explain the result, why it matters, and any caveats.",
                key="report.composer.narrative",
            )

            selected_format = cast(
                Literal["HTML", "PDF"],
                st.radio(
                    "Report format",
                    options=["HTML", "PDF"],
                    horizontal=True,
                    key="report.composer.format_choice",
                ),
            )
            html_mode: Literal["document", "gallery"] = "document"
            if selected_format == "HTML":
                html_experience = st.radio(
                    "HTML experience",
                    options=["Interactive gallery", "Publication document"],
                    captions=[
                        "Live plots with one searchable dataframe per figure.",
                        "Static figures optimized for reading and printing.",
                    ],
                    horizontal=True,
                    key="report.composer.html_experience",
                )
                html_mode = "gallery" if html_experience == "Interactive gallery" else "document"

            data = self._api.state_manager.get_data()
            table_col, limit_col, layout_col = st.columns(3)
            with table_col:
                include_table = st.checkbox(
                    "Include current data table",
                    value=data is not None,
                    disabled=data is None,
                    key="report.composer.include_table",
                )
            with limit_col:
                row_limit = int(
                    st.number_input(
                        "Displayed table rows",
                        min_value=1,
                        max_value=500,
                        value=50,
                        disabled=not include_table,
                        key="report.composer.row_limit",
                    )
                )
            with layout_col:
                if html_mode == "gallery":
                    compose_panel = False
                    st.caption("Gallery mode keeps every selected figure in its own review card.")
                else:
                    compose_panel = st.checkbox(
                        "Combine figures as panels",
                        value=len(selected_ids) > 1,
                        disabled=len(selected_ids) < 2,
                        key="report.composer.panel",
                    )
            current_signature = (
                title,
                tuple(selected_ids),
                narrative_heading,
                narrative_text,
                include_table,
                row_limit,
                compose_panel,
                selected_format,
                html_mode,
                id(data),
                data.shape if data is not None else None,
            )
            if st.button(
                ":material/description: Build report",
                type="primary",
                width="stretch",
                key="report.composer.build",
            ):
                if not selected_ids:
                    st.warning("Select at least one report figure.")
                else:
                    try:
                        report = self._create_report(
                            title=title,
                            selected_ids=list(selected_ids),
                            compose_panel=compose_panel,
                            table=data if include_table else None,
                            narrative_heading=narrative_heading,
                            narrative_text=narrative_text,
                            row_limit=row_limit,
                        )
                        fmt = cast(Literal["html", "pdf"], selected_format.lower())
                        payload = render_report(plots, report, fmt=fmt, html_mode=html_mode)
                    except Exception as exc:
                        st.exception(exc)
                    else:
                        st.session_state[_BYTES_KEY] = payload
                        st.session_state[_FORMAT_KEY] = fmt
                        st.session_state[_NAME_KEY] = sanitize_filename(title) or "analysis-report"
                        st.session_state[_SIGNATURE_KEY] = current_signature

            stored_payload = st.session_state.get(_BYTES_KEY)
            stored_fmt = st.session_state.get(_FORMAT_KEY)
            filename = st.session_state.get(_NAME_KEY)
            rendered_signature = st.session_state.get(_SIGNATURE_KEY)
            if (
                isinstance(stored_payload, bytes)
                and stored_fmt in {"html", "pdf"}
                and isinstance(filename, str)
                and rendered_signature == current_signature
            ):
                artifact = (
                    "Interactive gallery"
                    if stored_fmt == "html" and html_mode == "gallery"
                    else "Report"
                )
                st.success(
                    f"{artifact} ready · {len(selected_ids)} selected figure(s) · "
                    f"{row_limit if include_table else 0} overview-table row limit"
                )
                download_label = (
                    "Download HTML gallery"
                    if stored_fmt == "html" and html_mode == "gallery"
                    else f"Download {str(stored_fmt).upper()} report"
                )
                st.download_button(
                    download_label,
                    data=stored_payload,
                    file_name=f"{filename}.{stored_fmt}",
                    mime="text/html" if stored_fmt == "html" else "application/pdf",
                    width="stretch",
                    key="report.composer.download",
                )
            elif isinstance(stored_payload, bytes):
                st.info("Report settings changed. Build again before downloading.")

    def _create_report(
        self,
        *,
        title: str,
        selected_ids: list[int],
        compose_panel: bool,
        table: pd.DataFrame | None,
        narrative_heading: str,
        narrative_text: str,
        row_limit: int,
    ) -> AnalysisReport:
        """Create an immutable report from current application state."""
        plots = cast(list[BasePlot], self._api.state_manager.get_plots())
        by_id = {plot.plot_id: plot for plot in plots}
        figures: tuple[ReportFigure, ...]
        if compose_panel and len(selected_ids) > 1:
            columns = min(2, len(selected_ids))
            dashboard = self._api.create_dashboard(
                selected_ids,
                title="Selected figures",
                columns=columns,
                rows=(len(selected_ids) + columns - 1) // columns,
                panel_labels="auto",
            )
            figures = (ReportFigure(dashboard.plot_ids, dashboard.title, dashboard=dashboard),)
        else:
            figures = tuple(
                ReportFigure((plot_id,), by_id[plot_id].name) for plot_id in selected_ids
            )

        state = self._api.state_manager
        provenance = ReportService.capture_provenance(
            state.get_data(),
            use_parser=state.is_using_parser(),
            csv_path=state.get_csv_path(),
            stats_path=state.get_stats_path(),
            stats_pattern=state.get_stats_pattern(),
            parse_variables=state.get_parse_variables(),
            history=state.get_portfolio_history(),
        )
        tables = {"Current workspace data": table} if table is not None else None
        narrative = {narrative_heading: narrative_text.strip()} if narrative_text.strip() else None
        return ReportService.create(
            title,
            figures,
            tables=tables,
            narrative=narrative,
            provenance=provenance,
            environment=EnvironmentMetadataService.capture(),
            table_row_limit=row_limit,
        )
