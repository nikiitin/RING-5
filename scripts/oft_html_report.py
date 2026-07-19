"""Add a feature summary and filters to a native OpenFastTrace HTML report.

The native OFT document remains the canonical report. This module reads its
green/red trace outcomes, verifies that every inventory item is present, and
injects the summary before the artifact details.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections.abc import Mapping
from typing import Any, cast


class OftHtmlReportError(ValueError):
    """The native OFT HTML cannot safely be enhanced."""


_REQUIREMENT_RESULT = re.compile(
    r'<section class="sitem" id="req~ring5\.([^"~]+(?:\.[^"~]+)*)~\d+">'
    r".*?<summary[^>]*>\s*<span class=\"([^\"]+)\">",
    re.DOTALL,
)


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def inventory_fingerprint(inventory: Mapping[str, Any]) -> str:
    """Return a deterministic fingerprint for report-staleness checks."""
    canonical = json.dumps(inventory, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def extract_oft_coverage(native_html: str, inventory: Mapping[str, Any]) -> dict[str, bool]:
    """Extract authoritative requirement coverage from OFT's HTML markers.

    Args:
        native_html: Complete HTML emitted by ``oft trace -o html``.
        inventory: Validated RING-5 inventory expected in the trace.

    Returns:
        Requirement ID to OFT-covered boolean.

    Raises:
        OftHtmlReportError: The document is not native OFT HTML or is incomplete.
    """
    required_sections = ("feat", "req", "impl", "test", "uman")
    missing_sections = [
        artifact
        for artifact in required_sections
        if f'<section id="{artifact}">' not in native_html
    ]
    if missing_sections:
        raise OftHtmlReportError(
            "Native OFT HTML is missing artifact sections: " + ", ".join(missing_sections)
        )

    groups = cast(list[dict[str, Any]], inventory["groups"])
    missing_groups = [
        str(group["id"])
        for group in groups
        if f' id="feat~ring5.{group["id"]}~1"' not in native_html
    ]
    if missing_groups:
        raise OftHtmlReportError(
            "Native OFT HTML is missing feature groups: " + ", ".join(missing_groups)
        )

    coverage: dict[str, bool] = {}
    for requirement_id, classes in _REQUIREMENT_RESULT.findall(native_html):
        class_names = set(classes.split())
        if "green" in class_names:
            coverage[requirement_id] = True
        elif "red" in class_names:
            coverage[requirement_id] = False
        else:
            raise OftHtmlReportError(
                f"Requirement {requirement_id!r} has no OFT green/red result marker."
            )

    features = cast(list[dict[str, Any]], inventory["features"])
    expected = {str(feature["id"]) for feature in features}
    missing_requirements = sorted(expected - set(coverage))
    unexpected_requirements = sorted(set(coverage) - expected)
    if missing_requirements:
        raise OftHtmlReportError(
            "Native OFT HTML is missing requirements: " + ", ".join(missing_requirements)
        )
    if unexpected_requirements:
        raise OftHtmlReportError(
            "Native OFT HTML contains requirements absent from the inventory: "
            + ", ".join(unexpected_requirements)
        )
    return coverage


def _requirement_card(feature: Mapping[str, Any], covered: bool) -> str:
    feature_id = str(feature["id"])
    status = str(feature["status"])
    coverage = "covered" if covered else "uncovered"
    label = "Covered by OFT" if covered else "Uncovered in OFT"
    search_text = " ".join(
        (
            feature_id,
            str(feature["title"]),
            str(feature["description"]),
            " ".join(cast(list[str], feature["tags"])),
        )
    ).lower()
    tags = "".join(f'<span class="human-tag">{_escape(tag)}</span>' for tag in feature["tags"])
    native_id = f"req~ring5.{feature_id}~{feature['revision']}"
    return f"""
<article class="human-requirement" data-group="{_escape(feature['group'])}"
  data-status="{_escape(status)}" data-coverage="{coverage}"
  data-search="{_escape(search_text)}">
  <div class="human-requirement-heading">
    <div><code>{_escape(native_id)}</code><h4>{_escape(feature['title'])}</h4></div>
    <div class="human-badges">
      <span class="human-badge status-{_escape(status)}">{_escape(status.title())}</span>
      <span class="human-badge coverage-{coverage}">{label}</span>
    </div>
  </div>
  <p>{_escape(feature['description'])}</p>
  <div class="human-card-footer">
    <div class="human-tags">{tags}</div>
    <a href="#{_escape(native_id)}">View canonical OFT trace ↓</a>
  </div>
