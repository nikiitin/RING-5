"""Human-first source-data section for self-contained Plotly HTML exports."""

# flake8: noqa: E501 -- embedded CSS/JavaScript remains readable as browser source.

from __future__ import annotations

import pandas as pd

_STYLE = """
.ring5-source-data {
  --ring5-border: #d8dbe6;
  --ring5-muted: #5c6478;
  --ring5-surface: #f7f8fc;
  --ring5-accent: #5b3fd4;
  color: #171a24;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  margin: 2rem auto;
  max-width: 1400px;
  padding: 0 1.25rem 2rem;
}
.ring5-source-data * { box-sizing: border-box; }
.ring5-source-data__heading { margin-bottom: 1rem; }
.ring5-source-data__heading h2 { font-size: 1.5rem; margin: 0 0 .25rem; }
.ring5-source-data__heading p { color: var(--ring5-muted); margin: 0; }
.ring5-source-data__controls {
  align-items: end;
  display: flex;
  flex-wrap: wrap;
  gap: .75rem;
  justify-content: space-between;
  margin-bottom: .75rem;
}
.ring5-source-data__controls label { color: var(--ring5-muted); display: grid; font-size: .82rem; gap: .25rem; }
.ring5-source-data__controls input,
.ring5-source-data__controls select,
.ring5-source-data button {
  background: #fff;
  border: 1px solid var(--ring5-border);
  border-radius: .45rem;
  color: #171a24;
  font: inherit;
  min-height: 2.4rem;
  padding: .45rem .7rem;
}
.ring5-source-data__controls input { min-width: min(28rem, 78vw); }
.ring5-source-data button { cursor: pointer; }
.ring5-source-data button:hover { border-color: var(--ring5-accent); }
.ring5-source-data button:focus-visible,
.ring5-source-data input:focus-visible,
.ring5-source-data select:focus-visible { outline: 3px solid #c8bfff; outline-offset: 1px; }
.ring5-source-data__table-wrap {
  border: 1px solid var(--ring5-border);
  border-radius: .55rem;
  max-height: 34rem;
  overflow: auto;
}
.ring5-source-data table { border-collapse: separate; border-spacing: 0; min-width: 100%; width: max-content; }
.ring5-source-data th,
.ring5-source-data td { border-bottom: 1px solid var(--ring5-border); padding: .55rem .7rem; text-align: left; }
.ring5-source-data th { background: var(--ring5-surface); position: sticky; top: 0; z-index: 1; }
.ring5-source-data th button {
  background: transparent;
  border: 0;
  font-weight: 700;
  min-height: auto;
  padding: 0;
  text-align: left;
}
.ring5-source-data tbody tr:nth-child(even) { background: #fafbfe; }
.ring5-source-data td { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .88rem; }
.ring5-source-data__empty { color: var(--ring5-muted); font-family: inherit !important; padding: 2rem !important; text-align: center !important; }
.ring5-source-data__footer { align-items: center; display: flex; flex-wrap: wrap; gap: .65rem; justify-content: space-between; margin-top: .75rem; }
.ring5-source-data__footer p { color: var(--ring5-muted); margin: 0; }
.ring5-source-data__pagination { align-items: center; display: flex; gap: .5rem; }
.ring5-source-data__pagination button:disabled { cursor: not-allowed; opacity: .45; }
@media (prefers-color-scheme: dark) {
  .ring5-source-data {
    --ring5-border: #3b4054;
    --ring5-muted: #b6bdd1;
    --ring5-surface: #232738;
    color: #f5f6fb;
  }
  .ring5-source-data__controls input,
  .ring5-source-data__controls select,
  .ring5-source-data button { background: #1b1f2d; color: #f5f6fb; }
  .ring5-source-data tbody tr:nth-child(even) { background: #171b28; }
}
"""

