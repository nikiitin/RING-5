"""
Perl Worker Pool - Connection pooling for Perl parser processes.

Maintains a pool of persistent Perl processes to eliminate startup overhead.
Features:
- Automatic worker health monitoring and restart
- Comprehensive error handling and logging
- Worker crash recovery
- Request timeout handling
- Statistics and monitoring
"""

import atexit
from contextlib import ExitStack, suppress
import logging
import os
import queue
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

from src.core.common.security_limits import MAX_PARSE_LINE_COUNT, MAX_PARSE_RESULT_BYTES
from src.parsing.gem5.impl.source_events import SOURCE_WIRE_READY
from src.core.common.parse_failure import (
    bounded_parse_text,
    classify_parse_failure,
    parse_error_text,
)
from src.core.models.parse_failure_models import ParseDataRuntimeError, ParseDataValueError

logger = logging.getLogger(__name__)

DEFAULT_PERL_WORKERS = 2


def _default_pool_size() -> int:
    """Resolve the number of persistent Perl workers.

    Defaults to two persistent processes to bound memory on developer machines.
    Override with ``RING5_PERL_POOL_SIZE`` (an integer >= 1).
    """
    override = os.environ.get("RING5_PERL_POOL_SIZE")
    if override is None:
        return DEFAULT_PERL_WORKERS

    try:
        size = int(override)
    except ValueError:
        logger.warning("Ignoring non-integer RING5_PERL_POOL_SIZE=%r", override)
        return DEFAULT_PERL_WORKERS

    if size < 1:
        logger.warning("Ignoring non-positive RING5_PERL_POOL_SIZE=%r", override)
        return DEFAULT_PERL_WORKERS
    return size


@dataclass
class WorkerStats:
    """Statistics for a worker process."""

    pid: int
    requests_served: int
    errors_encountered: int
    restarts: int
    last_used: float
    is_healthy: bool


@dataclass
class _WorkerGeneration:
    """Exact process and pipe-reader handles owned by one worker generation."""

    process: subprocess.Popen[str]
    line_queue: queue.Queue[str | BaseException | None]
    pipes: tuple[IO[str] | None, ...]
    reader_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None


