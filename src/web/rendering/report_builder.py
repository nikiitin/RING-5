"""Deterministic, self-contained HTML and PDF analysis reports."""

from __future__ import annotations

import base64
import io
import textwrap
from collections.abc import Sequence
from datetime import datetime, timezone
from html import escape
from typing import Literal, cast

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure as MplFigure

from src.core.models.report_models import AnalysisReport, ReportFigure, ReportTable
from src.core.services.managers.semantic_metadata_service import SemanticMetadataService
from src.core.services.visualization.accessibility_service import AccessibilityService
from src.web.pages.ui.plotting.base_plot import BasePlot, _relabel_traces
from src.web.rendering.dashboard_builder import render_dashboard
from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_traces

ReportFormat = Literal["html", "pdf"]


def _single_plot_figure(plot: BasePlot) -> MplFigure:
    """Render one plot through the engine-independent Matplotlib path."""
    if plot.processed_data is None:
        raise ValueError(f"Report plot '{plot.name}' has no processed data.")
    effective = SemanticMetadataService.enrich_figure_config(plot.processed_data, plot.config)
    effective = AccessibilityService.apply_defaults(effective, plot.plot_type)
    traces = plot.create_traces(plot.processed_data, effective)
    traces = AccessibilityService.apply_non_color_encodings(traces, effective)
    traces = _relabel_traces(traces, effective.get("legend_labels"))
    figure, _spec = build_matplotlib_figure_from_traces(effective, plot.plot_type, traces)
    return figure


def _figure_png(plots: Sequence[BasePlot], by_id: dict[int, BasePlot], item: ReportFigure) -> bytes:
    """Render one report figure to deterministic PNG bytes."""
    if item.dashboard is None:
        figure = _single_plot_figure(by_id[item.plot_ids[0]])
    else:
        figure = cast(
            MplFigure,
            render_dashboard(plots, item.dashboard, engine="matplotlib"),
        )
    output = io.BytesIO()
    try:
        figure.savefig(
            output,
            format="png",
            dpi=144,
            bbox_inches="tight",
            facecolor=figure.get_facecolor(),
            metadata={"Software": "RING-5"},
        )
        return output.getvalue()
    finally:
        plt.close(figure)


def _environment_rows(report: AnalysisReport) -> list[tuple[str, str, str]]:
    """Flatten captured environment metadata for both output formats."""
    environment = report.environment
    rows = [
        ("Runtime", "RING-5", environment.ring5_version),
        ("Runtime", "Python", environment.python_version),
        ("Runtime", "Python implementation", environment.python_implementation),
        ("Platform", "Operating system", environment.operating_system),
        ("Platform", "Architecture", environment.architecture),
    ]
    rows.extend(
        ("Dependency", name, version or "Not available")
        for name, version in environment.dependencies.items()
    )
    rows.extend(
        ("Renderer", name, version or "Not available")
        for name, version in environment.renderers.items()
    )
    rows.extend(
        ("External tool", name, version or "Not available")
        for name, version in environment.external_tools.items()
    )
    return rows


def _provenance_rows(report: AnalysisReport) -> list[tuple[str, str]]:
    """Return ordered provenance facts."""
    provenance = report.provenance
    return [
        ("Source type", provenance.source_kind),
        ("Source", provenance.source_location),
        ("Data SHA-256", provenance.data_sha256),
        ("Rows", str(provenance.row_count)),
        ("Columns", str(provenance.column_count)),
        ("Column names", ", ".join(provenance.columns) or "None"),
        ("Parser variables", ", ".join(provenance.parser_variables) or "None"),
        ("Operations", " → ".join(provenance.operations) or "None"),
    ]


def _html_table(table: ReportTable) -> str:
    """Render one escaped report table."""
    headings = "".join(f'<th scope="col">{escape(column)}</th>' for column in table.columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in row) + "</tr>"
        for row in table.rows
    )
    note = (
        f'<p class="table-note">Showing {len(table.rows)} of {table.total_rows} rows.</p>'
        if table.truncated
        else f'<p class="table-note">{table.total_rows} rows.</p>'
    )
    return (
        f'<section class="report-table"><h2>{escape(table.title)}</h2>{note}'
        f'<div class="table-scroll"><table><thead><tr>{headings}</tr></thead>'
        f"<tbody>{body}</tbody></table></div></section>"
    )


