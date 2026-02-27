"""
Work Pool Facades for Scanning and Parsing Operations.

Provides singleton facades for submitting async work to the unified WorkPool.
Follows the Facade Pattern to simplify async job submission and tracking.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from concurrent.futures import Future

from src.core.models import ScannedVariable
from src.parsing.gem5.impl.pool.parse_work import ParsedVarsDict, ParseWork
from src.parsing.gem5.impl.pool.scan_work import ScanWork
from src.parsing.gem5.impl.pool.work_pool import WorkPool


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

    _singleton: ScanWorkPool | None = None
    _singleton_lock: threading.Lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> ScanWorkPool:
        """
        Get the singleton instance of ScanWorkPool.

        Returns:
            The singleton ScanWorkPool instance
        """
        with cls._singleton_lock:
            if cls._singleton is None:
                cls._singleton = ScanWorkPool()
            return cls._singleton

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (primarily for testing)."""
        with cls._singleton_lock:
            cls._singleton = None

    def __init__(self) -> None:
        """Initialize the scan work pool with WorkPool backend."""
        self._workPool: WorkPool = WorkPool.get_instance()
        self._futures: list[Future[list[ScannedVariable]]] = []

    def submit_batch_async(
        self, works: Sequence[ScanWork], chunk_size: int | None = None
    ) -> list[Future[list[ScannedVariable]]]:
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

        # Release references to completed futures from previous batches
        # to prevent unbounded memory growth in this singleton.
        self._futures.clear()

        # Auto-calculate optimal chunk size
        # Use default of 4 workers if we can't determine pool size
        if chunk_size is None:
            chunk_size = max(1, len(works) // 8)  # Conservative default

        current_batch_futures: list[Future[list[ScannedVariable]]] = []

        # Submit in optimized chunks to reduce overhead
        for i in range(0, len(works), chunk_size):
            chunk = works[i : i + chunk_size]
            for work in chunk:
                if work is not None:
                    future: Future[list[ScannedVariable]] = self._workPool.submit(
                        work, use_threads=True
                    )
                    self._futures.append(future)
                    current_batch_futures.append(future)

        return current_batch_futures

    def cancel_all(self) -> None:
        """
        Cancel all pending futures and release references.

        This attempts to cancel all submitted work that hasn't started yet,
        then clears the internal list to free memory.
        """
        for f in self._futures:
            f.cancel()
        self._futures.clear()


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

    _instance: ParseWorkPool | None = None
    _instance_lock: threading.Lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> ParseWorkPool:
        """
        Get the singleton instance of ParseWorkPool.

        Returns:
            The singleton ParseWorkPool instance
        """
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = ParseWorkPool()
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance.

        Used primarily for testing to clear the singleton state.
        """
        with cls._instance_lock:
            cls._instance = None

    def __init__(self) -> None:
        """Initialize the parse work pool with WorkPool backend."""
        self._work_pool: WorkPool = WorkPool.get_instance()
        self._futures: list[Future[ParsedVarsDict]] = []

    def submit_batch_async(self, works: Sequence[ParseWork]) -> list[Future[ParsedVarsDict]]:
        """
        Submit a batch of parsing works with optimized chunking.

        Args:
            works: List of ParseWork instances to execute in parallel

        Returns:
            List of Future objects for tracking execution status
        """
        if not works:
            return []

        # Release references to completed futures from previous batches
        # to prevent unbounded memory growth in this singleton.
        self._futures.clear()

        # Auto-calculate optimal chunk size
        # Use conservative default to avoid overhead
        chunk_size = max(1, len(works) // 8)

        current_batch_futures: list[Future[ParsedVarsDict]] = []

        # Submit in optimized chunks to reduce overhead
        for i in range(0, len(works), chunk_size):
            chunk = works[i : i + chunk_size]
            for work in chunk:
                if work is not None:
                    future: Future[ParsedVarsDict] = self._work_pool.submit(work, use_threads=True)
                    self._futures.append(future)
                    current_batch_futures.append(future)

        return current_batch_futures

    def cancel_all(self) -> None:
        """
        Cancel all pending futures and release references.

        This attempts to cancel all submitted work that hasn't started yet,
        then clears the internal list to free memory.
        """
        for f in self._futures:
            f.cancel()
        self._futures.clear()
