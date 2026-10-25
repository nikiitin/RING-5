"""Replacement restoration, parser isolation and persisted identity regressions."""

from __future__ import annotations

import io
import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

from src.core.services.autosave_recovery_service import AutosaveRecoveryService
from src.core.services.background_job_service import BackgroundJobService
from src.core.services.browser_upload_service import BrowserUploadService
from src.core.services.data_services.config_service import ConfigService
from src.core.services.data_services.csv_pool_service import CsvPoolService
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.services.data_services.variable_service import VariableService
from src.core.services.environment_metadata_service import EnvironmentMetadataService
from src.core.services.import_preview_service import ImportPreviewService
from src.core.services.portfolio_bundle_service import PortfolioBundleService
from src.core.state.repositories.parser_state_repository import ParserStateRepository
from src.core.state.repositories.session_repository import SessionRepository
from src.core.state.repository_state_manager import RepositoryStateManager


def test_parser_state_owns_nested_configuration_and_unique_identity() -> None:
    first, second = ParserStateRepository(), ParserStateRepository()
    original = second.get_parse_variables()
    first.get_parse_variables()[0]["name"] = "changed"
    assert second.get_parse_variables() == original
    assert first.get_parse_variables()[0]["_id"] != original[0]["_id"]
    entries = [
        {"name": name, "type": "scalar", "_id": identifier, "metadata": {"x": []}}
        for name, identifier in zip("abcde", ["same", "same", "", None, 3], strict=True)
    ]
    first.set_parse_variables(entries)
    entries[0]["metadata"]["x"].append("external")
    variables = first.get_parse_variables()
    identifiers = [item["_id"] for item in variables]
    assert len(set(identifiers)) == 5
    assert all(isinstance(identifier, str) and identifier for identifier in identifiers)
    assert variables[0]["metadata"] == {"x": []}
    variables[0]["metadata"]["x"].append("external")
    assert first.get_parse_variables()[0]["metadata"] == {"x": []}
    first.set_parse_variables(
        [item for item in first.get_parse_variables() if item["_id"] != "same"]
    )
    assert len(first.get_parse_variables()) == 4
    normalized = VariableService.ensure_variable_ids(entries)
    assert len({item["_id"] for item in normalized}) == 5


@pytest.mark.parametrize("data_csv", ["", '"invalid'])
def test_restore_replaces_existing_data_and_previews(data_csv: str) -> None:
    repository = SessionRepository()
    repository.data_repo.add_dataset("old", pd.DataFrame({"x": [1]}))
    repository.data_repo.set_processed_data(pd.DataFrame({"x": [99]}))
    repository.preview_repo.set_preview("reduction", pd.DataFrame({"x": [88]}))
    report = repository.restore_from_portfolio({"data_csv": data_csv, "plots": []})
    assert repository.data_repo.get_data() is None
    assert repository.data_repo.get_processed_data() is None
    assert repository.data_repo.list_datasets() == ()
    assert not repository.preview_repo.has_preview("reduction")
    assert bool(report.data_error) == bool(data_csv)


def test_parser_strategy_round_trips_and_legacy_restore_defaults() -> None:
    state = RepositoryStateManager()
    state.set_parser_strategy("config_aware")
    payload = PortfolioService(state).serialize_workspace(None, [], {}, 0)
    restored = SessionRepository()
    restored.restore_from_portfolio(json.loads(payload))
    assert restored.parser_repo.get_parser_strategy() == "config_aware"
    restored.restore_from_portfolio({})
    assert restored.parser_repo.get_parser_strategy() == "simple"
    assert restored.parser_repo.get_simulator() == "gem5"


def test_autosave_detects_custom_variable_options_and_empty_selection() -> None:
    variables = ParserStateRepository().get_parse_variables()
    assert not AutosaveRecoveryService._custom_parse_variables(variables)
    variables[0]["repeat"] = 3
    assert AutosaveRecoveryService._custom_parse_variables(variables)
    assert AutosaveRecoveryService._custom_parse_variables([])


