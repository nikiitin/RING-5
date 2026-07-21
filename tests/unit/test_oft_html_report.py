"""Tests for the RING-5 summary added to native OpenFastTrace HTML."""

from copy import deepcopy
from typing import Any

import pytest

from scripts.oft_evidence import EvidenceMarker
from scripts.oft_html_report import (
    OftHtmlReportError,
    evidence_fingerprint,
    enhance_oft_html,
    extract_oft_coverage,
    inventory_fingerprint,
)


@pytest.fixture
def small_inventory() -> dict[str, Any]:
    """Return two requirements with opposite native OFT outcomes."""
    return {
        "project": "RING-5",
        "groups": [
            {
                "id": "workspace",
                "title": "Workspace",
                "description": "Interactive analysis workspace.",
            }
        ],
        "features": [
            {
                "id": "workspace.covered",
                "group": "workspace",
                "revision": 1,
                "status": "approved",
                "title": "Covered behavior",
                "description": "Has a complete native trace.",
                "tags": ["workspace"],
                "evidence": {
                    "implementation": ["src/example.py::run"],
                    "tests": ["tests/test_example.py::test_run"],
                    "documentation": ["docs/example.md#behavior"],
                },
            },
            {
                "id": "workspace.future",
                "group": "workspace",
                "revision": 1,
                "status": "proposed",
                "title": "Future behavior",
                "description": "Still needs trace coverage.",
                "tags": ["future"],
                "implementation_branch": "006-workspace-future",
                "evidence": {"implementation": [], "tests": [], "documentation": []},
            },
        ],
        "discovery_bindings": {"navigation_pages": {"Workspace": "workspace.covered"}},
    }


@pytest.fixture
def native_oft_html() -> str:
    """Return the minimum native structure consumed by the enhancer."""
    return """<!DOCTYPE html>
<html><head><style>.green { color: green; }.red { color: red; }</style>
<title>Specification items by artifact type</title></head><body><main>
<section id="feat">
<section class="sitem" id="feat~ring5.workspace~1">native group</section>
</section>
<section id="impl">native implementations
<section class="sitem" id="impl~ring5.workspace.covered-101~0"><details>
<p class="origin">src/example.py:12</p><a href="#req~ring5.workspace.covered~1">covers</a>
</details></section></section>
<section id="req">
<section class="sitem" id="req~ring5.workspace.covered~1"><details><summary>
<span class="green">&check;</span> Covered behavior</summary>
<p>native covered detail</p></details></section>
<section class="sitem" id="req~ring5.workspace.future~1"><details><summary>
<span class="red">&#10007;</span> Future behavior</summary>
<p>native uncovered detail</p></details></section>
</section>
<section id="test">native tests
<section class="sitem" id="test~ring5.workspace.covered-102~0"><details>
<p class="origin">tests/test_example.py:24</p><a href="#req~ring5.workspace.covered~1">covers</a>
</details></section></section>
<section id="uman">native documentation
<section class="sitem" id="uman~ring5.workspace.covered.documentation~1"><details>
<p class="origin">docs/example.md:8</p><a href="#req~ring5.workspace.covered~1">covers</a>
</details></section></section>
</main></body></html>"""


@pytest.fixture
def source_markers() -> list[EvidenceMarker]:
    """Return exact locators corresponding to the native fixture origins."""
    return [
        EvidenceMarker("impl", "workspace.covered", 1, "src/example.py", "run", 12),
        EvidenceMarker("test", "workspace.covered", 1, "tests/test_example.py", "test_run", 24),
        EvidenceMarker("uman", "workspace.covered", 1, "docs/example.md", "behavior", 8),
    ]


def test_coverage_is_read_from_native_oft_markers(
    native_oft_html: str, small_inventory: dict[str, Any]
) -> None:
    """Green and red OFT results, not evidence heuristics, drive the overview."""
    # [test->req~ring5.trace.human-html-report~1]
    assert extract_oft_coverage(native_oft_html, small_inventory) == {
        "workspace.covered": True,
        "workspace.future": False,
    }