</article>
"""


def _human_layer(inventory: Mapping[str, Any], coverage: Mapping[str, bool]) -> str:
    project_name = str(inventory["project"])
    groups = cast(list[dict[str, Any]], inventory["groups"])
    features = cast(list[dict[str, Any]], inventory["features"])
    bindings = cast(dict[str, dict[str, str]], inventory["discovery_bindings"])
    by_group: dict[str, list[dict[str, Any]]] = {str(group["id"]): [] for group in groups}
    for feature in features:
        by_group[str(feature["group"])].append(feature)

    covered_count = sum(coverage.values())
    uncovered = [feature for feature in features if not coverage[str(feature["id"])]]
    approved = sum(feature["status"] == "approved" for feature in features)
    future = len(features) - approved
    binding_count = sum(len(values) for values in bindings.values())
    percentage = round(100 * covered_count / len(features)) if features else 100

    group_options = "".join(
        f'<option value="{_escape(group["id"])}">{_escape(group["title"])}</option>'
        for group in groups
    )
    group_cards: list[str] = []
    requirement_sections: list[str] = []
    for group in groups:
        group_id = str(group["id"])
        group_features = by_group[group_id]
        group_covered = sum(coverage[str(feature["id"])] for feature in group_features)
        ratio = round(100 * group_covered / len(group_features)) if group_features else 100
        group_cards.append(f"""
<a class="human-group-card" href="#human-group-{_escape(group_id)}">
  <span>{group_covered}/{len(group_features)} covered by OFT</span>
  <h3>{_escape(group['title'])}</h3><p>{_escape(group['description'])}</p>
  <i aria-label="{ratio}% covered"><i style="width:{ratio}%"></i></i>
</a>
""")
        cards = "".join(
            _requirement_card(feature, coverage[str(feature["id"])]) for feature in group_features
        )
        requirement_sections.append(f"""
<section class="human-requirement-group" id="human-group-{_escape(group_id)}">
  <div class="human-section-title">
    <div><small>Feature group</small><h3>{_escape(group['title'])}</h3></div>
    <span>{len(group_features)} requirements</span>
  </div>
  <div class="human-requirement-list">{cards}</div>
</section>
""")

    if uncovered:
        uncovered_html = "".join(
            (
                '<a href="#req~ring5.{id}~{revision}">'
                "<strong>{title}</strong><span>{id}</span></a>"
            ).format(
                id=_escape(feature["id"]),
                revision=feature["revision"],
                title=_escape(feature["title"]),
            )
            for feature in uncovered
        )
    else:
        uncovered_html = (
            '<div class="human-all-covered"><b>✓</b><div>'
            "<strong>No uncovered requirements</strong>"
            "<p>OpenFastTrace reports complete links for every cataloged requirement.</p>"
            "</div></div>"
        )

    discovery_cards = "".join(
        f'<div class="human-source"><code>{_escape(source)}</code>'
        f"<strong>{len(values)}</strong></div>"
        for source, values in sorted(bindings.items())
    )
    return f"""
<!-- RING-5 summary added to the native OpenFastTrace HTML below. -->
<header class="human-hero">
  <div><small>{_escape(project_name)} · Native OpenFastTrace report</small>
  <h1>Feature traceability report</h1>
  <p>This report lists the requirements and their OpenFastTrace coverage status.
  The complete OFT artifact report follows the summary.</p></div>
</header>
<nav class="human-nav" aria-label="Report sections">
  <a href="#human-overview">Overview</a><a href="#human-features">Features</a>
  <a href="#human-uncovered">Uncovered</a>
  <a href="#human-requirements">Requirements</a>
  <a href="#human-discovery">Drift coverage</a>
  <a href="#oft-native-heading">Canonical OFT trace</a>
