"""Deterministic, self-contained HTML and PDF analysis reports."""

# flake8: noqa: E501 -- embedded HTML/CSS/JavaScript remains readable as browser source.

from __future__ import annotations

import base64
import io
import textwrap
from collections.abc import Sequence
from datetime import datetime, timezone
from html import escape
from typing import Literal, cast

import matplotlib.pyplot as plt
import plotly.graph_objects as go
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure as MplFigure
from plotly.offline import get_plotlyjs

from src.core.common.utils import sanitize_filename
from src.core.models.report_models import AnalysisReport, ReportFigure, ReportTable
from src.core.services.managers.semantic_metadata_service import SemanticMetadataService
from src.core.services.visualization.accessibility_service import AccessibilityService
from src.web.pages.ui.plotting.base_plot import BasePlot, _relabel_traces
from src.web.rendering.dashboard_builder import render_dashboard
from src.web.rendering.interactive_html_export import (
    interactive_source_data_assets,
    interactive_source_data_section,
)
from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_traces
from src.web.rendering.trace_to_plotly import traces_to_plotly

ReportFormat = Literal["html", "pdf"]
ReportHtmlMode = Literal["document", "gallery"]


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


def _single_plot_plotly(plot: BasePlot) -> go.Figure:
    """Render one plot through the engine-independent Plotly path."""
    if plot.processed_data is None:
        raise ValueError(f"Report plot '{plot.name}' has no processed data.")
    effective = SemanticMetadataService.enrich_figure_config(plot.processed_data, plot.config)
    effective = AccessibilityService.apply_defaults(effective, plot.plot_type)
    traces = plot.create_traces(plot.processed_data, effective)
    traces = AccessibilityService.apply_non_color_encodings(traces, effective)
    traces = _relabel_traces(traces, effective.get("legend_labels"))
    figure = traces_to_plotly(traces)
    if not traces.traces:
        figure.update_layout(title_text="Please select at least one X and one Y column.")
    return plot.apply_common_layout(figure, effective)


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


