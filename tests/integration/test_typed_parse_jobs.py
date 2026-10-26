"""Actual worker jobs retain typed output and exact source requests through durable reuse."""

from __future__ import annotations

import math
import os
import sqlite3
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.application_api import ApplicationAPI
from src.core.common import parsed_output
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parse_job_models import ParseJobSnapshot, ParseJobStatus
from src.core.models.parsing_models import StatConfig
from src.core.services.data_services.csv_pool_service import CsvPoolService
from src.core.services.parse_job_store import InvalidStoredOutput, ParseJobStore
from src.core.services.parse_job_workspace import ParseJobRuntimeWorkspace
from src.parsing.registry import SimulatorRegistry


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[ApplicationAPI, None, None]:
    runtime = ParseJobRuntimeWorkspace(tmp_path / "jobs")
    monkeypatch.setattr(ParseJobRuntimeWorkspace, "get_instance", lambda: runtime)
    pool = tmp_path / "recent"
    pool.mkdir()
    monkeypatch.setattr(CsvPoolService, "_pool_dir", pool)
    facade = ApplicationAPI()
    try:
        yield facade
    finally:
        facade.close(wait=True)
        runtime.close()


def _stats(root: Path, tokens: tuple[str, ...] = ("1.25", "0")) -> None:
    for index, token in enumerate(tokens):
        directory = root / f"run-{index}"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "stats.txt").write_text(f"simTicks {token}\n", encoding="utf-8")


def _variables(literal: str) -> list[StatConfig]:
    return [
        StatConfig("value", "scalar", source_name="simTicks", params={"source_type": "scalar"}),
        StatConfig(
            "label", "configuration", params={"source_type": "configuration", "on_empty": literal}
        ),
    ]


def _settled(api: ApplicationAPI, job_id: str) -> ParseJobSnapshot:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        snapshot = api.get_parse_job(job_id)
        assert snapshot is not None
        if snapshot.status.is_terminal:
            return snapshot
        time.sleep(0.01)
    raise AssertionError("Real parse job did not reach a terminal state")


@pytest.mark.parametrize(
    "literal", ["NA", "nan", "NaN", "", "001", "μarch", "  whitespace  ", "95%"]
)
@pytest.mark.parametrize("incremental", [False, True])
def test_real_background_full_incremental_consume_and_cache_preserve_literal_cells(
    api: ApplicationAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    literal: str,
    incremental: bool,
) -> None:
    inputs = tmp_path / "inputs"
    _stats(inputs)
    name = "submit_incremental_parse_async" if incremental else "submit_parse_async"
    submit = MagicMock(wraps=getattr(api._parser, name))
    monkeypatch.setattr(api._parser, name, submit)
    job = api.submit_parse_job(
        str(inputs), "stats.txt", _variables(literal), incremental=incremental
    )
    api.state_manager.set_simulator("editor-only-value")
    terminal = _settled(api, job.job_id)
    assert terminal.status == ParseJobStatus.SUCCEEDED, terminal.errors
    assert terminal.output is not None and terminal.published_output is not None
    expected = ParsedOutputIO.to_frame(terminal.published_output)
    assert expected["value"].tolist() == [1.25, 0.0]
    assert expected["label"].tolist() == [literal, literal]
    assert expected["value"].dtype.kind == "f"
    assert all(type(value) is str for value in expected["label"])
    service = api._get_parse_job_service()
    reopened = ParseJobStore(service.session_dir / "jobs.sqlite3")
    assert reopened.get_job(job.job_id) == terminal
    captured = reopened.get_request(job.job_id).source_context
    assert captured.simulator == "gem5"
    assert captured.strict is False and captured.scan_limit is None
    receipt = api.consume_parse_job(job.job_id)
    assert receipt.output == terminal.published_output
    assert receipt.source_context == captured
    loaded = api.state_manager.get_data()
    assert loaded is not None
    assert loaded.to_dict("list") == expected.to_dict("list")
    cached = api.submit_parse_job(
        str(inputs), "stats.txt", _variables(literal), incremental=incremental
    )
    assert cached.status == ParseJobStatus.SUCCEEDED and cached.cache_hit
    assert cached.completed_files == cached.total_files == 2
    assert cached.progress == 1.0
    assert submit.call_count == 1
    cached_receipt = api.consume_parse_job(cached.job_id)
    assert cached_receipt.output == receipt.output
    assert cached_receipt.source_context == receipt.source_context
    assert ParsedOutputIO.to_frame(cached_receipt.output).to_dict("list") == expected.to_dict(
        "list"
    )


