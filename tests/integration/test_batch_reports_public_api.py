"""Public API coverage for deterministic HTML and PDF analysis reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import ring5

pytestmark = pytest.mark.public_api


def _workspace(session: ring5.Session, tmp_path: Path) -> tuple[pd.DataFrame, Any, Any]:
    csv_path = tmp_path / "measurements.csv"
    csv_path.write_text("benchmark,ipc\na,1.0\nb,1.4\nc,1.2\n<script>,0.8\n", encoding="utf-8")
    data = session.load(str(csv_path))
    bar = session.create_plot(
        "bar", data=data, config={"x": "benchmark", "y": "ipc"}, name="IPC bars"
    )
    line = session.create_plot(
        "line", data=data, config={"x": "benchmark", "y": "ipc"}, name="IPC trend"
    )
    return data, bar, line


def test_report_contains_every_content_type_and_is_byte_stable(tmp_path: Path) -> None:
    # [test->req~ring5.export.batch-reports~1]
    with ring5.Session() as session:
        data, bar, line = _workspace(session, tmp_path)
        original = data.copy(deep=True)
        dashboard = session.create_dashboard(
            [bar, line], title="Comparison panels", columns=2, panel_labels="auto"
        )
        report = session.create_report(
            "CPU performance review",
            [bar, dashboard],
            tables={"Selected measurements": data},
            narrative={"Executive finding": "IPC improved for <script>alert('unsafe')</script>."},
            figure_captions=["Individual result.", "Side-by-side comparison."],
            table_row_limit=2,
        )

        html_first = session.report_bytes(report, "html")
        html_second = session.report_bytes(report, "html")
        pdf_first = session.report_bytes(report, "pdf")
        pdf_second = session.report_bytes(report, "pdf")

        html_path = tmp_path / "reports" / "review.html"
        pdf_path = tmp_path / "reports" / "review.pdf"
        assert session.export_report(report, str(html_path), fmt="html") == str(html_path)
        assert session.export_report(report, str(pdf_path)) == str(pdf_path)

    assert isinstance(report, ring5.AnalysisReport)
    assert isinstance(report.figures[0], ring5.ReportFigure)
    assert isinstance(report.tables[0], ring5.ReportTable)
    assert isinstance(report.narrative[0], ring5.ReportNarrative)
    assert isinstance(report.provenance, ring5.ReportProvenance)
    assert report.provenance.source_kind == "CSV"
    assert report.provenance.source_location.endswith("measurements.csv")
    assert report.tables[0].truncated is True
    assert html_first == html_second == html_path.read_bytes()
    assert pdf_first == pdf_second == pdf_path.read_bytes()
    assert html_first.startswith(b"<!doctype html>")
    assert html_first.count(b"data:image/png;base64,") == 2
    assert b"&lt;script&gt;" in html_first
    assert b"<script>alert" not in html_first
    assert b"Data provenance" in html_first
    assert b"Execution environment" in html_first
    assert b"Showing 2 of 4 rows" in html_first
    assert pdf_first.startswith(b"%PDF-")
    assert pdf_first.count(b"/Type /Page") >= 6
    pd.testing.assert_frame_equal(data, original)


def test_report_validation_and_export_failures_are_typed(tmp_path: Path) -> None:
    with ring5.Session() as session:
        data, bar, line = _workspace(session, tmp_path)
        report = session.create_report("Valid", [line.plot_id])
        assert report.figures[0].plot_ids == (line.plot_id,)

        with pytest.raises(ring5.DataValidationError, match="needs from 1"):
            session.create_report("Empty", [])
        with pytest.raises(ring5.DataValidationError, match="figure_captions"):
            session.create_report("Bad captions", [bar], figure_captions=[])
        with pytest.raises(ring5.DataValidationError, match="not registered"):
            session.create_report("Unknown", [999])
        missing_dashboard = ring5.DashboardSpec(
            plot_ids=(998, 999),
            rows=1,
            columns=2,
            panel_titles=("Missing A", "Missing B"),
        )
        with pytest.raises(ring5.DataValidationError, match="dashboard plots"):
            session.create_report("Unknown dashboard", [missing_dashboard])
        with pytest.raises(ring5.DataValidationError, match="row_limit"):
            session.create_report("Bad limit", [bar], tables={"Data": data}, table_row_limit=0)
        with pytest.raises(ring5.ExportError, match="analysis report"):
            session.report_bytes(report, "docx")  # type: ignore[arg-type]
        with pytest.raises(ring5.ExportError, match="HTML or PDF"):
            session.export_report(report, str(tmp_path / "report.unknown"))
        with pytest.raises(ring5.ExportError, match="Could not write"):
            session.export_report(report, str(tmp_path), fmt="html")

        session.api.state_manager.set_plots([])
        with pytest.raises(ring5.ExportError, match="no longer available"):
            session.report_bytes(report, "html")
        with pytest.raises(ring5.ExportError, match="no longer available"):
            session.export_report(report, str(tmp_path / "missing.html"))
