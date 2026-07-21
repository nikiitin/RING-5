"""Tests for independent OFT requirement readiness signals."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.generate_oft_html_report import load_execution_results
from scripts.oft_readiness import assess_requirement_readiness


def _feature() -> dict[str, object]:
    return {
        "id": "trace.example",
        "title": "Example",
        "description": "The behavior shall be reviewable.",
        "evidence": {
            "implementation": ["src/example.py::run"],
            "tests": ["tests/test_example.py::test_run"],
            "documentation": ["docs/example.md#behavior"],
        },
    }


def test_readiness_keeps_evidence_trace_and_execution_independent() -> None:
    """A native green trace cannot stand in for an actual execution result."""
    # [test->req~ring5.trace.readiness-checklist~1]
    checks = assess_requirement_readiness(_feature(), native_covered=True)

    assert [check.key for check in checks] == [
        "specification",
        "implementation",
        "test",
        "documentation",
        "native-trace",
        "execution",
    ]
    assert [check.state for check in checks] == [
        "ready",
        "ready",
        "ready",
        "ready",
        "covered",
        "not-recorded",
    ]

    partial = _feature()
    partial["evidence"] = {
        "implementation": [],
        "tests": ["tests/test_example.py::test_run"],
        "documentation": [],
    }
    states = {
        check.key: check.state
        for check in assess_requirement_readiness(
            partial, native_covered=False, execution_status="failed"
        )
    }
    assert states == {
        "specification": "ready",
        "implementation": "missing",
        "test": "ready",
        "documentation": "missing",
        "native-trace": "uncovered",
        "execution": "failed",
    }


def test_execution_result_document_is_versioned_and_inventory_bounded(
    tmp_path: Path,
) -> None:
    """Only explicit results for known requirement IDs reach the HTML report."""
    # [test->req~ring5.trace.readiness-checklist~1]
    path = tmp_path / "execution.json"
    inventory = {"features": [{"id": "trace.example"}, {"id": "trace.other"}]}
    document = {
        "format": "ring5.oft-execution-results",
        "schema_version": 1,
        "requirements": {"trace.example": "passed", "trace.other": "not-run"},
    }
    path.write_text(json.dumps(document), encoding="utf-8")

    assert load_execution_results(path, inventory) == {
        "trace.example": "passed",
        "trace.other": "not-run",
    }

    document["requirements"] = {"trace.unknown": "passed"}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown execution requirement IDs"):
        load_execution_results(path, inventory)

    document["requirements"] = {"trace.example": "maybe"}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid execution statuses"):
        load_execution_results(path, inventory)
