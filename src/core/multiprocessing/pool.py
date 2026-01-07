import os
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, Future
from typing import List, Optional, Union, Callable
from .job import Job

class WorkPool:
    """
    Unified singleton pool manager for parallel task execution.
    Supports both ProcessPool (for CPU-bound tasks) and ThreadPool (for IO-bound tasks).
    """
    _instance: Optional['WorkPool'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WorkPool, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._num_workers = os.cpu_count() or 1
        self._process_executor: Optional[ProcessPoolExecutor] = None
        self._thread_executor: Optional[ThreadPoolExecutor] = None
        
        # Use spawn context for processes to avoid fork warnings
        try:
            self._mp_context = multiprocessing.get_context("spawn")
        except ValueError:
            self._mp_context = None
            
        self._initialized = True

    @classmethod
    def get_instance(cls) -> 'WorkPool':
        return cls()

    def _get_process_executor(self) -> ProcessPoolExecutor:
        if self._process_executor is None:
            self._process_executor = ProcessPoolExecutor(
                max_workers=max(1, self._num_workers - 1),
                mp_context=self._mp_context
            )
        return self._process_executor

    def _get_thread_executor(self) -> ThreadPoolExecutor:
        if self._thread_executor is None:
            self._thread_executor = ThreadPoolExecutor(
                max_workers=self._num_workers * 2
            )
        return self._thread_executor

    def submit(self, task: Union[Job, Callable], use_threads: bool = False) -> Future:
        """Submit a single task to the pool."""
        executor = self._get_thread_executor() if use_threads else self._get_process_executor()
        return executor.submit(task)

    def map(self, tasks: List[Union[Job, Callable]], use_threads: bool = False):
        """Map a list of tasks to the pool."""
        executor = self._get_thread_executor() if use_threads else self._get_process_executor()
        return list(executor.map(tasks))

    def shutdown(self, wait: bool = True):
        """Shutdown the executors."""
        if self._process_executor:
            self._process_executor.shutdown(wait=wait)
            self._process_executor = None
        if self._thread_executor:
            self._thread_executor.shutdown(wait=wait)
            self._thread_executor = None

    def reset(self):
        """Force reset the executors."""
        self.shutdown(wait=False)
