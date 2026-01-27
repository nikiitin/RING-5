"""
Work Pool Facades for Scanning and Parsing Operations.

Provides singleton facades for submitting async work to the unified WorkPool.
Follows the Facade Pattern to simplify async job submission and tracking.
"""

import logging
from concurrent.futures import Future
from typing import Any, List, Optional, TypeVar

from src.core.multiprocessing.pool import WorkPool
from src.parsers.workers.parse_work import ParseWork
from src.parsers.workers.scan_work import ScanWork

logger: logging.Logger = logging.getLogger(__name__)

# Type variable for generic Future results
T = TypeVar("T")


class ScanWorkPool:
    """
    Facade for scanning work pool.

    Delegates to the unified WorkPool manager.
    Simple submission wrapper that returns Futures for external tracking.

    Usage:
        pool = ScanWorkPool.get_instance()
        futures = pool.submit_batch_async(work_items)
        results = [f.result() for f in futures]
    """

    _singleton: Optional["ScanWorkPool"] = None

    @classmethod
    def get_instance(cls) -> "ScanWorkPool":
        """
        Get the singleton instance of ScanWorkPool.

        Returns:
            The singleton ScanWorkPool instance
        """
        if cls._singleton is None:
            cls._singleton = ScanWorkPool()
        return cls._singleton

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (primarily for testing)."""
        cls._singleton = None

    def __init__(self) -> None:
        """Initialize the scan work pool with WorkPool backend."""
        self._workPool: WorkPool = WorkPool.get_instance()
        self._futures: List[Future[Any]] = []

    def submit_batch_async(
        self, works: List[ScanWork], chunk_size: Optional[int] = None
    ) -> List[Future[Any]]:
        """
        Submit a batch of scan works with optimized chunking.

        Args:
            works: List of ScanWork instances to execute in parallel
            chunk_size: Optional chunk size for batching (auto-calculated if None)

        Returns:
            List of Future objects for tracking execution status
        """
        if not works:
            return []

        # Auto-calculate optimal chunk size
        # Use default of 4 workers if we can't determine pool size
        if chunk_size is None:
            chunk_size = max(1, len(works) // 8)  # Conservative default

        current_batch_futures: List[Future[Any]] = []

        # Submit in optimized chunks to reduce overhead
        for i in range(0, len(works), chunk_size):
            chunk = works[i:i + chunk_size]
            for work in chunk:
                if work is not None:
                    future: Future[Any] = self._workPool.submit(work)
                    self._futures.append(future)
                    current_batch_futures.append(future)

        return current_batch_futures

    def add_work(self, work: ScanWork) -> None:
        """
        Add a single scan work unit to the pool.

        Args:
            work: ScanWork instance to execute
        """
        if work is not None:
            future: Future[Any] = self._workPool.submit(work)
            self._futures.append(future)

    def get_all_futures(self) -> List[Future[Any]]:
        """
        Get all tracked futures from submitted work.

        Returns:
            List of all Future objects tracked by this pool
        """
        return self._futures

    def cancel_all(self) -> None:
        """
        Cancel all pending futures in the pool.

        This attempts to cancel all submitted work that hasn't started yet.
        """
        for f in self._futures:
            f.cancel()


class ParseWorkPool:
    """
    Facade for parsing work pool.

    Delegates to the unified WorkPool manager.
    Simple submission wrapper that returns Futures for external tracking.

    Usage:
        pool = ParseWorkPool.get_instance()
        futures = pool.submit_batch_async(work_items)
        results = [f.result() for f in futures]
    """

    _instance: Optional["ParseWorkPool"] = None

    @classmethod
    def get_instance(cls) -> "ParseWorkPool":
        """
        Get the singleton instance of ParseWorkPool.

        Returns:
            The singleton ParseWorkPool instance
        """
        if cls._instance is None:
            cls._instance = ParseWorkPool()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance.

        Used primarily for testing to clear the singleton state.
        """
        cls._instance = None

    def __init__(self) -> None:
        """Initialize the parse work pool with WorkPool backend."""
        self._work_pool: WorkPool = WorkPool.get_instance()
        self._futures: List[Future[Any]] = []

    def start_pool(self) -> None:
        """Ensure the underlying pool is ready (no-op for compatibility)."""
        pass

    def submit_batch_async(self, works: List[ParseWork]) -> List[Future[Any]]:
        """
        Submit a batch of parsing works with optimized chunking.

        Args:
            works: List of ParseWork instances to execute in parallel

        Returns:
            List of Future objects for tracking execution status
        """
        if not works:
            return []

        # Auto-calculate optimal chunk size
        # Use conservative default to avoid overhead
        chunk_size = max(1, len(works) // 8)

        current_batch_futures: List[Future[Any]] = []

        # Submit in optimized chunks to reduce overhead
        for i in range(0, len(works), chunk_size):
            chunk = works[i:i + chunk_size]
            for work in chunk:
                if work is not None:
                    future: Future[Any] = self._work_pool.submit(work)
                    self._futures.append(future)
                    current_batch_futures.append(future)

        return current_batch_futures

    def add_work(self, work: ParseWork) -> None:
        """
        Add a single parsing task to the pool.

        Args:
            work: ParseWork instance to execute
        """
        if work is not None:
            future: Future[Any] = self._work_pool.submit(work)
            self._futures.append(future)

    def get_all_futures(self) -> List[Future[Any]]:
        """
        Get all tracked futures from submitted work.

        Returns:
            List of all Future objects tracked by this pool
        """
        return self._futures

    def cancel_all(self) -> None:
        """
        Cancel all pending futures in the pool.

        This attempts to cancel all submitted work that hasn't started yet.
        """
        for f in self._futures:
            f.cancel()