</nav>
<div class="human-report">
  <section id="human-overview" class="human-section">
    <div class="human-section-heading">
      <small>Summary</small><h2>OFT coverage</h2>
    </div>
    <div class="human-metrics">
      <div><span>Requirements</span><strong>{len(features)}</strong></div>
      <div class="good"><span>Covered by OFT</span><strong>{covered_count}</strong></div>
      <div class="bad"><span>Uncovered in OFT</span><strong>{len(uncovered)}</strong></div>
      <div><span>Approved now</span><strong>{approved}</strong></div>
      <div><span>Future items</span><strong>{future}</strong></div>
    </div>
    <p class="human-callout"><strong>{percentage}% OFT trace coverage.</strong>
    The covered and uncovered totals use the requirement results produced by OpenFastTrace.</p>
  </section>
  <section id="human-features" class="human-section">
    <div class="human-section-heading"><small>Catalog</small>
      <h2>Feature groups</h2><p>Each group links to its requirements.</p>
    </div>
    <div class="human-group-grid">{''.join(group_cards)}</div>
  </section>
  <section id="human-uncovered" class="human-section">
    <div class="human-section-heading"><small>Coverage gaps</small>
      <h2>Uncovered requirements</h2>
      <p>Any requirement marked red by OpenFastTrace appears here.</p>
    </div><div class="human-uncovered">{uncovered_html}</div>
  </section>
  <section id="human-requirements" class="human-section">
    <div class="human-section-heading"><small>Catalog</small>
      <h2>Requirements</h2><p>Search and filter the product catalog; each card links
      to its canonical OFT item below.</p>
    </div>
    <div class="human-controls">
      <label>Search<input id="human-search" type="search"
        placeholder="Try parser, heatmap, export…"></label>
      <label>Feature group<select id="human-group-filter">
        <option value="all">All groups</option>{group_options}</select></label>
      <label>Status<select id="human-status-filter">
        <option value="all">All statuses</option>
        <option value="approved">Approved</option>
        <option value="proposed">Proposed</option>
        <option value="draft">Draft</option></select></label>
      <label>OFT coverage<select id="human-coverage-filter">
        <option value="all">All</option><option value="covered">Covered</option>
        <option value="uncovered">Uncovered</option></select></label>
    </div>
    <p id="human-results" class="human-results">{len(features)} requirements shown</p>
    <div>{''.join(requirement_sections)}</div>
    <p id="human-no-results" class="human-no-results" hidden>
      No requirements match these filters.</p>
  </section>
  <section id="human-discovery" class="human-section">
    <div class="human-section-heading"><small>Inventory validation</small>
      <h2>Live surface coverage</h2><p>{binding_count} values from {len(bindings)}
      registries, APIs, schemas, formats, and commands are bound to requirements
      before OFT traces them.</p>
    </div><div class="human-source-grid">{discovery_cards}</div>
  </section>
</div>
<div class="human-native-intro" id="oft-native-heading"><small>OFT artifacts</small>
  <h2>Complete OpenFastTrace report</h2><p>Everything below this point is the native
  OFT artifact graph, including origins, links, revisions, tags, and trace outcomes.</p>
</div>
"""


_HUMAN_CSS = r"""

