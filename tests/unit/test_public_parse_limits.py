"""Public parse-boundary tests for incomplete and over-time work."""

from concurrent.futures import Future
from typing import Any
from unittest.mock import MagicMock

import pytest

from ring5._parse import ParseJob, build_stat_configs
from ring5.errors import ParseError, ScanError
from src.core.models import ScanFileResult, ScannedVariable, ScanResult

pytestmark = pytest.mark.public_api


def test_build_stat_configs_rejects_partial_scan() -> None:
    api = MagicMock()
    first: Future[ScanFileResult] = Future()
    first.set_result(
        ScanFileResult(
            file_path="good/stats.txt",
            variables=[ScannedVariable(name="simTicks", type="scalar")],
        )
    )
    second: Future[ScanFileResult] = Future()
    second.set_result(ScanFileResult("large/stats.txt", error="line limit exceeded"))
    api.submit_scan_async.return_value = [first, second]
    api.finalize_scan.return_value = ScanResult(
        variables=[ScannedVariable(name="simTicks", type="scalar")],
        failures=[ScanFileResult("large/stats.txt", error="line limit exceeded")],
        scanned_files=2,
    )

    with pytest.raises(ScanError, match="1 of 2 file.*line limit exceeded"):
        build_stat_configs(api, "results", ["simTicks"])


def test_parse_job_timeout_is_typed_and_cancels_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pending: Future[dict[str, Any]] = Future()
    monkeypatch.setattr("ring5._parse.PARSE_BATCH_TIMEOUT_SECONDS", 0)
    job = ParseJob(
        api=MagicMock(),
        futures=[pending],
        var_names=["simTicks"],
        output_dir="output",
        strategy="simple",
        stats_path="results",
        stats_pattern="stats.txt",
    )

    with pytest.raises(ParseError, match="cancellation succeeded for 1"):
        job.finalize()

    assert pending.cancelled()


def test_unknown_variable_error_reports_actual_scanned_file_count() -> None:
    api = MagicMock()
    futures: list[Future[ScanFileResult]] = []
    for index in range(2):
        future: Future[ScanFileResult] = Future()
        future.set_result(
            ScanFileResult(
                file_path=f"run-{index}/stats.txt",
                variables=[ScannedVariable(name="simTicks", type="scalar")],
            )
        )
        futures.append(future)
    api.submit_scan_async.return_value = futures
    api.finalize_scan.return_value = ScanResult(
        variables=[ScannedVariable(name="simTicks", type="scalar")],
        scanned_files=2,
    )

    with pytest.raises(ScanError, match=r"Scanned 2 file\(s\) \(up to 10 files\)"):
        build_stat_configs(api, "results", ["missing"], scan_limit=10)