_GALLERY_STYLE = """
:root{--ink:#181826;--muted:#64677a;--line:#dcddea;--surface:#f7f7fb;--card:#fff;
--accent:#5b3fd4;--accent-soft:#eeeaff;--shadow:0 12px 35px rgba(32,27,67,.08)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:#f4f3f9;color:var(--ink);font:16px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,
BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0}
.gallery-shell{margin:auto;max-width:1480px;padding:2.5rem 1.5rem 5rem}
.gallery-hero{background:linear-gradient(135deg,#29204f,#5b3fd4);border-radius:1.1rem;color:#fff;
padding:2rem 2.25rem;box-shadow:var(--shadow)}
.gallery-hero h1{font-size:clamp(2rem,4vw,3.35rem);letter-spacing:-.045em;line-height:1.05;margin:0}
.gallery-hero p{color:#e8e2ff;margin:.75rem 0 0;max-width:68rem}
.gallery-summary{display:flex;flex-wrap:wrap;gap:.6rem;margin-top:1.4rem}
.gallery-chip{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.24);
border-radius:99rem;font-size:.86rem;padding:.35rem .75rem}
.gallery-narrative{background:var(--card);border:1px solid var(--line);border-radius:.9rem;
margin:1.25rem 0;padding:1.25rem 1.5rem}
.gallery-narrative h2{font-size:1.25rem;margin:0 0 .4rem}
.gallery-narrative p{margin:0;white-space:normal}
.gallery-toolbar{align-items:end;background:rgba(255,255,255,.94);border:1px solid var(--line);
border-radius:.9rem;display:flex;flex-wrap:wrap;gap:.8rem;justify-content:space-between;
margin:1.25rem 0;padding:1rem 1.15rem;position:sticky;top:.75rem;z-index:20;
box-shadow:0 8px 22px rgba(32,27,67,.07)}
.gallery-controls{display:flex;flex:1;flex-wrap:wrap;gap:.75rem}
.gallery-toolbar label{color:var(--muted);display:grid;font-size:.8rem;gap:.25rem}
.gallery-toolbar input,.gallery-toolbar select{background:#fff;border:1px solid var(--line);
border-radius:.45rem;color:var(--ink);font:inherit;min-height:2.45rem;padding:.45rem .7rem}
.gallery-toolbar input{min-width:min(29rem,72vw)}
.gallery-toolbar input:focus-visible,.gallery-toolbar select:focus-visible{outline:3px solid #c9c0ff;
outline-offset:1px}
.gallery-count{color:var(--muted);font-size:.9rem;margin:.55rem 0}
.gallery-feed{display:grid;gap:1.25rem}
.gallery-card{background:var(--card);border:1px solid var(--line);border-radius:1rem;
box-shadow:var(--shadow);overflow:hidden;padding:1.35rem 1.5rem 1.5rem}
.gallery-card[hidden]{display:none}
.gallery-card__header{align-items:start;display:flex;gap:1rem;justify-content:space-between}
.gallery-card__header h2{font-size:1.5rem;letter-spacing:-.02em;margin:.15rem 0 .25rem}
.gallery-card__header p{color:var(--muted);margin:0}
.gallery-card__type{background:var(--accent-soft);border-radius:99rem;color:#4930bd;
display:inline-block;font-size:.75rem;font-weight:700;letter-spacing:.04em;padding:.28rem .62rem;
text-transform:uppercase}
.gallery-card__number{color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
.gallery-chart{margin:.6rem -.4rem 0;min-height:360px;overflow-x:auto}
.gallery-data{border-top:1px solid var(--line);margin-top:.65rem;padding-top:.8rem}
.gallery-data summary{cursor:pointer;font-weight:700;padding:.35rem 0}
.gallery-data summary::marker{color:var(--accent)}
.gallery-card .ring5-source-data{margin:1rem 0 0;max-width:none;padding:0}
.gallery-card .ring5-source-data__heading h3{font-size:1.1rem;margin:0 0 .2rem}
.gallery-metadata{background:var(--card);border:1px solid var(--line);border-radius:1rem;
margin-top:1.5rem;padding:1.25rem 1.5rem}
.gallery-metadata h2{font-size:1.3rem;margin:1.5rem 0 .5rem}
.gallery-metadata h2:first-child{margin-top:0}
.gallery-metadata table,.report-table table{border-collapse:collapse;width:100%}
.gallery-metadata th,.gallery-metadata td,.report-table th,.report-table td{border:1px solid var(--line);
padding:.48rem .65rem;text-align:left;vertical-align:top}
.gallery-metadata thead th,.report-table thead th{background:var(--surface)}
.gallery-tables{background:var(--card);border:1px solid var(--line);border-radius:1rem;
margin-top:1.5rem;padding:0 1.5rem 1.5rem}
.gallery-tables .table-scroll{overflow-x:auto}
.gallery-footer{color:var(--muted);margin:2rem 0;text-align:center}
@media(max-width:700px){.gallery-shell{padding:1rem .65rem 3rem}.gallery-hero{padding:1.4rem}
.gallery-card{padding:1rem}.gallery-card__header{display:block}.gallery-card__number{display:block;margin-top:.5rem}
.gallery-toolbar{position:static}.gallery-toolbar input{min-width:100%}}
@media(prefers-color-scheme:dark){:root{--ink:#f5f4fb;--muted:#b9b7ca;--line:#3c3a4b;
--surface:#262431;--card:#1d1b26;--accent-soft:#332b5e}body{background:#14131a}
.gallery-toolbar{background:rgba(29,27,38,.94)}.gallery-toolbar input,.gallery-toolbar select{
background:#17151e;color:var(--ink)}.gallery-card__type{color:#cfc4ff}}
@media print{.gallery-toolbar,.gallery-data{display:none}.gallery-shell{max-width:none;padding:0}
.gallery-card{break-inside:avoid;box-shadow:none}}
"""

_GALLERY_SCRIPT = """
(() => {
  const search = document.querySelector("[data-ring5-gallery-search]");
  const type = document.querySelector("[data-ring5-gallery-type]");
  const count = document.querySelector("[data-ring5-gallery-count]");
  const cards = Array.from(document.querySelectorAll("[data-ring5-gallery-item]"));
  if (!search || !type || !count) return;
  const render = () => {
    const query = String(search.value || "").trim().toLocaleLowerCase();
    const selectedType = String(type.value || "all");
    let visible = 0;
    cards.forEach(card => {
      const matchesText = !query || String(card.dataset.ring5Search || "").includes(query);
      const matchesType = selectedType === "all" || card.dataset.ring5Type === selectedType;
      card.hidden = !(matchesText && matchesType);
      if (!card.hidden) visible += 1;
    });
    count.textContent = `${visible.toLocaleString()} of ${cards.length.toLocaleString()} plots visible`;
  };
  search.addEventListener("input", render);
  type.addEventListener("change", render);
  render();
})();
"""


