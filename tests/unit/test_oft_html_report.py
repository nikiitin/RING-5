"""Tests for the RING-5 summary added to native OpenFastTrace HTML."""

from copy import deepcopy
from typing import Any

import pytest

from scripts.oft_html_report import (
    OftHtmlReportError,
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
            },
            {
                "id": "workspace.future",
                "group": "workspace",
                "revision": 1,
                "status": "proposed",
                "title": "Future behavior",
                "description": "Still needs trace coverage.",
                "tags": ["future"],
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
<section id="impl">native implementations</section>
<section id="req">
<section class="sitem" id="req~ring5.workspace.covered~1"><details><summary>
<span class="green">&check;</span> Covered behavior</summary>
<p>native covered detail</p></details></section>
<section class="sitem" id="req~ring5.workspace.future~1"><details><summary>
<span class="red">&#10007;</span> Future behavior</summary>
<p>native uncovered detail</p></details></section>
</section>
<section id="test">native tests</section><section id="uman">native documentation</section>
</main></body></html>"""


def test_coverage_is_read_from_native_oft_markers(
    native_oft_html: str, small_inventory: dict[str, Any]
) -> None:
    """Green and red OFT results, not evidence heuristics, drive the overview."""
    assert extract_oft_coverage(native_oft_html, small_inventory) == {
        "workspace.covered": True,
        "workspace.future": False,
    }


def test_human_layer_preserves_native_trace_and_links_to_it(
    native_oft_html: str, small_inventory: dict[str, Any]
) -> None:
    """The enhanced document keeps canonical items and adds product navigation."""
    report = enhance_oft_html(native_oft_html, small_inventory)

    assert "Feature traceability report" in report
    assert "1 of 2 requirements shown" not in report  # Updated by JS only after filtering.
    assert "2 requirements shown" in report
    assert 'data-coverage="covered"' in report
    assert 'data-coverage="uncovered"' in report
    assert 'href="#req~ring5.workspace.future~1"' in report
    assert "native covered detail" in report
    assert "native uncovered detail" in report
    assert '<main id="oft-native-report">' in report
    assert (
        f'<meta name="ring5-inventory-sha256" '
        f'content="{inventory_fingerprint(small_inventory)}">'
    ) in report


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
    incomplete = native_oft_html.replace(
        '<section class="sitem" id="req~ring5.workspace.future~1">',
        '<section class="sitem" id="req~ring5.unexpected~1">',
    )

    with pytest.raises(OftHtmlReportError, match="missing requirements: workspace.future"):
        extract_oft_coverage(incomplete, small_inventory)


def test_non_oft_html_is_rejected(small_inventory: dict[str, Any]) -> None:
    """The enhancer never creates a parallel report from arbitrary HTML."""
    with pytest.raises(OftHtmlReportError, match="missing artifact sections"):
        enhance_oft_html("<html><body></body></html>", small_inventory)