@pytest.mark.parametrize("token", ["nan", "inf", "-inf", "0", "5e-324"])
def test_background_numeric_missing_zero_and_infinity_remain_numbers(
    api: ApplicationAPI,
    tmp_path: Path,
    token: str,
) -> None:
    inputs = tmp_path / "inputs"
    _stats(inputs, (token,))
    job = api.submit_parse_job(str(inputs), "stats.txt", _variables("nan"))
    terminal = _settled(api, job.job_id)
    assert terminal.status == ParseJobStatus.SUCCEEDED, terminal.errors
    receipt = api.consume_parse_job(job.job_id)
    frame = ParsedOutputIO.to_frame(receipt.output)
    value = float(frame["value"].iloc[0])
    assert math.isnan(value) if token == "nan" else value == float(token)
    assert frame["value"].dtype.kind == "f"
    assert frame["label"].tolist() == ["nan"]


@pytest.mark.parametrize("incremental", [False, True])
def test_real_partial_consumption_never_enters_success_cache_and_resubmission_parses_again(
    api: ApplicationAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    incremental: bool,
) -> None:
    inputs = tmp_path / "inputs"
    _stats(inputs, ("1.25", "1e400"))
    name = "submit_incremental_parse_async" if incremental else "submit_parse_async"
    submit = MagicMock(wraps=getattr(api._parser, name))
    monkeypatch.setattr(api._parser, name, submit)
    for attempt in range(2):
        job = api.submit_parse_job(
            str(inputs), "stats.txt", _variables("001"), incremental=incremental
        )
        terminal = _settled(api, job.job_id)
        assert terminal.status == ParseJobStatus.PARTIAL, terminal.errors
        assert terminal.error_count == 1
        assert terminal.output is not None and terminal.published_output is None
        assert not terminal.cache_hit
        assert ParsedOutputIO.to_frame(terminal.output).to_dict("list") == {
            "value": [1.25],
            "label": ["001"],
        }
        receipt = api.consume_parse_job(job.job_id, allow_partial=True)
        assert receipt.status == ParseJobStatus.PARTIAL
        assert ParsedOutputIO.to_frame(receipt.output).to_dict("list") == {
            "value": [1.25],
            "label": ["001"],
        }
        service = api._get_parse_job_service()
        assert service._store.get_published(job.fingerprint) is None
        assert submit.call_count == attempt + 1
        if incremental:
            assert not (service.session_dir / "incremental-cache.json").exists()


@pytest.mark.parametrize("declared", [None, "custom-backend"])
def test_injected_backend_context_records_only_the_explicit_simulator_declaration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    declared: str | None,
) -> None:
    inputs = tmp_path / "inputs"
    _stats(inputs, ("1.25",))
    runtime = ParseJobRuntimeWorkspace(tmp_path / "jobs")
    monkeypatch.setattr(ParseJobRuntimeWorkspace, "get_instance", lambda: runtime)
    pool = tmp_path / "recent"
    pool.mkdir()
    monkeypatch.setattr(CsvPoolService, "_pool_dir", pool)
    facade = ApplicationAPI(parser=SimulatorRegistry.get_parser("gem5"))
    try:
        facade.state_manager.set_simulator("mutable-editor")
        job = facade.submit_parse_job(
            str(inputs), "stats.txt", _variables("NA"), simulator=declared
        )
        terminal = _settled(facade, job.job_id)
        assert terminal.status == ParseJobStatus.SUCCEEDED, terminal.errors
        assert facade.consume_parse_job(job.job_id).source_context.simulator == declared
    finally:
        facade.close(wait=True)
        runtime.close()


@pytest.mark.parametrize("consumed", [False, True])
@pytest.mark.parametrize("corruption", ["csv", "descriptor", "missing"])
def test_corrupt_cached_success_is_invalidated_and_real_work_reparses(
    api: ApplicationAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    consumed: bool,
    corruption: str,
) -> None:
    inputs = tmp_path / "inputs"
    _stats(inputs, ("1.25",))
    submit = MagicMock(wraps=api._parser.submit_parse_async)
    monkeypatch.setattr(api._parser, "submit_parse_async", submit)
    first = api.submit_parse_job(str(inputs), "stats.txt", _variables("NA"))
    terminal = _settled(api, first.job_id)
    assert terminal.status == ParseJobStatus.SUCCEEDED, terminal.errors
    assert terminal.published_output is not None
    service = api._get_parse_job_service()
    if consumed:
        api.consume_parse_job(first.job_id)
    if corruption == "missing":
        Path(terminal.published_output.csv_path).unlink()
    elif corruption == "csv":
        path = Path(terminal.published_output.csv_path)
        path.write_bytes(path.read_bytes().replace(b"1.25", b"9.25"))
    else:
        with sqlite3.connect(service.session_dir / "jobs.sqlite3") as connection:
            if consumed:
                connection.execute("UPDATE published_results SET output_json='{}'")
            else:
                connection.execute(
                    "UPDATE jobs SET published_json='{}' WHERE job_id=?", (first.job_id,)
                )
    second = api.submit_parse_job(str(inputs), "stats.txt", _variables("NA"))
    assert not second.cache_hit and second.job_id != first.job_id
    succeeded = _settled(api, second.job_id)
    assert succeeded.status == ParseJobStatus.SUCCEEDED, succeeded.errors
    receipt = api.consume_parse_job(second.job_id)
    assert ParsedOutputIO.to_frame(receipt.output).to_dict("list") == {
        "value": [1.25],
        "label": ["NA"],
    }
    assert submit.call_count == 2
    assert first.job_id not in service._file_futures
    assert first.job_id not in service._orchestration_futures
    cached = api.submit_parse_job(str(inputs), "stats.txt", _variables("NA"))
    assert cached.cache_hit
    assert submit.call_count == 2


