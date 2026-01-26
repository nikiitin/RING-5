import logging
from typing import Any, List

from src.core.multiprocessing.pool import WorkPool
from src.parsers.workers.scan_work import ScanWork

logger = logging.getLogger(__name__)


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
        import threading
        self._workPool = WorkPool.get_instance()
        self._futures = []
        self._lock = threading.Lock()
        
        # Async State
        self._job_thread = None
        self._cancel_event = threading.Event()
        self._results = []
        self._progress = {"total": 0, "current": 0, "status": "idle", "errors": []}

    def submit_batch_async(self, works: List[ScanWork]) -> None:
        """
        Submit a batch of scan works to be processed in a background thread.
        Raises RuntimeError if a job is already running.
        """
        # 1. Check if busy
        if not self._lock.acquire(blocking=False):
             raise RuntimeError("Scanner is currently busy. Please wait.")
        
        try:
             # Double check thread is not alive (cleanup)
             if self._job_thread and self._job_thread.is_alive():
                  self._lock.release()
                  raise RuntimeError("Scanner thread is still running.")

             # 2. Reset State
             self._cancel_event.clear()
             self._futures = []
             self._results = []
             self._progress = {
                 "total": len(works),
                 "current": 0, 
                 "status": "running", 
                 "errors": []
             }

             # 3. Start Thread
             import threading
             self._job_thread = threading.Thread(
                 target=self._run_batch_worker,
                 args=(works,),
                 daemon=True
             )
             self._job_thread.start()
             
        except Exception as e:
            # If start fails, release lock
            if self._lock.locked():
                 self._lock.release()
            self._progress["status"] = "error"
            self._progress["errors"].append(str(e))
            raise e
        
        # Release lock to allow progress polling while worker runs.
        self._lock.release()

    def _run_batch_worker(self, works: List[ScanWork]):
        """Internal worker function running in thread."""
        from concurrent.futures import as_completed
        
        try:
             # Submit all work
             for work in works:
                 if self._cancel_event.is_set():
                     break
                 self.add_work(work)
            
             # Wait for results
             for future in as_completed(self._futures):
                 if self._cancel_event.is_set():
                     # Signal all remaining futures to cancel (best effort)
                     for f in self._futures:
                         f.cancel()
                     break
                 
                 try:
                     result = future.result()
                     if result:
                         self._results.append(result)
                 except Exception as e:
                     self._progress["errors"].append(str(e))
                 
                 self._progress["current"] += 1
            
             if self._cancel_event.is_set():
                 self._progress["status"] = "cancelled"
             else:
                 self._progress["status"] = "done"

        except Exception as e:
             logger.error(f"SCANNER: Async worker failed: {e}", exc_info=True)
             self._progress["status"] = "error"
             self._progress["errors"].append(str(e))
        finally:
             # Cleanup futures
             self._futures = []

    def cancel_current_job(self):
        """Signal the current job to cancel."""
        self._cancel_event.set()

    def get_status(self) -> dict:
        """Get the current progress status."""
        # Simple read, atomic enough for UI polling
        return self._progress.copy()

    def get_results_async_snapshot(self) -> List[Any]:
        """Get the results collected so far (or final results)."""
        return list(self._results)



    def add_work(self, work: ScanWork) -> None:
        """Add work to the pool."""
        if work is not None:
            future = self._workPool.submit(work)
            self._futures.append(future)




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
        from concurrent.futures import as_completed
        from tqdm import tqdm

        results = []
        if not self._futures:
            return results

        logger.info(f"PARSER: Collecting results from {len(self._futures)} parsing jobs...")

        with tqdm(total=len(self._futures), desc="Parsing") as pbar:
            for future in as_completed(self._futures):
                try:
                    pbar.update(1)
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    # Fail Fast, Fail Loud: Use logger.error with exc_info=True
                    logger.error(f"PARSER Error in parsing job: {e}", exc_info=True)

        # Clear futures for next batch
        self._futures = []
        return results