def _gallery_plotly_figure(
    plots: Sequence[BasePlot], by_id: dict[int, BasePlot], item: ReportFigure
) -> go.Figure:
    """Render an interactive figure or dashboard for one gallery card."""
    if item.dashboard is None:
        return _single_plot_plotly(by_id[item.plot_ids[0]])
    return cast(go.Figure, render_dashboard(plots, item.dashboard, engine="plotly"))


def _gallery_source_sections(item: ReportFigure, by_id: dict[int, BasePlot], index: int) -> str:
    """Build one independently interactive source table per plot in a card."""
    sections: list[str] = []
    for source_index, plot_id in enumerate(item.plot_ids, start=1):
        plot = by_id[plot_id]
        if plot.processed_data is None:
            raise ValueError(f"Report plot '{plot.name}' has no processed data.")
        title = "Source dataframe" if len(item.plot_ids) == 1 else f"{plot.name} · source dataframe"
        stem = sanitize_filename(plot.name) or f"plot-{plot_id}"
        sections.append(
            interactive_source_data_section(
                plot.processed_data,
                section_id=f"ring5-gallery-data-{index}-{source_index}",
                title=title,
                csv_filename=f"{stem}-source-data.csv",
                heading_level=3,
            )
        )
    return "".join(sections)


def _gallery_card(
    plots: Sequence[BasePlot],
    by_id: dict[int, BasePlot],
    item: ReportFigure,
    index: int,
    total: int,
) -> str:
    """Render one searchable plot-and-data card."""
    figure = _gallery_plotly_figure(plots, by_id, item)
    fragment = figure.to_html(
        full_html=False,
        include_plotlyjs=False,
        div_id=f"ring5-gallery-figure-{index}",
        config={"displaylogo": False, "responsive": True},
    )
    source_plots = [by_id[plot_id] for plot_id in item.plot_ids]
    plot_type = "dashboard" if item.dashboard is not None else source_plots[0].plot_type
    type_label = plot_type.replace("_", " ")
    rows = sum(len(plot.processed_data) for plot in source_plots if plot.processed_data is not None)
    columns = sorted(
        {
            str(column)
            for plot in source_plots
            if plot.processed_data is not None
            for column in plot.processed_data.columns
        }
    )
    data_summary = (
        f"{rows:,} processed rows · {len(columns):,} unique columns"
        if len(source_plots) > 1
        else f"{rows:,} rows × {len(columns):,} columns"
    )
    caption = f"<p>{escape(item.caption)}</p>" if item.caption else ""
    search_text = " ".join(
        [item.title, item.caption, type_label, data_summary, *columns]
        + [plot.name for plot in source_plots]
    ).lower()
    source_sections = _gallery_source_sections(item, by_id, index)
    return f"""
<article class="gallery-card" id="ring5-gallery-card-{index}" data-ring5-gallery-item data-ring5-type="{escape(plot_type, quote=True)}" data-ring5-search="{escape(search_text, quote=True)}">
  <header class="gallery-card__header">
    <div><span class="gallery-card__type">{escape(type_label)}</span>
      <h2>{escape(item.title)}</h2>{caption}<p>{escape(data_summary)}</p></div>
    <span class="gallery-card__number">{index} / {total}</span>
  </header>
  <div class="gallery-chart">{fragment}</div>
  <details class="gallery-data" open><summary>Explore the dataframe behind this plot</summary>
    {source_sections}
  </details>
</article>
"""


