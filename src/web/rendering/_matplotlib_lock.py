"""Serialize native Matplotlib work that shares process-global rendering state."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from threading import RLock
from typing import ParamSpec, TypeVar

# rc_context restores all rcParams, including settings changed by another thread.
# Figure construction must share the export lock so new artists cannot inherit
# temporary export settings. Nested connectors and report builds re-enter it.
MATPLOTLIB_LOCK = RLock()
_P = ParamSpec("_P")
_R = TypeVar("_R")


def serialized_matplotlib(operation: Callable[_P, _R]) -> Callable[_P, _R]:
    """Run one native rendering operation under the shared reentrant lock."""

    @wraps(operation)
    def guarded(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        with MATPLOTLIB_LOCK:
            return operation(*args, **kwargs)

    return guarded
