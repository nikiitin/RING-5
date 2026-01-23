from tqdm import tqdm

from src.core.multiprocessing.pool import WorkPool
from src.parsing.impl.multiprocessing.parseWork import ParseWork


class ParseWorkPool:
    """
    Facade for parsing work pool, now using the unified WorkPool manager.
    Maintains the existing API for compatibility.
    """

    _singleton = None

    @classmethod
    def getInstance(cls):
        if cls._singleton is None:
            cls._singleton = ParseWorkPool()
        return cls._singleton

    @classmethod
    def reset(cls):
        """Reset the singleton instance to force fresh state."""
        cls._singleton = None

    def __init__(self) -> None:
        self._workPool = WorkPool.get_instance()
        self._futures = []

    def addWork(self, work: ParseWork) -> None:
        """Add work to the pool."""
        if work is not None:
            future = self._workPool.submit(work)
            self._futures.append(future)

    def startPool(self) -> None:
        """
        No-op for compatibility.
        The unified WorkPool handles its own lifecycle.
        Clears previous futures for a fresh start.
        """
        self._futures = []
        print("ParseWorkPool (Unified) ready!")

    def getResults(self) -> list:
        """
        Wait for all submitted work to finish and collect results.
        """
        results = []
        print(f"Collecting results from {len(self._futures)} parsing jobs...")

        for future in tqdm(self._futures, desc="Parsing progress"):
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as e:
                print(f"Error in parsing job: {e}")
                import traceback

                traceback.print_exc()

        # Clear futures for next batch
        self._futures = []
        return results
