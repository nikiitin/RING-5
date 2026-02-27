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
import logging
import queue
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WorkerStats:
    """Statistics for a worker process."""

    pid: int
    requests_served: int
    errors_encountered: int
    restarts: int
    last_used: float
    is_healthy: bool


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
        # Queue-based stdout reader: ONE persistent thread per worker
        # instead of spawning a thread per readline call.
        self._line_queue: queue.Queue[str | None] = queue.Queue()
        self._reader_thread: threading.Thread | None = None

        # Start the worker
        self._start_worker()

    def _start_worker(self) -> None:
        """Start or restart the Perl worker process."""
        try:
            logger.info(f"[Worker-{self.worker_id}] Starting Perl worker process...")

            # Drain any leftover data from a previous reader thread
            while not self._line_queue.empty():
                try:
                    self._line_queue.get_nowait()
                except queue.Empty:
                    break

            # Start Perl server with full executable path
            self.process = subprocess.Popen(
                [self.perl_exe, self.script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,  # Unbuffered for immediate I/O
            )

            # Start ONE persistent reader thread for this worker's stdout
            self._start_reader_thread()

            # Wait for READY signal (with timeout)
            # Increased from 5s to 30s to handle slow container/host process start
            timeout = 30.0
            ready_line = self._read_line_with_timeout(timeout=timeout)

            if ready_line != "READY":
                raise RuntimeError(
                    f"Worker did not send READY signal within {timeout}s (got: '{ready_line}')"
                )

            self.is_healthy = True
            logger.info(
                f"[Worker-{self.worker_id}] Worker started successfully (PID: {self.process.pid})"
            )

        except Exception as e:
            logger.error(f"[Worker-{self.worker_id}] FAILED to start worker: {e}", exc_info=True)
            self.is_healthy = False
            raise

    def _start_reader_thread(self) -> None:
        """Start a persistent background thread that reads stdout into a queue.

        One thread per worker lifetime (not per read call). The thread exits
        when the process closes stdout (EOF) or the process dies.
        """

        def _reader() -> None:
            try:
                while self.process and self.process.stdout:
                    line = self.process.stdout.readline()
                    if not line:
                        # EOF — process closed stdout
                        self._line_queue.put(None)
                        break
                    self._line_queue.put(line.strip())
            except Exception:
                self._line_queue.put(None)

        self._reader_thread = threading.Thread(
            target=_reader, daemon=True, name=f"perl-reader-{self.worker_id}"
        )
        self._reader_thread.start()

    def _read_line_with_timeout(self, timeout: float = 30.0) -> str:
        """
        Read a line from the worker's stdout queue with timeout.

        The actual I/O is performed by the persistent reader thread started
        in ``_start_reader_thread``. This method simply pulls from the queue,
        avoiding thread-per-read accumulation.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            Line read from worker stdout

        Raises:
            TimeoutError: If no line arrives within timeout
            RuntimeError: If the reader thread signals EOF
        """
        try:
            line = self._line_queue.get(timeout=timeout)
        except queue.Empty:
            logger.error(f"[Worker-{self.worker_id}] Read timeout after {timeout}s")
            raise TimeoutError(f"Read timeout after {timeout}s")

        if line is None:
            raise RuntimeError(f"Worker-{self.worker_id} stdout closed (EOF)")

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
        with self._lock:
            if not self.is_healthy:
                raise RuntimeError(f"Worker-{self.worker_id} is not healthy")

            try:
                logger.debug(f"[Worker-{self.worker_id}] Parsing file: {file_path}")

                # Build command with || separator to allow spaces in paths
                args = [file_path] + variables
                command = "PARSE " + "||".join(args) + "\n"

                # Send command
                if not self.process or not self.process.stdin:
                    raise RuntimeError("Worker stdin not available")

                self.process.stdin.write(command)
                self.process.stdin.flush()

                # Read output lines until END_PARSE marker
                output_lines = []
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
                        logger.error(f"[Worker-{self.worker_id}] Perl error: {line}")
                        self.errors_encountered += 1
                        # Continue reading to END_PARSE
                    elif line == "RESTART_NEEDED":
                        logger.warning(f"[Worker-{self.worker_id}] Worker needs restart")
                        self.is_healthy = False
                        # Will be restarted by pool manager
                    else:
                        output_lines.append(line)

                self.requests_served += 1
                self.last_used = time.time()

                logger.debug(
                    f"[Worker-{self.worker_id}] Completed: {len(output_lines)} lines "
                    f"in {elapsed:.2f}s"
                )

                return output_lines, True

            except Exception as e:
                logger.error(f"[Worker-{self.worker_id}] Parse failed: {e}", exc_info=True)
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

            except Exception as e:
                logger.error(f"[Worker-{self.worker_id}] Health check failed: {e}")
                self.is_healthy = False
                return False

    def restart(self) -> bool:
        """
        Restart the worker process.

        Returns:
            True if restart successful
        """
        logger.warning(f"[Worker-{self.worker_id}] Restarting worker...")

        # Shutdown old process
        self.shutdown()

        # Start new process
        try:
            self._start_worker()
            self.restarts += 1
            logger.info(f"[Worker-{self.worker_id}] Worker restarted successfully")
            return True
        except Exception as e:
            logger.error(f"[Worker-{self.worker_id}] Restart failed: {e}")
            return False

    def shutdown(self) -> None:
        """Gracefully shutdown the worker."""
        with self._lock:
            if self.process is not None:
                if self.process.poll() is None:
                    try:
                        # Try graceful shutdown
                        if self.process.stdin is not None:
                            self.process.stdin.write("SHUTDOWN\n")
                            self.process.stdin.flush()
                        self.process.wait(timeout=2.0)
                        logger.info(f"[Worker-{self.worker_id}] Graceful shutdown complete")
                    except Exception:
                        # Force kill
                        self.process.kill()
                        logger.warning(f"[Worker-{self.worker_id}] Forced shutdown")
                # Always close subprocess pipes to prevent resource leaks
                for pipe in (
                    self.process.stdin,
                    self.process.stdout,
                    self.process.stderr,
                ):
                    if pipe:
                        try:
                            pipe.close()
                        except OSError:
                            pass
                self.process = None
                self.is_healthy = False

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
    """
    Pool of Perl worker processes with automatic health monitoring.

    Provides robust connection pooling with:
    - Automatic worker restart on failure
    - Load balancing across workers
    - Health monitoring
    - Statistics tracking
    """

    def __init__(self, pool_size: int = 4):
        """
        Initialize worker pool - THE PRIMARY MECHANISM.

        Args:
            pool_size: Number of worker processes to maintain
        """
        self.pool_size = pool_size
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
            raise RuntimeError("Perl executable not found in PATH")
        # After validation, we know it's not None
        self.perl_exe: str = perl_exe_path

        # Locate Perl server script (in src/parsing/perl/)
        self.script_path = str(Path(__file__).parent.parent.parent / "perl" / "fileParserServer.pl")

        if not Path(self.script_path).exists():
            logger.error(f"Perl server script not found: {self.script_path}")
            raise FileNotFoundError(f"Perl server script not found: {self.script_path}")

        # Initialize pool - this is the ONLY mechanism now!
        self._initialize_pool()
        self._start_health_monitor()
        logger.info(f"Worker pool initialized as PRIMARY mechanism ({pool_size} workers)")

    def _initialize_pool(self) -> None:
        """Initialize worker processes."""
        logger.info(f"Initializing {self.pool_size} Perl workers...")

        for i in range(self.pool_size):
            try:
                worker = PerlWorker(
                    worker_id=i, script_path=self.script_path, perl_exe=self.perl_exe
                )
                self.workers.append(worker)
                self.worker_queue.put(worker)
                logger.info(f"Worker {i} initialized")
            except Exception as e:
                logger.error(f"Failed to initialize worker {i}: {e}")
                # Continue with fewer workers

        if not self.workers:
            raise RuntimeError("CRITICAL: No workers could be started!")

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

                # Skip workers used recently — health check PING/PONG adds latency
                # and could collide with a parse that starts between is_busy check
                # and health_check() call (TOCTOU window)
                if time.time() - worker.last_used < 60.0:
                    continue

                # Capture health state BEFORE health_check() mutates is_healthy.
                # If was_healthy=True, the worker is currently in the queue (alive but about
                # to fail the check). If was_healthy=False, it's already out of the queue.
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

        for _attempt in range(max_retries):
            # Circuit breaker: fail fast if majority of workers are unhealthy
            with self._lock:
                healthy_count = sum(1 for w in self.workers if w.is_healthy)
            if healthy_count == 0 and failures > 0:
                logger.error("Circuit breaker: no healthy workers remaining")
                raise RuntimeError("All workers unhealthy — circuit breaker tripped")

            try:
                # Get available worker with per-attempt timeout
                worker = self.worker_queue.get(timeout=per_attempt_timeout)

                try:
                    # Note: is_busy is a simple boolean attribute. Python's GIL
                    # guarantees atomic reads/writes. The health monitor reads
                    # this flag to skip busy workers (best-effort), so no
                    # additional synchronization is required.
                    worker.is_busy = True
                    output_lines, success = worker.parse_file(file_path, variables, timeout)
                    worker.is_busy = False

                    if success:
                        return output_lines
                    else:
                        failures += 1
                        logger.warning(
                            f"Worker-{worker.worker_id} failed, retrying with different worker"
                        )
                        # Don't return worker to queue yet, health monitor will handle it

                except Exception as e:
                    failures += 1
                    logger.error(f"Parse error with worker-{worker.worker_id}: {e}")
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
                logger.error("Timeout waiting for available worker")
                raise TimeoutError("No workers available within timeout") from e

        # All workers failed
        logger.error("CRITICAL: All workers failed to parse file!")
        raise RuntimeError("All workers failed")

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
        if self._health_monitor_thread is not None:
            self._health_monitor_thread.join(timeout=self._health_check_interval + 1)
            self._health_monitor_thread = None

        # Shutdown all workers
        with self._lock:
            for worker in self.workers:
                worker.shutdown()

        logger.info("Worker pool shutdown complete")

    def __del__(self) -> None:
        """Ensure workers are cleaned up on garbage collection."""
        try:
            if hasattr(self, "_shutdown_event") and not self._shutdown_event.is_set():
                self.shutdown()
        except Exception:  # nosec B110 — __del__ must not raise
            pass


# Singleton instance
_worker_pool_instance: PerlWorkerPool | None = None
_pool_lock = threading.Lock()


def get_worker_pool(pool_size: int = 4) -> PerlWorkerPool:
    """
    Get or create the singleton worker pool - THE PRIMARY MECHANISM.

    Args:
        pool_size: Number of workers (only used on first call)

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
    """Shutdown the global worker pool."""
    global _worker_pool_instance

    with _pool_lock:
        if _worker_pool_instance is not None:
            _worker_pool_instance.shutdown()
            _worker_pool_instance = None