def test_human_layer_preserves_native_trace_and_links_to_it(
    native_oft_html: str,
    small_inventory: dict[str, Any],
    source_markers: list[EvidenceMarker],
) -> None:
    """The enhanced document keeps canonical items and adds product navigation."""
    # [test->req~ring5.trace.human-html-report~1]
    report = enhance_oft_html(native_oft_html, small_inventory, source_markers)

    assert "Feature traceability report" in report
    assert "1 of 2 requirements shown" not in report  # Updated by JS only after filtering.
    assert "2 requirements shown" in report
    assert 'data-coverage="covered"' in report
    assert 'data-coverage="uncovered"' in report
    assert 'href="#req~ring5.workspace.future~1"' in report
    assert "native covered detail" in report
    assert "native uncovered detail" in report
    assert "What “covered” means" in report
    assert "Covered does not mean" in report
    assert "src/example.py::run" in report
    assert "line 12" in report
    assert 'href="#impl~ring5.workspace.covered-101~0"' in report
    assert '<main id="oft-native-report">' in report
    assert (
        f'<meta name="ring5-inventory-sha256" '
        f'content="{inventory_fingerprint(small_inventory)}">'
    ) in report
    assert (
        f'<meta name="ring5-evidence-sha256" ' f'content="{evidence_fingerprint(source_markers)}">'
    ) in report


def test_status_views_expose_every_lifecycle_without_rewriting_oft_results(
    native_oft_html: str,
    small_inventory: dict[str, Any],
) -> None:
    """Status views filter inventory metadata while OFT stays authoritative."""
    # [test->req~ring5.trace.future-status-reporting~1]
    report = enhance_oft_html(native_oft_html, small_inventory)

    for status in ("approved", "proposed", "draft", "in-development", "blocked"):
        assert f'data-status-view="{status}"' in report
        assert f'<option value="{status}">' in report
    assert 'data-status="approved" data-coverage="covered"' in report
    assert 'data-status="proposed" data-coverage="uncovered"' in report
    assert report.index("Requirement status views") < report.index('<main id="oft-native-report">')
    assert "native covered detail" in report
    assert "native uncovered detail" in report


def test_future_requirement_card_exposes_its_implementation_branch(
    native_oft_html: str,
    small_inventory: dict[str, Any],
) -> None:
    """The human report keeps branch ownership beside its requirement."""
    # [test->req~ring5.trace.branch-association~1]
    report = enhance_oft_html(native_oft_html, small_inventory)

    assert "Implementation branch <code>006-workspace-future</code>" in report
    assert (
        'data-search="workspace.future future behavior still needs trace coverage. future '
        '006-workspace-future"' in report
    )


def test_human_labels_are_html_escaped(
    native_oft_html: str, small_inventory: dict[str, Any]
) -> None:
    """Inventory text cannot inject markup into the OFT-derived report."""
    inventory = deepcopy(small_inventory)
    inventory["features"][0]["title"] = "<script>alert(1)</script>"

    report = enhance_oft_html(native_oft_html, inventory)

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in report
    assert "<script>alert(1)</script>" not in report


def test_missing_native_requirement_is_rejected(
    native_oft_html: str, small_inventory: dict[str, Any]
) -> None:
    """A human report cannot hide an item that native OFT did not import."""
    # [test->req~ring5.trace.human-html-report~1]
    incomplete = native_oft_html.replace(
        '<section class="sitem" id="req~ring5.workspace.future~1">',
        '<section class="sitem" id="req~ring5.unexpected~1">',
    )

    with pytest.raises(OftHtmlReportError, match="missing requirements: workspace.future"):
        extract_oft_coverage(incomplete, small_inventory)


def test_non_oft_html_is_rejected(small_inventory: dict[str, Any]) -> None:
    """The enhancer never creates a parallel report from arbitrary HTML."""
    # [test->req~ring5.trace.human-html-report~1]
    with pytest.raises(OftHtmlReportError, match="missing artifact sections"):
        enhance_oft_html("<html><body></body></html>", small_inventory)
