"""Singleton pool for managing parallel parsing jobs."""

from typing import List

from tqdm import tqdm

from src.core.multiprocessing.pool import WorkPool
from src.parsing.workers.parse_work import ParseWork


class ParseWorkPool:
    """
    Singleton facade for parsing work pool.
    Uses the unified WorkPool manager for parallel execution.
    """

    _instance = None

    @classmethod
    def get_instance(cls) -> "ParseWorkPool":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = ParseWorkPool()
        return cls._instance

    # Backward compatibility alias
    @classmethod
    def getInstance(cls) -> "ParseWorkPool":
        return cls.get_instance()

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton for fresh state."""
        cls._instance = None

    def __init__(self) -> None:
        self._pool = WorkPool.get_instance()
        self._futures: List = []

    def add_work(self, work: ParseWork) -> None:
        """Submit work to the pool."""
        if work is not None:
            future = self._pool.submit(work)
            self._futures.append(future)

    # Backward compatibility alias
    def addWork(self, work: ParseWork) -> None:
        self.add_work(work)

    def start_pool(self) -> None:
        """Clear futures for a fresh batch (pool is always running)."""
        self._futures = []
        print("ParseWorkPool ready.")

    # Backward compatibility alias
    def startPool(self) -> None:
        self.start_pool()

    def get_results(self) -> List:
        """Wait for all jobs and collect results."""
        results = []
        print(f"Collecting {len(self._futures)} parsing results...")

        for future in tqdm(self._futures, desc="Parsing"):
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as e:
                print(f"Parsing error: {e}")

        self._futures = []
        return results

    # Backward compatibility alias
    def getResults(self) -> List:
        return self.get_results()
