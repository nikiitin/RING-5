from typing import Any, List

from tqdm import tqdm

from src.core.multiprocessing.pool import WorkPool
from src.parsers.workers.scan_work import ScanWork


class ScanWorkPool:
    """
    Facade for scanning work pool.
    Delegates to the unified WorkPool manager.
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

    def add_work(self, work: ScanWork) -> None:
        """Add work to the pool."""
        if work is not None:
            future = self._workPool.submit(work)
            self._futures.append(future)

    def get_results(self) -> List[Any]:
        """
        Wait for all submitted work to finish and collect results.
        """
        results = []
        # Update description based on type of work if possible, but generic is fine
        print(f"Collecting results from {len(self._futures)} scanning jobs...")

        for future in tqdm(self._futures, desc="Scanning progress"):
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as e:
                # Log error but don't crash
                print(f"Error in scanning job: {e}")

        # Clear futures for next batch
        self._futures = []
        return results


class ParseWorkPool:
    """
    Facade for parsing work pool.
    Delegates to the unified WorkPool manager.
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
        # WorkPool handles this automatically but method kept for interface compatibility
        pass

    def add_work(self, work: Any) -> None:
        """Add a parsing task to the pool."""
        if work is not None:
            future = self._work_pool.submit(work)
            self._futures.append(future)

    def get_results(self) -> List[Any]:
        """
        Wait for all submitted work to finish and collect results.
        """
        results = []
        if not self._futures:
            return results

        # tqdm usage for user feedback during long parsing operations
        for future in tqdm(self._futures, desc="Parsing progress"):
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as e:
                # Robust error handling: Log but continue
                print(f"Error in parsing job: {e}")

        # Clear futures for next batch
        self._futures = []
        return results
