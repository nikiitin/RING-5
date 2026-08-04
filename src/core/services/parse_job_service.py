"""Session-owned orchestration for background parse jobs."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import shutil
import threading
import uuid
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import (
    FIRST_COMPLETED,
    CancelledError,
    Future,
    ThreadPoolExecutor,
    wait,
)
from enum import Enum
from pathlib import Path
from typing import Any

from src.core.common.utils import normalize_user_path, sanitize_glob_pattern
from src.core.models import (
    IncrementalParseBatchResult,
    ParseBatchResult,
    ParseFileSignature,
    ParseJobConflictError,
    ParseJobNotConsumableError,
    ParseJobNotFoundError,
    ParseJobReceipt,
    ParseJobRequest,
    ParseJobSnapshot,
    ParseJobStatus,
)
from src.core.models.parse_job_models import JsonValue
from src.core.services.parse_job_store import ParseJobStore
from src.core.services.parse_job_workspace import ParseJobRuntimeWorkspace

logger = logging.getLogger(__name__)

PARSER_CONTRACT_VERSION = "1"

SubmitParse = Callable[
    [str, str, Sequence[JsonValue], str, str, list[JsonValue] | None, bool],
    ParseBatchResult | IncrementalParseBatchResult,
]
FinalizeParse = Callable[
    [
        str,
        ParseBatchResult | IncrementalParseBatchResult,
        list[dict[str, Any]],
        bool,
        str,
    ],
    str | None,
]
PublishCsv = Callable[[str, str], str]
BeforeCleanup = Callable[[ParseJobReceipt], None]


def build_parse_job_request(
    *,
    stats_path: str,
    stats_pattern: str,
    variables: Sequence[object],
    strategy_type: str,
    scanned_variables: Sequence[object] | None = None,
    simulator: str = "gem5",
    parser_contract_version: str = PARSER_CONTRACT_VERSION,
    incremental: bool = False,
) -> ParseJobRequest:
    """Canonicalize a request and compute its content-and-input fingerprint."""
    normalized_path = normalize_user_path(stats_path)
    if not normalized_path.exists():
        raise FileNotFoundError(f"Stats path does not exist: {stats_path}")
    if not normalized_path.is_dir():
        raise NotADirectoryError(f"Stats path is not a directory: {stats_path}")

    normalized_pattern = sanitize_glob_pattern(stats_pattern)
    variables_json = _canonical_json(list(variables), strip_internal_ids=True)
    scanned_json = _canonical_json(
        list(scanned_variables) if scanned_variables is not None else [],
        strip_internal_ids=True,
    )
    signatures: list[ParseFileSignature] = []
    seen_paths: set[str] = set()
    for candidate in normalized_path.rglob(normalized_pattern):
        try:
            resolved = candidate.resolve()
            if not resolved.is_file():
                continue
            resolved_string = str(resolved)
            if resolved_string in seen_paths:
                continue
            stat = resolved.stat()
        except OSError:
            continue
        seen_paths.add(resolved_string)
        signatures.append(
            ParseFileSignature(
                path=resolved_string,
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
            )
        )
    signatures.sort(key=lambda item: item.path)

    fingerprint_payload = {
        "simulator": simulator,
        "parser_contract_version": parser_contract_version,
        "stats_path": str(normalized_path),
        "stats_pattern": normalized_pattern,
        "strategy_type": strategy_type,
        "variables": json.loads(variables_json),
        "scanned_variables": json.loads(scanned_json),
        "matching_files": [
            {
                "path": signature.path,
                "size": signature.size,
                "mtime_ns": signature.mtime_ns,
            }
            for signature in signatures
        ],
        "incremental": incremental,
    }
    encoded = json.dumps(
        fingerprint_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    fingerprint = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return ParseJobRequest(
        simulator=simulator,
        parser_contract_version=parser_contract_version,
        stats_path=str(normalized_path),
        stats_pattern=normalized_pattern,
        strategy_type=strategy_type,
        variables_json=variables_json,
        scanned_variables_json=scanned_json,
        file_signatures=tuple(signatures),
        fingerprint=fingerprint,
        incremental=incremental,
    )


class ParseJobService:
    """Own one session's persisted jobs and one orchestration thread."""

    # [impl->req~ring5.ingestion.session-background-parse~1]

    def __init__(
        self,
        submit_parse: SubmitParse,
        finalize_parse: FinalizeParse,
        publish_csv: PublishCsv,
        *,
        runtime_workspace: ParseJobRuntimeWorkspace | None = None,
    ) -> None:
        """Create an isolated session workspace and metadata store."""
        self._submit_parse = submit_parse
        self._finalize_parse = finalize_parse
        self._publish_csv = publish_csv
        self._runtime_workspace = (
            runtime_workspace
            if runtime_workspace is not None
            else ParseJobRuntimeWorkspace.get_instance()
        )
        self.session_dir = self._runtime_workspace.create_session_workspace()
        self._attempts_dir = self.session_dir / "attempts"
        self._attempts_dir.mkdir(mode=0o700)
        self._store = ParseJobStore(self.session_dir / "jobs.sqlite3")
        self._operation_lock = threading.RLock()
        self._executor: ThreadPoolExecutor | None = None
        self._cancel_events: dict[str, threading.Event] = {}
        self._file_futures: dict[str, list[Future[dict[str, Any]]]] = {}
        self._orchestration_futures: dict[str, Future[None]] = {}
        self._discard_when_terminal: set[str] = set()
        self._closed = False
        self._runtime_workspace.register_session_closer(self.session_dir, self.close)

    def submit(
        self,
        *,
        stats_path: str,
        stats_pattern: str,
        variables: Sequence[object],
        strategy_type: str,
        scanned_variables: Sequence[object] | None = None,
        simulator: str = "gem5",
        parser_contract_version: str = PARSER_CONTRACT_VERSION,
        incremental: bool = False,
    ) -> ParseJobSnapshot:
        """Persist and enqueue a parse attempt without waiting for file work."""
        request = build_parse_job_request(
            stats_path=stats_path,
            stats_pattern=stats_pattern,
            variables=variables,
            strategy_type=strategy_type,
            scanned_variables=scanned_variables,
            simulator=simulator,
            parser_contract_version=parser_contract_version,
            incremental=incremental,
        )
        with self._operation_lock:
            return self._submit_request(request, attempt=1, ignore_cached_result=False)

    def get(self, job_id: str) -> ParseJobSnapshot | None:
        """Return a session-owned job snapshot."""
        return self._store.get_job(job_id)

    def get_active(self) -> ParseJobSnapshot | None:
        """Return the session's only active job, if any."""
        return self._store.get_active_job()

    def cancel(self, job_id: str) -> ParseJobSnapshot:
        """Cooperatively cancel only the specified session job."""
        with self._operation_lock:
            snapshot = self._require_job(job_id)
            if snapshot.status.is_terminal:
                return snapshot
            event = self._cancel_events.setdefault(job_id, threading.Event())
            event.set()
            if snapshot.status != ParseJobStatus.CANCELLING:
                snapshot = self._store.transition(
                    job_id,
                    ParseJobStatus.CANCELLING,
                    "Cancelling pending files; waiting for running files",
                )
            for future in self._file_futures.get(job_id, []):
                future.cancel()
            return snapshot

    def retry(self, job_id: str) -> ParseJobSnapshot:
        """Recompute file signatures and enqueue a fresh explicit attempt."""
        with self._operation_lock:
            snapshot = self._require_job(job_id)
            if snapshot.status not in {
                ParseJobStatus.PARTIAL,
                ParseJobStatus.FAILED,
                ParseJobStatus.CANCELLED,
            }:
                raise ParseJobNotConsumableError(
                    f"Parse job in {snapshot.status.value} state cannot be retried"
                )
            active = self._store.get_active_job()
            if active is not None and active.job_id != job_id:
                raise ParseJobConflictError(
                    f"Parse job {active.job_id} is already active in this session"
                )
            old_request = self._store.get_request(job_id)
            variables = old_request.variables()
            scanned_variables = old_request.scanned_variables()
            request = build_parse_job_request(
                stats_path=old_request.stats_path,
                stats_pattern=old_request.stats_pattern,
                variables=variables,
                strategy_type=old_request.strategy_type,
                scanned_variables=scanned_variables,
                simulator=old_request.simulator,
                parser_contract_version=old_request.parser_contract_version,
                incremental=old_request.incremental,
            )
            attempt_dir = self._store.delete_job(job_id)
            shutil.rmtree(attempt_dir, ignore_errors=True)
            self._cancel_events.pop(job_id, None)
            self._file_futures.pop(job_id, None)
            self._orchestration_futures.pop(job_id, None)
            return self._submit_request(
                request,
                attempt=snapshot.attempt + 1,
                ignore_cached_result=True,
            )

    def consume(
        self,
        job_id: str,
        *,
        allow_partial: bool = False,
        before_cleanup: BeforeCleanup | None = None,
    ) -> ParseJobReceipt:
        """Publish if needed and delete transient data after optional consumption."""
        with self._operation_lock:
            snapshot = self._require_job(job_id)
            if snapshot.status == ParseJobStatus.PARTIAL and not allow_partial:
                raise ParseJobNotConsumableError("Partial parse results require allow_partial=True")
            if snapshot.status not in {ParseJobStatus.SUCCEEDED, ParseJobStatus.PARTIAL}:
                raise ParseJobNotConsumableError(
                    f"Parse job in {snapshot.status.value} state cannot be consumed"
                )

            published_path = snapshot.published_csv_path
            if snapshot.status == ParseJobStatus.PARTIAL:
                output_path = snapshot.output_csv_path
                if output_path is None or not Path(output_path).is_file():
                    raise FileNotFoundError("Partial parse output is no longer available")
                published_path = self._publish_output(job_id, snapshot.fingerprint, output_path)
            if published_path is None or not Path(published_path).is_file():
                self._store.forget_published(snapshot.fingerprint)
                raise FileNotFoundError("Published parse result is no longer available")

            receipt = ParseJobReceipt(
                job_id=job_id,
                fingerprint=snapshot.fingerprint,
                csv_path=published_path,
                status=snapshot.status,
                reused=snapshot.cache_hit,
            )
            if before_cleanup is not None:
                before_cleanup(receipt)
            self._store.remember_published(snapshot.fingerprint, published_path)
            attempt_dir = self._store.delete_job(job_id)
            shutil.rmtree(attempt_dir, ignore_errors=True)
            self._cancel_events.pop(job_id, None)
            self._file_futures.pop(job_id, None)
            self._orchestration_futures.pop(job_id, None)
            return receipt

    def dismiss(self, job_id: str) -> None:
        """Acknowledge a terminal job and remove all of its transient data."""
        with self._operation_lock:
            snapshot = self._require_job(job_id)
            if not snapshot.status.is_terminal:
                raise ParseJobNotConsumableError("An active parse job cannot be dismissed")
            attempt_dir = self._store.delete_job(job_id)
            shutil.rmtree(attempt_dir, ignore_errors=True)
            self._cancel_events.pop(job_id, None)
            self._file_futures.pop(job_id, None)
            self._orchestration_futures.pop(job_id, None)

    def reset(self) -> None:
        """Cancel active work and discard every unconsumed session attempt."""
        with self._operation_lock:
            active = self._store.get_active_job()
            for snapshot in self._store.list_jobs():
                if snapshot.status.is_terminal:
                    self._delete_transient_job(snapshot.job_id)
            if active is None:
                return
            self._discard_when_terminal.add(active.job_id)
            event = self._cancel_events.setdefault(active.job_id, threading.Event())
            event.set()
            current = self._store.get_job(active.job_id)
            if current is not None and current.status != ParseJobStatus.CANCELLING:
                self._store.transition(
                    active.job_id,
                    ParseJobStatus.CANCELLING,
                    "Session reset; discarding parser output",
                )
            for future in self._file_futures.get(active.job_id, []):
                future.cancel()

    def close(self) -> None:
        """Cancel active work, wait for safe parser return, and delete the session."""
        with self._operation_lock:
            if self._closed:
                return
            self._closed = True
            active = self._store.get_active_job()
            if active is not None:
                event = self._cancel_events.setdefault(active.job_id, threading.Event())
                event.set()
                if active.status != ParseJobStatus.CANCELLING:
                    self._store.transition(
                        active.job_id,
                        ParseJobStatus.CANCELLING,
                        "Session closed; waiting for running files",
                    )
                for future in self._file_futures.get(active.job_id, []):
                    future.cancel()
            executor = self._executor
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=False)
        with self._operation_lock:
            self._cancel_events.clear()
            self._file_futures.clear()
            self._orchestration_futures.clear()
            self._discard_when_terminal.clear()
            self._runtime_workspace.release_session_workspace(self.session_dir)

    def _submit_request(
        self,
        request: ParseJobRequest,
        *,
        attempt: int,
        ignore_cached_result: bool,
    ) -> ParseJobSnapshot:
        if self._closed:
            raise RuntimeError("Parse job service is closed")

        active = self._store.get_active_job()
        if active is not None:
            if active.fingerprint == request.fingerprint:
                return active
            raise ParseJobConflictError(
                f"Parse job {active.job_id} is already active in this session"
            )

        existing = self._store.get_latest_by_fingerprint(request.fingerprint)
        if existing is not None and not ignore_cached_result:
            return existing

        if not ignore_cached_result:
            published_path = self._store.get_published(request.fingerprint)
            if published_path is not None:
                if Path(published_path).is_file():
                    job_id = uuid.uuid4().hex
                    attempt_dir = self._create_attempt_dir(job_id)
                    return self._store.create_job(
                        job_id,
                        request,
                        attempt_dir,
                        attempt,
                        status=ParseJobStatus.SUCCEEDED,
                        phase="Reusing session result from Recent CSVs",
                        published_csv_path=published_path,
                        cache_hit=True,
                    )
                self._store.forget_published(request.fingerprint)

        job_id = uuid.uuid4().hex
        attempt_dir = self._create_attempt_dir(job_id)
        try:
            snapshot = self._store.create_job(job_id, request, attempt_dir, attempt)
        except Exception:
            shutil.rmtree(attempt_dir, ignore_errors=True)
            raise
        event = threading.Event()
        self._cancel_events[job_id] = event
        executor = self._get_executor()
        self._orchestration_futures[job_id] = executor.submit(self._run_job, job_id)
        return snapshot

    def _run_job(self, job_id: str) -> None:
        results: list[dict[str, Any]] = []
        try:
            event = self._cancel_events[job_id]
            request = self._store.get_request(job_id)
            attempt_dir = self._store.get_attempt_dir(job_id)
            with self._operation_lock:
                if event.is_set():
                    self._mark_cancelled(job_id)
                    return
                self._store.transition(job_id, ParseJobStatus.RUNNING, "Preparing parser work")

            variables = request.variables()
            scanned_values = request.scanned_variables()
            scanned_variables = scanned_values if scanned_values else None
            batch = self._submit_parse(
                request.stats_path,
                request.stats_pattern,
                variables,
                str(attempt_dir),
                request.strategy_type,
                scanned_variables,
                request.incremental,
            )
            futures = batch.futures
            reused_files = (
                batch.reused_file_count if isinstance(batch, IncrementalParseBatchResult) else 0
            )
            total_files = (
                batch.total_file_count
                if isinstance(batch, IncrementalParseBatchResult)
                else len(futures)
            )
            with self._operation_lock:
                self._file_futures[job_id] = futures
                if event.is_set():
                    for future in futures:
                        future.cancel()
            self._store.update_progress(
                job_id,
                reused_files,
                total_files,
                (
                    f"Reusing {reused_files} unchanged files; parsing {len(futures)} files"
                    if reused_files
                    else ("Parsing files" if futures else "No matching parser work")
                ),
            )
            completed = reused_files
            pending = set(futures)
            while pending:
                if event.is_set():
                    for future in pending:
                        future.cancel()
                done, pending = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED)
                for future in done:
                    if future.cancelled():
                        continue
                    try:
                        result = future.result()
                        completed += 1
                        if result:
                            results.append(result)
                    except CancelledError:
                        continue
                    except Exception as exc:
                        completed += 1
                        self._store.append_error(job_id, _format_error(exc))
                    self._store.update_progress(
                        job_id,
                        completed,
                        total_files,
                        f"Prepared {completed} of {total_files} files",
                    )

            with self._operation_lock:
                self._file_futures.pop(job_id, None)
            if event.is_set():
                results.clear()
                self._mark_cancelled(job_id)
                return

            snapshot = self._store.get_job(job_id)
            if snapshot is None:
                return
            reusable_only = (
                isinstance(batch, IncrementalParseBatchResult)
                and batch.reused_file_count > 0
                and snapshot.error_count == 0
            )
            if not results and not reusable_only:
                if snapshot.error_count == 0:
                    self._store.append_error(job_id, "No usable parsing results were produced")
                self._mark_failed(job_id, "Parsing produced no usable results")
                return

            self._store.update_progress(
                job_id,
                completed,
                total_files,
                "Finalizing CSV",
            )
            output_path = self._finalize_parse(
                str(attempt_dir),
                batch,
                results,
                snapshot.error_count == 0,
                request.strategy_type,
            )
            results.clear()
            if event.is_set():
                self._mark_cancelled(job_id)
                return
            if output_path is None or not Path(output_path).is_file():
                self._store.append_error(job_id, "Parser did not generate a final CSV")
                self._mark_failed(job_id, "CSV finalization failed")
                return

            snapshot = self._store.get_job(job_id)
            if snapshot is None:
                return
            if snapshot.error_count > 0:
                with self._operation_lock:
                    if event.is_set():
                        self._mark_cancelled(job_id)
                        return
                    self._store.transition(
                        job_id,
                        ParseJobStatus.PARTIAL,
                        "Some files failed; partial CSV is ready",
                        output_csv_path=output_path,
                    )
                return

            with self._operation_lock:
                if event.is_set():
                    self._mark_cancelled(job_id)
                    return
                current = self._store.get_job(job_id)
                if current is None or current.status == ParseJobStatus.CANCELLING:
                    self._mark_cancelled(job_id)
                    return
                published_path = self._publish_output(job_id, request.fingerprint, output_path)
                self._store.transition(
                    job_id,
                    ParseJobStatus.SUCCEEDED,
                    "CSV is ready in Recent CSVs",
                    output_csv_path=output_path,
                    published_csv_path=published_path,
                )
        except Exception as exc:
            results.clear()
            try:
                cancel_event = self._cancel_events.get(job_id)
                if cancel_event is not None and cancel_event.is_set():
                    self._mark_cancelled(job_id)
                else:
                    self._store.append_error(job_id, _format_error(exc))
                    self._mark_failed(job_id, "Parsing failed")
            except (ParseJobNotFoundError, OSError):
                logger.debug("Parse job %s disappeared during shutdown", job_id)
            logger.error("Background parse job %s failed: %s", job_id, exc, exc_info=True)

    def _mark_cancelled(self, job_id: str) -> None:
        with self._operation_lock:
            snapshot = self._store.get_job(job_id)
            if snapshot is None or snapshot.status.is_terminal:
                return
            self._store.transition(
                job_id,
                ParseJobStatus.CANCELLED,
                "Cancelled; running parser calls returned safely",
            )
            if job_id in self._discard_when_terminal:
                self._discard_when_terminal.discard(job_id)
                self._delete_transient_job(job_id)

    def _mark_failed(self, job_id: str, phase: str) -> None:
        with self._operation_lock:
            snapshot = self._store.get_job(job_id)
            if snapshot is None or snapshot.status.is_terminal:
                return
            if snapshot.status == ParseJobStatus.CANCELLING:
                self._mark_cancelled(job_id)
                return
            self._store.transition(job_id, ParseJobStatus.FAILED, phase)

    def _publish_output(self, job_id: str, fingerprint: str, output_path: str) -> str:
        file_name = f"parsed_{fingerprint[:16]}_{job_id}.csv"
        return self._publish_csv(output_path, file_name)

    def _create_attempt_dir(self, job_id: str) -> Path:
        attempt_dir = self._attempts_dir / job_id
        attempt_dir.mkdir(mode=0o700)
        return attempt_dir

    def _get_executor(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix=f"ring5-parse-{self.session_dir.name[:8]}",
            )
        return self._executor

    def _require_job(self, job_id: str) -> ParseJobSnapshot:
        snapshot = self._store.get_job(job_id)
        if snapshot is None:
            raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        return snapshot

    def _delete_transient_job(self, job_id: str) -> None:
        attempt_dir = self._store.delete_job(job_id)
        shutil.rmtree(attempt_dir, ignore_errors=True)
        self._cancel_events.pop(job_id, None)
        self._file_futures.pop(job_id, None)
        self._orchestration_futures.pop(job_id, None)


def _format_error(exc: BaseException) -> str:
    message = str(exc).replace("\n", " ").replace("\r", " ")
    return f"{type(exc).__name__}: {message}"


def _canonical_json(value: object, *, strip_internal_ids: bool) -> str:
    normalized = _to_json_value(value, strip_internal_ids=strip_internal_ids)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def _to_json_value(value: object, *, strip_internal_ids: bool) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return _to_json_value(value.value, strip_internal_ids=strip_internal_ids)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _to_json_value(dataclasses.asdict(value), strip_internal_ids=strip_internal_ids)
    if isinstance(value, Mapping):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            string_key = str(key)
            if strip_internal_ids and string_key == "_id":
                continue
            result[string_key] = _to_json_value(item, strip_internal_ids=strip_internal_ids)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_to_json_value(item, strip_internal_ids=strip_internal_ids) for item in value]
    raise TypeError(f"Unsupported parse request value: {type(value).__name__}")
