"""
Work Pool — singleton thread-pool manager for parallel parse/scan work.

Backends dispatch their callable per-file work units to this thread pool; the
heavy CPU work typically runs out-of-process in the backend's own workers, so a
thread pool (not a process pool) is the right executor here.
"""

from __future__ import annotations

import atexit
import logging
import os
import threading
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DEFAULT_WORKERS = 2


def _default_workers() -> int:
    """Return the bounded worker count, honoring an explicit deployment override."""
    value = os.environ.get("RING5_WORK_POOL_SIZE")
    if value is None:
        return DEFAULT_WORKERS

    try:
        workers = int(value)
    except ValueError:
        logger.warning("Ignoring non-integer RING5_WORK_POOL_SIZE=%r", value)
        return DEFAULT_WORKERS

    if workers < 1:
        logger.warning("Ignoring non-positive RING5_WORK_POOL_SIZE=%r", value)
        return DEFAULT_WORKERS
    return workers


class WorkPool:
    """Unified singleton thread-pool manager for parallel task execution."""

    _instance: WorkPool | None = None
    _initialized: bool
    _new_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> WorkPool:
        """Return the process-wide singleton, creating it under a lock if needed."""
        with cls._new_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        """Initialize the executor configuration once for the singleton instance."""
        # Guard runs under the construction lock so two threads racing the very
        # first WorkPool() can never both run the init body.
        with self._new_lock:
            if self._initialized:
                return
            self._num_workers = _default_workers()
            self._thread_executor: ThreadPoolExecutor | None = None
            self._retiring_executor: ThreadPoolExecutor | None = None
            self._executor_lock = threading.Lock()
            self._global_shutdown_lock = threading.Lock()
            self._admission_closed = False
            self._worker_context = threading.local()
            self._initialized = True

    @classmethod
    def get_instance(cls) -> WorkPool:
        """Return the process-wide work-pool instance."""
        return cls()

    def submit[_Result](self, task: Callable[[], _Result]) -> Future[_Result]:
        # [impl->req~ring5.api.process-lifecycle~1]
        """Submit one callable and return its caller-owned future."""
        return self.submit_many([task])[0]

    def submit_many[_Result](self, tasks: Sequence[Callable[[], _Result]]) -> list[Future[_Result]]:
        """Submit a batch without retaining its futures or results.

        Args:
            tasks: Callable work items in submission order.

        Returns:
            One caller-owned future per work item, in the same order.

        Raises:
            TypeError: A work item is not callable.
            RuntimeError: Explicit global shutdown is still draining accepted work.
        """
        captured = tuple(tasks)
        if not all(callable(task) for task in captured):
            raise TypeError("Every work item must be callable.")
        if not captured:
            return []
        with self._executor_lock:
            if self._admission_closed or self._retiring_executor is not None:
                raise RuntimeError("Work pool is shutting down; retry after shutdown completes.")
            if self._thread_executor is None:
                self._thread_executor = ThreadPoolExecutor(
                    max_workers=self._num_workers,
                    thread_name_prefix="ring5-work",
                    initializer=self._mark_worker,
                )
            return [self._thread_executor.submit(task) for task in captured]

    def _mark_worker(self) -> None:
        """Identify owned worker threads without inspecting executor internals."""
        self._worker_context.active = True

    def _check_shutdown_thread(self) -> None:
        """Reject self-join before acquiring locks another caller may hold while draining."""
        if getattr(self._worker_context, "active", False):
            raise RuntimeError("Work pool workers cannot wait for their own shutdown.")

    @contextmanager
    def shutdown_scope(self) -> Iterator[None]:
        # [impl->req~ring5.api.process-lifecycle~1]
        """Drain work and keep admission closed while dependencies are released.

        Global shutdowns serialize independently of the submission lock. Failed
        draining or dependency cleanup leaves admission closed until a successful
        global retry. Ordinary session cleanup does not enter this scope.

        Raises:
            RuntimeError: An owned worker attempts to wait for its own shutdown.
        """
        self._check_shutdown_thread()
        with self._global_shutdown_lock:
            with self._executor_lock:
                self._admission_closed = True
            self.shutdown(wait=True)
            yield
            with self._executor_lock:
                self._admission_closed = False

    def shutdown(self, wait: bool = False) -> None:
        # [impl->req~ring5.api.process-lifecycle~1]
        """Drain accepted work and release the current executor.

        New submissions fail while shutdown drains. After retirement completes,
        submission creates a fresh bounded executor. Session cancellation uses
        owned futures and does not shut this shared pool down.

        Args:
            wait: Wait for accepted work and executor threads to finish.

        Raises:
            RuntimeError: An owned worker tries to wait for its own shutdown.
        """
        if wait:
            self._check_shutdown_thread()
        starts_retirement = False
        with self._executor_lock:
            if self._thread_executor is not None:
                self._retiring_executor = self._thread_executor
                self._thread_executor = None
                starts_retirement = True
            retiring = self._retiring_executor
        if retiring is not None:
            if wait:
                self._drain_executor(retiring)
            elif starts_retirement:
                threading.Thread(
                    target=self._drain_executor,
                    args=(retiring,),
                    name="ring5-work-retirement",
                    daemon=True,
                ).start()

    def _drain_executor(self, executor: ThreadPoolExecutor) -> None:
        """Join a retiring executor outside the submission lock."""
        executor.shutdown(wait=True)
        with self._executor_lock:
            if self._retiring_executor is executor:
                self._retiring_executor = None
        logger.info("WorkPool executor shut down")


def _shutdown_workpool() -> None:
    """Shutdown the global WorkPool singleton at interpreter exit."""
    if WorkPool._instance is not None:
        WorkPool._instance.shutdown(wait=True)
        WorkPool._instance = None


atexit.register(_shutdown_workpool)
