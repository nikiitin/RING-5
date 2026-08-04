"""Tests for session-scoped background parsing jobs."""

from __future__ import annotations

import fcntl
import shutil
import sqlite3
import threading
import time
from collections.abc import Callable, Generator, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.application_api import ApplicationAPI
from src.core.models import (
    InvalidParseJobTransition,
    ParseBatchResult,
    ParseFileSignature,
    ParseJobConflictError,
    ParseJobNotConsumableError,
    ParseJobNotFoundError,
    ParseJobStatus,
)
from src.core.models.parse_job_models import JsonValue
from src.core.services.parse_job_service import (
    ParseJobService,
    build_parse_job_request,
)
from src.core.services.parse_job_store import (
    MAX_ERROR_LENGTH,
    MAX_STORED_ERRORS,
    ParseJobStore,
)
from src.core.services.parse_job_workspace import ParseJobRuntimeWorkspace


def _stats_tree(root: Path, contents: Sequence[str] = ("simTicks 1\n",)) -> None:
    for index, content in enumerate(contents):
        stats = root / f"run-{index}" / "stats.txt"
        stats.parent.mkdir(parents=True)
        stats.write_text(content)


def _completed_future(
    result: dict[str, Any] | None = None,
    error: BaseException | None = None,
) -> Future[dict[str, Any]]:
    future: Future[dict[str, Any]] = Future()
    if error is not None:
        future.set_exception(error)
    else:
        future.set_result(result or {})
    return future


def _wait_for_status(
    service: ParseJobService,
    job_id: str,
    statuses: set[ParseJobStatus],
    timeout: float = 5.0,
) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = service.get(job_id)
        if snapshot is not None and snapshot.status in statuses:
            return snapshot
        time.sleep(0.01)
    snapshot = service.get(job_id)
    raise AssertionError(f"Timed out waiting for {statuses}; last snapshot={snapshot}")


class _ServiceFactory:
    def __init__(self, root: Path) -> None:
        self.runtime = ParseJobRuntimeWorkspace(root / "jobs")
        self.services: list[ParseJobService] = []

    def create(
        self,
        submit: Callable[
            [str, str, Sequence[JsonValue], str, str, list[JsonValue] | None, bool],
            ParseBatchResult,
        ],
        *,
        finalize: (
            Callable[
                [str, ParseBatchResult, list[dict[str, Any]], bool, str],
                str | None,
            ]
            | None
        ) = None,
        publish: Callable[[str, str], str] | None = None,
    ) -> ParseJobService:
        pool = self.runtime.jobs_root.parent / "recent"
        pool.mkdir(exist_ok=True)

        def default_finalize(
            output_dir: str,
            _batch: ParseBatchResult,
            _results: list[dict[str, Any]],
            _complete: bool,
            _strategy: str,
        ) -> str:
            output = Path(output_dir) / "final.csv"
            output.write_text("simTicks\n1\n")
            return str(output)

        def default_publish(source: str, name: str) -> str:
            destination = pool / name
            shutil.copyfile(source, destination)
            return str(destination)

        service = ParseJobService(
            submit,
            finalize or default_finalize,
            publish or default_publish,
            runtime_workspace=self.runtime,
        )
        self.services.append(service)
        return service

    def close(self) -> None:
        for service in self.services:
            service.close()
        self.runtime.close()


@pytest.fixture
def service_factory(tmp_path: Path) -> Generator[_ServiceFactory, None, None]:
    factory = _ServiceFactory(tmp_path)
    yield factory
    factory.close()


