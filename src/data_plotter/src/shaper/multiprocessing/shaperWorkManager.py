import src.utils.utils as utils
import os
from tqdm import tqdm
from src.shaper.multiprocessing.shaperWorker import shaperWorker as shaperWorker
from shaperWork import ShaperWork as ShaperWork
from concurrent.futures import ThreadPoolExecutor

class ShaperWorkManager:
    """
    Manages the execution of shapers with dependencies.
    Here we require a manager to solve the dependencies and
    will use futures to execute the shapers and get notified
    whenever a work is finished
    """
    _workers = None
    _dependencies : dict
    _executingWorks : dict
    _completedWorks : dict
    _currentFutures : list
    _json : dict
    _numCores : int
    _isFinished : bool
    _pbar : tqdm

    @property
    def completedWorks(self) -> dict:
        return self._completedWorks
    
    @property
    def isFinished(self) -> bool:
        return self._isFinished

    def __init__(self, json : dict, csvPath : str, plot_shapers_ids: set):
        numCores = os.cpu_count()
        if numCores is None:
            # OS library failed! We will use 1 core!
            numCores = 1
        self._numCores = numCores
        # Works dictionary {work_id: {json, after:[work_id,...]}}
        # We must check that there is no circular dependency
        self._json = json
        self._dependencies = {}  # {work_id : work}
        self._executingWorks = {}  # {work_id : work}
        self._completedWorks = {}  # {work_id : csv_path}
        self._currentFutures = []  # [futures]
        # Add the initial non-dependent works to the queue
        for work_id, workInfo in self._json.items():
            work = ShaperWork(work_id, workInfo)
            if not utils.checkElementExistNoException(workInfo, 'after'):
                # No dependencies, so this work can be added to the queue
                # We can set srcCsvs and dstCsv here!
                work.srcCsv = [csvPath]
                work.dstCsv = utils.createTmpFile()
                self._executingWorks[work_id] = work
            else:
                deps = utils.getElementValue(workInfo, 'after')
                if isinstance(deps, str):
                    deps = [deps]
                if not isinstance(deps, list):
                    raise ValueError(f"Work {work_id} has an after dependency that is not a list.")
                # Check if there is any cyclic dependency
                if self._checkCyclicDependencies(work_id, deps):
                    raise ValueError(f"Work {work_id} has a cyclic dependency.")
                # Add it to dependency tracking
                work.deps = deps
                self._dependencies[work_id] = work
                # We cannot know which is the tmp file yet!
                # We could but this way is safer  :)
        # Filter all queues
        self._filterQueues(plot_shapers_ids)
        self._startThreadPool()

    def _getDependencyList(self, id: str) -> list:
        # Get the list of dependencies for a work
        if id in self._executingWorks:
            return []
        elif id in self._dependencies:
            work : ShaperWork = self._dependencies[id]
            deps = work.deps
            if len(deps) == 0:
                raise ValueError(f"Dependent work {id} has no dependencies.")
            for dep in deps:
                childDeps = self._getDependencyList(dep)
                if len(childDeps) > 0:
                    deps.extend(childDeps)
            return deps
        else:
            raise ValueError(f"Work {id} is not a dependency or an executing work.")

    def _filterQueues(self, used_ids: set):
        # Filter the queues to remove those unused ids
        realUsedWorks: set = set()
        for work_id in used_ids:
            realUsedWorks.add(work_id)
            deps = self._getDependencyList(work_id)
            for dep in deps:
                realUsedWorks.add(dep)
        for work_id in self._dependencies.keys():
            if work_id not in realUsedWorks:
                self._dependencies.pop(work_id)
        for work_id in self._executingWorks.keys():
            if work_id not in realUsedWorks:
                self._executingWorks.pop(work_id)
        # Queues should be purged at this point
        

    def _checkCyclicDependencies(self, work_id: str, dependencies: list) -> bool:
        # Check recursively if there is any cyclic dependency
        # This is a helper function for the constructor
        for dependency in dependencies:
            # Check if the dependency exists in the json
            if dependency not in self._json.keys():
                raise ValueError(f"Work {work_id} has an after dependency that does not exist: {dependency}.")
            if dependency in self._dependencies.keys():
                # Get the remote dependency list
                remoteDep : ShaperWork = self._dependencies[dependency]
                remoteDepList = remoteDep.deps
                if work_id in remoteDepList:
                    return True
                else:
                    return self._checkCyclicDependencies(work_id, remoteDepList)
        return False

    def _startThreadPool(self):
        # Check if the thread pool is already running
        if self._workers is None:
            self._workers = ThreadPoolExecutor(max_workers=self._numCores)
        else:
            raise Exception("Error: Thread pool is already running!")

    def _checkDependantsToSubmit(self, work_id: str):
        # Check if there are any dependants that now fulfill their dependecies
        # and submit them to the thread pool
        dependant : ShaperWork
        for depwork_id, dependant in self._dependencies:
            for dependency in dependant.deps:
                if dependency == work_id:
                    # Remove the dependency from the dependant
                    dependant.deps.remove(work_id)
                    # Get the csv from the completed works
                    # Forward the csv to the dependant
                    dependant.srcCsv.append(self._completedWorks[work_id])
                    # Check if the dependant has no more dependencies
                    if len(dependant.deps) == 0:
                        # Create a tmp csv file for the dependant
                        dependant.dstCsv = utils.createTmpFile()
                        # Add the dependant to the executing dict
                        self._executingWorks[depwork_id] = dependant
                        # Submit the dependant to the thread pool
                        self._submitWork(depwork_id, dependant)

    def _handleWorkFinish(self, work_id: str, future):
        # Get the result of the future
        # if false, raise an exception, something went wrong
        if not future.result():
            raise Exception(f"Error: Work {work_id} failed!")
        # Remove the work from the executing dict
        work : ShaperWork = self._executingWorks.pop(work_id)
        if work is None:
            raise Exception(f"Error: Work {work_id} not found in executing dict!")
        # Update the progress bar
        self._pbar.update(1)
        # Add the work to the completed dict
        self._completedWorks[work_id] = work.dstCsv
        # Check for dependants that now fulfill all their dependencies
        self._checkDependantsToSubmit(work_id)
        if self._workers is not None and len(self._executingWorks) == 0:
            self._workers.shutdown()
            self._isFinished = True
        # All work is done, 
    
    def _submitWork(self, work_id: str, work: ShaperWork):
        if self._workers is None:
            raise Exception("Error: Thread pool is not running!")
        future = self._workers.submit(shaperWorker.executeWork, work)
        future.add_done_callback(lambda f, work_id=work_id: self._handleWorkFinish(work_id, f))

    def __call__(self):
        # Submit all works that have no dependencies
        for work_id, work in self._executingWorks:
            if len(work.deps) != 0:
                raise Exception(f"Error: Work {work_id} has dependencies!")
            self._submitWork(work_id, work)
        self._pbar = tqdm(total=len(self._json.items()), desc="Shaping data")
        # Works will do the callback with handleWorkFinish
        self._isFinished = False

    def __del__(self):
        print("ShaperWorkManager cleaning...")
        for workCsv in self._completedWorks.values():
            print(f"Removing {workCsv}")
            if os.path.exists(workCsv):
                os.remove(workCsv)
        print("ShaperWorkManager cleaned!")