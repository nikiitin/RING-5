"""SQLite persistence for session-scoped parse job metadata."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from src.core.models import (
    InvalidParseJobTransition,
    ParseFileSignature,
    ParseJobNotFoundError,
    ParseJobRequest,
    ParseJobSnapshot,
    ParseJobStatus,
)

MAX_STORED_ERRORS = 20
MAX_ERROR_LENGTH = 1_000
MAX_REQUEST_JSON_BYTES = 1_000_000
MAX_PHASE_LENGTH = 200

_ALLOWED_TRANSITIONS: dict[ParseJobStatus, frozenset[ParseJobStatus]] = {
    ParseJobStatus.QUEUED: frozenset(
        {
            ParseJobStatus.RUNNING,
            ParseJobStatus.CANCELLING,
            ParseJobStatus.CANCELLED,
            ParseJobStatus.FAILED,
        }
    ),
    ParseJobStatus.RUNNING: frozenset(
        {
            ParseJobStatus.CANCELLING,
            ParseJobStatus.SUCCEEDED,
            ParseJobStatus.PARTIAL,
            ParseJobStatus.FAILED,
            ParseJobStatus.CANCELLED,
        }
    ),
    ParseJobStatus.CANCELLING: frozenset({ParseJobStatus.CANCELLED}),
    ParseJobStatus.SUCCEEDED: frozenset(),
    ParseJobStatus.PARTIAL: frozenset(),
    ParseJobStatus.FAILED: frozenset(),
    ParseJobStatus.CANCELLED: frozenset(),
}


class ParseJobStore:
    """Persist bounded job metadata in one session-local SQLite database."""

    def __init__(self, db_path: Path) -> None:
        """Initialize the database schema."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    completed_files INTEGER NOT NULL,
                    total_files INTEGER NOT NULL,
                    error_count INTEGER NOT NULL,
                    errors_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    finished_at REAL,
                    attempt INTEGER NOT NULL,
                    attempt_dir TEXT NOT NULL,
                    output_csv_path TEXT,
                    published_csv_path TEXT,
                    cache_hit INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS jobs_fingerprint_idx
                    ON jobs(fingerprint, created_at DESC);
                CREATE TABLE IF NOT EXISTS published_results (
                    fingerprint TEXT PRIMARY KEY,
                    csv_path TEXT NOT NULL,
                    published_at REAL NOT NULL
                );
                """)

    def create_job(
        self,
        job_id: str,
        request: ParseJobRequest,
        attempt_dir: Path,
        attempt: int,
        *,
        status: ParseJobStatus = ParseJobStatus.QUEUED,
        phase: str = "Queued",
        published_csv_path: str | None = None,
        cache_hit: bool = False,
    ) -> ParseJobSnapshot:
        """Insert a new parse attempt."""
        request_json = self._encode_request(request)
        now = time.time()
        finished_at = now if status.is_terminal else None
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, fingerprint, request_json, status, phase,
                    completed_files, total_files, error_count, errors_json,
                    created_at, started_at, finished_at, attempt, attempt_dir,
                    output_csv_path, published_csv_path, cache_hit
                ) VALUES (?, ?, ?, ?, ?, 0, ?, 0, '[]', ?, NULL, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    job_id,
                    request.fingerprint,
                    request_json,
                    status.value,
                    phase[:MAX_PHASE_LENGTH],
                    len(request.file_signatures),
                    now,
                    finished_at,
                    attempt,
                    str(attempt_dir),
                    published_csv_path,
                    int(cache_hit),
                ),
            )
        snapshot = self.get_job(job_id)
        if snapshot is None:
            raise RuntimeError("New parse job could not be read back")
        return snapshot

    def get_job(self, job_id: str) -> ParseJobSnapshot | None:
        """Return a job snapshot, if present."""
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._snapshot_from_row(row) if row is not None else None

    def get_request(self, job_id: str) -> ParseJobRequest:
        """Return the immutable original request for a job."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT request_json FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        return self._decode_request(str(row["request_json"]))

    def get_attempt_dir(self, job_id: str) -> Path:
        """Return the controlled temporary directory for an attempt."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT attempt_dir FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        return Path(str(row["attempt_dir"]))

    def get_active_job(self) -> ParseJobSnapshot | None:
        """Return the session's active parse attempt."""
        statuses = (
            ParseJobStatus.QUEUED.value,
            ParseJobStatus.RUNNING.value,
            ParseJobStatus.CANCELLING.value,
        )
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM jobs
                WHERE status IN (?, ?, ?)
                ORDER BY created_at DESC LIMIT 1
                """,
                statuses,
            ).fetchone()
        return self._snapshot_from_row(row) if row is not None else None

    def get_latest_by_fingerprint(self, fingerprint: str) -> ParseJobSnapshot | None:
        """Return the newest attempt for a request fingerprint."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM jobs WHERE fingerprint = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (fingerprint,),
            ).fetchone()
        return self._snapshot_from_row(row) if row is not None else None

    def list_jobs(self) -> list[ParseJobSnapshot]:
        """Return all unconsumed attempts in creation order."""
        with self._lock, self._connect() as connection:
            rows = connection.execute("SELECT * FROM jobs ORDER BY created_at").fetchall()
        return [self._snapshot_from_row(row) for row in rows]

    def transition(
        self,
        job_id: str,
        status: ParseJobStatus,
        phase: str,
        *,
        output_csv_path: str | None = None,
        published_csv_path: str | None = None,
    ) -> ParseJobSnapshot:
        """Apply a validated status transition."""
        now = time.time()
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT status, started_at FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
            current = ParseJobStatus(str(row["status"]))
            if status not in _ALLOWED_TRANSITIONS[current]:
                raise InvalidParseJobTransition(
                    f"Cannot transition parse job from {current.value} to {status.value}"
                )
            started_at = row["started_at"]
            if status == ParseJobStatus.RUNNING and started_at is None:
                started_at = now
            finished_at = now if status.is_terminal else None
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, phase = ?, started_at = ?, finished_at = ?,
                    output_csv_path = COALESCE(?, output_csv_path),
                    published_csv_path = COALESCE(?, published_csv_path)
                WHERE job_id = ?
                """,
                (
                    status.value,
                    phase[:MAX_PHASE_LENGTH],
                    started_at,
                    finished_at,
                    output_csv_path,
                    published_csv_path,
                    job_id,
                ),
            )
        snapshot = self.get_job(job_id)
        if snapshot is None:
            raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        return snapshot

    def update_progress(
        self,
        job_id: str,
        completed_files: int,
        total_files: int,
        phase: str,
    ) -> ParseJobSnapshot:
        """Update bounded progress metadata without changing state."""
        bounded_total = max(0, total_files)
        bounded_completed = min(max(0, completed_files), bounded_total)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs SET completed_files = ?, total_files = ?, phase = ?
                WHERE job_id = ?
                """,
                (
                    bounded_completed,
                    bounded_total,
                    phase[:MAX_PHASE_LENGTH],
                    job_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        snapshot = self.get_job(job_id)
        if snapshot is None:
            raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        return snapshot

    def append_error(self, job_id: str, error: str) -> ParseJobSnapshot:
        """Increment the full error count and retain only bounded messages."""
        clean_error = error.replace("\x00", "")[:MAX_ERROR_LENGTH]
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT error_count, errors_json FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
            errors = json.loads(str(row["errors_json"]))
            if not isinstance(errors, list):
                errors = []
            if len(errors) < MAX_STORED_ERRORS:
                errors.append(clean_error)
            connection.execute(
                "UPDATE jobs SET error_count = ?, errors_json = ? WHERE job_id = ?",
                (int(row["error_count"]) + 1, json.dumps(errors), job_id),
            )
        snapshot = self.get_job(job_id)
        if snapshot is None:
            raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        return snapshot

    def delete_job(self, job_id: str) -> Path:
        """Delete a full job record and return its attempt directory."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT attempt_dir FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
            connection.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        return Path(str(row["attempt_dir"]))

    def remember_published(self, fingerprint: str, csv_path: str) -> None:
        """Retain the session-only fingerprint-to-Recent mapping."""
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO published_results(fingerprint, csv_path, published_at)
                VALUES (?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    csv_path = excluded.csv_path,
                    published_at = excluded.published_at
                """,
                (fingerprint, csv_path, time.time()),
            )

    def get_published(self, fingerprint: str) -> str | None:
        """Return a mapped Recent CSV path."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT csv_path FROM published_results WHERE fingerprint = ?",
                (fingerprint,),
            ).fetchone()
        return str(row["csv_path"]) if row is not None else None

    def forget_published(self, fingerprint: str) -> None:
        """Invalidate a stale fingerprint-to-Recent mapping."""
        with self._lock, self._connect() as connection:
            connection.execute(
                "DELETE FROM published_results WHERE fingerprint = ?", (fingerprint,)
            )

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Open one transactional connection and always close it.

        A ``sqlite3.Connection`` context manager commits or rolls back, but it
        does not close the connection.  Wrapping that behavior here prevents
        short-lived job operations from leaking connections until cyclic
        garbage collection runs on an arbitrary worker thread.
        """
        connection = sqlite3.connect(self.db_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _encode_request(request: ParseJobRequest) -> str:
        """Serialize a request while enforcing the session metadata limit."""
        payload = {
            "simulator": request.simulator,
            "parser_contract_version": request.parser_contract_version,
            "stats_path": request.stats_path,
            "stats_pattern": request.stats_pattern,
            "strategy_type": request.strategy_type,
            "variables_json": request.variables_json,
            "scanned_variables_json": request.scanned_variables_json,
            "file_signatures": [
                {
                    "path": signature.path,
                    "size": signature.size,
                    "mtime_ns": signature.mtime_ns,
                }
                for signature in request.file_signatures
            ],
            "fingerprint": request.fingerprint,
            "incremental": request.incremental,
        }
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        if len(encoded.encode("utf-8")) > MAX_REQUEST_JSON_BYTES:
            raise ValueError("Parse request metadata exceeds the 1 MB session limit")
        return encoded

    @staticmethod
    def _decode_request(encoded: str) -> ParseJobRequest:
        """Reconstruct an immutable request from trusted session storage."""
        payload = json.loads(encoded)
        signatures = tuple(
            ParseFileSignature(
                path=str(item["path"]),
                size=int(item["size"]),
                mtime_ns=int(item["mtime_ns"]),
            )
            for item in payload["file_signatures"]
        )
        return ParseJobRequest(
            simulator=str(payload["simulator"]),
            parser_contract_version=str(payload["parser_contract_version"]),
            stats_path=str(payload["stats_path"]),
            stats_pattern=str(payload["stats_pattern"]),
            strategy_type=str(payload["strategy_type"]),
            variables_json=str(payload["variables_json"]),
            scanned_variables_json=str(payload["scanned_variables_json"]),
            file_signatures=signatures,
            fingerprint=str(payload["fingerprint"]),
            incremental=bool(payload.get("incremental", False)),
        )

    @staticmethod
    def _snapshot_from_row(row: sqlite3.Row) -> ParseJobSnapshot:
        """Convert one SQLite row into an immutable public snapshot."""
        errors_value = json.loads(str(row["errors_json"]))
        errors = (
            tuple(str(value) for value in errors_value) if isinstance(errors_value, list) else ()
        )
        return ParseJobSnapshot(
            job_id=str(row["job_id"]),
            fingerprint=str(row["fingerprint"]),
            status=ParseJobStatus(str(row["status"])),
            phase=str(row["phase"]),
            completed_files=int(row["completed_files"]),
            total_files=int(row["total_files"]),
            error_count=int(row["error_count"]),
            errors=errors,
            created_at=float(row["created_at"]),
            started_at=float(row["started_at"]) if row["started_at"] is not None else None,
            finished_at=float(row["finished_at"]) if row["finished_at"] is not None else None,
            attempt=int(row["attempt"]),
            output_csv_path=(
                str(row["output_csv_path"]) if row["output_csv_path"] is not None else None
            ),
            published_csv_path=(
                str(row["published_csv_path"]) if row["published_csv_path"] is not None else None
            ),
            cache_hit=bool(row["cache_hit"]),
        )
