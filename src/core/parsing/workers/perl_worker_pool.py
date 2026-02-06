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

import logging
import queue
import shutil
import subprocess  # nosec B404 - Required for persistent Perl worker processes
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        self.process: Optional[subprocess.Popen[str]] = None
        self.is_healthy = False
        self.requests_served = 0
        self.errors_encountered = 0
        self.restarts = 0
        self.last_used = 0.0
        self._lock = threading.Lock()

        # Start the worker
        self._start_worker()

    def _start_worker(self) -> None:
        """Start or restart the Perl worker process."""
        try:
            logger.info(f"[Worker-{self.worker_id}] Starting Perl worker process...")

            # Start Perl server with full executable path
            self.process = subprocess.Popen(  # nosec B603 - Validated paths, no shell
                [self.perl_exe, self.script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,  # Unbuffered for immediate I/O
            )

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

    def _read_line_with_timeout(self, timeout: float = 30.0) -> str:
        """
        Read a line from worker with timeout.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            Line read from worker stdout

        Raises:
            TimeoutError: If read takes longer than timeout
        """
        if not self.process or not self.process.stdout:
            raise RuntimeError("Worker process not available")

        # Use threading for timeout
        result = []
        error = []

        def read_line() -> None:
            if self.process is None or self.process.stdout is None:
                return
            try:
                line = self.process.stdout.readline()
                result.append(line.strip() if line else "")
            except Exception as e:
                error.append(e)

        thread = threading.Thread(target=read_line, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            logger.error(f"[Worker-{self.worker_id}] Read timeout after {timeout}s")
            raise TimeoutError(f"Read timeout after {timeout}s")

        if error:
            raise error[0]

        return result[0] if result else ""

    def parse_file(
        self, file_path: str, variables: List[str], timeout: float = 120.0
    ) -> Tuple[List[str], bool]:
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
            if self.process and self.process.poll() is None:
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
                finally:
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
        self.workers: List[PerlWorker] = []
        self.worker_queue: queue.Queue[PerlWorker] = queue.Queue()
        self._lock = threading.Lock()
        self._shutdown = False
        self._health_check_interval = 30.0  # seconds
        self._health_monitor_thread: Optional[threading.Thread] = None

        # Locate Perl executable (full path for security)
        perl_exe_path = shutil.which("perl")
        if not perl_exe_path:
            logger.error("Perl executable not found in PATH")
            raise RuntimeError("Perl executable not found in PATH")
        # After validation, we know it's not None
        self.perl_exe: str = perl_exe_path

        # Locate Perl server script
        self.script_path = str(Path(__file__).parent.parent / "perl" / "fileParserServer.pl")

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
            while not self._shutdown:
                time.sleep(self._health_check_interval)
                self._check_worker_health()

        self._health_monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._health_monitor_thread.start()

    def _check_worker_health(self) -> None:
        """Check health of all workers and restart unhealthy ones."""
        logger.debug("Running health checks...")

        with self._lock:
            for worker in self.workers:
                if not worker.health_check():
                    logger.warning(f"Worker-{worker.worker_id} is unhealthy, restarting...")
                    if worker.restart():
                        logger.info(f"Worker-{worker.worker_id} restarted successfully")
                    else:
                        logger.error(f"Worker-{worker.worker_id} restart failed!")

    def parse_file(self, file_path: str, variables: List[str], timeout: float = 120.0) -> List[str]:
        """
        Parse a file using the worker pool.

        Args:
            file_path: Path to stats file
            variables: List of variable patterns
            timeout: Maximum parse time

        Returns:
            List of output lines from Perl parser

        Raises:
            RuntimeError: If all workers fail
        """
        max_retries = len(self.workers)  # Try each worker once

        for _attempt in range(max_retries):
            try:
                # Get available worker (blocks if all busy)
                worker = self.worker_queue.get(timeout=timeout)

                try:
                    output_lines, success = worker.parse_file(file_path, variables, timeout)

                    if success:
                        return output_lines
                    else:
                        logger.warning(
                            f"Worker-{worker.worker_id} failed, retrying with different worker"
                        )
                        # Don't return worker to queue yet, health monitor will handle it

                except Exception as e:
                    logger.error(f"Parse error with worker-{worker.worker_id}: {e}")
                finally:
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

    def get_stats(self) -> Dict[str, Any]:
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

        self._shutdown = True

        # Shutdown all workers
        with self._lock:
            for worker in self.workers:
                worker.shutdown()

        logger.info("Worker pool shutdown complete")


# Singleton instance
_worker_pool_instance: Optional[PerlWorkerPool] = None
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
        return _worker_pool_instance


def shutdown_worker_pool() -> None:
    """Shutdown the global worker pool."""
    global _worker_pool_instance

    with _pool_lock:
        if _worker_pool_instance is not None:
            _worker_pool_instance.shutdown()
            _worker_pool_instance = None
