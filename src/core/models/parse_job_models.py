"""Immutable models for session-scoped background parsing jobs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from src.core.models.parsed_output_models import ParsedOutput
from src.core.models.source_context_models import ParserSourceContext


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
    """Submission metadata for an input file; cache identity uses its content digest."""

    path: str
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class ParseJobRequest:
    """Immutable, serializable description of one parse request.

    The source context owns the actual resolved request independently of editor
    state. Matching file signatures are captured at submission and recomputed
    when a user explicitly retries an attempt.
    """

    source_context: ParserSourceContext
    file_signatures: tuple[ParseFileSignature, ...]
    fingerprint: str
    incremental: bool = False

    def __post_init__(self) -> None:
        if type(self.source_context) is not ParserSourceContext:
            raise TypeError("Parse job request requires an actual parser source context.")
        if type(self.file_signatures) is not tuple or any(
            type(signature) is not ParseFileSignature for signature in self.file_signatures
        ):
            raise TypeError("Parse job signatures require an immutable tuple.")
        if (
            type(self.fingerprint) is not str
            or len(self.fingerprint) != 64
            or any(char not in "0123456789abcdef" for char in self.fingerprint)
        ):
            raise ValueError("Parse job fingerprint requires a lowercase SHA-256 digest.")
        if type(self.incremental) is not bool:
            raise TypeError("Parse job incremental policy must be boolean.")


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
    output: ParsedOutput | None = None
    published_output: ParsedOutput | None = None
    cache_hit: bool = False

    @property
    def output_csv_path(self) -> str | None:
        """CSV location of the staged explicit typed output, when finalized."""
        return self.output.csv_path if self.output is not None else None

    @property
    def published_csv_path(self) -> str | None:
        """CSV location of the published explicit typed output, when promoted."""
        return self.published_output.csv_path if self.published_output is not None else None

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
    output: ParsedOutput
    source_context: ParserSourceContext
    status: ParseJobStatus
    reused: bool

    @property
    def csv_path(self) -> str:
        """Published CSV location; typed consumers must retain the descriptor."""
        return self.output.csv_path

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
