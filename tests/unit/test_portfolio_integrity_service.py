"""Tests for checksummed and optionally signed portfolio manifests."""

from __future__ import annotations

import copy
import math
from typing import Any

import pytest

from src.core.services.portfolio_integrity_service import (
    PortfolioIntegrityError,
    PortfolioIntegrityService,
)


def _portfolio() -> dict[str, Any]:
    return {
        "schema_version": 4,
        "version": "4.0",
        "timestamp": "2026-07-21T10:00:00+00:00",
        "environment_metadata": {"ring5_version": "1.0"},
        "data_csv": "benchmark,ipc\na,1.2\n",
        "data_semantics": {"ipc": {"unit": "instructions/cycle"}},
        "csv_path": "/results/input.csv",
        "plots": [
            {
                "id": 1,
                "name": "IPC",
                "plot_type": "bar",
                "config": {"x": "benchmark", "y": "ipc"},
                "processed_data": "benchmark,ipc\na,1.2\n",
                "processed_semantics": {"ipc": {"unit": "instructions/cycle"}},
                "pipeline": [],
            }
        ],
        "plot_counter": 1,
        "config": {"theme": "paper"},
        "parse_variables": [],
        "use_parser": False,
        "stats_path": None,
        "stats_pattern": None,
        "scanned_variables": [],
        "manager_history": [],
        "portfolio_history": [],
    }


def _with_manifest(*, key: str | bytes | None = None) -> dict[str, Any]:
    portfolio = _portfolio()
    portfolio["integrity_manifest"] = PortfolioIntegrityService.create_manifest(
        portfolio,
        signing_key=key,
        key_id="research-key",
    )
    return portfolio


def test_checksum_manifest_reports_named_sections_without_claiming_authenticity() -> None:
    # [test->req~ring5.portfolio.signed-manifests~1]
    portfolio = _with_manifest()

    report = PortfolioIntegrityService.verify(portfolio)

    assert report.status == "checksum-valid"
    assert report.safe_to_restore
    assert report.checksum_valid is True
    assert report.signature_present is False
    assert report.signature_valid is None
    assert tuple(section.name for section in report.sections) == (
        "inputs",
        "configuration",
        "outputs",
    )
    assert all(section.matches for section in report.sections)


def test_signature_requires_the_matching_secret_for_authentication() -> None:
    # [test->req~ring5.portfolio.signed-manifests~1]
    portfolio = _with_manifest(key="shared research secret")

    unverified = PortfolioIntegrityService.verify(portfolio)
    wrong = PortfolioIntegrityService.verify(portfolio, signing_key="wrong secret")
    verified = PortfolioIntegrityService.verify(
        portfolio,
        signing_key="shared research secret",
    )

    assert unverified.status == "signature-unverified"
    assert unverified.key_id == "research-key"
    assert wrong.status == "signature-invalid"
    assert wrong.signature_valid is False
    assert not wrong.safe_to_restore
    assert verified.status == "signature-valid"
    assert verified.signature_valid is True


@pytest.mark.parametrize(
    ("mutation", "changed_section"),
    [
        (lambda value: value.__setitem__("data_csv", "benchmark,ipc\na,9.9\n"), "inputs"),
        (lambda value: value["config"].__setitem__("theme", "changed"), "configuration"),
        (
            lambda value: value["plots"][0].__setitem__("processed_data", "benchmark,ipc\na,9.9\n"),
            "outputs",
        ),
    ],
)
def test_modified_content_identifies_the_affected_section(
    mutation: Any,
    changed_section: str,
) -> None:
    # [test->req~ring5.portfolio.signed-manifests~1]
    portfolio = _with_manifest()
    mutation(portfolio)

    report = PortfolioIntegrityService.verify(portfolio)

    assert report.status == "modified"
    assert report.checksum_valid is False
    assert not report.safe_to_restore
    assert {section.name for section in report.sections if not section.matches} == {changed_section}


def test_whole_document_checksum_covers_metadata_outside_named_sections() -> None:
    portfolio = _with_manifest()
    portfolio["timestamp"] = "2026-07-21T11:00:00+00:00"

    report = PortfolioIntegrityService.verify(portfolio)

    assert report.status == "modified"
    assert all(section.matches for section in report.sections)


def test_legacy_and_invalid_manifests_are_explicit() -> None:
    legacy = PortfolioIntegrityService.verify(_portfolio())
    malformed = _portfolio()
    malformed["integrity_manifest"] = {"format": "unknown"}

    invalid = PortfolioIntegrityService.verify(malformed)

    assert legacy.status == "legacy-unverified"
    assert legacy.safe_to_restore
    assert invalid.status == "invalid-manifest"
    assert not invalid.safe_to_restore


def test_restore_policy_blocks_modification_and_requires_verified_signature() -> None:
    signed = _with_manifest(key="shared research secret")
    unverified = PortfolioIntegrityService.verify(signed)
    verified = PortfolioIntegrityService.verify(
        signed,
        signing_key="shared research secret",
    )
    modified = copy.deepcopy(signed)
    modified["config"]["theme"] = "changed"

    with pytest.raises(PortfolioIntegrityError, match="verified signature"):
        PortfolioIntegrityService.require_restorable(
            unverified,
            require_signature=True,
        )
    PortfolioIntegrityService.require_restorable(verified, require_signature=True)
    with pytest.raises(PortfolioIntegrityError, match="does not match"):
        PortfolioIntegrityService.require_restorable(PortfolioIntegrityService.verify(modified))
    with pytest.raises(PortfolioIntegrityError, match="not signed"):
        PortfolioIntegrityService.require_restorable(
            PortfolioIntegrityService.verify(_with_manifest()),
            require_signature=True,
        )


@pytest.mark.parametrize(
    ("key", "key_id", "message"),
    [
        (b"", "key", "cannot be empty"),
        ("secret", "", "non-empty"),
        ("secret", "x" * 129, "128 characters"),
        ("secret", "bad\nkey", "control characters"),
    ],
)
def test_signing_inputs_are_bounded_and_validated(
    key: str | bytes,
    key_id: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        PortfolioIntegrityService.create_manifest(
            _portfolio(),
            signing_key=key,
            key_id=key_id,
        )


def test_non_json_content_is_rejected_before_manifest_creation() -> None:
    portfolio = _portfolio()
    portfolio["config"] = {"invalid": math.nan}

    with pytest.raises(ValueError, match="canonical JSON"):
        PortfolioIntegrityService.create_manifest(portfolio)