def _html_report(report: AnalysisReport, images: Sequence[bytes]) -> bytes:
    """Build a standalone, accessible HTML document."""
    narrative = "".join(
        f"<section><h2>{escape(item.heading)}</h2>"
        f"<p class=\"narrative\">{escape(item.text).replace(chr(10), '<br>')}</p></section>"
        for item in report.narrative
    )
    figures = "".join(
        f"<figure><h2>{escape(item.title)}</h2>"
        f'<img alt="{escape(item.title)}" src="data:image/png;base64,'
        f"{base64.b64encode(image).decode('ascii')}\">"
        f"<figcaption>{escape(item.caption)}</figcaption></figure>"
        for item, image in zip(report.figures, images, strict=True)
    )
    tables = "".join(_html_table(table) for table in report.tables)
    provenance = "".join(
        f'<tr><th scope="row">{escape(label)}</th><td>{escape(value)}</td></tr>'
        for label, value in _provenance_rows(report)
    )
    environment = "".join(
        f'<tr><td>{escape(section)}</td><th scope="row">{escape(component)}</th>'
        f"<td>{escape(version)}</td></tr>"
        for section, component, version in _environment_rows(report)
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{escape(report.title)}</title><style>
:root{{--ink:#17202a;--muted:#5b6573;--line:#d9dee5;--panel:#f7f9fb;}}
*{{box-sizing:border-box}}
body{{color:var(--ink);font:16px/1.55 system-ui,sans-serif;margin:0}}
main{{margin:auto;max-width:1120px;padding:3rem 2rem 5rem}}
h1{{font-size:2.25rem;margin-bottom:.25rem}}
h2{{font-size:1.35rem;margin-top:2.25rem}} .lede{{color:var(--muted);margin-top:0}}
.narrative{{white-space:normal}}
figure{{border-top:1px solid var(--line);margin:2.5rem 0;padding-top:.5rem}}
figure img{{display:block;height:auto;margin:auto;max-width:100%}}
figcaption,.table-note{{color:var(--muted)}}
.table-scroll{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid var(--line);padding:.45rem .6rem;text-align:left;vertical-align:top}}
thead th{{background:var(--panel)}} .metadata th{{width:14rem}}
footer{{color:var(--muted);margin-top:3rem}}
@media print{{main{{max-width:none;padding:0}} figure,.report-table{{break-inside:avoid}}}}
</style></head><body><main><header><h1>{escape(report.title)}</h1>
<p class="lede">Deterministic RING-5 analysis report</p></header>{narrative}{figures}{tables}
<section><h2>Data provenance</h2>
<table class="metadata"><tbody>{provenance}</tbody></table></section>
<section><h2>Execution environment</h2><table><thead><tr>
<th>Area</th><th>Component</th><th>Version</th></tr></thead>
<tbody>{environment}</tbody></table></section>
<footer>Generated by RING-5. This self-contained report does not load remote scripts
or assets.</footer>
</main></body></html>"""
    return document.encode("utf-8")


def _wrapped_lines(text: str, *, width: int = 96) -> list[str]:
    """Wrap plain text while preserving paragraph boundaries."""
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        lines.extend(textwrap.wrap(paragraph, width=width) or [""])
    return lines


def _pdf_text_pages(pdf: PdfPages, heading: str, lines: Sequence[str]) -> None:
    """Write deterministic paginated text pages."""
    chunks = [lines[index : index + 45] for index in range(0, len(lines), 45)] or [[]]
    for page_number, chunk in enumerate(chunks, start=1):
        figure = plt.figure(figsize=(8.27, 11.69))
        figure.text(
            0.08,
            0.94,
            heading if len(chunks) == 1 else f"{heading} · {page_number}/{len(chunks)}",
            fontsize=18,
            weight="bold",
            va="top",
        )
        figure.text(0.08, 0.89, "\n".join(chunk), fontsize=9.5, family="monospace", va="top")
        pdf.savefig(figure)
        plt.close(figure)


def _pdf_figure_page(pdf: PdfPages, item: ReportFigure, image: bytes) -> None:
    """Write one titled report-figure page."""
    figure = plt.figure(figsize=(11.69, 8.27))
    axis = figure.add_axes((0.05, 0.12, 0.9, 0.76))
    axis.imshow(plt.imread(io.BytesIO(image), format="png"))
    axis.axis("off")
    figure.text(0.05, 0.95, item.title, fontsize=17, weight="bold", va="top")
    if item.caption:
        figure.text(0.05, 0.05, "\n".join(_wrapped_lines(item.caption, width=130)), fontsize=9)
    pdf.savefig(figure)
    plt.close(figure)


def _pdf_table_pages(pdf: PdfPages, table: ReportTable) -> None:
    """Write a report table across deterministic row pages."""
    page_size = 24
    chunks = [
        table.rows[index : index + page_size] for index in range(0, len(table.rows), page_size)
    ]
    if not chunks:
        chunks = [()]
    for page_number, rows in enumerate(chunks, start=1):
        figure, axis = plt.subplots(figsize=(11.69, 8.27))
        axis.axis("off")
        suffix = f" · {page_number}/{len(chunks)}" if len(chunks) > 1 else ""
        figure.suptitle(f"{table.title}{suffix}", fontsize=16, weight="bold", y=0.97)
        rendered = axis.table(
            cellText=[list(row) for row in rows],
            colLabels=list(table.columns),
            cellLoc="left",
            colLoc="left",
            loc="upper center",
        )
        rendered.auto_set_font_size(False)
        rendered.set_fontsize(7)
        rendered.scale(1, 1.35)
        note = (
            f"Showing {len(table.rows)} of {table.total_rows} rows"
            if table.truncated
            else f"{table.total_rows} rows"
        )
        figure.text(0.05, 0.04, note, fontsize=8)
        pdf.savefig(figure)
        plt.close(figure)


def _pdf_report(report: AnalysisReport, images: Sequence[bytes]) -> bytes:
    """Build a deterministic multi-page PDF document."""
    output = io.BytesIO()
    fixed_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
    metadata = {
        "Title": report.title,
        "Author": "RING-5",
        "Creator": "RING-5",
        "Producer": "RING-5",
        "CreationDate": fixed_date,
        "ModDate": fixed_date,
    }
    with plt.rc_context({"text.usetex": False}), PdfPages(output, metadata=metadata) as pdf:
        cover_lines = [
            "Deterministic RING-5 analysis report",
            "",
            f"Figures: {len(report.figures)}",
            f"Tables: {len(report.tables)}",
            f"Narrative sections: {len(report.narrative)}",
        ]
        _pdf_text_pages(pdf, report.title, cover_lines)
        for section in report.narrative:
            _pdf_text_pages(pdf, section.heading, _wrapped_lines(section.text))
        for item, image in zip(report.figures, images, strict=True):
            _pdf_figure_page(pdf, item, image)
        for table in report.tables:
            _pdf_table_pages(pdf, table)
        provenance_lines = [f"{name}: {value}" for name, value in _provenance_rows(report)]
        _pdf_text_pages(pdf, "Data provenance", provenance_lines)
        environment_lines = [
            f"{section} · {component}: {version}"
            for section, component, version in _environment_rows(report)
        ]
        _pdf_text_pages(pdf, "Execution environment", environment_lines)
    return output.getvalue()


def render_report(plots: Sequence[BasePlot], report: AnalysisReport, *, fmt: ReportFormat) -> bytes:
    # [impl->req~ring5.export.batch-reports~1]
    """Render a complete report to self-contained HTML or PDF bytes.

    Args:
        plots: Live plot workspace used to resolve report figure IDs.
        report: Immutable report specification.
        fmt: ``"html"`` or ``"pdf"``.

    Returns:
        Deterministic report bytes.

    Raises:
        ValueError: The format or a selected live plot is unavailable.
    """
    if fmt not in {"html", "pdf"}:
        raise ValueError("Report format must be 'html' or 'pdf'.")
    by_id = {plot.plot_id: plot for plot in plots}
    required = {plot_id for item in report.figures for plot_id in item.plot_ids}
    missing = sorted(required - set(by_id))
    if missing:
        raise ValueError("Report plots are no longer available: " + ", ".join(map(str, missing)))
    images = tuple(_figure_png(plots, by_id, item) for item in report.figures)
    if fmt == "html":
        return _html_report(report, images)
    return _pdf_report(report, images)
