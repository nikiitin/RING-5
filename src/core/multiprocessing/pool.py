"""
Work Pool - Unified Parallel Execution Manager.

Implements a singleton pattern for managing parallel task execution using
both process and thread pools. Provides a unified interface for spawning
CPU-bound and IO-bound work across multiple worker processes.

Features:
- Process pooling for heavy computation (parsing, analysis)
- Thread pooling for IO operations (file I/O, network)
- Dynamic worker scaling based on system CPU count
- Job queue management and result tracking
"""

import multiprocessing
import os
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing.context import SpawnContext
from typing import Any, Callable, List, Optional, Union

from .job import Job


class WorkPool:
    """
    Unified singleton pool manager for parallel task execution.
    Supports both ProcessPool (for CPU-bound tasks) and ThreadPool (for IO-bound tasks).
    """

    _instance: Optional["WorkPool"] = None
    _initialized: bool

    def __new__(cls) -> "WorkPool":
        if cls._instance is None:
            cls._instance = super(WorkPool, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._num_workers = os.cpu_count() or 1
        self._process_executor: Optional[ProcessPoolExecutor] = None
        self._thread_executor: Optional[ThreadPoolExecutor] = None

        # Use spawn context for processes to avoid fork warnings
        try:
            self._mp_context: Optional[SpawnContext] = multiprocessing.get_context("spawn")
        except ValueError:
            self._mp_context = None

        self._initialized = True

    @classmethod
    def get_instance(cls) -> "WorkPool":
        return cls()

    def _get_process_executor(self) -> ProcessPoolExecutor:
        if self._process_executor is None:
            self._process_executor = ProcessPoolExecutor(
                max_workers=max(1, self._num_workers - 1), mp_context=self._mp_context
            )
        return self._process_executor

    def _get_thread_executor(self) -> ThreadPoolExecutor:
        if self._thread_executor is None:
            self._thread_executor = ThreadPoolExecutor(max_workers=self._num_workers * 2)
        return self._thread_executor

    def submit(self, task: Union[Job, Callable[[], Any]], use_threads: bool = False) -> Future[Any]:
        """Submit a single task to the pool."""
        executor = self._get_thread_executor() if use_threads else self._get_process_executor()
        return executor.submit(task)

    def map(
        self, tasks: List[Union[Job, Callable[[], Any]]], use_threads: bool = False
    ) -> List[Any]:
        """Map a list of tasks to the pool."""
        executor = self._get_thread_executor() if use_threads else self._get_process_executor()
        # Execute each task individually since they may be different callables
        results = [executor.submit(task).result() for task in tasks]
        return results

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executors."""
        if self._process_executor:
            self._process_executor.shutdown(wait=wait)
            self._process_executor = None
        if self._thread_executor:
            self._thread_executor.shutdown(wait=wait)
            self._thread_executor = None

    def reset(self) -> None:
        """Force reset the executors."""
        self.shutdown(wait=False)