class PerlWorker:
    """
    Single Perl worker process with health monitoring.

    Manages one persistent Perl subprocess and handles all communication,
    error detection, and recovery.
    """

    def __init__(self, worker_id: int, script_path: str, perl_exe: str):
        """
        Initialize a Perl worker.

        Args:
            worker_id: Unique identifier for this worker
            script_path: Path to the Perl server script
            perl_exe: Full path to Perl executable
        """
        self.worker_id = worker_id
        self.script_path = script_path
        self.perl_exe = perl_exe
        self.process: subprocess.Popen[str] | None = None
        self.is_healthy = False
        self.requests_served = 0
        self.errors_encountered = 0
        self.restarts = 0
        self.last_used = 0.0
        self.is_busy = False
        self._lock = threading.Lock()
        self._lifecycle_lock = threading.RLock()
        # Per-process queues prevent output from a stopped worker reaching its replacement.
        self._line_queue: queue.Queue[str | BaseException | None] | None = None
        self._reader_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None

        # Start the worker
        self._start_worker()

    def _start_worker(self) -> None:
        """Start or restart the Perl worker process.

        Each generation gets a line queue and reader bound to its own stdout,
        preventing protocol output from crossing a restart boundary.

        The process swap runs under ``self._lock`` so a concurrent parse or health
        check (both take ``self._lock``) can't read the queue or write stdin
        mid-restart — the race that left parses hung under heavy load.
        """
        with self._lifecycle_lock, ExitStack() as startup:
            with self._lock:
                if self.process is not None:
                    raise RuntimeError("Shut down the current generation before starting a worker.")
                try:
                    logger.info("[Worker-%s] Starting Perl worker process...", self.worker_id)
                    process: subprocess.Popen[str] = subprocess.Popen(
                        [self.perl_exe, self.script_path],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="strict",
                        bufsize=1,
                        env={
                            **os.environ,
                            "RING5_MAX_PARSE_LINES": str(MAX_PARSE_LINE_COUNT),
                            "RING5_MAX_SOURCE_BYTES": str(MAX_PARSE_RESULT_BYTES),
                        },
                    )
                    generation = _WorkerGeneration(
                        process,
                        queue.Queue(),
                        (process.stdin, process.stdout, process.stderr),
                    )
                    startup.callback(self._retire_generation, generation)
                    # Publication stays under the worker lock. Cleanup owns this
                    # exact generation even if a pipe-reader startup fails.
                    self.process = process
                    self._line_queue = generation.line_queue
                    self._reader_thread = None
                    self._stderr_thread = None
                    self.is_healthy = False
                    try:
                        self._start_reader_thread(process.stdout, generation.line_queue)
                        self._start_stderr_drainer(process.stderr)
                        timeout = 30.0
                        ready_line = self._read_line_with_timeout(timeout=timeout)
                        if ready_line != SOURCE_WIRE_READY:
                            raise ParseDataRuntimeError(
                                f"Worker did not send READY signal within {timeout}s "
                                f"(got: '{ready_line}')"
                            )
                        self.is_healthy = True
                        logger.info(
                            "[Worker-%s] Worker started successfully (PID: %s)",
                            self.worker_id,
                            process.pid,
                        )
                    finally:
                        generation.reader_thread = self._reader_thread
                        generation.stderr_thread = self._stderr_thread
                except UnicodeError as error:
                    if classify_parse_failure(error) != "configuration":
                        raise
                    raise ParseDataRuntimeError(
                        bounded_parse_text(
                            "Perl worker startup output is not valid UTF-8: "
                            f"{parse_error_text(error)}"
                        )
                    ) from error
                except (ParseDataRuntimeError, OSError) as error:
                    if classify_parse_failure(error) is None:
                        raise
                    logger.error(
                        "[Worker-%s] FAILED to start worker: %s",
                        self.worker_id,
                        parse_error_text(error),
                    )
                    raise
            startup.pop_all()

    def _start_reader_thread(
        self, stdout: Any, line_queue: queue.Queue[str | BaseException | None]
    ) -> None:
        """Start a reader thread bound to ONE process generation.

        Reads from the explicitly-captured ``stdout`` into the explicitly-captured
        ``line_queue`` (never ``self.process``/``self._line_queue``), so a stale
        reader left over from a previous generation only drains its own dead pipe
        into its own dead queue. Stream errors retain their identity through the
        queue; a final ``None`` sentinel preserves EOF after success or failure.
        """

        def _reader() -> None:
            try:
                if stdout is None:
                    return
                while True:
                    line = stdout.readline()
                    if not line:
                        return
                    line_queue.put(line.strip())
            except (OSError, ValueError) as error:
                line_queue.put(error)
            finally:
                line_queue.put(None)

        self._reader_thread = threading.Thread(
            target=_reader, daemon=True, name=f"perl-reader-{self.worker_id}"
        )
        self._reader_thread.start()

    def _start_stderr_drainer(self, stderr: Any) -> None:
        """Continuously drain this generation's stderr so its pipe never fills.

        The Perl server logs to stderr (one INFO line per request, plus
        warnings/errors). Those bytes are never consumed by the protocol, so
        without a drainer the pipe fills and blocks the Perl process mid-write —
        stalling stdout and hanging the parse. Perl ERROR lines are surfaced to
        the logger; the rest is discarded. Bound to an explicit ``stderr`` (not
        ``self.process``) so a restarted worker's old drainer exits on EOF.
        """

        def _drain() -> None:
            try:
                if stderr is None:
                    return
                for line in stderr:
                    if "ERROR" in line:
                        logger.warning(
                            "[Worker-%s][perl] %s", self.worker_id, bounded_parse_text(line.strip())
                        )
            except (OSError, ValueError) as exc:
                if classify_parse_failure(exc) not in ("io", "configuration"):
                    raise
                logger.debug(
                    "[Worker-%s] stderr drainer stopped: %s", self.worker_id, parse_error_text(exc)
                )

        self._stderr_thread = threading.Thread(
            target=_drain, daemon=True, name=f"perl-stderr-{self.worker_id}"
        )
        self._stderr_thread.start()

    def _read_line_with_timeout(self, timeout: float = 30.0) -> str:
        """
        Read a line from the worker's stdout queue with timeout.

        The actual I/O is performed by the per-generation reader thread
        (``_start_reader_thread``). Callers hold ``self._lock``, so the queue
        snapshot taken here is stable for the duration of the read.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            Line read from worker stdout

        Raises:
            TimeoutError: If no line arrives within timeout
            RuntimeError: If there is no live queue or the reader signals EOF
        """
        line_queue = self._line_queue
        if line_queue is None:
            raise ParseDataRuntimeError(f"Worker-{self.worker_id} has no active stdout queue")

        try:
            line = line_queue.get(timeout=timeout)
        except queue.Empty as error:
            if classify_parse_failure(error) != "transport":
                raise
            logger.error(f"[Worker-{self.worker_id}] Read timeout after {timeout}s")
            raise TimeoutError(f"Read timeout after {timeout}s")

        if line is None:
            raise ParseDataRuntimeError(f"Worker-{self.worker_id} stdout closed (EOF)")
        if isinstance(line, BaseException):
            raise line

        return line

    def parse_file(
        self, file_path: str, variables: list[str], timeout: float = 120.0
    ) -> tuple[list[str], bool]:
        """
        Parse a file using this worker.

        Args:
            file_path: Path to stats file
            variables: List of variable patterns to extract
            timeout: Maximum seconds to wait for parsing

        Returns:
            Tuple of (output_lines, success)

        Raises:
            RuntimeError: If worker is not healthy
            TimeoutError: If parsing exceeds timeout
        """
        protocol_fields = [file_path, *variables]
        if any("||" in field or "\n" in field or "\r" in field for field in protocol_fields):
            raise ParseDataValueError("Perl worker request contains a reserved protocol delimiter.")

        with self._lock:
            if not self.is_healthy:
                raise ParseDataRuntimeError(f"Worker-{self.worker_id} is not healthy")

            try:
                logger.debug(f"[Worker-{self.worker_id}] Parsing file: {file_path}")

                # Build command with || separator to allow spaces in paths
                args = [file_path] + variables
                command = "PARSE " + "||".join(args) + "\n"

                # Send command
                if not self.process or not self.process.stdin:
                    raise ParseDataRuntimeError("Worker stdin not available")

                self.process.stdin.write(command)
                self.process.stdin.flush()

                # Read output lines until END_PARSE marker
                output_lines = []
                protocol_error: str | None = None
                start_time = time.time()

                while True:
                    elapsed = time.time() - start_time
                    if elapsed > timeout:
                        logger.error(f"[Worker-{self.worker_id}] TIMEOUT after {timeout}s")
                        self.errors_encountered += 1
                        self.is_healthy = False
                        raise TimeoutError(f"Parse timeout after {timeout}s")

                    line = self._read_line_with_timeout(timeout=min(30.0, timeout - elapsed))

                    if line == "END_PARSE":
                        break
                    elif line.startswith("ERROR"):
                        logger.error(
                            f"[Worker-{self.worker_id}] Perl error: {bounded_parse_text(line)}"
                        )
                        self.errors_encountered += 1
                        protocol_error = line
                        # Continue reading to END_PARSE
                    elif line == "RESTART_NEEDED":
                        logger.warning(f"[Worker-{self.worker_id}] Worker needs restart")
                        self.is_healthy = False
                        # Will be restarted by pool manager
                    else:
                        output_lines.append(line)

                self.requests_served += 1
                self.last_used = time.time()

                if protocol_error is not None:
                    logger.error(
                        "[Worker-%s] Parse request failed: %s",
                        self.worker_id,
                        bounded_parse_text(protocol_error),
                    )
                    return [], False

                logger.debug(
                    f"[Worker-{self.worker_id}] Completed: {len(output_lines)} lines "
                    f"in {elapsed:.2f}s"
                )

                return output_lines, True

            except UnicodeError as error:
                if classify_parse_failure(error) != "configuration":
                    raise
                self.errors_encountered += 1
                self.is_healthy = False
                message = bounded_parse_text(
                    f"Perl worker output is not valid UTF-8: {parse_error_text(error)}"
                )
                logger.error("[Worker-%s] %s", self.worker_id, message)
                raise ParseDataRuntimeError(message) from error
            except (ParseDataRuntimeError, OSError) as e:
                if classify_parse_failure(e) is None:
                    raise
                logger.error("[Worker-%s] Parse failed: %s", self.worker_id, parse_error_text(e))
                self.errors_encountered += 1
                self.is_healthy = False
                return [], False

    def health_check(self) -> bool:
        """
        Perform health check on worker.

        Returns:
            True if worker is healthy
        """
        with self._lock:
            if not self.process or self.process.poll() is not None:
                logger.warning(f"[Worker-{self.worker_id}] Process is dead")
                self.is_healthy = False
                return False

            if self.process.stdin is None:
                logger.error(f"[Worker-{self.worker_id}] stdin is None")
                self.is_healthy = False
                return False

            try:
                # Send PING command
                self.process.stdin.write("PING\n")
                self.process.stdin.flush()

                # Wait for PONG
                response = self._read_line_with_timeout(timeout=2.0)

                if response == "PONG":
                    self.is_healthy = True
                    return True
                else:
                    logger.warning(
                        f"[Worker-{self.worker_id}] Unexpected ping response: {response}"
                    )
                    self.is_healthy = False
                    return False

            except UnicodeError as error:
                if classify_parse_failure(error) != "configuration":
                    raise
                logger.error(
                    "[Worker-%s] Health check decoding failed: %s",
                    self.worker_id,
                    parse_error_text(error),
                )
                self.is_healthy = False
                return False
            except (ParseDataRuntimeError, OSError) as e:
                if classify_parse_failure(e) is None:
                    raise
                logger.error(
                    "[Worker-%s] Health check failed: %s", self.worker_id, parse_error_text(e)
                )
                self.is_healthy = False
                return False

    def restart(self) -> bool:
        """
        Restart the worker process.

        Returns:
            True if restart successful
        """
        with self._lifecycle_lock:
            logger.warning(f"[Worker-{self.worker_id}] Restarting worker...")

            # Shutdown old process
            self.shutdown()

            # Start new process
            try:
                self._start_worker()
                self.restarts += 1
                # Reset usage so the freshly-restarted worker isn't immediately re-pinged by
                # the health monitor (a redundant PING right after a clean restart).
                self.last_used = time.time()
                logger.info(f"[Worker-{self.worker_id}] Worker restarted successfully")
                return True
            except (ParseDataRuntimeError, ParseDataValueError, OSError) as e:
                if classify_parse_failure(e) is None:
                    raise
                logger.error("[Worker-%s] Restart failed: %s", self.worker_id, parse_error_text(e))
                return False

    def shutdown(self) -> None:
        """Reap the owned generation, close its pipes and join its readers."""
        with self._lifecycle_lock:
            with self._lock:
                process = self.process
                if process is None:
                    return
                generation = _WorkerGeneration(
                    process,
                    self._line_queue if self._line_queue is not None else queue.Queue(),
                    (process.stdin, process.stdout, process.stderr),
                    self._reader_thread,
                    self._stderr_thread,
                )
            self._retire_generation(generation)

    def _retire_generation(self, generation: _WorkerGeneration) -> None:
        """Retire exact startup/stop handles without claiming a newer generation."""
        with self._lock:
            if self.process is generation.process:
                self.process = None
                self.is_healthy = False
                self._line_queue = None
        process = generation.process
        try:
            if process.poll() is None:
                try:
                    if process.stdin is not None:
                        process.stdin.write("SHUTDOWN\n")
                        process.stdin.flush()
                    process.wait(timeout=2.0)
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    with suppress(ProcessLookupError):
                        process.kill()
                    process.wait()
        finally:
            # Reaping the owned Perl child closes its write ends, so both
            # readers finish on EOF before their parent-side pipes are closed.
            for thread in (generation.reader_thread, generation.stderr_thread):
                if thread is not None and thread.is_alive():
                    thread.join()
            for pipe in generation.pipes:
                if pipe is not None:
                    with suppress(OSError, ValueError):
                        pipe.close()

    def get_stats(self) -> WorkerStats:
        """Get worker statistics."""
        return WorkerStats(
            pid=self.process.pid if self.process else -1,
            requests_served=self.requests_served,
            errors_encountered=self.errors_encountered,
            restarts=self.restarts,
            last_used=self.last_used,
            is_healthy=self.is_healthy,
        )


