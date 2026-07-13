"""
Work Pool Facades for Scanning and Parsing Operations.

Provides singleton facades for submitting async work to the unified WorkPool.
Follows the Facade Pattern to simplify async job submission and tracking.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from concurrent.futures import Future
from typing import Any, ClassVar, Generic, Self, TypeVar, cast

from src.core.models import ScanFileResult
from src.parsing.framework.job import Job
from src.parsing.framework.work_pool import WorkPool
from src.parsing.gem5.impl.pool.parse_work import ParsedVarsDict, ParseWork
from src.parsing.gem5.impl.pool.scan_work import ScanWork

_W = TypeVar("_W", bound=Job)  # work-item type
_R = TypeVar("_R")  # result type


class _BatchWorkPool(Generic[_W, _R]):
    """Singleton facade over the unified :class:`WorkPool` — submit a batch, get one
    future per work item.

    The returned futures are the caller's handles: the singleton keeps no reference to them
    (retaining the last batch let one caller cancel another caller's in-flight work and
    pinned its results in memory). Cancellation is per-handle: ``future.cancel()`` on the
    futures you own. Each concrete subclass keeps its OWN singleton (via ``cls.__dict__``).
    """

    _singleton: ClassVar["_BatchWorkPool[Any, Any] | None"] = None
    _singleton_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self._work_pool: WorkPool = WorkPool.get_instance()

    @classmethod
    def get_instance(cls) -> Self:
        """Get the per-subclass singleton instance."""
        with cls._singleton_lock:
            # __dict__ (not inherited): each subclass keeps its own instance, never the
            # base's — ScanWorkPool and ParseWorkPool are independent singletons.
            inst = cls.__dict__.get("_singleton")
            if inst is None:
                inst = cls()
                cls._singleton = inst
            return cast(Self, inst)

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (primarily for testing)."""
        with cls._singleton_lock:
            cls._singleton = None

    def submit_batch_async(self, works: Sequence[_W]) -> list[Future[_R]]:
        """Submit a batch to the shared pool — one future per (non-None) work item."""
        return [self._work_pool.submit(w) for w in works if w is not None]


class ScanWorkPool(_BatchWorkPool[ScanWork, ScanFileResult]):
    """Facade for the scanning work pool."""


class ParseWorkPool(_BatchWorkPool[ParseWork, ParsedVarsDict]):
    """Facade for the parsing work pool."""
