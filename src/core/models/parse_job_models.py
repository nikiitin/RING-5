"""Immutable models for session-scoped background parsing jobs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TypeAlias

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class ParseJobStatus(StrEnum):
    """Lifecycle states for a background parse attempt."""

    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_active(self) -> bool:
        """Return whether work may still be executing for this status."""
        return self in {
            ParseJobStatus.QUEUED,
            ParseJobStatus.RUNNING,
            ParseJobStatus.CANCELLING,
        }

    @property
    def is_terminal(self) -> bool:
        """Return whether the attempt has reached a terminal state."""
        return not self.is_active


@dataclass(frozen=True)
class ParseFileSignature:
    """Stable metadata for one input file included in a request fingerprint."""

    path: str
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class ParseJobRequest:
    """Immutable, serializable description of one parse request.

    Variable configurations are held as canonical JSON rather than mutable
    dictionaries. The matching file signatures are captured at submission
    time and recomputed when a user explicitly retries an attempt.
    """

    simulator: str
    parser_contract_version: str
    stats_path: str
    stats_pattern: str
    strategy_type: str
    variables_json: str
    scanned_variables_json: str
    file_signatures: tuple[ParseFileSignature, ...]
    fingerprint: str
    incremental: bool = False

    def variables(self) -> list[JsonValue]:
        """Decode the canonical variable configuration."""
        value = json.loads(self.variables_json)
        if not isinstance(value, list):
            raise ValueError("Stored parse variables must be a JSON list")
        return value

    def scanned_variables(self) -> list[JsonValue]:
        """Decode the canonical scanned-variable configuration."""
        value = json.loads(self.scanned_variables_json)
        if not isinstance(value, list):
            raise ValueError("Stored scanned variables must be a JSON list")
        return value


@dataclass(frozen=True)
class ParseJobSnapshot:
    """Read-only view of persisted parse job state."""

    job_id: str
    fingerprint: str
    status: ParseJobStatus
    phase: str
    completed_files: int
    total_files: int
    error_count: int
    errors: tuple[str, ...]
    created_at: float
    started_at: float | None
    finished_at: float | None
    attempt: int
    output_csv_path: str | None = None
    published_csv_path: str | None = None
    cache_hit: bool = False

    @property
    def elapsed_seconds(self) -> float:
        """Return elapsed wall-clock seconds for display."""
        end = self.finished_at if self.finished_at is not None else time.time()
        start = self.started_at if self.started_at is not None else self.created_at
        return max(0.0, end - start)

    @property
    def progress(self) -> float:
        """Return progress as a bounded fraction."""
        if self.total_files <= 0:
            return 0.0
        return min(1.0, max(0.0, self.completed_files / self.total_files))


@dataclass(frozen=True)
class ParseJobReceipt:
    """Result returned after a terminal job is consumed by the script thread."""

    job_id: str
    fingerprint: str
    csv_path: str
    status: ParseJobStatus
    reused: bool

    def exists(self) -> bool:
        """Return whether the published Recent CSV is still present."""
        return Path(self.csv_path).is_file()


class ParseJobError(RuntimeError):
    """Base class for session parsing job errors."""


class ParseJobNotFoundError(ParseJobError):
    """Raised when a session does not own the requested job."""


class ParseJobConflictError(ParseJobError):
    """Raised when a different request is already active in the session."""


class InvalidParseJobTransition(ParseJobError):
    """Raised when a state transition violates the job lifecycle."""


class ParseJobNotConsumableError(ParseJobError):
    """Raised when a job cannot yet be consumed."""
