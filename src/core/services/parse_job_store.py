"""Current SQLite persistence for bounded typed background parse jobs."""

from __future__ import annotations

import json
import math
import sqlite3
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

from src.core.common.parsed_output_codec import (
    decode_parsed_output,
    encode_parsed_output,
    unique_json_object,
)
from src.core.common.source_context_codec import SourceContextCodec
from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.common.security_limits import MAX_PARSE_FILES, MAX_PARSE_FILE_BYTES
from src.core.models.parsed_output_models import ParsedOutput
from src.core.models.source_context_models import ParserSourceContext
from src.core.models.parse_job_models import (
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
PARSE_JOB_STORE_VERSION = 1


class InvalidStoredOutput(ValueError):
    """A durable optimization record has an invalid current output descriptor."""


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
    """Persist one current session format with explicit source and output metadata."""

    def __init__(self, db_path: Path) -> None:
        """Initialize an empty database or validate its exact current format."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            objects = connection.execute(
                "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
            ).fetchall()
            if version == 0 and not objects:
                connection.executescript("""
                    CREATE TABLE jobs (
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
                        output_json TEXT,
                        published_json TEXT,
                        cache_hit INTEGER NOT NULL DEFAULT 0
                    );
                    CREATE INDEX jobs_fingerprint_idx ON jobs(fingerprint, created_at DESC);
                    CREATE TABLE published_results (
                        fingerprint TEXT PRIMARY KEY,
                        output_json TEXT NOT NULL,
                        published_at REAL NOT NULL
                    );
                    PRAGMA user_version = 1;
                """)
            elif version != PARSE_JOB_STORE_VERSION:
                raise ValueError(f"Unsupported parse job store format: {version}.")
            expected = {
                "jobs": {
                    "job_id",
                    "fingerprint",
                    "request_json",
                    "status",
                    "phase",
                    "completed_files",
                    "total_files",
                    "error_count",
                    "errors_json",
                    "created_at",
                    "started_at",
                    "finished_at",
                    "attempt",
                    "attempt_dir",
                    "output_json",
                    "published_json",
                    "cache_hit",
                },
                "published_results": {"fingerprint", "output_json", "published_at"},
            }
            for table, fields in expected.items():
                actual = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
                if actual != fields:
                    raise ValueError("Parse job store schema does not match its current format.")

    def create_job(
        self,
        job_id: str,
        request: ParseJobRequest,
        attempt_dir: Path,
        attempt: int,
        *,
        status: ParseJobStatus = ParseJobStatus.QUEUED,
        phase: str = "Queued",
        published_output: ParsedOutput | None = None,
        cache_hit: bool = False,
    ) -> ParseJobSnapshot:
        """Insert an actual attempt or a verified complete cached result."""
        _text(job_id)
        _text(phase)
        if type(attempt) is not int or attempt < 1:
            raise ValueError("Parse job attempt must be a positive integer.")
        if type(status) is not ParseJobStatus or type(cache_hit) is not bool:
            raise TypeError("Parse job status and cache policy must be current typed values.")
        if not isinstance(attempt_dir, Path):
            raise TypeError("Parse job attempt directory must be a Path.")
        if cache_hit and (status != ParseJobStatus.SUCCEEDED or published_output is None):
            raise ValueError("Only a complete typed success can be a cached parse job.")
        request_json = self._encode_request(request)
        published = encode_parsed_output(published_output) if published_output is not None else None
        now = time.time()
        finished_at = now if status.is_terminal else None
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (job_id, fingerprint, request_json, status, phase,
                    completed_files, total_files, error_count, errors_json,
                    created_at, started_at, finished_at, attempt, attempt_dir,
                    output_json, published_json, cache_hit)
                VALUES (?, ?, ?, ?, ?, 0, ?, 0, '[]', ?, NULL, ?, ?, ?, NULL, ?, ?)
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
                    published,
                    int(cache_hit),
                ),
            )
        return self._require_job(job_id)

    def get_job(self, job_id: str) -> ParseJobSnapshot | None:
        """Return one current typed snapshot, if present."""
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._snapshot_from_row(row) if row is not None else None

    def _require_job(self, job_id: str) -> ParseJobSnapshot:
        snapshot = self.get_job(job_id)
        if snapshot is None:
            raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        return snapshot

    def get_request(self, job_id: str) -> ParseJobRequest:
        """Decode the exact source request before execution or replay."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT request_json FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        return self._decode_request(row["request_json"])

    def get_attempt_dir(self, job_id: str) -> Path:
        """Return the attempt directory supplied by the session owner."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT attempt_dir FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        return Path(_text(row["attempt_dir"]))

    def get_active_job(self) -> ParseJobSnapshot | None:
        """Return the session's queued, running or cancelling attempt."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE status IN (?, ?, ?) ORDER BY created_at DESC LIMIT 1",
                (
                    ParseJobStatus.QUEUED.value,
                    ParseJobStatus.RUNNING.value,
                    ParseJobStatus.CANCELLING.value,
                ),
            ).fetchone()
        return self._snapshot_from_row(row) if row is not None else None

    def get_latest_by_fingerprint(self, fingerprint: str) -> ParseJobSnapshot | None:
        """Return the newest unconsumed attempt for an exact request."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE fingerprint = ? ORDER BY created_at DESC LIMIT 1",
                (fingerprint,),
            ).fetchone()
        return self._snapshot_from_row(row) if row is not None else None

    def list_jobs(self) -> list[ParseJobSnapshot]:
        """Return every unconsumed current attempt in creation order."""
        with self._lock, self._connect() as connection:
            rows = connection.execute("SELECT * FROM jobs ORDER BY created_at").fetchall()
        return [self._snapshot_from_row(row) for row in rows]

    def transition(
        self,
        job_id: str,
        status: ParseJobStatus,
        phase: str,
        *,
        output: ParsedOutput | None = None,
        published_output: ParsedOutput | None = None,
    ) -> ParseJobSnapshot:
        """Apply an allowed lifecycle transition and exact descriptor values."""
        if type(status) is not ParseJobStatus:
            raise TypeError("Parse job transitions require ParseJobStatus.")
        _text(phase)
        encoded = encode_parsed_output(output) if output is not None else None
        published = encode_parsed_output(published_output) if published_output is not None else None
        now = time.time()
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT status, started_at FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
            current = ParseJobStatus(row["status"])
            if status not in _ALLOWED_TRANSITIONS[current]:
                raise InvalidParseJobTransition(
                    f"Cannot transition parse job from {current.value} to {status.value}"
                )
            started_at = (
                now
                if status == ParseJobStatus.RUNNING and row["started_at"] is None
                else row["started_at"]
            )
            connection.execute(
                """UPDATE jobs SET status = ?, phase = ?, started_at = ?, finished_at = ?,
                output_json = COALESCE(?, output_json), published_json = COALESCE(?, published_json)
                WHERE job_id = ?""",
                (
                    status.value,
                    phase[:MAX_PHASE_LENGTH],
                    started_at,
                    now if status.is_terminal else None,
                    encoded,
                    published,
                    job_id,
                ),
            )
        return self._require_job(job_id)

    def update_progress(
        self, job_id: str, completed_files: int, total_files: int, phase: str
    ) -> ParseJobSnapshot:
        """Retain bounded progress without changing lifecycle state."""
        if type(completed_files) is not int or type(total_files) is not int:
            raise TypeError("Parse job progress counts must be integers.")
        total = max(0, total_files)
        completed = min(max(0, completed_files), total)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET completed_files = ?, total_files = ?, phase = ? WHERE job_id = ?",
                (completed, total, phase[:MAX_PHASE_LENGTH], job_id),
            )
            if cursor.rowcount == 0:
                raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        return self._require_job(job_id)

    def append_error(self, job_id: str, error: str) -> ParseJobSnapshot:
        """Increment all failures while retaining only bounded text diagnostics."""
        clean = error.replace("\x00", "")[:MAX_ERROR_LENGTH]
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT error_count, errors_json FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
            errors = list(_errors(row["errors_json"]))
            if len(errors) < MAX_STORED_ERRORS:
                errors.append(clean)
            connection.execute(
                "UPDATE jobs SET error_count = ?, errors_json = ? WHERE job_id = ?",
                (_count(row["error_count"]) + 1, json.dumps(errors), job_id),
            )
        return self._require_job(job_id)

    def delete_job(self, job_id: str) -> Path:
        """Remove an attempt record and return its owned directory for disposal."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT attempt_dir FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
            directory = Path(_text(row["attempt_dir"]))
            connection.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        return directory

    def discard_cached_success(self, fingerprint: str) -> tuple[str, Path] | None:
        """Evict only the latest corrupt success; invalid partial records stay visible."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT job_id, status, attempt_dir FROM jobs WHERE fingerprint = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (fingerprint,),
            ).fetchone()
            if row is None or row["status"] != ParseJobStatus.SUCCEEDED.value:
                return None
            removed = (_text(row["job_id"]), Path(_text(row["attempt_dir"])))
            connection.execute(
                "DELETE FROM jobs WHERE job_id = ? AND status = ?",
                (removed[0], ParseJobStatus.SUCCEEDED.value),
            )
        return removed

    def remember_published(self, fingerprint: str, output: ParsedOutput) -> None:
        """Retain an explicit complete-success output in this session's cache."""
        encoded = encode_parsed_output(output)
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO published_results(fingerprint, output_json, published_at)
                VALUES (?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET output_json = excluded.output_json,
                published_at = excluded.published_at""",
                (fingerprint, encoded, time.time()),
            )

    def get_published(self, fingerprint: str) -> ParsedOutput | None:
        """Decode an explicit cached output; its caller verifies current file integrity."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT output_json FROM published_results WHERE fingerprint = ?", (fingerprint,)
            ).fetchone()
        return _output(row["output_json"]) if row is not None else None

    def forget_published(self, fingerprint: str) -> None:
        """Invalidate a missing or corrupt complete-success cache mapping."""
        with self._lock, self._connect() as connection:
            connection.execute(
                "DELETE FROM published_results WHERE fingerprint = ?", (fingerprint,)
            )

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Commit or roll back one operation and always close its connection."""
        connection = sqlite3.connect(self.db_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _encode_request(request: ParseJobRequest) -> str:
        """Encode current bounded source/signature facts without coercion."""
        if type(request) is not ParseJobRequest:
            raise TypeError("Parse job storage requires ParseJobRequest.")
        context = request.source_context
        if (
            len(context.variables_json) + len(context.scanned_variables_json)
            > MAX_REQUEST_JSON_BYTES
        ):
            raise ValueError("Parse request metadata exceeds the 1 MB session limit")
        if (
            len(context.variables_json.encode("utf-8"))
            + len(context.scanned_variables_json.encode("utf-8"))
            > MAX_REQUEST_JSON_BYTES
        ):
            raise ValueError("Parse request metadata exceeds the 1 MB session limit")
        if len(request.file_signatures) > MAX_PARSE_FILES:
            raise ValueError("Parse request exceeds its source file limit.")
        signatures = []
        path_bytes = 0
        for signature in request.file_signatures:
            _signature_fields(signature.path, signature.size, signature.mtime_ns)
            path_bytes += len(signature.path.encode("utf-8")) + 100
            if path_bytes > MAX_REQUEST_JSON_BYTES:
                raise ValueError("Parse request metadata exceeds the 1 MB session limit")
            signatures.append(
                {"path": signature.path, "size": signature.size, "mtime_ns": signature.mtime_ns}
            )
        payload = {
            "source_context": SourceContextCodec.to_payload(context),
            "file_signatures": signatures,
            "fingerprint": request.fingerprint,
            "incremental": request.incremental,
        }
        chunks = []
        size = 0
        for chunk in json.JSONEncoder(
            ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False
        ).iterencode(payload):
            size += len(chunk.encode("utf-8"))
            if size > MAX_REQUEST_JSON_BYTES:
                raise ValueError("Parse request metadata exceeds the 1 MB session limit")
            chunks.append(chunk)
        return "".join(chunks)

    @staticmethod
    def _decode_request(encoded: str) -> ParseJobRequest:
        """Reject unsupported request fields and values before constructing a job."""
        if (
            type(encoded) is not str
            or len(encoded) > MAX_REQUEST_JSON_BYTES
            or len(encoded.encode("utf-8")) > MAX_REQUEST_JSON_BYTES
        ):
            raise ValueError("Parse request metadata exceeds the 1 MB session limit")
        try:
            payload = json.loads(encoded, object_pairs_hook=unique_json_object)
        except (ValueError, RecursionError):
            payload = None
        if type(payload) is not dict or payload.keys() != {
            "source_context",
            "file_signatures",
            "fingerprint",
            "incremental",
        }:
            raise ValueError("Stored parse request has invalid or unsupported fields.")
        context = SourceContextCodec.from_payload(payload["source_context"])
        if type(context) is not ParserSourceContext:
            raise TypeError("Parse jobs require a parser source context.")
        values = payload["file_signatures"]
        if type(values) is not list or len(values) > MAX_PARSE_FILES:
            raise ValueError("Stored parse signatures require a bounded list.")
        signatures = []
        for item in values:
            if type(item) is not dict or item.keys() != {"path", "size", "mtime_ns"}:
                raise ValueError("Stored source signature has unsupported fields.")
            _signature_fields(item["path"], item["size"], item["mtime_ns"])
            signatures.append(ParseFileSignature(item["path"], item["size"], item["mtime_ns"]))
        request = ParseJobRequest(
            context, tuple(signatures), payload["fingerprint"], payload["incremental"]
        )
        ParseJobStore._encode_request(request)
        return request

    @staticmethod
    def _snapshot_from_row(row: sqlite3.Row) -> ParseJobSnapshot:
        """Read exact current metadata and descriptors without filesystem inference."""
        flag = row["cache_hit"]
        if type(flag) is not int or flag not in (0, 1):
            raise ValueError("Stored parse cache flag is invalid.")
        return ParseJobSnapshot(
            job_id=_text(row["job_id"]),
            fingerprint=_text(row["fingerprint"]),
            status=ParseJobStatus(_text(row["status"])),
            phase=_text(row["phase"]),
            completed_files=_count(row["completed_files"]),
            total_files=_count(row["total_files"]),
            error_count=_count(row["error_count"]),
            errors=_errors(row["errors_json"]),
            created_at=_time(row["created_at"]),
            started_at=_time(row["started_at"]) if row["started_at"] is not None else None,
            finished_at=_time(row["finished_at"]) if row["finished_at"] is not None else None,
            attempt=_count(row["attempt"]),
            output=_output(row["output_json"]),
            published_output=_output(row["published_json"]),
            cache_hit=flag == 1,
        )


def _text(value: object) -> str:
    if type(value) is not str or not value:
        raise TypeError("Stored parse metadata requires non-empty text.")
    return value


def _count(value: object) -> int:
    if type(value) is not int or value < 0:
        raise TypeError("Stored parse counts require non-negative integers.")
    return value


def _time(value: object) -> float:
    if type(value) not in (int, float) or not math.isfinite(cast(float, value)):
        raise TypeError("Stored parse timestamps require finite numbers.")
    return float(cast(float, value))


def _signature_fields(path: object, size: object, mtime_ns: object) -> None:
    if type(path) is not str or not path or len(path) > MAX_INPUT_LENGTH:
        raise TypeError("Stored source paths require bounded non-empty text.")
    if type(size) is not int or not 0 <= size <= MAX_PARSE_FILE_BYTES:
        raise TypeError("Stored source sizes require bounded non-negative integers.")
    if type(mtime_ns) is not int or mtime_ns.bit_length() > 128:
        raise TypeError("Stored source timestamps require signed integer nanoseconds.")


def _errors(value: object) -> tuple[str, ...]:
    if (
        type(value) is not str
        or len(value.encode("utf-8")) > MAX_STORED_ERRORS * MAX_ERROR_LENGTH * 12 + 2
    ):
        raise ValueError("Stored parse errors exceed their text budget.")
    try:
        errors = json.loads(value)
    except (ValueError, RecursionError):
        errors = None
    if (
        type(errors) is not list
        or len(errors) > MAX_STORED_ERRORS
        or any(type(error) is not str or len(error) > MAX_ERROR_LENGTH for error in errors)
    ):
        raise ValueError("Stored parse errors require a bounded text array.")
    return tuple(errors)


def _output(value: object) -> ParsedOutput | None:
    if value is None:
        return None
    try:
        if type(value) is not str:
            raise TypeError("Stored output must be descriptor text.")
        return decode_parsed_output(value)
    except (TypeError, ValueError, RecursionError):
        pass
    raise InvalidStoredOutput("Stored parsed output descriptor is invalid.")