def test_csv_metadata_follows_replacement_and_counts_records(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text('name,note\nA,"first\nsecond"\n\n   \n', encoding="utf-8")
    CsvPoolService.clear_caches()
    assert CsvPoolService._get_csv_metadata(str(path))["rows"] == 1
    replacement = tmp_path / "next.csv"
    replacement.write_text("new\n1\n2\n3\n", encoding="utf-8")
    replacement.replace(path)
    metadata = CsvPoolService._get_csv_metadata(str(path))
    assert metadata["columns"] == ["new"]
    assert metadata["rows"] == 3
    path.write_text("changed\n7\n", encoding="utf-8")
    assert CsvPoolService._get_csv_metadata(str(path))["columns"] == ["changed"]


def test_import_aware_offsets_use_utc_and_uint64_keeps_every_bit(tmp_path: Path) -> None:
    path = tmp_path / "time.csv"
    path.write_text(
        "when\n2026-10-20T12:00:00+02:00\n2026-10-20T12:00:00+01:00\n", encoding="utf-8"
    )
    frame = ImportPreviewService.load(ImportPreviewService.preview(str(path)))
    assert frame["when"].dt.hour.tolist() == [10, 11]
    assert str(frame["when"].dt.tz) == "UTC"
    path.write_text("value,label\n18446744073709551615,max\n,missing\n", encoding="utf-8")
    frame = ImportPreviewService.load(ImportPreviewService.preview(str(path)))
    assert frame["value"].iloc[0] == 2**64 - 1
    assert str(frame["value"].dtype) == "UInt64"
    assert pd.isna(frame["value"].iloc[1])


@pytest.mark.parametrize(
    "values,message",
    [
        ("2026-10-20T12:00:00+02:00\n2026-10-20T12:00:00", "timezone-aware and naive"),
        ("-1\n18446744073709551615", "negative values"),
    ],
)
def test_import_unrepresentable_mixtures_fail_during_preview(
    tmp_path: Path, values: str, message: str
) -> None:
    path = tmp_path / "mixed.csv"
    path.write_text("value\n" + values + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        ImportPreviewService.preview(str(path))


def test_environment_capture_returns_independent_provenance() -> None:
    before = EnvironmentMetadataService.capture()
    changed = EnvironmentMetadataService.capture()
    changed.dependencies["pandas"] = "incorrect"
    changed.renderers.clear()
    changed.external_tools["perl"] = "incorrect"
    assert EnvironmentMetadataService.capture() == before


def test_bundle_source_checkout_requirements_are_valid() -> None:
    requirements = PortfolioBundleService._requirements(
        {"ring5_version": "source checkout", "dependencies": {"pandas": "3.0.5"}}
    )
    assert "ring5==source checkout" not in requirements
    assert "pandas==3.0.5" in requirements


def test_catalog_skips_bad_encoding_and_serializes_logical_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ConfigService, "get_config_dir", lambda: tmp_path)
    (tmp_path / "invalid.json").write_bytes(b"\xff")
    payload = ConfigService.export_configuration("Shared", "test", [])
    barrier = threading.Barrier(2)

    def importing() -> str:
        barrier.wait(timeout=2)
        try:
            ConfigService.import_configuration(payload)
        except ValueError:
            return "conflict"
        return "saved"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: importing(), range(2)))
    assert sorted(results) == ["conflict", "saved"]
    assert len(ConfigService.load_saved_configs()) == 1


def test_background_external_cancellation_is_visible() -> None:
    service = BackgroundJobService()
    future: Future[object] = Future()
    try:
        job = service.track_futures("scan", "scan", [future])
        assert future.cancel()
        completed = service.get(job.job_id)
        assert completed.status == "cancelled"
        assert completed.started_at is None
    finally:
        service.close(wait=True)


def test_queued_callable_records_actual_start() -> None:
    service = BackgroundJobService(max_workers=1)
    release = threading.Event()
    first_started, second_started = threading.Event(), threading.Event()

    def first() -> None:
        first_started.set()
        assert release.wait(2)

    def second() -> None:
        second_started.set()
        assert release.wait(2)

    try:
        service.submit("export", "first", first)
        assert first_started.wait(2)
        job = service.submit("export", "second", second)
        assert service.get(job.job_id).status == "queued"
        release.set()
        assert second_started.wait(2)
        assert service.get(job.job_id).started_at is not None
    finally:
        release.set()
        service.close(wait=True)


def test_excel_rejects_data_under_unnamed_trailing_header(tmp_path: Path) -> None:
    workbook = Workbook()
    workbook.active.append(["name", None])
    workbook.active.append(["A", 17])
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    with pytest.raises(ValueError, match="beyond its named header"):
        BrowserUploadService.inspect("data.xlsx", "", output.getvalue(), tmp_path)


def test_bundle_requirements_exclude_invalid_distribution_names() -> None:
    requirements = PortfolioBundleService._requirements(
        {
            "ring5_version": "source checkout",
            "dependencies": {".bad": "1", "-bad": "1", "λ": "1", "valid-name": "1.2", "a": "2"},
        }
    )
    assert requirements.splitlines()[-2:] == ["a==2", "valid-name==1.2"]
    assert (
        ".bad==" not in requirements and "-bad==" not in requirements and "λ==" not in requirements
    )
