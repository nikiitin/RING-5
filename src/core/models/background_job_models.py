"""Immutable background-job status and bounded diagnostic records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BackgroundJobKind = Literal["scan", "parse", "transformation", "export"]
BackgroundJobStatus = Literal[
    "queued",
    "running",
    "cancelling",
    "cancelled",
    "completed",
    "failed",
]


@dataclass(frozen=True)
class BackgroundJobLogEntry:
    """One bounded failure recorded by a background job.

    Attributes:
        timestamp: UTC timestamp in ISO 8601 form.
        attempt: One-based attempt number.
        message: Single-line bounded diagnostic without a traceback.
    """

    timestamp: str
    attempt: int
    message: str


@dataclass(frozen=True)
class BackgroundJobInfo:
    # [impl->req~ring5.workspace.background-jobs~1]
    """Immutable status snapshot for one session-owned background job.

    Attributes:
        job_id: Opaque stable identifier.
        kind: Scan, parse, transformation, or export category.
        label: Human-readable operation label.
        status: Current lifecycle state.
        completed_units: Settled work units in the current attempt.
        total_units: Total work units in the current attempt.
        attempt: One-based attempt number.
        created_at: Initial submission time in UTC.
        started_at: Current-attempt start time, when known.
        finished_at: Current-attempt terminal time, when known.
        cancel_requested: Whether cancellation was requested for this attempt.
        retryable: Whether the operation can be submitted again.
        result_available: Whether the completed result is retained by the job center.
        errors: Bounded failures across attempts, oldest first.
    """

    job_id: str
    kind: BackgroundJobKind
    label: str
    status: BackgroundJobStatus
    completed_units: int
    total_units: int
    attempt: int
    created_at: str
    started_at: str | None
    finished_at: str | None
    cancel_requested: bool
    retryable: bool
    result_available: bool
    errors: tuple[BackgroundJobLogEntry, ...] = ()

    @property
    def progress(self) -> float:
        """Return completion progress from zero through one."""
        if self.total_units == 0:
            return 1.0 if self.terminal else 0.0
        return min(1.0, self.completed_units / self.total_units)

    @property
    def terminal(self) -> bool:
        """Return whether this attempt can no longer change state."""
        return self.status in {"cancelled", "completed", "failed"}
