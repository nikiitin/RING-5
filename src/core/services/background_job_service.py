"""Thread-safe session-owned background-job tracking and execution."""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import partial
from typing import Any, cast

from src.core.common.security_limits import (
    MAX_BACKGROUND_JOB_ERROR_LENGTH,
    MAX_BACKGROUND_JOB_ERRORS,
    MAX_BACKGROUND_JOB_LABEL_LENGTH,
    MAX_BACKGROUND_JOBS,
)
from src.core.models.background_job_models import (
    BackgroundJobInfo,
    BackgroundJobKind,
    BackgroundJobLogEntry,
    BackgroundJobStatus,
)

_RESULT_MISSING = object()
_KINDS: frozenset[str] = frozenset({"scan", "parse", "transformation", "export"})
_TERMINAL: frozenset[str] = frozenset({"cancelled", "completed", "failed"})

FutureFactory = Callable[[], Sequence[Future[Any]]]


@dataclass
class _JobState:
    job_id: str
    kind: BackgroundJobKind
    label: str
    status: BackgroundJobStatus
    total_units: int
    created_at: str
    retry_factory: FutureFactory | None
    retain_result: bool
    completed_units: int = 0
    attempt: int = 1
    started_at: str | None = None
    finished_at: str | None = None
    cancel_requested: bool = False
    errors: list[BackgroundJobLogEntry] = field(default_factory=list)
    futures: tuple[Future[Any], ...] = ()
    result: object = _RESULT_MISSING
    generation: int = 1


