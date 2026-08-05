"""Incremental parsing coverage for the session background orchestrator."""

from __future__ import annotations

import csv
import shutil
import time
from concurrent.futures import Future
from pathlib import Path
from typing import Any

from src.core.application_api import ApplicationAPI
from src.core.models import IncrementalParseBatchResult, ParseJobStatus
from src.core.models.parse_job_models import JsonValue
from src.core.services.parse_job_service import ParseJobService
from src.core.services.parse_job_workspace import ParseJobRuntimeWorkspace
from src.parsing.framework.incremental_cache import fingerprint_inputs
from src.parsing.gem5.impl.strategies.file_parser_strategy import INTERNAL_SIM_PATH_KEY


def test_incremental_background_job_finalizes_an_all_reused_batch(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.incremental-parsing~1]
    stats_file = tmp_path / "inputs" / "run" / "stats.txt"
    stats_file.parent.mkdir(parents=True)
    stats_file.write_text("simTicks 100\n", encoding="utf-8")
    batch = IncrementalParseBatchResult(
        futures=[],
        var_names=["simTicks"],
        output_dir=str(tmp_path / "output"),
        strategy_type="simple",
        cache_path=str(tmp_path / "cache.json"),
        configuration_hash="a" * 64,
        fingerprints=((str(stats_file.resolve()), "b" * 64),),
        cached_rows=((str(stats_file.resolve()), (("simTicks", "100"),)),),
        changed_files=(),
        removed_files=(),
    )

    def submit(
        _path: str,
        _pattern: str,
        _variables: list[JsonValue],
        _output: str,
        _strategy: str,
        _scanned: list[JsonValue] | None,
        incremental: bool,
    ) -> IncrementalParseBatchResult:
        assert incremental is True
        return batch

    def finalize(
        output_dir: str,
        received_batch: IncrementalParseBatchResult,
        results: list[dict[str, Any]],
        complete: bool,
        strategy: str,
    ) -> str:
        assert received_batch is batch
        assert results == []
        assert complete is True
        assert strategy == "simple"
        output = Path(output_dir) / "results.csv"
        output.write_text("simTicks\n100\n", encoding="utf-8")
        return str(output)

    recent = tmp_path / "recent"
    recent.mkdir()

    def publish(source: str, name: str) -> str:
        destination = recent / name
        shutil.copyfile(source, destination)
        return str(destination)

    runtime = ParseJobRuntimeWorkspace(tmp_path / "jobs")
    service = ParseJobService(submit, finalize, publish, runtime_workspace=runtime)
    try:
        snapshot = service.submit(
            stats_path=str(stats_file.parent.parent),
            stats_pattern="stats.txt",
            variables=[{"name": "simTicks", "type": "scalar"}],
            strategy_type="simple",
            incremental=True,
        )
        deadline = time.monotonic() + 5
        current = service.get(snapshot.job_id)
        while current is not None and current.status.is_active and time.monotonic() < deadline:
            time.sleep(0.01)
            current = service.get(snapshot.job_id)

        assert current is not None
        assert current.status == ParseJobStatus.SUCCEEDED
        assert current.completed_files == 1
        assert current.total_files == 1
    finally:
        service.close()
        runtime.close()