/* RING-5 report summary. Native OFT selectors and content remain below. */
:root {
  --h-ink:#172033;
  --h-muted:#5d6879;
  --h-line:#dfe4eb;
  --h-soft:#f5f7fa;
  --h-brand:#5036b3;
  --h-good:#177245;
  --h-good-soft:#e8f6ef;
  --h-bad:#a53b19;
  --h-bad-soft:#fff0e9;
}
body { margin:0; color:var(--h-ink); background:var(--h-soft); line-height:1.5; }
.human-hero {
  padding:4rem max(1.25rem,calc((100vw - 1180px)/2));
  color:white;
  background:linear-gradient(125deg,#25175e,#5036b3 58%,#846ad9);
}
.human-hero div { max-width:820px; }
.human-hero small,
.human-section-heading small,
.human-native-intro small,
.human-section-title small {
  font-weight:800;
  letter-spacing:.12em;
  text-transform:uppercase;
}
.human-hero h1 {
  margin:.5rem 0 1rem;
  font-size:clamp(2.4rem,6vw,4.6rem);
  line-height:1.02;
}
.human-hero p { max-width:720px; color:#ebe6ff; font-size:1.08rem; }
.human-nav {
  position:sticky;
  top:0;
  z-index:200;
  display:flex;
  gap:1.2rem;
  overflow:auto;
  width:auto;
  padding:.85rem max(1.25rem,calc((100vw - 1180px)/2));
  background:rgba(255,255,255,.96);
  border-bottom:1px solid var(--h-line);
}
.human-nav a {
  color:var(--h-ink);
  font-size:.88rem;
  font-weight:700;
  text-decoration:none;
  white-space:nowrap;
}
.human-report,
.human-native-intro { width:min(1180px,calc(100% - 2rem)); margin:auto; }
.human-section { margin:0 0 4rem; padding-top:3rem; scroll-margin-top:3rem; }
.human-section-heading { margin-bottom:1.3rem; }
.human-section-heading h2,
.human-native-intro h2 {
  margin:.25rem 0;
  font-size:clamp(1.7rem,4vw,2.3rem);
}
.human-section-heading p,
.human-native-intro p { max-width:700px; color:var(--h-muted); }
.human-metrics { display:grid; grid-template-columns:repeat(5,1fr); gap:.8rem; }
.human-metrics>div {
  min-height:125px;
  padding:1.1rem;
  background:white;
  border:1px solid var(--h-line);
  border-radius:16px;
  box-shadow:0 12px 34px rgba(32,42,65,.08);
}
.human-metrics span {
  display:block;
  color:var(--h-muted);
  font-size:.75rem;
  font-weight:800;
  text-transform:uppercase;
}
.human-metrics strong { display:block; margin-top:.35rem; font-size:2.2rem; }
.human-metrics .good strong { color:var(--h-good); }
.human-metrics .bad strong { color:var(--h-bad); }
.human-callout {
  padding:1rem 1.15rem;
  color:#42377a;
  background:#eeeafe;
  border-radius:14px;
}
.human-group-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; }
.human-group-card {
  display:flex;
  flex-direction:column;
  min-height:215px;
  padding:1.2rem;
  color:var(--h-ink);
  text-decoration:none;
  background:white;
  border:1px solid var(--h-line);
  border-radius:17px;
  box-shadow:0 10px 26px rgba(32,42,65,.07);
}
.human-group-card>span {
  color:var(--h-good);
  font-size:.75rem;
  font-weight:800;
  text-transform:uppercase;
}
.human-group-card h3 { margin:.6rem 0 .35rem; }
.human-group-card p { flex:1; color:var(--h-muted); font-size:.9rem; }
.human-group-card>i {
  display:block;
  height:7px;
  overflow:hidden;
  background:#e8ebf0;
  border-radius:9px;
}
.human-group-card>i>i { display:block; height:100%; background:var(--h-good); }
.human-all-covered {
  display:flex;
  gap:1rem;
  align-items:center;
  padding:1.3rem;
  background:var(--h-good-soft);
  border:1px solid #b8dfcb;
  border-radius:15px;
}
.human-all-covered>b {
  display:grid;
  place-items:center;
  width:42px;
  height:42px;
  color:white;
  background:var(--h-good);
  border-radius:50%;
}
.human-all-covered p { margin:.15rem 0; color:#315c47; }
.human-uncovered>a {
  display:flex;
  justify-content:space-between;
  padding:1rem;
  color:var(--h-bad);
  background:var(--h-bad-soft);
  border-bottom:1px solid #f2c9b8;
  text-decoration:none;
}
.human-controls {
  position:sticky;
  top:3.2rem;
  z-index:150;
  display:grid;
  grid-template-columns:2fr repeat(3,1fr);
  gap:.7rem;
  padding:.85rem;
  background:rgba(255,255,255,.97);
  border:1px solid var(--h-line);
  border-radius:14px;
  box-shadow:0 10px 25px rgba(32,42,65,.07);
}
.human-controls label {
  display:grid;
  gap:.2rem;
  color:var(--h-muted);
  font-size:.7rem;
  font-weight:800;
  text-transform:uppercase;
}
.human-controls input,
.human-controls select {
  min-width:0;
  height:42px;
  padding:0 .7rem;
  background:white;
  border:1px solid #c9d0da;
  border-radius:9px;
}
.human-results { color:var(--h-muted); font-weight:700; }
.human-requirement-group { margin:2.5rem 0; scroll-margin-top:8rem; }
.human-section-title {
  display:flex;
  justify-content:space-between;
  align-items:end;
  padding-top:1rem;
  border-top:1px solid var(--h-line);
}
.human-section-title h3 { margin:.2rem 0; }
.human-section-title>span { color:var(--h-muted); font-size:.85rem; }
.human-requirement-list { display:grid; gap:.75rem; margin-top:1rem; }
.human-requirement {
  padding:1.1rem 1.2rem;
  background:white;
  border:1px solid var(--h-line);
  border-left:5px solid var(--h-good);
  border-radius:13px;
}
.human-requirement[data-coverage="uncovered"] { border-left-color:var(--h-bad); }
.human-requirement-heading,
.human-card-footer { display:flex; justify-content:space-between; gap:1rem; }
.human-requirement code { color:var(--h-muted); font-size:.72rem; }
.human-requirement h4 { margin:.15rem 0; }
.human-requirement p { color:#3f4a5b; }
.human-badges,
.human-tags { display:flex; flex-wrap:wrap; gap:.35rem; }
.human-badge,
.human-tag {
  padding:.22rem .52rem;
  border-radius:999px;
  font-size:.7rem;
  font-weight:750;
  white-space:nowrap;
}
.status-approved,
.coverage-covered { color:var(--h-good); background:var(--h-good-soft); }
.status-proposed,
.status-draft { color:#6c5c16; background:#faf4d5; }
.coverage-uncovered { color:var(--h-bad); background:var(--h-bad-soft); }
.human-tag { color:#4f5968; background:#eef1f5; font-weight:600; }
.human-card-footer>a { font-size:.8rem; font-weight:750; }
.human-source-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:.45rem; }
.human-source {
  display:flex;
  justify-content:space-between;
  gap:1rem;
  padding:.65rem .8rem;
  background:white;
  border:1px solid var(--h-line);
  border-radius:9px;
}
.human-source code { overflow-wrap:anywhere; }
.human-source strong { color:var(--h-brand); }
.human-no-results {
  padding:2rem;
  text-align:center;
  background:white;
  border-radius:12px;
}
.human-native-intro {
  padding:3rem 0 1rem;
  border-top:4px solid var(--h-brand);
  scroll-margin-top:4rem;
}
body>nav:not(.human-nav) {
  position:static;
  width:min(1180px,calc(100% - 2rem));
  margin:0 auto;
  padding:.65rem 1rem;
  background:white;
  border:1px solid var(--h-line);
  border-bottom:0;
  border-radius:14px 14px 0 0;
}
main#oft-native-report {
  position:static;
  width:min(1180px,calc(100% - 2rem));
  margin:0 auto 5rem;
  padding:0;
  background:white;
  border:1px solid var(--h-line);
  border-radius:14px;
}
main#oft-native-report>.sitem,
main#oft-native-report>section { scroll-margin-top:4rem; }
[hidden] { display:none !important; }
@media(max-width:850px) {
  .human-metrics { grid-template-columns:repeat(2,1fr); }
  .human-group-grid,
  .human-source-grid { grid-template-columns:repeat(2,1fr); }
  .human-controls { position:static; grid-template-columns:1fr 1fr; }
}
@media(max-width:560px) {
  .human-metrics,
  .human-group-grid,
  .human-source-grid,
  .human-controls { grid-template-columns:1fr; }
  .human-requirement-heading,
  .human-card-footer,
  .human-section-title { align-items:flex-start; flex-direction:column; }
}
@media print {
  .human-nav,
  .human-controls { display:none; }
  .human-hero { padding:1rem; color:var(--h-ink); background:white; }
  .human-hero p { color:var(--h-muted); }
  .human-report,
  .human-native-intro,
  main#oft-native-report { width:100%; }
}
"""


_HUMAN_SCRIPT = r"""
<script>
(() => {
  const cards=[...document.querySelectorAll('.human-requirement')];
  const groups=[...document.querySelectorAll('.human-requirement-group')];
  const search=document.querySelector('#human-search');
  const group=document.querySelector('#human-group-filter');
  const status=document.querySelector('#human-status-filter');
  const coverage=document.querySelector('#human-coverage-filter');
  const count=document.querySelector('#human-results');
  const empty=document.querySelector('#human-no-results');
  function filter(){
    const term=search.value.trim().toLowerCase();let visible=0;
    cards.forEach(card=>{
      const show=(!term||card.dataset.search.includes(term))
        &&(group.value==='all'||card.dataset.group===group.value)
        &&(status.value==='all'||card.dataset.status===status.value)
        &&(coverage.value==='all'||card.dataset.coverage===coverage.value);
      card.hidden=!show;
      if(show)visible+=1;
    });
    groups.forEach(section=>{
      section.hidden=!section.querySelector('.human-requirement:not([hidden])');
    });
    count.textContent=`${visible} of ${cards.length} requirements shown`;empty.hidden=visible!==0;
  }
  [search,group,status,coverage].forEach(control=>{
    control.addEventListener(control===search?'input':'change',filter);
  });
})();
</script>
"""


def enhance_oft_html(native_html: str, inventory: Mapping[str, Any]) -> str:
    """Insert the RING-5 summary into native OFT HTML while retaining its trace graph."""
    coverage = extract_oft_coverage(native_html, inventory)
    if "</style>" not in native_html or "<body>" not in native_html or "<main>" not in native_html:
        raise OftHtmlReportError("Native OFT HTML does not have the expected document structure.")

    fingerprint = inventory_fingerprint(inventory)
    report = native_html.replace(
        "</head>",
        f'  <meta name="ring5-inventory-sha256" content="{fingerprint}">\n</head>',
        1,
    )
    report = report.replace("</style>", _HUMAN_CSS + "\n</style>", 1)
    report = report.replace(
        "<title>Specification items by artifact type</title>",
        "<title>RING-5 feature coverage · OpenFastTrace</title>",
        1,
    )
    report = report.replace("<body>", "<body>\n" + _human_layer(inventory, coverage), 1)
    report = report.replace("<main>", '<main id="oft-native-report">', 1)
    report = report.replace("</body>", _HUMAN_SCRIPT + "\n</body>", 1)
    return report
