import multiprocessing
import os

# External dependency
from tqdm import tqdm

from src.data_plotter.multiprocessing.plotWork import PlotWork
from src.data_plotter.multiprocessing.plotWorker import PlotWorker


class PlotWorkPool:
    _singleton = None
    _workers = None
    _workQueue = None
    _resultQueue = None
    _nWorks = 0

    @classmethod
    def getInstance(cls):
        if cls._singleton is None:
            cls._singleton = PlotWorkPool()
        return cls._singleton

    def __init__(self) -> None:
        # Get the number of cores available
        self._numCores = os.cpu_count()

    def _createWorker(self, workQueue, resultQueue):
        # Create a worker
        worker = PlotWorker(workQueue, resultQueue)
        return worker

    def addWork(self, work: PlotWork) -> None:
        # Add the work to the queue
        if work is None:
            self._nWorks += 0
        else:
            self._nWorks += 1
        self._workQueue.put(work)

    def startPool(self) -> None:
        # Create/restart the pool
        self._nWorks = 0
        self._workers = []
        self._workQueue = multiprocessing.JoinableQueue()
        self._resultQueue = multiprocessing.Queue()
        for i in range(self._numCores - 1):
            worker = self._createWorker(self._workQueue, self._resultQueue)
            worker.start()
            self._workers.append(worker)
        print("Plotter pool started!")

    def setFinishJob(self) -> None:
        # Put the finish work in the queue
        # This method MUST be called at some point
        # after startPool() method, otherwise all
        # processes will be blocked forever
        self.addWork(None)
        # Join the pool only if it was started
        if self._workers is not None:
            # Join the pool (wait for all processes to finish)
            self._workQueue.join()
        else:
            raise RuntimeError("Pool was not started!")
        # Get the results from the queue
        # Every worker can put more than one result
        print("Checking results...")
        errors = 0
        successes = 0
        for i in tqdm(range(self._nWorks)):
            try:
                r = self._resultQueue.get()
                if r == 0:
                    successes += 1
                elif r == 1:
                    errors += 1
                elif r is None:
                    continue
                else:
                    raise RuntimeError("Unknown error code!")
            except Exception:
                print("Error while getting results from queue!")
                raise
        # Return the results
        print(f"Errors: {errors}")
        print(f"Successes: {successes}")