class BackgroundJobService:
    """Track bounded job state and execute session-owned callable work."""

    def __init__(self, *, max_workers: int = 2) -> None:
        """Create an empty job center with a lazy bounded worker pool."""
        if not isinstance(max_workers, int) or isinstance(max_workers, bool) or max_workers < 1:
            raise ValueError("Background-job max_workers must be a positive integer.")
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="ring5-background",
        )
        self._jobs: OrderedDict[str, _JobState] = OrderedDict()
        self._lock = threading.RLock()
        self._closed = False

    def submit(
        self,
        kind: BackgroundJobKind,
        label: str,
        operation: Callable[[], Any],
        *,
        retryable: bool = True,
    ) -> BackgroundJobInfo:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Execute one callable asynchronously and retain its completed result."""
        if not callable(operation):
            raise TypeError("Background operation must be callable.")

        def submit_operation() -> Sequence[Future[Any]]:
            return (self._executor.submit(operation),)

        return self._create(
            kind,
            label,
            submit_operation,
            retry_factory=submit_operation if retryable else None,
            retain_result=True,
        )

    def track_futures(
        self,
        kind: BackgroundJobKind,
        label: str,
        futures: Sequence[Future[Any]],
        *,
        retry_factory: FutureFactory | None = None,
    ) -> BackgroundJobInfo:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Track existing futures without retaining their potentially large results."""
        captured = self._validate_futures(futures)
        if retry_factory is not None and not callable(retry_factory):
            raise TypeError("Background-job retry factory must be callable.")
        return self._create(
            kind,
            label,
            lambda: captured,
            retry_factory=retry_factory,
            retain_result=False,
        )

    def list(self) -> tuple[BackgroundJobInfo, ...]:
        """Return newest-first immutable snapshots of every retained job."""
        with self._lock:
            return tuple(self._snapshot(state) for state in reversed(self._jobs.values()))

    def get(self, job_id: str) -> BackgroundJobInfo:
        """Return one immutable job snapshot."""
        with self._lock:
            return self._snapshot(self._state(job_id))

    def cancel(self, job_id: str) -> BackgroundJobInfo:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Request cancellation without claiming already-running work stopped."""
        with self._lock:
            state = self._state(job_id)
            if state.status in _TERMINAL:
                return self._snapshot(state)
            state.cancel_requested = True
            for future in state.futures:
                future.cancel()
            if all(future.done() for future in state.futures):
                self._finish(state, "cancelled")
            else:
                state.status = "cancelling"
            return self._snapshot(state)

    def retry(self, job_id: str) -> BackgroundJobInfo:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Start another attempt of a retryable terminal job."""
        with self._lock:
            state = self._state(job_id)
            if state.status not in _TERMINAL:
                raise RuntimeError("Only a finished background job can be retried.")
            if state.retry_factory is None:
                raise RuntimeError("This background job is not retryable.")
            if self._closed:
                raise RuntimeError("The background-job center is closed.")
            state.attempt += 1
            state.generation += 1
            state.completed_units = 0
            state.started_at = None
            state.finished_at = None
            state.cancel_requested = False
            state.result = _RESULT_MISSING
            try:
                futures = self._validate_futures(state.retry_factory())
            except Exception as exc:
                state.total_units = 0
                self._log_failure(state, exc)
                self._finish(state, "failed")
                return self._snapshot(state)
            self._attach(state, futures)
            return self._snapshot(state)

    def cancel_all(self) -> int:
        """Request cancellation for every active job and return the count."""
        with self._lock:
            active = [
                job_id for job_id, state in self._jobs.items() if state.status not in _TERMINAL
            ]
            for job_id in active:
                self.cancel(job_id)
            return len(active)

    def result(self, job_id: str) -> Any:
        """Return a retained completed result without waiting for active work."""
        with self._lock:
            state = self._state(job_id)
            if state.status not in _TERMINAL:
                raise RuntimeError("Background job is still running.")
            if state.status != "completed":
                detail = state.errors[-1].message if state.errors else state.status
                raise RuntimeError(f"Background job did not complete successfully: {detail}")
            if not state.retain_result:
                raise RuntimeError("This result remains available from its original job handle.")
            if state.result is _RESULT_MISSING:
                raise RuntimeError("The completed background-job result is unavailable.")
            return state.result

    def dismiss_finished(self) -> int:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Remove terminal records and release their retained results."""
        with self._lock:
            finished = [job_id for job_id, state in self._jobs.items() if state.status in _TERMINAL]
            for job_id in finished:
                del self._jobs[job_id]
            return len(finished)

    def close(self, *, wait: bool = False) -> None:
        """Request cancellation and release this center's worker pool."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            for state in self._jobs.values():
                if state.status not in _TERMINAL:
                    state.cancel_requested = True
                    for future in state.futures:
                        future.cancel()
                    state.status = (
                        "cancelled"
                        if all(future.done() for future in state.futures)
                        else "cancelling"
                    )
                    if state.status == "cancelled":
                        state.finished_at = self._now()
        self._executor.shutdown(wait=wait, cancel_futures=True)

    def _create(
        self,
        kind: BackgroundJobKind,
        label: str,
        initial_factory: FutureFactory,
        *,
        retry_factory: FutureFactory | None,
        retain_result: bool,
    ) -> BackgroundJobInfo:
        validated_kind = self._validate_kind(kind)
        validated_label = self._validate_label(label)
        with self._lock:
            if self._closed:
                raise RuntimeError("The background-job center is closed.")
            self._make_room()
            job_id = uuid.uuid4().hex
            state = _JobState(
                job_id=job_id,
                kind=validated_kind,
                label=validated_label,
                status="queued",
                total_units=0,
                created_at=self._now(),
                retry_factory=retry_factory,
                retain_result=retain_result,
            )
            self._jobs[job_id] = state
            try:
                futures = self._validate_futures(initial_factory())
            except Exception:
                del self._jobs[job_id]
                raise
            self._attach(state, futures)
            return self._snapshot(state)

    def _attach(self, state: _JobState, futures: tuple[Future[Any], ...]) -> None:
        state.futures = futures
        state.total_units = len(futures)
        state.status = "running" if any(future.running() for future in futures) else "queued"
        state.started_at = self._now() if state.status == "running" else None
        generation = state.generation
        if not futures:
            state.result = () if state.retain_result else _RESULT_MISSING
            self._finish(state, "completed")
            return
        for index, future in enumerate(futures):
            future.add_done_callback(partial(self._settled, state.job_id, generation, index))

    def _settled(
        self,
        job_id: str,
        generation: int,
        index: int,
        future: Future[Any],
    ) -> None:
        # [impl->req~ring5.workspace.background-jobs~1]
        with self._lock:
            state = self._jobs.get(job_id)
            if state is None or state.generation != generation:
                return
            if state.started_at is None:
                state.started_at = self._now()
            state.completed_units += 1
            result: object = _RESULT_MISSING
            if not future.cancelled():
                try:
                    result = future.result()
                    reported_error = self._reported_error(result)
                    if reported_error is not None:
                        self._log_failure(state, reported_error)
                except Exception as exc:
                    self._log_failure(state, exc)
            if state.retain_result and len(state.futures) == 1 and index == 0:
                state.result = result
            if state.completed_units < state.total_units:
                state.status = "cancelling" if state.cancel_requested else "running"
                return
            if state.cancel_requested:
                terminal: BackgroundJobStatus = "cancelled"
            elif state.errors and state.errors[-1].attempt == state.attempt:
                terminal = "failed"
            else:
                terminal = "completed"
            self._finish(state, terminal)
            state.futures = ()

    @staticmethod
    def _reported_error(result: object) -> str | None:
        if isinstance(result, dict):
            value = result.get("error")
        else:
            value = getattr(result, "error", None)
        return str(value) if value else None

    def _finish(self, state: _JobState, status: BackgroundJobStatus) -> None:
        state.status = status
        state.finished_at = self._now()
        if state.started_at is None:
            state.started_at = state.finished_at

    def _log_failure(self, state: _JobState, failure: object) -> None:
        # [impl->req~ring5.workspace.background-jobs~1]
        rendered = " ".join(str(failure).split()) or type(failure).__name__
        state.errors.append(
            BackgroundJobLogEntry(
                timestamp=self._now(),
                attempt=state.attempt,
                message=rendered[:MAX_BACKGROUND_JOB_ERROR_LENGTH],
            )
        )
        if len(state.errors) > MAX_BACKGROUND_JOB_ERRORS:
            del state.errors[: len(state.errors) - MAX_BACKGROUND_JOB_ERRORS]

    def _make_room(self) -> None:
        while len(self._jobs) >= MAX_BACKGROUND_JOBS:
            removable = next(
                (job_id for job_id, state in self._jobs.items() if state.status in _TERMINAL),
                None,
            )
            if removable is None:
                raise RuntimeError("Too many background jobs are active. Wait or cancel one.")
            del self._jobs[removable]

    def _state(self, job_id: object) -> _JobState:
        if not isinstance(job_id, str) or not job_id:
            raise ValueError("Background job ID must be non-empty text.")
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise KeyError(f"Background job {job_id!r} was not found.") from exc

    @staticmethod
    def _validate_futures(futures: Sequence[Future[Any]]) -> tuple[Future[Any], ...]:
        if isinstance(futures, (str, bytes, bytearray)) or not isinstance(futures, Sequence):
            raise TypeError("Background-job futures must be a sequence.")
        captured = tuple(futures)
        if not all(isinstance(future, Future) for future in captured):
            raise TypeError("Every background-job work item must be a Future.")
        return captured

    @staticmethod
    def _validate_kind(kind: object) -> BackgroundJobKind:
        if not isinstance(kind, str) or kind not in _KINDS:
            raise ValueError("Background job kind must be scan, parse, transformation, or export.")
        return cast(BackgroundJobKind, kind)

    @staticmethod
    def _validate_label(label: object) -> str:
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Background job label must be non-empty text.")
        normalized = " ".join(label.split())
        if len(normalized) > MAX_BACKGROUND_JOB_LABEL_LENGTH:
            raise ValueError(
                f"Background job label cannot exceed {MAX_BACKGROUND_JOB_LABEL_LENGTH} characters."
            )
        return normalized

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _snapshot(state: _JobState) -> BackgroundJobInfo:
        result_available = (
            state.status == "completed"
            and state.retain_result
            and state.result is not _RESULT_MISSING
        )
        return BackgroundJobInfo(
            job_id=state.job_id,
            kind=state.kind,
            label=state.label,
            status=state.status,
            completed_units=state.completed_units,
            total_units=state.total_units,
            attempt=state.attempt,
            created_at=state.created_at,
            started_at=state.started_at,
            finished_at=state.finished_at,
            cancel_requested=state.cancel_requested,
            retryable=state.retry_factory is not None,
            result_available=result_available,
            errors=tuple(state.errors),
        )
