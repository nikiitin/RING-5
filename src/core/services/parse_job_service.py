"""Session-owned orchestration for background parse jobs."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import threading
import uuid
from collections.abc import Callable, Sequence
from concurrent.futures import (
    FIRST_COMPLETED,
    CancelledError,
    Future,
    ThreadPoolExecutor,
    wait,
)
from pathlib import Path

from src.core.common.source_context_codec import SourceContextCodec
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.source_context_models import ParserSourceContext
from src.core.models.parsed_output_models import ParsedFileResult, ParsedOutput
from src.core.models.parsing_models import StatConfig
from src.core.models.data_models import ScannedVariableDict
from src.core.common.input_identity import fingerprint_inputs
from src.core.common.utils import normalize_user_path, validate_stats_pattern
from src.core.models.parsing_models import IncrementalParseBatchResult, ParseBatchResult
from src.core.models.parse_job_models import (
    ParseFileSignature,
    ParseJobConflictError,
    ParseJobNotConsumableError,
    ParseJobNotFoundError,
    ParseJobReceipt,
    ParseJobRequest,
    ParseJobSnapshot,
    ParseJobStatus,
)
from src.core.models.parsing_models import PARSER_RESULT_VERSION, require_current_parser_contract
from src.core.services.parse_job_store import (
    MAX_REQUEST_JSON_BYTES,
    InvalidStoredOutput,
    ParseJobStore,
)
from src.core.services.parse_job_workspace import ParseJobRuntimeWorkspace
from src.parsing.framework.file_discovery import find_stats_files

logger = logging.getLogger(__name__)

PARSER_CONTRACT_VERSION = str(PARSER_RESULT_VERSION)

SubmitParse = Callable[
    [ParserSourceContext, str, bool],
    ParseBatchResult | IncrementalParseBatchResult,
]
FinalizeParse = Callable[
    [ParseBatchResult | IncrementalParseBatchResult, list[ParsedFileResult], bool],
    ParsedOutput,
]
PublishCsv = Callable[[ParsedOutput, str], ParsedOutput]
BeforeCleanup = Callable[[ParseJobReceipt], None]


def build_parse_job_request(
    *,
    stats_path: str,
    stats_pattern: str,
    variables: Sequence[StatConfig],
    strategy_type: str,
    scanned_variables: Sequence[ScannedVariableDict] | None = None,
    simulator: str | None = None,
    parser_contract_version: str = PARSER_CONTRACT_VERSION,
    incremental: bool = False,
) -> ParseJobRequest:
    """Own the exact resolved request and fingerprint its actual source contents."""
    require_current_parser_contract(parser_contract_version)
    normalized_path = normalize_user_path(stats_path)
    if not normalized_path.exists():
        raise FileNotFoundError(f"Stats path does not exist: {stats_path}")
    if not normalized_path.is_dir():
        raise NotADirectoryError(f"Stats path is not a directory: {stats_path}")
    normalized_pattern = validate_stats_pattern(stats_pattern)
    scanned = () if scanned_variables is None else scanned_variables
    if isinstance(scanned, (str, bytes)) or any(type(value) is not dict for value in scanned):
        raise TypeError("Parse jobs require current scanned-variable payloads.")
    context = SourceContextCodec.parser(
        stats_path=str(normalized_path),
        stats_pattern=normalized_pattern,
        strategy_type=strategy_type,
        variables=variables,
        scanned_variables=scanned,
        simulator=simulator,
        parser_contract_version=parser_contract_version,
        scan_limit=None,
        strict=False,
        metadata_byte_limit=MAX_REQUEST_JSON_BYTES,
    )
    signatures: list[ParseFileSignature] = []
    matching_paths = find_stats_files(str(normalized_path), normalized_pattern, sort=True)
    for candidate in matching_paths:
        resolved = Path(candidate).resolve(strict=True)
        stat = resolved.stat()
        signatures.append(ParseFileSignature(str(resolved), stat.st_size, stat.st_mtime_ns))
    signatures.sort(key=lambda item: item.path)
    fingerprint_payload = {
        "source_context": SourceContextCodec.to_payload(context),
        "matching_files": fingerprint_inputs(matching_paths, strategy_type),
        "incremental": incremental,
    }
    encoded = json.dumps(
        fingerprint_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    request = ParseJobRequest(
        context, tuple(signatures), hashlib.sha256(encoded.encode("utf-8")).hexdigest(), incremental
    )
    ParseJobStore._encode_request(request)
    return request


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
        # Cancellation must remain signalable while publication waits outside
        # the serialized state-transition lock.
        self._cancel_event_lock = threading.Lock()
        self._executor: ThreadPoolExecutor | None = None
        self._cancel_events: dict[str, threading.Event] = {}
        self._file_futures: dict[str, tuple[Future[ParsedFileResult], ...]] = {}
        self._orchestration_futures: dict[str, Future[None]] = {}
        self._discard_when_terminal: set[str] = set()
        self._closed = False
        self._runtime_workspace.register_session_closer(self.session_dir, self.close)

    def submit(
        self,
        *,
        stats_path: str,
        stats_pattern: str,
        variables: Sequence[StatConfig],
        strategy_type: str,
        scanned_variables: Sequence[ScannedVariableDict] | None = None,
        simulator: str | None = None,
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
        snapshot = self._require_job(job_id)
        if snapshot.status.is_terminal:
            return snapshot
        self._signal_cancellation(job_id)
        with self._operation_lock:
            snapshot = self._require_job(job_id)
            if snapshot.status.is_terminal:
                return snapshot
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
            request = self._refresh_request(old_request)
            attempt_dir = self._store.delete_job(job_id)
            shutil.rmtree(attempt_dir, ignore_errors=True)
            self._remove_cancel_event(job_id)
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
        """Validate and consume actual output before deleting its transient attempt."""
        with self._operation_lock:
            snapshot = self._require_job(job_id)
            if snapshot.status == ParseJobStatus.PARTIAL and not allow_partial:
                raise ParseJobNotConsumableError("Partial parse results require allow_partial=True")
            if snapshot.status not in {ParseJobStatus.SUCCEEDED, ParseJobStatus.PARTIAL}:
                raise ParseJobNotConsumableError(
                    f"Parse job in {snapshot.status.value} state cannot be consumed"
                )
            request = self._store.get_request(job_id)
            published = snapshot.published_output
            if snapshot.status == ParseJobStatus.PARTIAL:
                if snapshot.output is None:
                    raise FileNotFoundError("Partial parse output is no longer available")
                ParsedOutputIO.read(snapshot.output)
                published = self._publish_output(job_id, snapshot.fingerprint, snapshot.output)
            if published is None:
                self._store.forget_published(snapshot.fingerprint)
                raise FileNotFoundError("Published parse result is no longer available")
            try:
                ParsedOutputIO.read(published)
            except (OSError, ValueError, TypeError):
                self._store.forget_published(snapshot.fingerprint)
                if snapshot.status == ParseJobStatus.PARTIAL:
                    self._discard_published_output(published)
                raise
            receipt = ParseJobReceipt(
                job_id,
                snapshot.fingerprint,
                published,
                request.source_context,
                snapshot.status,
                snapshot.cache_hit,
            )
            if before_cleanup is not None:
                try:
                    before_cleanup(receipt)
                except Exception:
                    if snapshot.status == ParseJobStatus.PARTIAL:
                        self._discard_published_output(published)
                    raise
            if snapshot.status == ParseJobStatus.SUCCEEDED:
                self._store.remember_published(snapshot.fingerprint, published)
            attempt_dir = self._store.delete_job(job_id)
            self._remove_attempt(job_id, attempt_dir)
            return receipt

    def dismiss(self, job_id: str) -> None:
        """Acknowledge a terminal job and remove all of its transient data."""
        with self._operation_lock:
            snapshot = self._require_job(job_id)
            if not snapshot.status.is_terminal:
                raise ParseJobNotConsumableError("An active parse job cannot be dismissed")
            attempt_dir = self._store.delete_job(job_id)
            shutil.rmtree(attempt_dir, ignore_errors=True)
            self._remove_cancel_event(job_id)
            self._file_futures.pop(job_id, None)
            self._orchestration_futures.pop(job_id, None)

    def reset(self) -> None:
        """Cancel active work and discard every unconsumed session attempt."""
        self._signal_all_cancellations()
        with self._operation_lock:
            active = self._store.get_active_job()
            for snapshot in self._store.list_jobs():
                if snapshot.status.is_terminal:
                    self._delete_transient_job(snapshot.job_id)
            if active is None:
                return
            self._discard_when_terminal.add(active.job_id)
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
        self._signal_all_cancellations()
        with self._operation_lock:
            if self._closed:
                return
            self._closed = True
            active = self._store.get_active_job()
            if active is not None:
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
            with self._cancel_event_lock:
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
        """Coalesce, reuse, or enqueue an already-canonical request."""
        if self._closed:
            raise RuntimeError("Parse job service is closed")

        active = self._store.get_active_job()
        if active is not None:
            if active.fingerprint == request.fingerprint:
                return active
            raise ParseJobConflictError(
                f"Parse job {active.job_id} is already active in this session"
            )

        try:
            existing = self._store.get_latest_by_fingerprint(request.fingerprint)
        except InvalidStoredOutput:
            stale = self._store.discard_cached_success(request.fingerprint)
            if stale is None:
                raise
            self._store.forget_published(request.fingerprint)
            self._remove_attempt(*stale)
            existing = None
        if existing is not None and not ignore_cached_result:
            if existing.status == ParseJobStatus.SUCCEEDED and not self._valid_output(
                existing.published_output
            ):
                self._store.forget_published(request.fingerprint)
                self._delete_transient_job(existing.job_id)
            else:
                return existing

        if not ignore_cached_result:
            try:
                published = self._store.get_published(request.fingerprint)
            except InvalidStoredOutput:
                self._store.forget_published(request.fingerprint)
                published = None
            if published is not None:
                if self._valid_output(published):
                    job_id = uuid.uuid4().hex
                    attempt_dir = self._create_attempt_dir(job_id)
                    try:
                        return self._store.create_job(
                            job_id,
                            request,
                            attempt_dir,
                            attempt,
                            status=ParseJobStatus.SUCCEEDED,
                            phase="Reusing session result from Recent CSVs",
                            published_output=published,
                            cache_hit=True,
                        )
                    except Exception:
                        shutil.rmtree(attempt_dir, ignore_errors=True)
                        raise
                self._store.forget_published(request.fingerprint)

        job_id = uuid.uuid4().hex
        attempt_dir = self._create_attempt_dir(job_id)
        try:
            snapshot = self._store.create_job(job_id, request, attempt_dir, attempt)
        except Exception:
            shutil.rmtree(attempt_dir, ignore_errors=True)
            raise
        event = threading.Event()
        with self._cancel_event_lock:
            self._cancel_events[job_id] = event
        try:
            executor = self._get_executor()
            orchestration = executor.submit(self._run_job, job_id)
        except Exception:
            self._delete_transient_job(job_id)
            raise
        self._orchestration_futures[job_id] = orchestration
        return snapshot

    def _run_job(self, job_id: str) -> None:
        """Drive typed file work to a visible terminal state on the owned executor."""
        results: list[ParsedFileResult] = []
        try:
            event = self._get_cancel_event(job_id)
            if event is None:
                return
            request = self._store.get_request(job_id)
            attempt_dir = self._store.get_attempt_dir(job_id)
            with self._operation_lock:
                if event.is_set():
                    self._mark_cancelled(job_id)
                    return
                self._store.transition(job_id, ParseJobStatus.RUNNING, "Preparing parser work")
            batch = self._submit_parse(
                request.source_context, str(attempt_dir), request.incremental
            )
            futures = batch.futures
            reused = (
                batch.reused_file_count if isinstance(batch, IncrementalParseBatchResult) else 0
            )
            total = (
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
                reused,
                total,
                (
                    f"Reusing {reused} unchanged files; parsing {len(futures)} files"
                    if reused
                    else ("Parsing files" if futures else "No matching parser work")
                ),
            )
            completed = reused
            pending = set(futures)
            while pending:
                if event.is_set():
                    for future in pending:
                        future.cancel()
                done, pending = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED)
                for future in done:
                    completed += 1
                    try:
                        result = future.result()
                        if type(result) is not ParsedFileResult:
                            raise TypeError("Parser workers must return ParsedFileResult values.")
                        results.append(result)
                    except CancelledError:
                        if not event.is_set():
                            self._store.append_error(
                                job_id, "Parser file work was cancelled before producing a result"
                            )
                    except Exception as exc:
                        self._store.append_error(job_id, _format_error(exc))
                    self._store.update_progress(
                        job_id, completed, total, f"Prepared {completed} of {total} files"
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
            if not results and not (
                isinstance(batch, IncrementalParseBatchResult) and batch.reused_file_count > 0
            ):
                if snapshot.error_count == 0:
                    self._store.append_error(job_id, "No usable parsing results were produced")
                self._mark_failed(job_id, "Parsing produced no usable results")
                return
            if self._refresh_request(request).fingerprint != request.fingerprint:
                raise ValueError("Parser inputs changed during execution; submit a new request.")
            self._store.update_progress(job_id, completed, total, "Finalizing CSV")
            output = self._finalize_parse(batch, results, snapshot.error_count == 0)
            results.clear()
            ParsedOutputIO.read(output)
            if event.is_set():
                self._mark_cancelled(job_id)
                return
            snapshot = self._store.get_job(job_id)
            if snapshot is None:
                return
            if snapshot.error_count > 0:
                with self._operation_lock:
                    current = self._store.get_job(job_id)
                    with self._cancel_event_lock:
                        cancelled = (
                            event.is_set()
                            or current is None
                            or current.status == ParseJobStatus.CANCELLING
                        )
                        if not cancelled:
                            self._store.transition(
                                job_id,
                                ParseJobStatus.PARTIAL,
                                "Some files failed; partial CSV is ready",
                                output=output,
                            )
                            return
                    self._mark_cancelled(job_id)
                return
            published = self._publish_output(job_id, request.fingerprint, output)
            ParsedOutputIO.read(published)
            with self._operation_lock:
                current = self._store.get_job(job_id)
                with self._cancel_event_lock:
                    cancelled = (
                        event.is_set()
                        or current is None
                        or current.status == ParseJobStatus.CANCELLING
                    )
                    if not cancelled:
                        self._store.transition(
                            job_id,
                            ParseJobStatus.SUCCEEDED,
                            "CSV is ready in Recent CSVs",
                            output=output,
                            published_output=published,
                        )
                        return
                self._discard_published_output(published)
                self._mark_cancelled(job_id)
        except Exception as exc:
            # This owned orchestration boundary persists failures before its Future completes.
            results.clear()
            try:
                event = self._get_cancel_event(job_id)
                if event is not None and event.is_set():
                    self._mark_cancelled(job_id)
                else:
                    self._store.append_error(job_id, _format_error(exc))
                    self._mark_failed(job_id, "Parsing failed")
            except (ParseJobNotFoundError, OSError):
                logger.debug("Parse job %s disappeared during shutdown", job_id)
            logger.error("Background parse job %s failed: %s", job_id, exc, exc_info=True)

    @staticmethod
    def _refresh_request(request: ParseJobRequest) -> ParseJobRequest:
        """Recompute signatures and content identity from the captured source request."""
        source = request.source_context
        return build_parse_job_request(
            stats_path=source.stats_path,
            stats_pattern=source.stats_pattern,
            variables=SourceContextCodec.variables(source),
            strategy_type=source.strategy_type,
            scanned_variables=SourceContextCodec.scanned_payloads(source),
            simulator=source.simulator,
            parser_contract_version=source.parser_contract_version,
            incremental=request.incremental,
        )

    @staticmethod
    def _valid_output(output: ParsedOutput | None) -> bool:
        """Permit cache reuse only after descriptor, content and read-stability validation."""
        if output is None:
            return False
        try:
            ParsedOutputIO.read(output)
        except (OSError, ValueError, TypeError):
            return False
        return True

    def _mark_cancelled(self, job_id: str) -> None:
        """Finish cancellation and discard reset jobs after workers return."""
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
        """Persist failure unless cancellation won the terminal-state race."""
        with self._operation_lock:
            snapshot = self._store.get_job(job_id)
            if snapshot is None or snapshot.status.is_terminal:
                return
            with self._cancel_event_lock:
                event = self._cancel_events.get(job_id)
                cancelled = snapshot.status == ParseJobStatus.CANCELLING or (
                    event is not None and event.is_set()
                )
                if not cancelled:
                    self._store.transition(job_id, ParseJobStatus.FAILED, phase)
                    return
            self._mark_cancelled(job_id)

    def _publish_output(self, job_id: str, fingerprint: str, output: ParsedOutput) -> ParsedOutput:
        """Publish under a collision-resistant Recent CSV name."""
        file_name = f"parsed_{fingerprint[:16]}_{job_id}.csv"
        return self._publish_csv(output, file_name)

    @staticmethod
    def _discard_published_output(output: ParsedOutput) -> None:
        """Remove a job-owned Recent CSV when cancellation wins publication."""
        try:
            Path(output.csv_path).unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove cancelled parse output %s", output.csv_path)

    def _get_cancel_event(self, job_id: str) -> threading.Event | None:
        """Return a cancellation event without racing session cleanup."""
        with self._cancel_event_lock:
            return self._cancel_events.get(job_id)

    def _remove_cancel_event(self, job_id: str) -> None:
        """Forget a cancellation event after its attempt is removed."""
        with self._cancel_event_lock:
            self._cancel_events.pop(job_id, None)

    def _signal_cancellation(self, job_id: str) -> None:
        """Signal cancellation before waiting for serialized job operations."""
        with self._cancel_event_lock:
            event = self._cancel_events.get(job_id)
            if event is not None:
                event.set()

    def _signal_all_cancellations(self) -> None:
        """Signal every retained attempt before reset or shutdown waits on publication."""
        with self._cancel_event_lock:
            for event in self._cancel_events.values():
                event.set()

    def _create_attempt_dir(self, job_id: str) -> Path:
        """Create the private temporary directory for one attempt."""
        attempt_dir = self._attempts_dir / job_id
        attempt_dir.mkdir(mode=0o700)
        return attempt_dir

    def _get_executor(self) -> ThreadPoolExecutor:
        """Lazily create the session's single orchestration executor."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix=f"ring5-parse-{self.session_dir.name[:8]}",
            )
        return self._executor

    def _require_job(self, job_id: str) -> ParseJobSnapshot:
        """Return a session-owned job or raise a typed lookup error."""
        snapshot = self._store.get_job(job_id)
        if snapshot is None:
            raise ParseJobNotFoundError(f"Unknown parse job: {job_id}")
        return snapshot

    def _delete_transient_job(self, job_id: str) -> None:
        """Remove persisted metadata and every handle owned by one settled attempt."""
        self._remove_attempt(job_id, self._store.delete_job(job_id))

    def _remove_attempt(self, job_id: str, attempt_dir: Path) -> None:
        """Dispose only this session's controlled attempt directory and owned handles."""
        if attempt_dir.resolve().parent != self._attempts_dir.resolve():
            raise ValueError("Parse attempt directory is outside this session's workspace.")
        shutil.rmtree(attempt_dir, ignore_errors=True)
        self._remove_cancel_event(job_id)
        self._file_futures.pop(job_id, None)
        self._orchestration_futures.pop(job_id, None)
        self._discard_when_terminal.discard(job_id)


def _format_error(exc: BaseException) -> str:
    """Flatten an exception into one bounded-store-friendly line."""
    message = str(exc).replace("\n", " ").replace("\r", " ")
    return f"{type(exc).__name__}: {message}"