def _html_gallery(
    plots: Sequence[BasePlot], by_id: dict[int, BasePlot], report: AnalysisReport
) -> bytes:
    # [impl->req~ring5.export.interactive-gallery~1]
    """Build a self-contained, searchable feed of interactive plots and dataframes."""
    narrative = "".join(
        f'<section class="gallery-narrative"><h2>{escape(item.heading)}</h2>'
        f'<p>{escape(item.text).replace(chr(10), "<br>")}</p></section>'
        for item in report.narrative
    )
    cards = "".join(
        _gallery_card(plots, by_id, item, index, len(report.figures))
        for index, item in enumerate(report.figures, start=1)
    )
    plot_types = sorted(
        {
            "dashboard" if item.dashboard is not None else by_id[item.plot_ids[0]].plot_type
            for item in report.figures
        }
    )
    type_options = "".join(
        f'<option value="{escape(value, quote=True)}">{escape(value.replace("_", " ").title())}</option>'
        for value in plot_types
    )
    tables = "".join(_html_table(table) for table in report.tables)
    tables_section = f'<section class="gallery-tables">{tables}</section>' if tables else ""
    provenance = "".join(
        f'<tr><th scope="row">{escape(label)}</th><td>{escape(value)}</td></tr>'
        for label, value in _provenance_rows(report)
    )
    environment = "".join(
        f'<tr><td>{escape(section)}</td><th scope="row">{escape(component)}</th>'
        f"<td>{escape(version)}</td></tr>"
        for section, component, version in _environment_rows(report)
    )
    source_style, source_script = interactive_source_data_assets()
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{escape(report.title)}</title><style>{_GALLERY_STYLE}\n{source_style}</style>
<script>{get_plotlyjs()}</script></head><body><main class="gallery-shell">
<header class="gallery-hero"><h1>{escape(report.title)}</h1>
<p>Interactive RING-5 plot gallery. Inspect each figure, then search, sort, page, or export the exact processed dataframe that produced it.</p>
<div class="gallery-summary"><span class="gallery-chip">{len(report.figures)} plot cards</span>
<span class="gallery-chip">Self-contained HTML</span><span class="gallery-chip">No remote assets</span></div>
</header>{narrative}
<section class="gallery-toolbar" aria-label="Gallery controls"><div class="gallery-controls">
<label>Find a plot<input type="search" data-ring5-gallery-search placeholder="Search titles, plot types, or columns…" autocomplete="off"></label>
<label>Plot type<select data-ring5-gallery-type><option value="all">All plot types</option>{type_options}</select></label>
</div><p class="gallery-count" data-ring5-gallery-count aria-live="polite"></p></section>
<section class="gallery-feed" aria-label="Plot gallery">{cards}</section>{tables_section}
<section class="gallery-metadata"><h2>Data provenance</h2><table><tbody>{provenance}</tbody></table>
<h2>Execution environment</h2><table><thead><tr><th>Area</th><th>Component</th><th>Version</th></tr></thead>
<tbody>{environment}</tbody></table></section>
<footer class="gallery-footer">Generated by RING-5. This self-contained gallery does not load remote scripts or assets.</footer>
</main><script>{source_script}</script><script>{_GALLERY_SCRIPT}</script></body></html>"""
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


def render_report(
    plots: Sequence[BasePlot],
    report: AnalysisReport,
    *,
    fmt: ReportFormat,
    html_mode: ReportHtmlMode = "document",
) -> bytes:
    # [impl->req~ring5.export.batch-reports~1]
    # [impl->req~ring5.export.interactive-gallery~1]
    """Render a complete report to self-contained HTML or PDF bytes.

    Args:
        plots: Live plot workspace used to resolve report figure IDs.
        report: Immutable report specification.
        fmt: ``"html"`` or ``"pdf"``.
        html_mode: Static publication ``"document"`` or interactive
            plot-and-data ``"gallery"`` output for HTML.

    Returns:
        Deterministic report bytes.

    Raises:
        ValueError: The format or a selected live plot is unavailable.
    """
    if fmt not in {"html", "pdf"}:
        raise ValueError("Report format must be 'html' or 'pdf'.")
    if html_mode not in {"document", "gallery"}:
        raise ValueError("HTML report mode must be 'document' or 'gallery'.")
    if fmt == "pdf" and html_mode != "document":
        raise ValueError("Interactive gallery mode is available only for HTML reports.")
    by_id = {plot.plot_id: plot for plot in plots}
    required = {plot_id for item in report.figures for plot_id in item.plot_ids}
    missing = sorted(required - set(by_id))
    if missing:
        raise ValueError("Report plots are no longer available: " + ", ".join(map(str, missing)))
    if fmt == "html" and html_mode == "gallery":
        return _html_gallery(plots, by_id, report)
    images = tuple(_figure_png(plots, by_id, item) for item in report.figures)
    if fmt == "html":
        return _html_report(report, images)
    return _pdf_report(report, images)
