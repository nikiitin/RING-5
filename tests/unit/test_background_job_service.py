"""Bounded session-owned background-job lifecycle tests."""

from __future__ import annotations

import threading
import time
from concurrent.futures import Future
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import pytest

from src.core.models import BackgroundJobInfo, BackgroundJobLogEntry
from src.core.services.background_job_service import BackgroundJobService


def _settled(service: BackgroundJobService, job_id: str) -> BackgroundJobInfo:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        info = service.get(job_id)
        if info.terminal:
            return info
        time.sleep(0.01)
    raise AssertionError(f"Background job {job_id} did not settle")


def test_callable_job_reports_progress_result_and_can_be_dismissed() -> None:
    # [test->req~ring5.workspace.background-jobs~1]
    service = BackgroundJobService(max_workers=1)
    started = threading.Event()
    release = threading.Event()

    def transform() -> dict[str, int]:
        started.set()
        assert release.wait(1)
        return {"rows": 3}

    try:
        submitted = service.submit("transformation", "  Shape   current table ", transform)
        assert started.wait(1)
        active = service.get(submitted.job_id)
        assert active.label == "Shape current table"
        assert active.kind == "transformation"
        assert active.status in {"queued", "running"}
        assert active.progress == 0.0

        release.set()
        completed = _settled(service, submitted.job_id)
        assert completed.status == "completed"
        assert completed.progress == 1.0
        assert completed.result_available
        assert service.result(submitted.job_id) == {"rows": 3}
        assert service.list() == (completed,)
        assert service.dismiss_finished() == 1
        assert service.list() == ()
    finally:
        service.close(wait=True)


def test_external_progress_errors_and_retry_keep_bounded_attempt_history() -> None:
    # [test->req~ring5.workspace.background-jobs~1]
    service = BackgroundJobService()
    first: Future[Any] = Future()
    second: Future[Any] = Future()
    retry_futures: list[Future[Any]] = []

    def retry() -> tuple[Future[Any], ...]:
        retry_futures.extend([Future(), Future()])
        return tuple(retry_futures)

    try:
        submitted = service.track_futures(
            "scan",
            "Scan simulator files",
            [first, second],
            retry_factory=retry,
        )
        first.set_result(SimpleNamespace(error=None))
        partial = service.get(submitted.job_id)
        assert partial.completed_units == 1
        assert partial.total_units == 2
        assert partial.progress == 0.5

        second.set_result(SimpleNamespace(error="unreadable stats file"))
        failed = service.get(submitted.job_id)
        assert failed.status == "failed"
        assert failed.errors[-1].message == "unreadable stats file"
        assert failed.errors[-1].attempt == 1
        assert not failed.result_available
        with pytest.raises(RuntimeError, match="did not complete"):
            service.result(submitted.job_id)

        retried = service.retry(submitted.job_id)
        assert retried.attempt == 2
        assert retried.retryable
        assert retried.completed_units == 0
        for future in retry_futures:
            future.set_result({"value": 1})
        completed = service.get(submitted.job_id)
        assert completed.status == "completed"
        assert completed.errors == failed.errors
        with pytest.raises(RuntimeError, match="original job handle"):
            service.result(submitted.job_id)
    finally:
        service.close(wait=True)


def test_running_cancellation_is_honest_and_eventually_cancels() -> None:
    service = BackgroundJobService(max_workers=1)
    started = threading.Event()
    release = threading.Event()

    def export() -> bytes:
        started.set()
        assert release.wait(1)
        return b"complete but discarded"

    try:
        job = service.submit("export", "Export figure", export, retryable=False)
        assert started.wait(1)
        cancelling = service.cancel(job.job_id)
        assert cancelling.status == "cancelling"
        assert cancelling.cancel_requested
        assert not cancelling.retryable

        release.set()
        cancelled = _settled(service, job.job_id)
        assert cancelled.status == "cancelled"
        assert cancelled.terminal
        assert service.cancel(job.job_id) == cancelled
        with pytest.raises(RuntimeError, match="did not complete"):
            service.result(job.job_id)
        with pytest.raises(RuntimeError, match="not retryable"):
            service.retry(job.job_id)
    finally:
        service.close(wait=True)


def test_error_log_and_job_catalog_are_bounded() -> None:
    service = BackgroundJobService()

    def failed_future() -> tuple[Future[Any], ...]:
        future: Future[Any] = Future()
        future.set_exception(RuntimeError("x" * 50))
        return (future,)

    try:
        with (
            patch("src.core.services.background_job_service.MAX_BACKGROUND_JOB_ERRORS", 2),
            patch("src.core.services.background_job_service.MAX_BACKGROUND_JOB_ERROR_LENGTH", 8),
        ):
            job = service.track_futures(
                "parse", "Parse", failed_future(), retry_factory=failed_future
            )
            service.retry(job.job_id)
            service.retry(job.job_id)
            failed = service.get(job.job_id)
            assert len(failed.errors) == 2
            assert [entry.attempt for entry in failed.errors] == [2, 3]
            assert all(len(entry.message) == 8 for entry in failed.errors)

        with patch("src.core.services.background_job_service.MAX_BACKGROUND_JOBS", 2):
            oldest = service.track_futures("scan", "Old", [])
            newer = service.track_futures("scan", "New", [])
            newest = service.track_futures("scan", "Newest", [])
            ids = {item.job_id for item in service.list()}
            assert oldest.job_id not in ids
            assert {newer.job_id, newest.job_id} <= ids
    finally:
        service.close(wait=True)


def test_validation_active_limit_and_close_are_explicit() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        BackgroundJobService(max_workers=0)
    service = BackgroundJobService()
    try:
        with pytest.raises(ValueError, match="kind"):
            service.track_futures("unknown", "Job", [])  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="label"):
            service.track_futures("scan", "", [])
        with pytest.raises(TypeError, match="sequence"):
            service.track_futures("scan", "Job", "bad")  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Future"):
            service.track_futures("scan", "Job", [object()])  # type: ignore[list-item]
        with pytest.raises(TypeError, match="retry factory"):
            service.track_futures("scan", "Job", [], retry_factory="bad")  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="callable"):
            service.submit("export", "Job", cast(Any, None))
        with pytest.raises((KeyError, ValueError)):
            service.get("missing")

        active_one: Future[Any] = Future()
        active_two: Future[Any] = Future()
        with patch("src.core.services.background_job_service.MAX_BACKGROUND_JOBS", 2):
            service.track_futures("scan", "One", [active_one])
            service.track_futures("parse", "Two", [active_two])
            with pytest.raises(RuntimeError, match="Too many"):
                service.track_futures("export", "Three", [])
        active_one.cancel()
        active_two.cancel()
    finally:
        service.close(wait=True)
    service.close()
    with pytest.raises(RuntimeError, match="closed"):
        service.track_futures("scan", "Closed", [])


def test_public_job_models_are_immutable_and_human_readable() -> None:
    log = BackgroundJobLogEntry("2026-07-21T10:00:00+00:00", 1, "failed")
    info = BackgroundJobInfo(
        "job",
        "scan",
        "Scan",
        "failed",
        0,
        0,
        1,
        "2026-07-21T10:00:00+00:00",
        None,
        None,
        False,
        True,
        False,
        (log,),
    )
    assert info.terminal
    assert info.progress == 1.0
    with pytest.raises(AttributeError):
        info.label = "Changed"  # type: ignore[misc]
