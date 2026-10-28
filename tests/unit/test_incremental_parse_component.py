"""Incremental parsing coverage for the session background orchestrator."""

from __future__ import annotations

import csv
import time
from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path

from src.core.common.stat_config_codec import StatConfigCodec
from src.core.application_api import ApplicationAPI
from src.core.models.parsing_models import IncrementalParseBatchResult, ParseBatchResult
from src.core.models.parse_job_models import ParseJobStatus
from src.core.services.parse_job_service import ParseJobService
from src.core.services.parse_job_workspace import ParseJobRuntimeWorkspace
from src.core.common.input_identity import fingerprint_inputs
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsed_output_models import ParsedFileResult, ParsedOutput
from src.core.models.source_context_models import ParserSourceContext
from tests.helpers.parsed_values import numeric_file


def test_incremental_background_job_finalizes_an_all_reused_batch(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.incremental-parsing~1]
    stats_file = tmp_path / "inputs" / "run" / "stats.txt"
    stats_file.parent.mkdir(parents=True)
    stats_file.write_text("simTicks 100\n", encoding="utf-8")
    batch = IncrementalParseBatchResult(
        futures=(),
        var_names=("simTicks",),
        output_dir=str(tmp_path / "output"),
        strategy_type="simple",
        cache_path=str(tmp_path / "cache.json"),
        configuration_hash="a" * 64,
        fingerprints=((str(stats_file.resolve()), "b" * 64),),
        cached_results=(numeric_file(str(stats_file.resolve()), {"simTicks": 100.0}),),
        changed_files=(),
        removed_files=(),
    )

    def submit(
        source: ParserSourceContext,
        output_dir: str,
        incremental: bool,
    ) -> IncrementalParseBatchResult:
        nonlocal batch
        assert incremental is True
        assert source.stats_pattern == "stats.txt"
        batch = replace(batch, output_dir=output_dir)
        return batch

    def finalize(
        received_batch: ParseBatchResult | IncrementalParseBatchResult,
        results: list[ParsedFileResult],
        complete: bool,
    ) -> ParsedOutput:
        assert received_batch is batch
        assert results == []
        assert complete is True
        assert received_batch.strategy_type == "simple"
        assert isinstance(received_batch, IncrementalParseBatchResult)
        table = ParsedOutputIO.resolve(
            received_batch.cached_results,
            received_batch.var_names,
            tuple(path for path, _ in received_batch.fingerprints),
            complete=complete,
        )
        return ParsedOutputIO.publish(Path(received_batch.output_dir) / "results.csv", table)

    recent = tmp_path / "recent"
    recent.mkdir()

    def publish(source: ParsedOutput, name: str) -> ParsedOutput:
        return ParsedOutputIO.publish(recent / name, ParsedOutputIO.read(source))

    runtime = ParseJobRuntimeWorkspace(tmp_path / "jobs")
    service = ParseJobService(submit, finalize, publish, runtime_workspace=runtime)
    try:
        snapshot = service.submit(
            stats_path=str(stats_file.parent.parent),
            stats_pattern="stats.txt",
            variables=[
                StatConfigCodec.from_draft(
                    {"name": "simTicks", "type": "scalar", "params": {"source_type": "scalar"}}
                )
            ],
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
    failed: Future[ParsedFileResult] = Future()
    failed.set_exception(RuntimeError("changed input failed"))
    batch = IncrementalParseBatchResult(
        futures=(failed,),
        var_names=("simTicks",),
        output_dir=str(tmp_path / "output"),
        strategy_type="simple",
        cache_path=str(tmp_path / "cache.json"),
        configuration_hash="a" * 64,
        fingerprints=(
            (str(cached_file.resolve()), "b" * 64),
            (str(changed_file.resolve()), "c" * 64),
        ),
        cached_results=(numeric_file(str(cached_file.resolve()), {"simTicks": 100.0}),),
        changed_files=(str(changed_file.resolve()),),
        removed_files=(),
    )

    def submit(
        source: ParserSourceContext,
        output_dir: str,
        _incremental: bool,
    ) -> IncrementalParseBatchResult:
        nonlocal batch
        assert source.stats_pattern == "stats.txt"
        batch = replace(batch, output_dir=output_dir)
        return batch

    def finalize(
        received_batch: ParseBatchResult | IncrementalParseBatchResult,
        results: list[ParsedFileResult],
        complete: bool,
    ) -> ParsedOutput:
        assert results == []
        assert complete is False
        assert isinstance(received_batch, IncrementalParseBatchResult)
        table = ParsedOutputIO.resolve(
            received_batch.cached_results,
            received_batch.var_names,
            tuple(path for path, _ in received_batch.fingerprints),
            complete=complete,
        )
        return ParsedOutputIO.publish(Path(received_batch.output_dir) / "results.csv", table)

    recent = tmp_path / "recent"
    recent.mkdir()

    def publish(source: ParsedOutput, name: str) -> ParsedOutput:
        return ParsedOutputIO.publish(recent / name, ParsedOutputIO.read(source))

    runtime = ParseJobRuntimeWorkspace(tmp_path / "jobs")
    service = ParseJobService(submit, finalize, publish, runtime_workspace=runtime)
    try:
        snapshot = service.submit(
            stats_path=str(tmp_path / "inputs"),
            stats_pattern="stats.txt",
            variables=[
                StatConfigCodec.from_draft(
                    {"name": "simTicks", "type": "scalar", "params": {"source_type": "scalar"}}
                )
            ],
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
        futures=(Future(), Future()),
        var_names=("simTicks",),
        output_dir=str(tmp_path / "output"),
        strategy_type="simple",
        cache_path=str(tmp_path / "cache.json"),
        configuration_hash="a" * 64,
        fingerprints=fingerprints,
        cached_results=(numeric_file(str(cached_file.resolve()), {"simTicks": 100.0}),),
        changed_files=(str(successful_file.resolve()), str(failed_file.resolve())),
        removed_files=(),
    )
    api = ApplicationAPI()
    try:
        output_path = api._finalize_background_parse(
            batch,
            [numeric_file(str(successful_file.resolve()), {"simTicks": 200.0})],
            False,
        )
    finally:
        api.close()

    assert output_path is not None
    with Path(output_path.csv_path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [{"simTicks": "100.0"}, {"simTicks": "200.0"}]
    assert not Path(batch.cache_path).exists()
