import logging
from typing import Any, List

from src.core.multiprocessing.pool import WorkPool
from src.parsers.workers.scan_work import ScanWork

logger = logging.getLogger(__name__)


class ScanWorkPool:
    """
    Facade for scanning work pool.
    Delegates to the unified WorkPool manager.
    Simple submission wrapper that returns Futures for external tracking.
    """

    _singleton = None

    @classmethod
    def get_instance(cls):
        if cls._singleton is None:
            cls._singleton = ScanWorkPool()
        return cls._singleton

    def __init__(self) -> None:
        self._workPool = WorkPool.get_instance()
        self._futures = []

    def submit_batch_async(self, works: List[ScanWork]) -> List[Any]:
        """
        Submit a batch of scan works.
        Returns a list of Futures.
        """
        current_batch_futures = []
        for work in works:
            if work is not None:
                future = self._workPool.submit(work)
                self._futures.append(future)
                current_batch_futures.append(future)
        return current_batch_futures

    def add_work(self, work: ScanWork) -> None:
        """Add work to the pool."""
        if work is not None:
            future = self._workPool.submit(work)
            self._futures.append(future)

    def get_all_futures(self) -> List[Any]:
        """Get all tracked futures."""
        return self._futures

    def cancel_all(self) -> None:
        """Cancel all pending futures."""
        for f in self._futures:
            f.cancel()




class ParseWorkPool:
    """
    Facade for parsing work pool.
    Delegates to the unified WorkPool manager.
    Simple submission wrapper that returns Futures for external tracking.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = ParseWorkPool()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton instance."""
        cls._instance = None

    def __init__(self) -> None:
        self._work_pool = WorkPool.get_instance()
        self._futures = []

    def start_pool(self) -> None:
        """Ensure the underlying pool is ready."""
        pass

    def submit_batch_async(self, works: List[Any]) -> List[Any]:
        """
        Submit a batch of parsing works.
        Returns a list of Futures.
        """
        current_batch_futures = []
        for work in works:
            if work is not None:
                future = self._work_pool.submit(work)
                self._futures.append(future)
                current_batch_futures.append(future)
        return current_batch_futures

    def add_work(self, work: Any) -> None:
        """Add a parsing task to the pool."""
        if work is not None:
            future = self._work_pool.submit(work)
            self._futures.append(future)

    def get_all_futures(self) -> List[Any]:
        """Get all tracked futures."""
        return self._futures

    def cancel_all(self) -> None:
        """Cancel all pending futures."""
        for f in self._futures:
            f.cancel()
