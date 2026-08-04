"""Incremental parsing coverage for the session background orchestrator."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from src.core.models import IncrementalParseBatchResult, ParseJobStatus
from src.core.models.parse_job_models import JsonValue
from src.core.services.parse_job_service import ParseJobService
from src.core.services.parse_job_workspace import ParseJobRuntimeWorkspace


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
