"""Runtime and session workspace lifecycle for background parse jobs."""

from __future__ import annotations

import atexit
import fcntl
import logging
import shutil
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from src.core.services.data_services.path_service import PathService

logger = logging.getLogger(__name__)


class ParseJobRuntimeWorkspace:
    """Own the process-level job directory and its exclusive runtime lock."""

    _instance: ParseJobRuntimeWorkspace | None = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> ParseJobRuntimeWorkspace:
        """Return the process-wide runtime workspace."""
        with cls._instance_lock:
            if cls._instance is None or cls._instance.closed:
                jobs_root = PathService.get_data_dir() / "jobs"
                cls._instance = cls(jobs_root)
            return cls._instance

    @classmethod
    def reset_for_tests(cls) -> None:
        """Close and forget the singleton runtime workspace."""
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance.close()
            cls._instance = None

    def __init__(self, jobs_root: Path) -> None:
        """Create a locked runtime directory after removing stale runtimes."""
        self.jobs_root = jobs_root.resolve()
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._closed = False
        self._session_closers: dict[Path, Callable[[], None]] = {}
        startup_lock_path = self.jobs_root / ".startup.lock"
        with startup_lock_path.open("a+", encoding="utf-8") as startup_lock:
            fcntl.flock(startup_lock.fileno(), fcntl.LOCK_EX)
            try:
                self._cleanup_orphans()
                self.runtime_id = uuid.uuid4().hex
                self.runtime_dir = self.jobs_root / self.runtime_id
                self.runtime_dir.mkdir(mode=0o700)
                self.lock_path = self.runtime_dir / "runtime.lock"
                self._lock_file: TextIO = self.lock_path.open("a+", encoding="utf-8")
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._lock_file.write(f"{self.runtime_id}\n")
                self._lock_file.flush()
            finally:
                fcntl.flock(startup_lock.fileno(), fcntl.LOCK_UN)
        atexit.register(self.close)

    @property
    def closed(self) -> bool:
        """Return whether process workspace cleanup has completed."""
        with self._lock:
            return self._closed

    def create_session_workspace(self) -> Path:
        """Create and return an isolated session directory."""
        with self._lock:
            if self._closed:
                raise RuntimeError("Parse job runtime workspace is closed")
            session_dir = self.runtime_dir / uuid.uuid4().hex
            session_dir.mkdir(mode=0o700)
            return session_dir

    def release_session_workspace(self, session_dir: Path) -> None:
        """Delete one session workspace without affecting sibling sessions."""
        with self._lock:
            if session_dir.parent != self.runtime_dir:
                raise ValueError("Session workspace does not belong to this runtime")
            self._session_closers.pop(session_dir, None)
            shutil.rmtree(session_dir, ignore_errors=True)

    def register_session_closer(self, session_dir: Path, closer: Callable[[], None]) -> None:
        """Register graceful session cancellation for process shutdown."""
        with self._lock:
            if self._closed:
                raise RuntimeError("Parse job runtime workspace is closed")
            if session_dir.parent != self.runtime_dir:
                raise ValueError("Session workspace does not belong to this runtime")
            self._session_closers[session_dir] = closer

    def close(self) -> None:
        """Delete all transient runtime data and release the process lock."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            closers = list(self._session_closers.values())
        for closer in closers:
            try:
                closer()
            except Exception as exc:
                logger.warning("Unable to close parse-job session cleanly: %s", exc)
        with self._lock:
            self._session_closers.clear()
            try:
                shutil.rmtree(self.runtime_dir, ignore_errors=True)
            finally:
                try:
                    fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                finally:
                    self._lock_file.close()

    def _cleanup_orphans(self) -> None:
        """Remove only runtime directories whose lock is not held."""
        for candidate in self.jobs_root.iterdir():
            if not candidate.is_dir():
                continue
            lock_path = candidate / "runtime.lock"
            try:
                lock_file = lock_path.open("a+", encoding="utf-8")
            except OSError:
                logger.warning("Unable to inspect parse-job runtime %s", candidate)
                continue

            acquired = False
            try:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except BlockingIOError:
                    continue
                shutil.rmtree(candidate)
            except OSError as exc:
                logger.warning("Unable to remove stale parse-job runtime %s: %s", candidate, exc)
            finally:
                if acquired:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
