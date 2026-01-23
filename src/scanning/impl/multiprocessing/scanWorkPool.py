from typing import Any, List

from tqdm import tqdm

from src.core.multiprocessing.pool import WorkPool
from src.scanning.impl.multiprocessing.scanWork import ScanWork


class ScanWorkPool:
    """
    Facade for scanning work pool.
    Delegates to the unified WorkPool manager.
    """

    _singleton = None

    @classmethod
    def getInstance(cls):
        if cls._singleton is None:
            cls._singleton = ScanWorkPool()
        return cls._singleton

    def __init__(self) -> None:
        self._workPool = WorkPool.get_instance()
        self._futures = []

    def addWork(self, work: ScanWork) -> None:
        """Add work to the pool."""
        if work is not None:
            future = self._workPool.submit(work)
            self._futures.append(future)

    def getResults(self) -> List[Any]:
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
