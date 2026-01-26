import logging
import os
from typing import Dict, List, Optional, Set

from tqdm import tqdm

import src.utils.utils as utils
from src.core.multiprocessing.pool import WorkPool
from src.web.services.shapers.multiprocessing.shaperWork import ShaperWork

logger = logging.getLogger(__name__)


class ShaperWorkManager:
    """
    Manages the execution of shapers with dependencies using a unified WorkPool.
    Solves dependencies and uses futures to execute shapers as they become ready.
    """

    def __init__(self, json_config: dict, csv_path: str, plot_shaper_ids: Set[str]):
        self._work_pool = WorkPool.get_instance()
        self._json = json_config
        self._csv_path = csv_path

        self._dependencies: Dict[str, ShaperWork] = {}  # work_id : work (waiting for deps)
        self._executing_works: Dict[str, ShaperWork] = {}  # work_id : work (submitted to pool)
        self._completed_works: Dict[str, str] = {}  # work_id : dst_csv_path

        self._is_finished = False
        self._pbar: Optional[tqdm] = None

        # Build work objects and identify initial tasks
        for work_id, work_info in self._json.items():
            work = ShaperWork(work_id, work_info)
            deps = (
                utils.getElementValue(work_info, "after")
                if utils.checkElementExistNoException(work_info, "after")
                else []
            )
            if isinstance(deps, str):
                deps = [deps]

            if not deps:
                # No dependencies, ready to execute
                work.srcCsv = [csv_path]
                work.dstCsv = utils.createTmpFile()
                self._executing_works[work_id] = work
            else:
                # Check for cyclic dependencies
                if self._check_cyclic_dependencies(work_id, deps):
                    raise ValueError(f"Work {work_id} has a cyclic dependency.")
                work.deps = deps
                self._dependencies[work_id] = work

        # Filter to only keep works needed for the requested plots
        self._filter_queues(plot_shaper_ids)

    @property
    def completedWorks(self) -> Dict[str, str]:
        return self._completed_works

    @property
    def isFinished(self) -> bool:
        return self._is_finished

    def _get_dependency_list(self, work_id: str) -> List[str]:
        if work_id in self._executing_works:
            return []
        elif work_id in self._dependencies:
            work = self._dependencies[work_id]
            deps = list(work.deps)  # Copy
            all_deps = list(deps)
            for dep in deps:
                all_deps.extend(self._get_dependency_list(dep))
            return list(set(all_deps))
        else:
            raise ValueError(f"Work {work_id} is not tracked.")

    def _filter_queues(self, used_ids: Set[str]):
        real_used_works = set()
        for work_id in used_ids:
            if work_id in self._json:  # Ensure it exists in config
                real_used_works.add(work_id)
                real_used_works.update(self._get_dependency_list(work_id))

        # Purge dependencies
        self._dependencies = {k: v for k, v in self._dependencies.items() if k in real_used_works}
        # Purge executing
        self._executing_works = {
            k: v for k, v in self._executing_works.items() if k in real_used_works
        }

    def _check_cyclic_dependencies(self, work_id: str, dependencies: List[str]) -> bool:
        for dep in dependencies:
            if dep not in self._json:
                raise ValueError(f"Work {work_id} depends on non-existent work {dep}.")
            if dep in self._dependencies:
                if work_id in self._dependencies[dep].deps:
                    return True
                if self._check_cyclic_dependencies(work_id, self._dependencies[dep].deps):
                    return True
        return False

    def _submit_work(self, work_id: str, work: ShaperWork):
        # Use ThreadPool (use_threads=True) as shaping is typically IO/Mixed
        # and may interact with shared memory/objects more safely in threads
        future = self._work_pool.submit(work, use_threads=True)
        future.add_done_callback(lambda f: self._handle_work_finish(work_id, f))

    def _handle_work_finish(self, work_id: str, future):
        try:
            if not future.result():
                raise Exception(f"Work {work_id} returned failure status")
        except Exception as e:
            logger.error("Work %s failed: %s", work_id, e, exc_info=True)
            # We might want to handle failures more gracefully
            return

        work = self._executing_works.pop(work_id, None)
        if not work:
            return

        self._completed_works[work_id] = work.dstCsv
        if self._pbar:
            self._pbar.update(1)

        # Check for dependants that can now be submitted
        ready_to_submit = []
        for dep_id, dependant in list(self._dependencies.items()):
            if work_id in dependant.deps:
                dependant.deps.remove(work_id)
                dependant.srcCsv.append(self._completed_works[work_id])
                if not dependant.deps:
                    dependant.dstCsv = utils.createTmpFile()
                    self._executing_works[dep_id] = dependant
                    self._dependencies.pop(dep_id)
                    ready_to_submit.append((dep_id, dependant))

        for rid, rwork in ready_to_submit:
            self._submit_work(rid, rwork)

        if not self._executing_works and not self._dependencies:
            self._is_finished = True
            if self._pbar:
                self._pbar.close()

    def __call__(self):
        total_works = len(self._executing_works) + len(self._dependencies)
        if total_works == 0:
            self._is_finished = True
            return

        self._pbar = tqdm(total=total_works, desc="Shaping data")
        self._is_finished = False

        # Submit initial works
        initial_works = list(self._executing_works.items())
        for work_id, work in initial_works:
            self._submit_work(work_id, work)

    def __del__(self):
        # Cleanup temporary files
        import contextlib

        for csv_path in self._completed_works.values():
            if os.path.exists(csv_path):
                with contextlib.suppress(Exception):
                    os.remove(csv_path)
