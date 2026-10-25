"""Portable advisory file locks for cooperating local transactions."""

from __future__ import annotations

import errno
import os
import threading
import weakref
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from importlib import import_module
from typing import BinaryIO, Protocol, cast

_WINDOWS = os.name == "nt"
_registry_lock = threading.Lock()
_locks: weakref.WeakValueDictionary[str, threading.RLock] = weakref.WeakValueDictionary()
_local = threading.local()


class _WindowsLocking(Protocol):
    LK_LOCK: int
    LK_NBLCK: int
    LK_UNLCK: int

    def locking(self, descriptor: int, mode: int, length: int) -> None:
        """Lock or unlock a byte range using the Windows runtime."""
        raise NotImplementedError


def _windows_adapter() -> _WindowsLocking:
    return cast(_WindowsLocking, import_module("msvcrt"))


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
            if _WINDOWS:
                msvcrt = _windows_adapter()

                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
                try:
                    msvcrt.locking(handle.fileno(), mode, 1)
                except OSError as exc:
                    if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        raise BlockingIOError(exc.errno, "File lock is held.") from exc
                    raise
            else:
                import fcntl

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
            if _WINDOWS:
                msvcrt = _windows_adapter()

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    """Hold a reentrant thread and process lock for one local transaction."""
    identity = os.path.normcase(str(path.resolve()))
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