def test_incremental_job_reuses_real_typed_rows_after_one_input_changes(
    api: ApplicationAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = tmp_path / "inputs"
    _stats(inputs)
    batches = []
    submit = api._parser.submit_incremental_parse_async

    def tracked(*args: Any, **kwargs: Any) -> Any:
        batch = submit(*args, **kwargs)
        batches.append(batch)
        return batch

    monkeypatch.setattr(api._parser, "submit_incremental_parse_async", tracked)
    first = api.submit_parse_job(str(inputs), "stats.txt", _variables("001"), incremental=True)
    assert _settled(api, first.job_id).status == ParseJobStatus.SUCCEEDED
    api.consume_parse_job(first.job_id)
    (inputs / "run-1" / "stats.txt").write_text("simTicks 2.5\n")
    second = api.submit_parse_job(str(inputs), "stats.txt", _variables("001"), incremental=True)
    assert _settled(api, second.job_id).status == ParseJobStatus.SUCCEEDED
    receipt = api.consume_parse_job(second.job_id)
    assert len(batches) == 2
    assert len(batches[0].futures) == 2
    assert len(batches[1].futures) == 1
    assert batches[1].reused_file_count == 1
    assert ParsedOutputIO.to_frame(receipt.output).to_dict("list") == {
        "value": [1.25, 2.5],
        "label": ["001", "001"],
    }


def test_background_request_reopen_and_receipt_preserve_owned_scanner_evidence(
    api: ApplicationAPI,
    tmp_path: Path,
) -> None:
    from src.core.common.source_context_codec import SourceContextCodec
    from src.core.models.data_models import ScannedVariableDict

    inputs = tmp_path / "inputs"
    _stats(inputs)
    metadata: ScannedVariableDict = {
        "name": "simTicks",
        "type": "scalar",
        "source_evidence": {"state": "resolved", "kind": "scalar", "basis": "backend_metadata"},
        "entries": [],
        "instances": [{"source_name": "simTicks", "indices": []}],
    }
    job = api.submit_parse_job(str(inputs), "stats.txt", _variables("001"), scanned_vars=[metadata])
    metadata["source_evidence"]["kind"] = "configuration"
    metadata["instances"][0]["source_name"] = "changed"
    terminal = _settled(api, job.job_id)
    assert terminal.status == ParseJobStatus.SUCCEEDED, terminal.errors
    service = api._get_parse_job_service()
    reopened = ParseJobStore(service.session_dir / "jobs.sqlite3")
    context = reopened.get_request(job.job_id).source_context
    stored = SourceContextCodec.scanned_payloads(context)
    expected = {
        "state": "resolved",
        "kind": "scalar",
        "basis": "backend_metadata",
    }
    assert stored[0]["source_evidence"] == expected
    assert stored[0]["instances"] == [{"source_name": "simTicks", "indices": []}]
    assert set(stored[0]) == {"name", "type", "entries", "source_evidence", "instances"}
    stored[0]["source_evidence"]["kind"] = "changed"
    assert SourceContextCodec.scanned_payloads(context)[0]["source_evidence"] == expected
    receipt = api.consume_parse_job(job.job_id)
    assert receipt.source_context == context
    assert (
        SourceContextCodec.scanned_payloads(receipt.source_context)[0]["source_evidence"]
        == expected
    )
    assert ParsedOutputIO.to_frame(receipt.output).to_dict("list") == {
        "value": [1.25, 0.0],
        "label": ["001", "001"],
    }


def test_corrupt_partial_descriptor_stays_visible_without_discard_or_reparse(
    api: ApplicationAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = tmp_path / "inputs"
    _stats(inputs, ("1.25", "1e400"))
    submit = MagicMock(wraps=api._parser.submit_parse_async)
    monkeypatch.setattr(api._parser, "submit_parse_async", submit)
    job = api.submit_parse_job(str(inputs), "stats.txt", _variables("001"))
    terminal = _settled(api, job.job_id)
    assert terminal.status == ParseJobStatus.PARTIAL
    assert terminal.output is not None
    service = api._get_parse_job_service()
    attempt = service._store.get_attempt_dir(job.job_id)
    with sqlite3.connect(service.session_dir / "jobs.sqlite3") as connection:
        connection.execute("UPDATE jobs SET output_json='{}' WHERE job_id=?", (job.job_id,))
    with pytest.raises(InvalidStoredOutput):
        api.submit_parse_job(str(inputs), "stats.txt", _variables("001"))
    with sqlite3.connect(service.session_dir / "jobs.sqlite3") as connection:
        assert connection.execute("SELECT job_id FROM jobs").fetchall() == [(job.job_id,)]
    assert attempt.is_dir() and Path(terminal.output.csv_path).is_file()
    assert submit.call_count == 1
    assert service._store.get_published(job.fingerprint) is None


@pytest.mark.parametrize("partial", [False, True])
def test_pool_promotion_failure_preserves_original_output_and_previous_pool_file(
    api: ApplicationAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    partial: bool,
) -> None:
    inputs = tmp_path / "inputs"
    _stats(inputs, ("1.25", "1e400") if partial else ("1.25",))
    pool = CsvPoolService.get_pool_dir()
    failed_targets: list[Path] = []
    original_replace = os.replace

    def fail_pool_replace(source: str, destination: Path) -> None:
        if destination.parent == pool:
            destination.write_bytes(b"previous pool contents\n")
            failed_targets.append(destination)
            raise OSError("Recent CSV replacement failed")
        original_replace(source, destination)

    local_os = MagicMock(wraps=os)
    local_os.replace.side_effect = fail_pool_replace
    monkeypatch.setattr(parsed_output, "os", local_os)
    job = api.submit_parse_job(str(inputs), "stats.txt", _variables("001"))
    terminal = _settled(api, job.job_id)
    service = api._get_parse_job_service()
    if partial:
        assert terminal.status == ParseJobStatus.PARTIAL
        with pytest.raises(OSError, match="replacement failed"):
            api.consume_parse_job(job.job_id, allow_partial=True)
        assert api.get_parse_job(job.job_id) == terminal
    else:
        assert terminal.status == ParseJobStatus.FAILED
        assert any("replacement failed" in error for error in terminal.errors)
    attempt = service._store.get_attempt_dir(job.job_id)
    originals = list(attempt.glob("*.csv"))
    assert len(originals) == 1
    assert b"1.25" in originals[0].read_bytes()
    assert len(failed_targets) == 1
    assert failed_targets[0].read_bytes() == b"previous pool contents\n"
    assert service._store.get_published(job.fingerprint) is None
    assert not list(pool.glob(".parsed-*.csv"))


@pytest.mark.parametrize("declared", [None, "gem5"])
def test_known_default_backend_retains_actual_simulator_with_matching_declaration(
    api: ApplicationAPI,
    tmp_path: Path,
    declared: str | None,
) -> None:
    inputs = tmp_path / "inputs"
    _stats(inputs, ("1.25",))
    job = api.submit_parse_job(str(inputs), "stats.txt", _variables("NA"), simulator=declared)
    terminal = _settled(api, job.job_id)
    assert terminal.status == ParseJobStatus.SUCCEEDED, terminal.errors
    receipt = api.consume_parse_job(job.job_id)
    assert receipt.source_context.simulator == "gem5"
    assert ParsedOutputIO.to_frame(receipt.output).to_dict("list") == {
        "value": [1.25],
        "label": ["NA"],
    }


def test_known_default_backend_mismatch_rejects_before_job_or_publication(
    api: ApplicationAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = tmp_path / "inputs"
    _stats(inputs, ("1.25",))
    pool = CsvPoolService.get_pool_dir()
    old = pool / "previous.csv"
    old.write_bytes(b"previous complete output\n")
    service = MagicMock(side_effect=AssertionError("Mismatched declaration reached job creation"))
    monkeypatch.setattr(api, "_get_parse_job_service", service)
    with pytest.raises(ValueError, match="does not match"):
        api.submit_parse_job(str(inputs), "stats.txt", _variables("NA"), simulator="other-backend")
    service.assert_not_called()
    assert api._parse_jobs is None
    assert api.get_active_parse_job() is None
    assert list(pool.iterdir()) == [old]
    assert old.read_bytes() == b"previous complete output\n"
    assert (inputs / "run-0" / "stats.txt").read_text() == "simTicks 1.25\n"


def test_simulator_declaration_wrong_type_rejects_before_job_creation(
    api: ApplicationAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = MagicMock(side_effect=AssertionError("Wrong declaration reached job creation"))
    monkeypatch.setattr(api, "_get_parse_job_service", service)
    with pytest.raises(TypeError, match="text or None"):
        api.submit_parse_job(
            "unused",
            "stats.txt",
            _variables("NA"),
            simulator=object(),  # type: ignore[arg-type]
        )
    service.assert_not_called()
    assert api._parse_jobs is None
