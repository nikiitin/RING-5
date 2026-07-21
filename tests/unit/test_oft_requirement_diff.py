"""Tests for Git-to-Git OFT requirement and native coverage diffs."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

import pytest

from scripts.diff_oft_inventory import (
    OftRequirementDiffError,
    build_requirement_diff,
    main,
    render_text,
)
from scripts.oft_html_report import inventory_fingerprint


def _feature(requirement_id: str, description: str, test: str) -> dict[str, Any]:
    return {
        "id": requirement_id,
        "group": "traceability",
        "revision": 1,
        "status": "approved",
        "title": requirement_id.title(),
        "description": description,
        "tags": ["traceability"],
        "evidence": {
            "implementation": ["src/example.py::run"],
            "tests": [test],
            "documentation": ["docs/example.md#behavior"],
        },
    }


def _inventory(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "project": "RING-5",
        "groups": [
            {
                "id": "traceability",
                "title": "Traceability",
                "description": "OFT governance.",
                "tags": ["traceability"],
            }
        ],
        "features": features,
        "discovery_bindings": {},
    }


def _report(inventory: dict[str, Any], coverage: dict[str, bool]) -> str:
    requirements = "".join(
        '<section class="sitem" id="req~ring5.{id}~{revision}"><details><summary>'
        '<span class="{result}">result</span></summary></details></section>'.format(
            id=feature["id"],
            revision=feature["revision"],
            result="green" if coverage[feature["id"]] else "red",
        )
        for feature in inventory["features"]
    )
    fingerprint = inventory_fingerprint(inventory)
    return (
        '<html><head><meta name="ring5-inventory-sha256" '
        f'content="{fingerprint}"></head><body>'
        '<section id="feat"><section class="sitem" '
        'id="feat~ring5.traceability~1"></section></section>'
        f'<section id="req">{requirements}</section>'
        '<section id="impl"></section><section id="test"></section>'
        '<section id="uman"></section></body></html>'
    )


def _write_state(repository: Path, inventory: dict[str, Any], coverage: dict[str, bool]) -> None:
    inventory_path = repository / "spec" / "oft" / "inventory.json"
    report_path = repository / "spec" / "oft" / "generated" / "report.html"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    report_path.write_text(_report(inventory, coverage), encoding="utf-8")


@pytest.fixture
def diff_repository(tmp_path: Path) -> Path:
    """Create a repository with committed base OFT state and changed working state."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "RING-5 Test"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "ring5@example.invalid"], cwd=tmp_path, check=True
    )
    base = _inventory(
        [
            _feature("trace.alpha", "Original behavior.", "tests/test.py::test_alpha"),
            _feature("trace.obsolete", "Removed behavior.", "tests/test.py::test_old"),
        ]
    )
    _write_state(tmp_path, base, {"trace.alpha": True, "trace.obsolete": False})
    subprocess.run(["git", "add", "spec/oft"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=tmp_path, check=True)

    current = _inventory(
        [
            _feature("trace.alpha", "Clarified behavior.", "tests/test.py::test_alpha_v2"),
            _feature("trace.beta", "Added behavior.", "tests/test.py::test_beta"),
        ]
    )
    _write_state(tmp_path, current, {"trace.alpha": False, "trace.beta": True})
    return tmp_path


def test_requirement_diff_compares_git_catalog_and_native_oft_reports(
    diff_repository: Path,
) -> None:
    """Added, removed, field changes, and OFT coverage transitions remain distinct."""
    # [test->req~ring5.trace.requirement-diff~1]
    diff = build_requirement_diff(diff_repository, "HEAD")

    assert diff.added == ("trace.beta",)
    assert diff.removed == ("trace.obsolete",)
    assert len(diff.changed) == 1
    assert diff.changed[0].requirement_id == "trace.alpha"
    assert diff.changed[0].fields == ("description", "evidence.tests")
    assert diff.covered == ("trace.beta",)
    assert diff.uncovered == ("trace.alpha",)
    assert diff.newly_covered == ()
    assert diff.newly_uncovered == ("trace.alpha",)
    text = render_text(diff)
    assert "Changed (1)" in text
    assert "Covered now (native OFT) (1)" in text


def test_requirement_diff_json_is_stable_and_machine_readable(
    diff_repository: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI exposes deterministic JSON without weakening the human default."""
    # [test->req~ring5.trace.requirement-diff~1]
    assert main(["HEAD", "--repository", str(diff_repository), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"] == {
        "added": 1,
        "changed": 1,
        "covered": 1,
        "newly_covered": 0,
        "newly_uncovered": 1,
        "removed": 1,
        "uncovered": 1,
    }
    assert payload["changed"] == [
        {"fields": ["description", "evidence.tests"], "id": "trace.alpha"}
    ]


def test_requirement_diff_rejects_stale_reports_and_unknown_revisions(
    diff_repository: Path,
) -> None:
    """Coverage is never inferred when either native report is stale or unavailable."""
    # [test->req~ring5.trace.requirement-diff~1]
    report = diff_repository / "spec" / "oft" / "generated" / "report.html"
    report.write_text(
        report.read_text(encoding="utf-8").replace('content="', 'content="bad'), encoding="utf-8"
    )

    with pytest.raises(OftRequirementDiffError, match="does not match its inventory fingerprint"):
        build_requirement_diff(diff_repository, "HEAD")
    with pytest.raises(OftRequirementDiffError):
        build_requirement_diff(diff_repository, "revision-that-does-not-exist")
