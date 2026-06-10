"""
Work Pool Facades for Scanning and Parsing Operations.

Provides singleton facades for submitting async work to the unified WorkPool.
Follows the Facade Pattern to simplify async job submission and tracking.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from concurrent.futures import Future

from src.core.models import ScanFileResult
from src.parsing.gem5.impl.pool.parse_work import ParsedVarsDict, ParseWork
from src.parsing.gem5.impl.pool.scan_work import ScanWork
from src.parsing.framework.work_pool import WorkPool


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

    def submit_batch_async(self, works: Sequence[ScanWork]) -> list[Future[ScanFileResult]]:
        """
        Submit a batch of scan works to the shared pool — one future per work.

        The returned futures are the caller's handles: the singleton keeps no
        reference to them (retaining the last batch here let one caller cancel
        another caller's in-flight work, and pinned its results in memory).
        Cancellation is per-handle: ``future.cancel()`` on the futures you own.

        Args:
            works: ScanWork instances to execute in parallel

        Returns:
            List of Future objects for tracking execution status
        """
        return [self._workPool.submit(w) for w in works if w is not None]


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

    def submit_batch_async(self, works: Sequence[ParseWork]) -> list[Future[ParsedVarsDict]]:
        """
        Submit a batch of parsing works to the shared pool — one future per work.

        The returned futures are the caller's handles: the singleton keeps no
        reference to them (retaining the last batch here let one caller cancel
        another caller's in-flight work, and pinned its results in memory).
        Cancellation is per-handle: ``future.cancel()`` on the futures you own.

        Args:
            works: ParseWork instances to execute in parallel

        Returns:
            List of Future objects for tracking execution status
        """
        return [self._work_pool.submit(w) for w in works if w is not None]
