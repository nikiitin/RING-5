from multiprocessing.pool import Pool
import multiprocessing
import os
from src.data_parser.src.impl.multiprocessing.parseWork import ParseWork
from src.data_parser.src.impl.multiprocessing.parseWorker import ParseWorker
# External dependency
from tqdm import tqdm

class ParseWorkPool:
    _singleton = None
    _workers = None
    _workQueue = None
    _resultQueue = None
    _nWorks = 0

    @classmethod
    def getInstance(cls):
        if cls._singleton is None:
            cls._singleton = ParseWorkPool()
        return cls._singleton
    
    def __init__(self) -> None:
        # Get the number of cores available
        self._numCores = os.cpu_count()

    def _createWorker(self, workQueue, resultQueue):
        # Create a worker
        worker = ParseWorker(workQueue, resultQueue)
        return worker

    def addWork(self, work: ParseWork) -> None:
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
        print("Pool started!")

    def getResults(self) -> list:
        # Put the finish work in the queue
        self.addWork(None)
        # This method MUST be called at some point
        # after startPool() method, otherwise all
        # processes will be blocked forever
        # Join the pool only if it was started
        if not self._workers is None:
            # Join the pool (wait for all processes to finish)
            self._workQueue.join()
        else :
            raise RuntimeError("Pool was not started!")
        # Get the results from the queue
        results = []
        # Every worker can put more than one result
        print("Formatting results...")
        for i in tqdm(range(self._nWorks)):
            try:
                r = self._resultQueue.get()
                if r is None:
                    continue
                results.append(r)
            except Exception:
                print("Error while getting results from queue!")
                raise
        # Return the results
        return results

    

