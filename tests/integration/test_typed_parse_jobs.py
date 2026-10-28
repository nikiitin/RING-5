"""Actual worker jobs retain typed output and exact source requests through durable reuse."""

from __future__ import annotations

import math
import os
import sqlite3
import time
from collections.abc import Generator
from contextlib import closing
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
    # Instance spies must not shadow methods on the shared application backend.
    monkeypatch.setattr(SimulatorRegistry, "_instances", {})
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
    # [test->req~ring5.ingestion.session-background-parse~1]
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
    assert cached.job_id != job.job_id
    assert cached.completed_files == cached.total_files == 2
    assert cached.progress == 1.0
    assert submit.call_count == 1
    cached_receipt = api.consume_parse_job(cached.job_id)
    assert cached_receipt.job_id != receipt.job_id
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
        with (
            closing(sqlite3.connect(service.session_dir / "jobs.sqlite3")) as connection,
            connection,
        ):
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
    with closing(sqlite3.connect(service.session_dir / "jobs.sqlite3")) as connection, connection:
        connection.execute("UPDATE jobs SET output_json='{}' WHERE job_id=?", (job.job_id,))
    with pytest.raises(InvalidStoredOutput):
        api.submit_parse_job(str(inputs), "stats.txt", _variables("001"))
    with closing(sqlite3.connect(service.session_dir / "jobs.sqlite3")) as connection, connection:
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


@pytest.mark.parametrize("incremental", [False, True])
def test_background_projection_reuses_exact_selected_evidence_not_unrelated_discovery(
    api: ApplicationAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    incremental: bool,
) -> None:
    from concurrent.futures import as_completed
    from copy import deepcopy
    import json
    from src.core.common.source_context_codec import SourceContextCodec
    from src.core.models.parsing_models import ScannedVariable, SourceInstance
    from src.core.models.source_evidence import ResolvedSourceKind
    from src.core.services.parse_job_store import MAX_REQUEST_JSON_BYTES

    inputs = tmp_path / "inputs"
    _stats(inputs)
    scan = api.finalize_scan(
        [future.result() for future in as_completed(api.submit_scan_async(str(inputs), limit=1))]
    )
    assert scan.complete and scan.scanned_files == 1
    actual = [value.to_dict() for value in scan.variables]
    unrelated = ScannedVariable(
        "unused",
        "vector",
        entries=[f"entry{index:05d}_" + "x" * 250 for index in range(5000)],
        source_evidence=ResolvedSourceKind("vector", "backend_metadata"),
        instances=(SourceInstance("unused", ()),),
    ).to_dict()
    catalog = [*actual, unrelated]
    original = deepcopy(catalog)
    assert len(json.dumps(catalog).encode("utf-8")) > MAX_REQUEST_JSON_BYTES
    method = "submit_incremental_parse_async" if incremental else "submit_parse_async"
    submit = MagicMock(wraps=getattr(api._parser, method))
    monkeypatch.setattr(api._parser, method, submit)
    first = api.submit_parse_job(
        str(inputs), "stats.txt", _variables("001"), scanned_vars=catalog, incremental=incremental
    )
    terminal = _settled(api, first.job_id)
    assert terminal.status == ParseJobStatus.SUCCEEDED, terminal.errors
    receipt = api.consume_parse_job(first.job_id)
    assert SourceContextCodec.scanned_payloads(receipt.source_context) == actual
    assert ParsedOutputIO.to_frame(receipt.output).to_dict("list") == {
        "value": [1.25, 0.0],
        "label": ["001", "001"],
    }
    assert catalog == original
    unrelated["entries"].append("later editor-only discovery")
    cached = api.submit_parse_job(
        str(inputs), "stats.txt", _variables("001"), scanned_vars=catalog, incremental=incremental
    )
    assert cached.status == ParseJobStatus.SUCCEEDED and cached.cache_hit
    assert cached.fingerprint == first.fingerprint and cached.job_id != first.job_id
    assert submit.call_count == 1
    reopened = ParseJobStore(api._get_parse_job_service().session_dir / "jobs.sqlite3")
    assert reopened.get_request(cached.job_id).source_context == receipt.source_context
    repeated = api.consume_parse_job(cached.job_id)
    assert repeated.source_context == receipt.source_context
    assert repeated.output == receipt.output


def test_selected_oversize_background_evidence_fails_before_fingerprints_or_worker(
    api: ApplicationAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from typing import NoReturn
    from src.core.models.parsing_models import ScannedVariable, SourceInstance
    from src.core.models.source_evidence import ResolvedSourceKind
    from src.core.services import parse_job_service

    inputs = tmp_path / "inputs"
    _stats(inputs)
    record = ScannedVariable(
        "large",
        "vector",
        entries=[f"entry{index:05d}_" + "x" * 250 for index in range(5000)],
        source_evidence=ResolvedSourceKind("vector", "backend_metadata"),
        instances=(SourceInstance("large", ()),),
    ).to_dict()
    config = StatConfig(
        "large", "vector", params={"source_type": "vector", "entries": [record["entries"][0]]}
    )

    def forbidden(*args: object, **kwargs: object) -> NoReturn:
        pytest.fail("Over-budget selected evidence reached fingerprinting or file work")

    monkeypatch.setattr(parse_job_service, "find_stats_files", forbidden)
    monkeypatch.setattr(api._parser, "submit_parse_async", forbidden)
    with pytest.raises(ValueError, match="budget"):
        api.submit_parse_job(str(inputs), "stats.txt", [config], scanned_vars=[record])
    assert api.get_active_parse_job() is None


@pytest.mark.parametrize("selection", ["no-match", "invalid-selected"])
def test_projected_numeric_request_keeps_backend_admission_before_file_work(
    api: ApplicationAPI,
    tmp_path: Path,
    selection: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from typing import NoReturn
    from src.core.common.source_context_codec import SourceContextCodec
    from src.core.models.parsing_models import ScannedVariable, SourceInstance
    from src.core.models.source_evidence import ResolvedSourceKind
    from src.parsing.framework.work_pool import WorkPool

    inputs = tmp_path / "inputs"
    _stats(inputs)
    record = ScannedVariable(
        r"cpu\d+.ipc",
        "vector",
        source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
        instances=(SourceInstance("cpu0.ipc", ("0",)),),
    ).to_dict()
    config = StatConfig(
        "chosen",
        "scalar",
        source_name=(r"missing\d+.ipc" if selection == "no-match" else r"cpu\d+.ipc"),
        is_regex=True,
        params={"source_type": "scalar", "selected_sources": ["cpu9.ipc"]},
    )
    context = SourceContextCodec.parser(
        stats_path=str(inputs),
        stats_pattern="stats.txt",
        strategy_type="simple",
        variables=[config],
        scanned_variables=[record],
        simulator="gem5",
        scan_limit=1,
        strict=False,
    )
    assert SourceContextCodec.variables(context)[0].params["selected_sources"] == ["cpu9.ipc"]
    assert SourceContextCodec.scanned_payloads(context) == (
        [] if selection == "no-match" else [record]
    )

    def forbidden(*args: object, **kwargs: object) -> NoReturn:
        pytest.fail("Invalid numeric selection reached file worker allocation")

    monkeypatch.setattr(WorkPool, "get_instance", forbidden)
    with pytest.raises(ValueError, match="explicit current scan|not a scanned pattern instance"):
        api.submit_parse_async(
            str(inputs),
            "stats.txt",
            SourceContextCodec.variables(context),
            str(tmp_path / "out"),
            scanned_vars=SourceContextCodec.scanned_variables(context),
        )
