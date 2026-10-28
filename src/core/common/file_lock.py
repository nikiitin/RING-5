"""Linux advisory file locks for cooperating local transactions."""

from __future__ import annotations

import fcntl
import threading
import weakref
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

_registry_lock = threading.Lock()
_locks: weakref.WeakValueDictionary[str, threading.RLock] = weakref.WeakValueDictionary()
_local = threading.local()


class AdvisoryFileLock:
    """Own one operating-system lock and its open file descriptor."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle: BinaryIO | None = None

    def acquire(self, *, blocking: bool = True) -> None:
        """Acquire an exclusive lock, raising BlockingIOError when unavailable."""
        if self._handle is not None:
            raise RuntimeError("File lock is already acquired.")
        handle = self.path.open("a+b")
        acquired = False
        try:
            flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), flags)
            acquired = True
        finally:
            if not acquired:
                handle.close()
        self._handle = handle

    def release(self) -> None:
        """Release an acquired lock and close its descriptor; safe to repeat."""
        handle, self._handle = self._handle, None
        if handle is None:
            return
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    """Hold a reentrant thread and process lock for one local transaction."""
    identity = str(path.resolve())
    with _registry_lock:
        # Active owners and waiters retain their lock; idle paths need no registry entry.
        lock = _locks.setdefault(identity, threading.RLock())
    with lock:
        held: set[str] = getattr(_local, "held", set())
        if identity in held:
            yield
            return
        advisory = AdvisoryFileLock(path)
        advisory.acquire()
        _local.held = {*held, identity}
        try:
            yield
        finally:
            _local.held = held
            advisory.release()