class TestParseJobFingerprint:
    def test_deterministic_and_ignores_ui_ids(self, tmp_path: Path) -> None:
        _stats_tree(tmp_path)
        first = build_parse_job_request(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[{"name": "simTicks", "type": "scalar", "_id": "one", "repeat": 1}],
            strategy_type="simple",
        )
        second = build_parse_job_request(
            stats_path=str(tmp_path / "."),
            stats_pattern=" stats.txt ",
            variables=[{"repeat": 1, "_id": "two", "type": "scalar", "name": "simTicks"}],
            strategy_type="simple",
        )
        assert first.fingerprint == second.fingerprint

    def test_background_adapter_preserves_stat_config_source_name(self) -> None:
        parser = MagicMock()
        parser.submit_parse_async.return_value = ParseBatchResult([], ["alias"])
        api = ApplicationAPI(parser=parser)
        try:
            api._submit_background_parse(
                "/stats",
                "stats.txt",
                [
                    {
                        "name": "alias",
                        "source_name": "system.cpu.ipc",
                        "type": "scalar",
                        "params": {},
                    }
                ],
                "/output",
                "simple",
                None,
                False,
            )
        finally:
            api.close()

        submitted = parser.submit_parse_async.call_args.args[2]
        assert submitted[0].name == "alias"
        assert submitted[0].source_name == "system.cpu.ipc"

    def test_variable_order_is_fingerprint_sensitive(self, tmp_path: Path) -> None:
        _stats_tree(tmp_path)
        common = {
            "stats_path": str(tmp_path),
            "stats_pattern": "stats.txt",
            "strategy_type": "simple",
        }
        first = build_parse_job_request(
            **common,
            variables=[
                {"name": "a", "type": "scalar"},
                {"name": "b", "type": "scalar"},
            ],
        )
        second = build_parse_job_request(
            **common,
            variables=[
                {"name": "b", "type": "scalar"},
                {"name": "a", "type": "scalar"},
            ],
        )
        assert first.fingerprint != second.fingerprint

    def test_uses_bounded_canonical_file_discovery(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fingerprint exactly the paths accepted by canonical discovery."""
        stats = tmp_path / "run" / "stats.txt"
        stats.parent.mkdir()
        stats.write_text("simTicks 1\n")
        discover = MagicMock(return_value=[str(stats)])
        monkeypatch.setattr(
            "src.core.services.parse_job_service.find_stats_files",
            discover,
        )

        request = build_parse_job_request(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )

        discover.assert_called_once_with(str(tmp_path.resolve()), "stats.txt", sort=True)
        assert request.file_signatures == (
            ParseFileSignature(
                path=str(stats.resolve()),
                size=stats.stat().st_size,
                mtime_ns=stats.stat().st_mtime_ns,
            ),
        )

    def test_disappearing_discovered_file_fails_fingerprinting(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Surface a file-removal race instead of caching an incomplete request."""
        missing = tmp_path / "removed" / "stats.txt"
        monkeypatch.setattr(
            "src.core.services.parse_job_service.find_stats_files",
            lambda *_args, **_kwargs: [str(missing)],
        )

        with pytest.raises(FileNotFoundError):
            build_parse_job_request(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=[],
                strategy_type="simple",
            )

    def test_config_and_input_signatures_change_fingerprint(self, tmp_path: Path) -> None:
        _stats_tree(tmp_path)

        def request(strategy: str = "simple") -> Any:
            return build_parse_job_request(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=[{"name": "simTicks", "type": "scalar"}],
                scanned_variables=[{"name": "simTicks", "type": "scalar"}],
                strategy_type=strategy,
            )

        baseline = request()
        assert request("config_aware").fingerprint != baseline.fingerprint
        assert (
            build_parse_job_request(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=[{"name": "simTicks", "type": "scalar"}],
                scanned_variables=[{"name": "simTicks", "type": "scalar"}],
                strategy_type="simple",
                incremental=True,
            ).fingerprint
            != baseline.fingerprint
        )
        assert (
            build_parse_job_request(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=[{"name": "simTicks", "type": "scalar", "repeat": 2}],
                scanned_variables=[{"name": "simTicks", "type": "scalar"}],
                strategy_type="simple",
            ).fingerprint
            != baseline.fingerprint
        )
        assert (
            build_parse_job_request(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=[{"name": "simTicks", "type": "scalar"}],
                scanned_variables=[{"name": "other", "type": "scalar"}],
                strategy_type="simple",
            ).fingerprint
            != baseline.fingerprint
        )
        assert (
            build_parse_job_request(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=[{"name": "simTicks", "type": "scalar"}],
                scanned_variables=[{"name": "simTicks", "type": "scalar"}],
                strategy_type="simple",
                simulator="other",
            ).fingerprint
            != baseline.fingerprint
        )
        assert (
            build_parse_job_request(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=[{"name": "simTicks", "type": "scalar"}],
                scanned_variables=[{"name": "simTicks", "type": "scalar"}],
                strategy_type="simple",
                parser_contract_version="2",
            ).fingerprint
            != baseline.fingerprint
        )

        added = tmp_path / "added" / "stats.txt"
        added.parent.mkdir()
        added.write_text("simTicks 2\n")
        with_added = request()
        assert with_added.fingerprint != baseline.fingerprint

        added.unlink()
        assert request().fingerprint == baseline.fingerprint
        added.write_text("simTicks 2\n")
        with_added = request()

        added.write_text("simTicks 200\n")
        with_changed_size = request()
        assert with_changed_size.fingerprint != with_added.fingerprint

        current = added.stat()
        added.touch()
        assert added.stat().st_mtime_ns != current.st_mtime_ns
        assert request().fingerprint != with_changed_size.fingerprint


class TestParseJobStore:
    def test_connections_close_after_each_operation(self, tmp_path: Path) -> None:
        store = ParseJobStore(tmp_path / "jobs.sqlite3")

        with store._connect() as connection:
            connection.execute("SELECT 1").fetchone()

        with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
            connection.execute("SELECT 1")

    def test_transitions_and_bounded_errors(self, tmp_path: Path) -> None:
        _stats_tree(tmp_path)
        request = build_parse_job_request(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        store = ParseJobStore(tmp_path / "jobs.sqlite3")
        store.create_job("job", request, attempt_dir, 1)
        running = store.transition("job", ParseJobStatus.RUNNING, "Running")
        assert running.started_at is not None

        bounded = store.update_progress("job", completed_files=12, total_files=3, phase="Work")
        assert bounded.completed_files == bounded.total_files == 3

        for index in range(MAX_STORED_ERRORS + 5):
            store.append_error("job", f"{index}-" + ("x" * (MAX_ERROR_LENGTH + 20)))
        snapshot = store.get_job("job")
        assert snapshot is not None
        assert snapshot.error_count == MAX_STORED_ERRORS + 5
        assert len(snapshot.errors) == MAX_STORED_ERRORS
        assert all(len(message) <= MAX_ERROR_LENGTH for message in snapshot.errors)

        store.transition("job", ParseJobStatus.FAILED, "Failed")
        with pytest.raises(InvalidParseJobTransition):
            store.transition("job", ParseJobStatus.RUNNING, "Invalid")

    def test_rejects_unbounded_request_metadata(self, tmp_path: Path) -> None:
        _stats_tree(tmp_path)
        request = build_parse_job_request(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[{"name": "x" * 1_100_000, "type": "scalar"}],
            strategy_type="simple",
        )
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        store = ParseJobStore(tmp_path / "jobs.sqlite3")

        with pytest.raises(ValueError, match="1 MB"):
            store.create_job("large", request, attempt_dir, 1)
        assert store.get_job("large") is None


class TestParseJobFlow:
    # [test->req~ring5.ingestion.session-background-parse~1]

    def test_executor_submission_failure_removes_queued_attempt(
        self,
        tmp_path: Path,
        service_factory: _ServiceFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Leave no phantom queued job when orchestration cannot be scheduled."""
        _stats_tree(tmp_path)
        service = service_factory.create(lambda *_args: ParseBatchResult([], []))
        executor = MagicMock()
        executor.submit.side_effect = RuntimeError("executor unavailable")
        monkeypatch.setattr(service, "_get_executor", lambda: executor)

        with pytest.raises(RuntimeError, match="executor unavailable"):
            service.submit(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=[],
                strategy_type="simple",
            )

        assert service._store.list_jobs() == []
        assert list((service.session_dir / "attempts").iterdir()) == []

    def test_success_consumption_and_session_reuse(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        _stats_tree(tmp_path)
        calls = 0

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            nonlocal calls
            calls += 1
            return ParseBatchResult(
                futures=[_completed_future({"simTicks": {"value": 1}})],
                var_names=["simTicks"],
            )

        service = service_factory.create(submit)
        first = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[{"name": "simTicks", "type": "scalar"}],
            strategy_type="simple",
        )
        assert first.status == ParseJobStatus.QUEUED
        succeeded = _wait_for_status(service, first.job_id, {ParseJobStatus.SUCCEEDED})
        assert succeeded.published_csv_path is not None
        receipt = service.consume(first.job_id)
        assert Path(receipt.csv_path).is_file()
        assert service.get(first.job_id) is None

        reused = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[{"type": "scalar", "name": "simTicks"}],
            strategy_type="simple",
        )
        assert reused.status == ParseJobStatus.SUCCEEDED
        assert reused.cache_hit is True
        assert calls == 1
        reused_receipt = service.consume(reused.job_id)
        assert reused_receipt.reused is True

        other_session = service_factory.create(submit)
        other = other_session.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[{"name": "simTicks", "type": "scalar"}],
            strategy_type="simple",
        )
        _wait_for_status(other_session, other.job_id, {ParseJobStatus.SUCCEEDED})
        assert calls == 2

    def test_failed_consumer_keeps_terminal_job_and_attempt(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        _stats_tree(tmp_path)

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            return ParseBatchResult(
                futures=[_completed_future({"simTicks": {"value": 1}})],
                var_names=["simTicks"],
            )

        service = service_factory.create(submit)
        job = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        terminal = _wait_for_status(service, job.job_id, {ParseJobStatus.SUCCEEDED})
        assert terminal.output_csv_path is not None
        attempt_dir = service._store.get_attempt_dir(job.job_id)

        def fail_to_load(_receipt: Any) -> None:
            raise ValueError("CSV could not be loaded")

        with pytest.raises(ValueError, match="could not be loaded"):
            service.consume(job.job_id, before_cleanup=fail_to_load)

        assert service.get(job.job_id) is not None
        assert attempt_dir.is_dir()
        assert service._store.get_published(job.fingerprint) is None

    def test_identical_active_submission_coalesces_and_different_conflicts(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        _stats_tree(tmp_path)
        release = threading.Event()
        executor = ThreadPoolExecutor(max_workers=1)

        def work() -> dict[str, Any]:
            release.wait()
            return {"simTicks": {"value": 1}}

        running = executor.submit(work)

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            return ParseBatchResult(futures=[running], var_names=["simTicks"])

        service = service_factory.create(submit)
        first = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[{"name": "simTicks", "type": "scalar"}],
            strategy_type="simple",
        )
        duplicate = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[{"name": "simTicks", "type": "scalar"}],
            strategy_type="simple",
        )
        assert duplicate.job_id == first.job_id
        with pytest.raises(ParseJobConflictError):
            service.submit(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=[{"name": "other", "type": "scalar"}],
                strategy_type="simple",
            )
        release.set()
        _wait_for_status(service, first.job_id, {ParseJobStatus.SUCCEEDED})
        executor.shutdown()

    @pytest.mark.parametrize(
        ("futures", "expected"),
        [
            ([], ParseJobStatus.FAILED),
            (
                [_completed_future(error=RuntimeError("file failed"))],
                ParseJobStatus.FAILED,
            ),
            (
                [
                    _completed_future({"simTicks": {"value": 1}}),
                    _completed_future(error=RuntimeError("one bad file")),
                ],
                ParseJobStatus.PARTIAL,
            ),
        ],
    )
    def test_no_work_total_failure_and_partial(
        self,
        tmp_path: Path,
        service_factory: _ServiceFactory,
        futures: list[Future[dict[str, Any]]],
        expected: ParseJobStatus,
    ) -> None:
        _stats_tree(tmp_path)

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            return ParseBatchResult(futures=futures, var_names=["simTicks"])

        service = service_factory.create(submit)
        job = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[{"name": "simTicks", "type": "scalar"}],
            strategy_type="simple",
        )
        terminal = _wait_for_status(service, job.job_id, {expected})
        assert terminal.error_count >= 1
        if expected == ParseJobStatus.PARTIAL:
            with pytest.raises(ParseJobNotConsumableError):
                service.consume(job.job_id)
            receipt = service.consume(job.job_id, allow_partial=True)
            assert Path(receipt.csv_path).is_file()

    def test_missing_cached_csv_is_invalidated_and_reparsed(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        _stats_tree(tmp_path)
        calls = 0

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            nonlocal calls
            calls += 1
            return ParseBatchResult(
                futures=[_completed_future({"simTicks": {"value": calls}})],
                var_names=["simTicks"],
            )

        service = service_factory.create(submit)
        first = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        _wait_for_status(service, first.job_id, {ParseJobStatus.SUCCEEDED})
        receipt = service.consume(first.job_id)
        Path(receipt.csv_path).unlink()

        replacement = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        _wait_for_status(service, replacement.job_id, {ParseJobStatus.SUCCEEDED})
        assert calls == 2

    def test_missing_unconsumed_csv_is_invalidated_and_reparsed(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        """Replace an unusable successful record instead of coalescing with it."""
        _stats_tree(tmp_path)
        calls = 0

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            nonlocal calls
            calls += 1
            return ParseBatchResult(
                futures=[_completed_future({"simTicks": {"value": calls}})],
                var_names=["simTicks"],
            )

        service = service_factory.create(submit)
        first = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        terminal = _wait_for_status(service, first.job_id, {ParseJobStatus.SUCCEEDED})
        assert terminal.published_csv_path is not None
        Path(terminal.published_csv_path).unlink()

        replacement = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )

        assert replacement.job_id != first.job_id
        assert service.get(first.job_id) is None
        _wait_for_status(service, replacement.job_id, {ParseJobStatus.SUCCEEDED})
        assert calls == 2


class TestParseJobCancellationAndRetry:
    def test_cancel_waits_for_running_future_and_never_publishes(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        _stats_tree(tmp_path, ("one\n", "two\n"))
        started = threading.Event()
        release = threading.Event()
        worker = ThreadPoolExecutor(max_workers=1)
        published: list[str] = []
        finalized: list[bool] = []

        def running_work() -> dict[str, Any]:
            started.set()
            release.wait()
            return {"simTicks": {"value": 1}}

        running = worker.submit(running_work)
        pending = worker.submit(lambda: {"simTicks": {"value": 2}})

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            return ParseBatchResult(futures=[running, pending], var_names=["simTicks"])

        def finalize(
            _output: str,
            _batch: ParseBatchResult,
            _results: list[dict[str, Any]],
            _complete: bool,
            _strategy: str,
        ) -> str | None:
            finalized.append(True)
            return None

        def publish(_source: str, name: str) -> str:
            published.append(name)
            return name

        service = service_factory.create(submit, finalize=finalize, publish=publish)
        job = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        assert started.wait(2)
        _wait_for_status(service, job.job_id, {ParseJobStatus.RUNNING})
        try:
            cancelling = service.cancel(job.job_id)
            assert cancelling.status == ParseJobStatus.CANCELLING
            deadline = time.monotonic() + 2
            while not pending.cancelled() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert pending.cancelled()
            current = service.get(job.job_id)
            assert current is not None
            assert current.status == ParseJobStatus.CANCELLING
        finally:
            release.set()
        cancelled = _wait_for_status(service, job.job_id, {ParseJobStatus.CANCELLED})
        assert cancelled.published_csv_path is None
        assert finalized == []
        assert published == []
        worker.shutdown()

    def test_one_session_cannot_cancel_another(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        _stats_tree(tmp_path)
        completed = _completed_future({"simTicks": {"value": 1}})

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            return ParseBatchResult(futures=[completed], var_names=[])

        owner = service_factory.create(submit)
        stranger = service_factory.create(submit)
        job = owner.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        with pytest.raises(ParseJobNotFoundError):
            stranger.cancel(job.job_id)
        owner.cancel(job.job_id)

    def test_retry_requires_action_and_recomputes_changed_inputs(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        _stats_tree(tmp_path)
        calls = 0

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            nonlocal calls
            calls += 1
            if calls == 1:
                return ParseBatchResult(
                    futures=[_completed_future(error=RuntimeError("bad"))],
                    var_names=[],
                )
            return ParseBatchResult(
                futures=[_completed_future({"simTicks": {"value": 2}})],
                var_names=["simTicks"],
            )

        service = service_factory.create(submit)
        first = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        failed = _wait_for_status(service, first.job_id, {ParseJobStatus.FAILED})
        ordinary_submit = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        assert ordinary_submit.job_id == failed.job_id
        assert calls == 1

        stats_file = tmp_path / "run-0" / "stats.txt"
        stats_file.write_text("simTicks 2000\n")
        retried = service.retry(failed.job_id)
        assert retried.attempt == 2
        assert retried.fingerprint != failed.fingerprint
        assert service.get(failed.job_id) is None
        _wait_for_status(service, retried.job_id, {ParseJobStatus.SUCCEEDED})
        assert calls == 2


class TestParseJobCleanup:
    def test_reset_discards_active_job_after_running_file_returns(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        _stats_tree(tmp_path)
        started = threading.Event()
        release = threading.Event()
        worker = ThreadPoolExecutor(max_workers=1)
        published: list[str] = []

        def work() -> dict[str, Any]:
            started.set()
            release.wait()
            return {"simTicks": {"value": 1}}

        running = worker.submit(work)

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            return ParseBatchResult(futures=[running], var_names=["simTicks"])

        service = service_factory.create(
            submit,
            publish=lambda _source, name: published.append(name) or name,
        )
        job = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        assert started.wait(2)
        _wait_for_status(service, job.job_id, {ParseJobStatus.RUNNING})
        service.reset()
        assert service.get(job.job_id) is not None
        release.set()
        deadline = time.monotonic() + 3
        while service.get(job.job_id) is not None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert service.get(job.job_id) is None
        assert published == []
        worker.shutdown()

    def test_reset_removes_terminal_metadata_but_preserves_recent_csv(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        _stats_tree(tmp_path)

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            return ParseBatchResult(
                futures=[_completed_future({"simTicks": {"value": 1}})],
                var_names=["simTicks"],
            )

        service = service_factory.create(submit)
        job = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        terminal = _wait_for_status(service, job.job_id, {ParseJobStatus.SUCCEEDED})
        assert terminal.published_csv_path is not None
        recent = Path(terminal.published_csv_path)
        service.reset()
        assert service.get(job.job_id) is None
        assert recent.is_file()

    def test_close_waits_for_running_parse_before_deleting_session(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        _stats_tree(tmp_path)
        started = threading.Event()
        release = threading.Event()
        worker = ThreadPoolExecutor(max_workers=1)
        running = worker.submit(
            lambda: (
                started.set(),
                release.wait(),
                {"simTicks": {"value": 1}},
            )[-1]
        )

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            return ParseBatchResult(futures=[running], var_names=["simTicks"])

        service = service_factory.create(submit)
        job = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        assert started.wait(2)
        _wait_for_status(service, job.job_id, {ParseJobStatus.RUNNING})
        deadline = time.monotonic() + 2
        while job.job_id not in service._file_futures and time.monotonic() < deadline:
            time.sleep(0.01)
        assert job.job_id in service._file_futures
        session_dir = service.session_dir
        close_thread = threading.Thread(target=service.close)
        close_thread.start()
        time.sleep(0.05)
        assert close_thread.is_alive()
        assert session_dir.exists()
        release.set()
        close_thread.join(3)
        assert not close_thread.is_alive()
        assert not session_dir.exists()
        worker.shutdown()

    def test_dismiss_and_close_remove_transient_workspaces(
        self, tmp_path: Path, service_factory: _ServiceFactory
    ) -> None:
        _stats_tree(tmp_path)

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            return ParseBatchResult(futures=[], var_names=[])

        service = service_factory.create(submit)
        session_dir = service.session_dir
        job = service.submit(
            stats_path=str(tmp_path),
            stats_pattern="stats.txt",
            variables=[],
            strategy_type="simple",
        )
        _wait_for_status(service, job.job_id, {ParseJobStatus.FAILED})
        attempt_dir = service._store.get_attempt_dir(job.job_id)
        service.dismiss(job.job_id)
        assert not attempt_dir.exists()
        assert session_dir.exists()
        service.close()
        assert not session_dir.exists()

    def test_orphan_cleanup_preserves_an_active_runtime(self, tmp_path: Path) -> None:
        jobs_root = tmp_path / "jobs"
        stale = jobs_root / "stale"
        stale.mkdir(parents=True)
        (stale / "runtime.lock").write_text("")

        active = jobs_root / "active"
        active.mkdir()
        active_lock = (active / "runtime.lock").open("a+")
        fcntl.flock(active_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        runtime = ParseJobRuntimeWorkspace(jobs_root)
        try:
            assert not stale.exists()
            assert active.exists()
            assert runtime.runtime_dir.exists()
        finally:
            runtime.close()
            fcntl.flock(active_lock.fileno(), fcntl.LOCK_UN)
            active_lock.close()

    def test_graceful_runtime_shutdown_closes_registered_sessions(self, tmp_path: Path) -> None:
        runtime = ParseJobRuntimeWorkspace(tmp_path / "jobs")

        def submit(
            _path: str,
            _pattern: str,
            _variables: Sequence[JsonValue],
            _output: str,
            _strategy: str,
            _scanned: list[JsonValue] | None,
            _incremental: bool,
        ) -> ParseBatchResult:
            return ParseBatchResult(futures=[], var_names=[])

        service = ParseJobService(
            submit,
            lambda _output, _results, _strategy, _names: None,
            lambda _source, name: name,
            runtime_workspace=runtime,
        )
        session_dir = service.session_dir

        runtime.close()

        assert not session_dir.exists()
        with pytest.raises(RuntimeError, match="closed"):
            service.submit(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=[],
                strategy_type="simple",
            )