_SCRIPT = """
(() => {
  const payloadNode = document.getElementById("ring5-source-data-payload");
  const root = document.getElementById("ring5-source-data");
  if (!payloadNode || !root) return;

  const payload = JSON.parse(payloadNode.textContent || "{}");
  const columns = Array.isArray(payload.columns) ? payload.columns : [];
  const rows = Array.isArray(payload.data) ? payload.data : [];
  const head = root.querySelector("thead tr");
  const body = root.querySelector("tbody");
  const filter = root.querySelector("[data-ring5-filter]");
  const pageSize = root.querySelector("[data-ring5-page-size]");
  const previous = root.querySelector("[data-ring5-previous]");
  const next = root.querySelector("[data-ring5-next]");
  const pageStatus = root.querySelector("[data-ring5-page-status]");
  const rowStatus = root.querySelector("[data-ring5-row-status]");
  const csvButton = root.querySelector("[data-ring5-csv]");
  let currentPage = 1;
  let sortColumn = -1;
  let sortDirection = 1;

  const display = value => value === null || value === undefined ? "—" : String(value);
  const compare = (left, right) => {
    if (left === null || left === undefined) return right === null || right === undefined ? 0 : 1;
    if (right === null || right === undefined) return -1;
    if (typeof left === "number" && typeof right === "number") return left - right;
    return String(left).localeCompare(String(right), undefined, {numeric: true, sensitivity: "base"});
  };

  columns.forEach((column, index) => {
    const th = document.createElement("th");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = String(column);
    button.title = `Sort by ${column}`;
    button.addEventListener("click", () => {
      sortDirection = sortColumn === index ? sortDirection * -1 : 1;
      sortColumn = index;
      currentPage = 1;
      render();
    });
    th.appendChild(button);
    head.appendChild(th);
  });

  const filteredRows = () => {
    const query = String(filter.value || "").trim().toLocaleLowerCase();
    const selected = query
      ? rows.filter(row => row.some(value => display(value).toLocaleLowerCase().includes(query)))
      : rows.slice();
    if (sortColumn >= 0) {
      selected.sort((left, right) => sortDirection * compare(left[sortColumn], right[sortColumn]));
    }
    return selected;
  };

  const render = () => {
    const selected = filteredRows();
    const size = Number(pageSize.value) || 25;
    const pageCount = Math.max(1, Math.ceil(selected.length / size));
    currentPage = Math.min(currentPage, pageCount);
    body.replaceChildren();
    const fragment = document.createDocumentFragment();
    const visibleRows = selected.slice((currentPage - 1) * size, currentPage * size);
    if (!visibleRows.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.className = "ring5-source-data__empty";
      cell.colSpan = Math.max(columns.length, 1);
      cell.textContent = "No rows match this filter.";
      row.appendChild(cell);
      fragment.appendChild(row);
    } else {
      visibleRows.forEach(values => {
        const row = document.createElement("tr");
        columns.forEach((_column, index) => {
          const cell = document.createElement("td");
          cell.textContent = display(values[index]);
          row.appendChild(cell);
        });
        fragment.appendChild(row);
      });
    }
    body.appendChild(fragment);
    rowStatus.textContent = `${selected.length.toLocaleString()} of ${rows.length.toLocaleString()} rows`;
    pageStatus.textContent = `Page ${currentPage.toLocaleString()} of ${pageCount.toLocaleString()}`;
    previous.disabled = currentPage <= 1;
    next.disabled = currentPage >= pageCount;
    head.querySelectorAll("th").forEach((th, index) => {
      th.setAttribute("aria-sort", index !== sortColumn ? "none" : sortDirection > 0 ? "ascending" : "descending");
    });
  };

  filter.addEventListener("input", () => { currentPage = 1; render(); });
  pageSize.addEventListener("change", () => { currentPage = 1; render(); });
  previous.addEventListener("click", () => { currentPage -= 1; render(); });
  next.addEventListener("click", () => { currentPage += 1; render(); });
  csvButton.addEventListener("click", () => {
    const quote = value => `"${display(value).replaceAll('"', '""')}"`;
    const csv = [columns, ...rows].map(row => row.map(quote).join(",")).join("\\r\\n");
    const url = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = "ring5-source-data.csv";
    link.click();
    URL.revokeObjectURL(url);
  });
  render();
})();
"""


def _json_payload(data: pd.DataFrame) -> str:
    """Serialize a dataframe for an inert script node without HTML breakouts."""
    frame = data.copy()
    frame.columns = [str(column) for column in frame.columns]
    payload = frame.to_json(
        orient="split",
        index=False,
        date_format="iso",
        default_handler=str,
    )
    return (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def add_interactive_source_data(html_document: str, data: pd.DataFrame) -> str:
    # [impl->req~ring5.export.plotly-html-source-data~1]
    """Append a searchable, sortable, paginated source table to Plotly HTML."""
    row_count, column_count = data.shape
    section = f"""
<section class="ring5-source-data" id="ring5-source-data" aria-labelledby="ring5-source-data-title">
  <div class="ring5-source-data__heading">
    <h2 id="ring5-source-data-title">Source data</h2>
    <p>The processed dataframe used to build this figure: {row_count:,} rows × {column_count:,} columns.</p>
  </div>
  <div class="ring5-source-data__controls">
    <label>Filter rows<input type="search" data-ring5-filter placeholder="Search every column…" autocomplete="off"></label>
    <label>Rows per page<select data-ring5-page-size><option>10</option><option selected>25</option><option>50</option><option>100</option></select></label>
    <button type="button" data-ring5-csv>Download source data as CSV</button>
  </div>
  <div class="ring5-source-data__table-wrap" role="region" aria-label="Interactive source dataframe" tabindex="0">
    <table><thead><tr></tr></thead><tbody></tbody></table>
  </div>
  <div class="ring5-source-data__footer">
    <p data-ring5-row-status aria-live="polite"></p>
    <div class="ring5-source-data__pagination">
      <button type="button" data-ring5-previous>Previous</button>
      <span data-ring5-page-status aria-live="polite"></span>
      <button type="button" data-ring5-next>Next</button>
    </div>
  </div>
</section>
<script id="ring5-source-data-payload" type="application/json">{_json_payload(data)}</script>
<script>{_SCRIPT}</script>
"""
    enriched = html_document.replace("</head>", f"<style>{_STYLE}</style></head>", 1)
    return enriched.replace("</body>", f"{section}</body>", 1)