def test_incremental_background_job_keeps_reused_rows_when_changed_work_fails(
    tmp_path: Path,
) -> None:
    """A current cached row makes an otherwise failed incremental batch partial."""
    cached_file = tmp_path / "inputs" / "cached" / "stats.txt"
    changed_file = tmp_path / "inputs" / "changed" / "stats.txt"
    for stats_file, value in ((cached_file, 100), (changed_file, 200)):
        stats_file.parent.mkdir(parents=True)
        stats_file.write_text(f"simTicks {value}\n", encoding="utf-8")
    failed: Future[dict[str, Any]] = Future()
    failed.set_exception(RuntimeError("changed input failed"))
    batch = IncrementalParseBatchResult(
        futures=[failed],
        var_names=["simTicks"],
        output_dir=str(tmp_path / "output"),
        strategy_type="simple",
        cache_path=str(tmp_path / "cache.json"),
        configuration_hash="a" * 64,
        fingerprints=(
            (str(cached_file.resolve()), "b" * 64),
            (str(changed_file.resolve()), "c" * 64),
        ),
        cached_rows=((str(cached_file.resolve()), (("simTicks", "100"),)),),
        changed_files=(str(changed_file.resolve()),),
        removed_files=(),
    )

    def submit(
        _path: str,
        _pattern: str,
        _variables: list[JsonValue],
        _output: str,
        _strategy: str,
        _scanned: list[JsonValue] | None,
        _incremental: bool,
    ) -> IncrementalParseBatchResult:
        return batch

    def finalize(
        output_dir: str,
        _batch: IncrementalParseBatchResult,
        results: list[dict[str, Any]],
        complete: bool,
        _strategy: str,
    ) -> str:
        assert results == []
        assert complete is False
        output = Path(output_dir) / "results.csv"
        output.write_text("simTicks\n100\n", encoding="utf-8")
        return str(output)

    recent = tmp_path / "recent"
    recent.mkdir()

    def publish(source: str, name: str) -> str:
        destination = recent / name
        shutil.copyfile(source, destination)
        return str(destination)

    runtime = ParseJobRuntimeWorkspace(tmp_path / "jobs")
    service = ParseJobService(submit, finalize, publish, runtime_workspace=runtime)
    try:
        snapshot = service.submit(
            stats_path=str(tmp_path / "inputs"),
            stats_pattern="stats.txt",
            variables=[{"name": "simTicks", "type": "scalar"}],
            strategy_type="simple",
            incremental=True,
        )
        deadline = time.monotonic() + 5
        current = service.get(snapshot.job_id)
        while current is not None and current.status.is_active and time.monotonic() < deadline:
            time.sleep(0.01)
            current = service.get(snapshot.job_id)

        assert current is not None
        assert current.status == ParseJobStatus.PARTIAL
        assert current.completed_files == 2
        assert current.total_files == 2
        assert current.output_csv_path is not None
    finally:
        service.close()
        runtime.close()


def test_gem5_partial_incremental_output_retains_valid_rows_without_updating_cache(
    tmp_path: Path,
) -> None:
    """Partial finalization merges successful and reused rows but leaves cache untouched."""
    inputs = tmp_path / "inputs"
    cached_file = inputs / "cached" / "stats.txt"
    successful_file = inputs / "successful" / "stats.txt"
    failed_file = inputs / "failed" / "stats.txt"
    for stats_file, value in (
        (cached_file, 100),
        (successful_file, 200),
        (failed_file, 300),
    ):
        stats_file.parent.mkdir(parents=True)
        stats_file.write_text(f"simTicks {value}\n", encoding="utf-8")

    fingerprints = fingerprint_inputs(
        [str(cached_file), str(successful_file), str(failed_file)],
        "simple",
    )
    batch = IncrementalParseBatchResult(
        futures=[],
        var_names=["simTicks"],
        output_dir=str(tmp_path / "output"),
        strategy_type="simple",
        cache_path=str(tmp_path / "cache.json"),
        configuration_hash="a" * 64,
        fingerprints=fingerprints,
        cached_rows=((str(cached_file.resolve()), (("simTicks", "100"),)),),
        changed_files=(str(successful_file.resolve()), str(failed_file.resolve())),
        removed_files=(),
    )
    api = ApplicationAPI()
    try:
        output_path = api._finalize_background_parse(
            batch.output_dir,
            batch,
            [
                {
                    INTERNAL_SIM_PATH_KEY: str(successful_file.resolve()),
                    "simTicks": "200",
                }
            ],
            False,
            "simple",
        )
    finally:
        api.close()

    assert output_path is not None
    with Path(output_path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [{"simTicks": "100"}, {"simTicks": "200"}]
    assert not Path(batch.cache_path).exists()