class PerlWorkerPool:
    """Balance requests across monitored, restartable Perl workers."""

    # [impl->req~ring5.ingestion.persistent-workers~1]

    def __init__(self, pool_size: int | None = None):
        """Initialize the persistent worker pool.

        Args:
            pool_size: Number of worker processes to maintain. When ``None``,
                defaults to two (see ``_default_pool_size``).
        """
        self.pool_size = pool_size if pool_size is not None else _default_pool_size()
        self.workers: list[PerlWorker] = []
        self.worker_queue: queue.Queue[PerlWorker] = queue.Queue()
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._health_check_interval = 30.0  # seconds
        self._health_monitor_thread: threading.Thread | None = None

        # Locate Perl executable (full path for security)
        perl_exe_path = shutil.which("perl")
        if not perl_exe_path:
            logger.error("Perl executable not found in PATH")
            raise ParseDataRuntimeError("Perl executable not found in PATH")
        self.perl_exe: str = perl_exe_path

        # Locate Perl server script (in src/parsing/perl/)
        self.script_path = str(Path(__file__).parent.parent.parent / "perl" / "fileParserServer.pl")

        if not Path(self.script_path).exists():
            logger.error(f"Perl server script not found: {self.script_path}")
            raise FileNotFoundError(f"Perl server script not found: {self.script_path}")

        with ExitStack() as startup:
            startup.callback(self.shutdown)
            self._initialize_pool()
            self._start_health_monitor()
            logger.info(f"Worker pool initialized with {self.pool_size} workers")
            startup.pop_all()

    def _initialize_pool(self) -> None:
        """Initialize worker processes."""
        logger.info(f"Initializing {self.pool_size} Perl workers...")
        last_error: BaseException | None = None

        for i in range(self.pool_size):
            try:
                worker = PerlWorker(
                    worker_id=i, script_path=self.script_path, perl_exe=self.perl_exe
                )
                self.workers.append(worker)
                self.worker_queue.put(worker)
                logger.info(f"Worker {i} initialized")
            except (ParseDataRuntimeError, OSError) as e:
                if classify_parse_failure(e) is None:
                    raise
                last_error = e
                logger.error("Failed to initialize worker %s: %s", i, parse_error_text(e))

        if not self.workers:
            raise ParseDataRuntimeError("No Perl workers could be started") from last_error

        if len(self.workers) < self.pool_size:
            logger.warning(
                f"Only {len(self.workers)}/{self.pool_size} workers started successfully"
            )

    def _start_health_monitor(self) -> None:
        """Start background health monitoring thread."""

        def monitor() -> None:
            logger.info("Health monitor started")
            while not self._shutdown_event.is_set():
                # Interruptible sleep: returns immediately when event is set
                self._shutdown_event.wait(timeout=self._health_check_interval)
                if not self._shutdown_event.is_set():
                    self._check_worker_health()

        self._health_monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._health_monitor_thread.start()

    def _check_worker_health(self) -> None:
        """Check health of all workers and restart unhealthy ones."""
        logger.debug("Running health checks...")

        with self._lock:
            for worker in self.workers:
                # Don't check busy workers to avoid blocking or interfering with active parsing
                if worker.is_busy:
                    continue

                # Avoid probing recently used healthy workers; failed workers require repair.
                if worker.is_healthy and time.time() - worker.last_used < 60.0:
                    continue

                # ``health_check`` mutates this flag; retain it to update the queue correctly.
                was_healthy = worker.is_healthy

                if not worker.health_check():
                    logger.warning(f"Worker-{worker.worker_id} is unhealthy, restarting...")

                    if worker.restart():
                        logger.info(f"Worker-{worker.worker_id} restarted successfully")
                        if not was_healthy:
                            # Worker was already out of the queue; add it back.
                            logger.info(
                                f"Returning Worker-{worker.worker_id} to queue after repair"
                            )
                            self.worker_queue.put(worker)
                        # If was_healthy, the worker object is still referenced in the
                        # queue; the in-place restart updated it so no re-add needed.
                    else:
                        logger.error(f"Worker-{worker.worker_id} restart failed!")

    def parse_file(self, file_path: str, variables: list[str], timeout: float = 120.0) -> list[str]:
        """
        Parse a file using the worker pool.

        Uses a circuit-breaker pattern: splits the total timeout across retries
        so that a series of failures doesn't block for N × timeout seconds.

        Args:
            file_path: Path to stats file
            variables: List of variable patterns
            timeout: Maximum total parse time across all retries

        Returns:
            List of output lines from Perl parser

        Raises:
            RuntimeError: If all workers fail
            TimeoutError: If no workers available within timeout
        """
        max_retries = len(self.workers)  # Try each worker once
        # Split total timeout across retries to avoid queue starvation
        per_attempt_timeout = max(5.0, timeout / max_retries)
        failures = 0
        last_exc: BaseException | None = None

        for _attempt in range(max_retries):
            # Circuit breaker: fail fast if majority of workers are unhealthy
            with self._lock:
                healthy_count = sum(1 for w in self.workers if w.is_healthy)
            if healthy_count == 0 and failures > 0:
                logger.error("Circuit breaker: no healthy workers remaining")
                raise ParseDataRuntimeError(
                    "All workers unhealthy — circuit breaker tripped"
                ) from last_exc

            try:
                # Get available worker with per-attempt timeout
                worker = self.worker_queue.get(timeout=per_attempt_timeout)

                try:
                    # Note: is_busy is a simple boolean attribute. Python's GIL
                    # guarantees atomic reads/writes. The health monitor reads
                    # this flag to skip busy workers (best-effort), so no
                    # additional synchronization is required.
                    worker.is_busy = True
                    # Use the per-attempt budget for the parse too (not the full timeout),
                    # so N retries cannot block for N × timeout as the docstring promises.
                    output_lines, success = worker.parse_file(
                        file_path, variables, per_attempt_timeout
                    )
                    worker.is_busy = False

                    if success:
                        return output_lines
                    else:
                        failures += 1
                        logger.warning(
                            f"Worker-{worker.worker_id} failed, retrying with different worker"
                        )
                        # Don't return worker to queue yet, health monitor will handle it

                except (ParseDataRuntimeError, ParseDataValueError, OSError) as e:
                    if classify_parse_failure(e) is None:
                        raise
                    failures += 1
                    last_exc = e
                    logger.error(
                        "Parse error with worker-%s: %s", worker.worker_id, parse_error_text(e)
                    )
                finally:
                    # Ensure busy flag is cleared even on exception
                    worker.is_busy = False
                    # Return worker to queue if still healthy
                    if worker.is_healthy:
                        self.worker_queue.put(worker)
                    else:
                        logger.warning(f"Worker-{worker.worker_id} marked unhealthy")
                        # Health monitor will restart it

            except queue.Empty as e:
                if classify_parse_failure(e) != "transport":
                    raise
                logger.error("Timeout waiting for available worker")
                raise TimeoutError("No workers available within timeout") from e

        # All workers failed
        logger.error("All workers failed to parse the file")
        raise ParseDataRuntimeError("All workers failed") from last_exc

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                "pool_size": len(self.workers),
                "healthy_workers": sum(1 for w in self.workers if w.is_healthy),
                "total_requests": sum(w.requests_served for w in self.workers),
                "total_errors": sum(w.errors_encountered for w in self.workers),
                "total_restarts": sum(w.restarts for w in self.workers),
                "workers": [w.get_stats() for w in self.workers],
            }

    def shutdown(self) -> None:
        """Shutdown the worker pool."""
        logger.info("Shutting down worker pool...")

        # Signal health monitor to stop (wakes it from sleep immediately)
        self._shutdown_event.set()

        # Wait for health monitor thread to finish
        monitor = self._health_monitor_thread
        self._health_monitor_thread = None
        if monitor is not None and monitor.is_alive():
            monitor.join()

        # Shutdown all workers
        with self._lock:
            for worker in self.workers:
                worker.shutdown()

        logger.info("Worker pool shutdown complete")


# Singleton instance
_worker_pool_instance: PerlWorkerPool | None = None
_pool_lock = threading.Lock()


def get_worker_pool(pool_size: int | None = None) -> PerlWorkerPool:
    # [impl->req~ring5.api.process-lifecycle~1]
    """
    Return the singleton worker pool, creating it when necessary.

    Args:
        pool_size: Number of workers (only used on first call). ``None`` resolves
            to two (override via ``RING5_PERL_POOL_SIZE``).

    Returns:
        PerlWorkerPool instance
    """
    global _worker_pool_instance

    with _pool_lock:
        if _worker_pool_instance is None:
            _worker_pool_instance = PerlWorkerPool(pool_size=pool_size)
            atexit.register(shutdown_worker_pool)
        return _worker_pool_instance


def shutdown_worker_pool() -> None:
    # [impl->req~ring5.api.process-lifecycle~1]
    """Shutdown the global worker pool."""
    global _worker_pool_instance

    with _pool_lock:
        if _worker_pool_instance is not None:
            _worker_pool_instance.shutdown()
            _worker_pool_instance = None
