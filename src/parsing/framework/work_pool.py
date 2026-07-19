"""
Work Pool — singleton thread-pool manager for parallel parse/scan work.

Backends dispatch their per-file work units (``Job``s) to this thread pool; the
heavy CPU work typically runs out-of-process in the backend's own workers, so a
thread pool (not a process pool) is the right executor here.
"""

from __future__ import annotations

import atexit
import logging
import os
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from src.parsing.framework.job import Job

logger = logging.getLogger(__name__)


class WorkPool:
    """Unified singleton thread-pool manager for parallel task execution."""

    _instance: WorkPool | None = None
    _initialized: bool
    _new_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> WorkPool:
        with cls._new_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        # Guard runs under the construction lock so two threads racing the very
        # first WorkPool() can never both run the init body.
        with self._new_lock:
            if self._initialized:
                return
            self._num_workers = os.cpu_count() or 1
            self._thread_executor: ThreadPoolExecutor | None = None
            self._executor_lock = threading.Lock()
            self._initialized = True

    @classmethod
    def get_instance(cls) -> WorkPool:
        """Return the process-wide work-pool instance."""
        return cls()

    def _get_thread_executor(self) -> ThreadPoolExecutor:
        # Locked lazy creation so concurrent first submits create exactly one
        # executor (the one shutdown() later releases), never a leaked extra.
        with self._executor_lock:
            if self._thread_executor is None:
                self._thread_executor = ThreadPoolExecutor(max_workers=self._num_workers * 2)
            return self._thread_executor

    def submit(self, task: Job | Callable[[], Any]) -> Future[Any]:
        # [impl->req~ring5.api.process-lifecycle~1]
        """Submit a single task to the thread pool."""
        return self._get_thread_executor().submit(task)

    def shutdown(self, wait: bool = False) -> None:
        # [impl->req~ring5.api.process-lifecycle~1]
        """Shutdown the executor and release resources."""
        # Lock the teardown symmetrically with the locked lazy creation in
        # _get_thread_executor, so a concurrent submit can't race the null-out.
        with self._executor_lock:
            if self._thread_executor is not None:
                self._thread_executor.shutdown(wait=wait)
                self._thread_executor = None
        logger.info("WorkPool executor shut down")


def _shutdown_workpool() -> None:
    """Shutdown the global WorkPool singleton at interpreter exit."""
    if WorkPool._instance is not None:
        WorkPool._instance.shutdown(wait=False)
        WorkPool._instance = None


atexit.register(_shutdown_workpool)
