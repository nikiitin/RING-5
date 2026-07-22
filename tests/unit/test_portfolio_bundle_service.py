"""Tests for bounded portable analysis bundle creation and validation."""

from __future__ import annotations

import json
import hashlib
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import pytest

from src.core.services.data_services.dataset_snapshot_service import DatasetSnapshotService
from src.core.services.data_services.path_service import PathService
from src.core.services.portfolio_bundle_service import PortfolioBundleService
from src.core.services.portfolio_integrity_service import PortfolioIntegrityService


def _portfolio_bytes(*, signed: bool = False) -> bytes:
    portfolio = {
        "schema_version": 4,
        "version": "4.0",
        "timestamp": "2026-07-21T10:00:00+00:00",
        "environment_metadata": {
            "format_version": 1,
            "ring5_version": "1.0.0",
            "python_version": "3.14.6",
            "python_implementation": "CPython",
            "operating_system": "Linux",
            "architecture": "x86_64",
            "dependencies": {"pandas": "3.0.1", "plotly": "6.5.0"},
            "renderers": {"plotly": "6.5.0"},
            "external_tools": {},
        },
        "data_csv": "benchmark,ipc\nalpha,1.25\n",
        "data_semantics": {},
        "csv_path": "/research/results.csv",
        "plots": [],
        "plot_counter": 0,
        "config": {},
        "parse_variables": [],
        "use_parser": False,
        "stats_path": None,
        "stats_pattern": None,
        "scanned_variables": [],
        "manager_history": [],
        "portfolio_history": [],
    }
    portfolio["integrity_manifest"] = PortfolioIntegrityService.create_manifest(
        portfolio,
        signing_key="shared bundle secret" if signed else None,
        key_id="lab-key",
    )
    return json.dumps(portfolio, indent=2).encode()


def _snapshot_bytes(tmp_path: Path) -> bytes:
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots):
        DatasetSnapshotService.save_snapshot(
            "exact-data",
            pd.DataFrame({"value": pd.Series([1, None], dtype="Int64")}),
            source_dataset="results",
        )
        return DatasetSnapshotService.export_snapshot("exact-data")


def test_bundle_round_trip_carries_required_optional_and_result_artifacts(
    tmp_path: Path,
) -> None:
    # [test->req~ring5.portfolio.portable-bundles~1]
    snapshot = _snapshot_bytes(tmp_path)
    first = PortfolioBundleService.create(
        "paper-a",
        _portfolio_bytes(),
        dataset_snapshot=("exact-data", snapshot),
        results={"figures/ipc.svg": b"<svg/>", "report.html": b"<html></html>"},
    )
    second = PortfolioBundleService.create(
        "paper-a",
        _portfolio_bytes(),
        dataset_snapshot=("exact-data", snapshot),
        results={"report.html": b"<html></html>", "figures/ipc.svg": b"<svg/>"},
    )

    contents = PortfolioBundleService.read(first)

    assert first == second
    assert contents.info.name == "paper-a"
    assert contents.info.portfolio_integrity.status == "checksum-valid"
    assert contents.info.source_count == 1
    assert contents.info.requirement_count == 3
    assert contents.info.dataset_snapshot is not None
    assert contents.info.dataset_snapshot.name == "exact-data"
    assert contents.info.result_names == ("figures/ipc.svg", "report.html")
    assert {result.name: result.data for result in contents.results} == {
        "figures/ipc.svg": b"<svg/>",
        "report.html": b"<html></html>",
    }
    assert contents.dataset_snapshot == snapshot
    assert contents.source_manifest["sources"][0]["kind"] == "csv"
    assert "pandas==3.0.1" in contents.requirements
    assert {artifact.role for artifact in contents.info.artifacts} >= {
        "portfolio",
        "source-manifest",
        "environment-metadata",
        "python-requirements",
        "dataset-snapshot",
        "result",
    }


def test_bundle_can_sign_copy_and_enforce_authentication_without_changing_input() -> None:
    # [test->req~ring5.portfolio.portable-bundles~1]
    original = _portfolio_bytes()
    payload = PortfolioBundleService.create(
        "signed-copy",
        original,
        signing_key="new shared secret",
        signing_key_id="transfer-key",
    )

    unverified = PortfolioBundleService.inspect(payload)
    verified = PortfolioBundleService.inspect(
        payload,
        signing_key="new shared secret",
        require_signature=True,
    )

    assert json.loads(original)["integrity_manifest"]["signature"] is None
    assert unverified.portfolio_integrity.status == "signature-unverified"
    assert unverified.portfolio_integrity.key_id == "transfer-key"
    assert verified.portfolio_integrity.status == "signature-valid"
    with pytest.raises(ValueError, match="does not verify"):
        PortfolioBundleService.inspect(
            payload,
            signing_key="wrong shared secret",
            require_signature=True,
        )


def test_member_tampering_and_undeclared_files_are_rejected() -> None:
    # [test->req~ring5.portfolio.portable-bundles~1]
    payload = PortfolioBundleService.create("paper", _portfolio_bytes())
    with ZipFile(BytesIO(payload)) as original:
        members = {name: original.read(name) for name in original.namelist()}
    members["sources/manifest.json"] += b" "
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as changed:
        for name, data in members.items():
            changed.writestr(name, data)
    with pytest.raises(ValueError, match="wrong size|checksum"):
        PortfolioBundleService.inspect(output.getvalue())

    members["sources/manifest.json"] = members["sources/manifest.json"].rstrip()
    members["undeclared.txt"] = b"not declared"
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as changed:
        for name, data in members.items():
            changed.writestr(name, data)
    with pytest.raises(ValueError, match="undeclared"):
        PortfolioBundleService.inspect(output.getvalue())


def test_rechecks_auxiliary_provenance_against_the_verified_portfolio() -> None:
    # [test->req~ring5.portfolio.portable-bundles~1]
    payload = PortfolioBundleService.create("paper", _portfolio_bytes())
    with ZipFile(BytesIO(payload)) as original:
        members = {name: original.read(name) for name in original.namelist()}
    source = json.loads(members["sources/manifest.json"])
    source["sources"][0]["location"] = "/different/source.csv"
    changed_source = json.dumps(source, indent=2, sort_keys=True).encode()
    manifest = json.loads(members["manifest.json"])
    record = next(item for item in manifest["members"] if item["path"] == "sources/manifest.json")
    record["size_bytes"] = len(changed_source)
    record["sha256"] = hashlib.sha256(changed_source).hexdigest()
    members["sources/manifest.json"] = changed_source
    members["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode()
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as changed:
        for name, data in members.items():
            changed.writestr(name, data)

    with pytest.raises(ValueError, match="does not match its portfolio"):
        PortfolioBundleService.inspect(output.getvalue())


@pytest.mark.parametrize(
    "name",
    ["../secret.txt", "/absolute.txt", "results/already-prefixed.txt", "bad\\name.txt"],
)
def test_result_paths_are_confined_to_the_results_directory(name: str) -> None:
    with pytest.raises(ValueError, match="result names"):
        PortfolioBundleService.create(
            "paper",
            _portfolio_bytes(),
            results={name: b"result"},
        )


def test_archive_path_traversal_is_rejected_before_reading_members() -> None:
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", b"{}")
        archive.writestr("../outside", b"unsafe")

    with pytest.raises(ValueError, match="unsafe archive member"):
        PortfolioBundleService.inspect(output.getvalue())
