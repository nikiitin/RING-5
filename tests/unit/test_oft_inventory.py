"""Tests for the generated OpenFastTrace feature inventory."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.generate_oft_inventory import (
    GENERATED_FILENAMES,
    HTML_REPORT_FILENAME,
    InventoryError,
    ROOT,
    check_html_report,
    discover_live_capabilities,
    load_inventory,
    render_inventory,
    validate_inventory,
    write_or_check,
)
from scripts.oft_evidence import collect_evidence_markers
from scripts.oft_html_report import evidence_fingerprint, inventory_fingerprint


def test_repository_inventory_is_valid_and_comprehensive() -> None:
    """Every catalog entry and live extension point has valid trace evidence."""
    # [test->req~ring5.trace.discovery-convergence~1]
    # [test->req~ring5.trace.inventory-generator~1]
    # [test->req~ring5.trace.registry-drift~1]
    inventory = load_inventory()
    live_capabilities = discover_live_capabilities()

    validate_inventory(inventory, live_capabilities=live_capabilities)

    assert len(inventory["groups"]) >= 10
    assert len(inventory["features"]) >= 100
    assert all(live_capabilities.values())


def test_rendered_inventory_is_deterministic_and_complete() -> None:
    """Rendering emits each normative ID exactly once in the expected files."""
    # [test->req~ring5.trace.inventory-generator~1]
    inventory = load_inventory()

    first = render_inventory(inventory)
    second = render_inventory(deepcopy(inventory))

    assert first == second
    assert tuple(first) == GENERATED_FILENAMES
    assert first["requirements.md"].count("`req~ring5.") == len(inventory["features"])
    assert first["features.md"].count("`feat~ring5.") == len(inventory["groups"])


def test_generated_file_check_detects_stale_output(tmp_path: Path) -> None:
    """Check mode distinguishes a matching generation from a stale artifact."""
    rendered = render_inventory(load_inventory())
    write_or_check(rendered, tmp_path, check=False)
    write_or_check(rendered, tmp_path, check=True)
    (tmp_path / "summary.md").write_text("stale\n", encoding="utf-8")

    with pytest.raises(InventoryError, match="stale generated file"):
        write_or_check(rendered, tmp_path, check=True)


def test_html_report_fingerprint_detects_missing_stale_or_non_native_output(
    tmp_path: Path,
) -> None:
    """Offline checks ensure the committed report came from the current inventory and OFT."""
    inventory = load_inventory()
    report = tmp_path / HTML_REPORT_FILENAME

    with pytest.raises(InventoryError, match="Missing OFT HTML report"):
        check_html_report(inventory, tmp_path)

    report.write_text("stale", encoding="utf-8")
    with pytest.raises(InventoryError, match="is stale"):
        check_html_report(inventory, tmp_path)

    marker = '<meta name="ring5-inventory-sha256" ' f'content="{inventory_fingerprint(inventory)}">'
    report.write_text(marker, encoding="utf-8")
    with pytest.raises(InventoryError, match="stale source origins"):
        check_html_report(inventory, tmp_path)

    source_marker = (
        '<meta name="ring5-evidence-sha256" '
        f'content="{evidence_fingerprint(collect_evidence_markers(ROOT))}">'
    )
    report.write_text(marker + source_marker, encoding="utf-8")
    with pytest.raises(InventoryError, match="lacks the native OFT trace"):
        check_html_report(inventory, tmp_path)

    report.write_text(marker + source_marker + '<main id="oft-native-report">', encoding="utf-8")
    check_html_report(inventory, tmp_path)


def test_unbound_live_capability_is_rejected() -> None:
    """A new registry value cannot silently bypass the feature inventory."""
    # [test->req~ring5.trace.discovery-convergence~1]
    # [test->req~ring5.trace.registry-drift~1]
    inventory = load_inventory()
    live_capabilities = dict(discover_live_capabilities())
    live_capabilities["plot_types"] = (*live_capabilities["plot_types"], "future_plot")

    with pytest.raises(InventoryError, match="untracked plot_types capability 'future_plot'"):
        validate_inventory(inventory, live_capabilities=live_capabilities)


def test_tag_that_openfasttrace_cannot_parse_is_rejected() -> None:
    """OFT word tags are enforced so filtering cannot silently return zero items."""
    inventory = load_inventory()
    inventory["features"][0]["tags"].append("invalid-tag")

    with pytest.raises(InventoryError, match="invalid OFT tag 'invalid-tag'"):
        validate_inventory(inventory, live_capabilities=discover_live_capabilities())


def test_proposed_requirement_can_expose_missing_coverage() -> None:
    """Future behavior may be cataloged before its evidence exists."""
    inventory = deepcopy(load_inventory())
    future = deepcopy(inventory["features"][0])
    future["id"] = "workspace.future-example"
    future["title"] = "Future example"
    future["status"] = "proposed"
    future["implementation_branch"] = "006-future-example"
    future["evidence"] = {"implementation": [], "tests": [], "documentation": []}
    inventory["features"].append(future)

    validate_inventory(inventory, live_capabilities=discover_live_capabilities())
    rendered = render_inventory(inventory)

    assert "Status: proposed" in rendered["requirements.md"]
    assert "status_proposed" in rendered["requirements.md"]


def test_all_requirement_lifecycle_statuses_are_valid_and_rendered() -> None:
    """Every report status is accepted and gets a distinct generated view."""
    # [test->req~ring5.trace.future-status-reporting~1]
    inventory = deepcopy(load_inventory())
    example = deepcopy(inventory["features"][0])
    statuses = ("approved", "proposed", "draft", "in-development", "blocked")
    for index, status in enumerate(statuses[1:]):
        feature = deepcopy(example)
        feature["id"] = f"workspace.status-example-{index}"
        feature["title"] = f"Status example {index}"
        feature["status"] = status
        feature["implementation_branch"] = f"006-status-example-{index}"
        feature["evidence"] = {"implementation": [], "tests": [], "documentation": []}
        inventory["features"].append(feature)

    validate_inventory(inventory, live_capabilities=discover_live_capabilities())
    rendered = render_inventory(inventory)

    for status in statuses:
        assert f"Status: {status}" in rendered["requirements.md"]
        assert f"status_{status.replace('-', '_')}" in rendered["requirements.md"]
    assert (
        "| Approved | Proposed | Draft | In development | Blocked | Total |"
        in rendered["summary.md"]
    )


def test_future_requirement_needs_a_valid_implementation_branch() -> None:
    """Future work cannot be cataloged without deterministic branch ownership."""
    # [test->req~ring5.trace.branch-association~1]
    inventory = deepcopy(load_inventory())
    feature = next(item for item in inventory["features"] if item["status"] != "approved")
    feature.pop("implementation_branch")

    with pytest.raises(InventoryError, match="implementation_branch is required"):
        validate_inventory(inventory, live_capabilities=discover_live_capabilities())

    feature["implementation_branch"] = "invalid branch"
    with pytest.raises(InventoryError, match="implementation_branch is invalid"):
        validate_inventory(inventory, live_capabilities=discover_live_capabilities())


def test_branch_associations_are_rendered_in_normative_and_summary_markdown() -> None:
    """Generated reviewers can find each future requirement's implementation branch."""
    # [test->req~ring5.trace.branch-association~1]
    rendered = render_inventory(load_inventory())

    assert "Implementation branch: 006-oft-requirement-history" in rendered["requirements.md"]
    assert (
        "| `trace.requirement-history` | proposed | `006-oft-requirement-history` |"
        in rendered["summary.md"]
    )


def test_duplicate_json_keys_are_rejected(tmp_path: Path) -> None:
    """Ambiguous hand-edited JSON fails loudly instead of losing a value."""
    path = tmp_path / "inventory.json"
    path.write_text('{"schema_version": 1, "schema_version": 2}', encoding="utf-8")

    with pytest.raises(InventoryError, match="duplicate JSON key 'schema_version'"):
        load_inventory(path)


def test_inventory_is_json_serializable_without_custom_types() -> None:
    """Keep the source catalog easy to review and consume by other tooling."""
    inventory = load_inventory()

    assert json.loads(json.dumps(inventory)) == inventory
    assert ROOT.joinpath("spec", "oft", "inventory.json").is_file()
