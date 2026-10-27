"""Linux process lock ownership, resource cleanup and path confinement."""

from __future__ import annotations

import errno
import gc
import subprocess
import sys
import weakref
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, RLock
from unittest.mock import Mock

import pytest

from src.core.common import file_lock as module
from src.core.common.file_lock import AdvisoryFileLock, file_lock
from src.core.common.utils import validate_path_within
from src.core.services.data_services import path_service
from src.core.services.data_services.path_service import PathService


def test_lock_excludes_other_process_until_release_even_after_exception(tmp_path: Path) -> None:
    path = tmp_path / "transaction.lock"
    code = (
        "from pathlib import Path\n"
        "from src.core.common.file_lock import AdvisoryFileLock\n"
        "import sys\n"
        "lock=AdvisoryFileLock(Path(sys.argv[1]))\n"
        "try: lock.acquire(blocking=False)\n"
        "except BlockingIOError: sys.exit(7)\n"
        "lock.release()\n"
    )

    def competing() -> int:
        return subprocess.run([sys.executable, "-c", code, str(path)], check=False).returncode

    with pytest.raises(ValueError, match="rollback"):
        with file_lock(path):
            with file_lock(path):
                assert competing() == 7
            raise ValueError("rollback")
    assert competing() == 0


def test_lock_failed_acquisition_keeps_current_owner_alive(tmp_path: Path) -> None:
    path = tmp_path / "owned.lock"
    owner, contender = AdvisoryFileLock(path), AdvisoryFileLock(path)
    owner.acquire()
    try:
        with pytest.raises(BlockingIOError):
            contender.acquire(blocking=False)
        assert contender._handle is None
        with pytest.raises(RuntimeError, match="already acquired"):
            owner.acquire()
    finally:
        owner.release()
        owner.release()
    contender.acquire(blocking=False)
    contender.release()


def test_idle_lock_registry_reclaims_paths_without_splitting_waiters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    waiter_ready, acquired, release_waiter = Event(), Event(), Event()
    identities: list[int] = []

    class ObservedRegistry(weakref.WeakValueDictionary[str, RLock]):
        def setdefault(self, key: str, default: RLock) -> RLock:
            value = super().setdefault(key, default)
            identities.append(id(value))
            if len(identities) == 2:
                waiter_ready.set()
            return value

    registry = ObservedRegistry()
    monkeypatch.setattr(module, "_locks", registry)
    path = tmp_path / "transaction.lock"

    def wait_for_lock() -> None:
        with file_lock(path):
            acquired.set()
            assert release_waiter.wait(5)

    with ThreadPoolExecutor(max_workers=1) as executor:
        with file_lock(path):
            lock_ref = weakref.ref(registry[str(path.resolve())])
            future = executor.submit(wait_for_lock)
            assert waiter_ready.wait(5)
            assert not acquired.is_set()
        try:
            assert acquired.wait(5)
            assert lock_ref() is not None
            assert identities[0] == identities[1]
        finally:
            release_waiter.set()
        future.result(timeout=5)
    gc.collect()
    assert lock_ref() is None
    for index in range(100):
        with file_lock(tmp_path / f"idle-{index}.lock"):
            assert len(registry) == 1
    assert len(registry) == 0


@pytest.mark.parametrize(
    "error", [BlockingIOError(errno.EAGAIN, "busy"), OSError(errno.EIO, "device")]
)
def test_failed_kernel_acquisition_closes_descriptor_and_preserves_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: OSError
) -> None:
    path = tmp_path / "failed.lock"
    lock = AdvisoryFileLock(path)
    with path.open("a+b") as handle:
        descriptor = handle.fileno()
        monkeypatch.setattr(Path, "open", Mock(return_value=handle))
        flock = Mock(side_effect=error)
        monkeypatch.setattr(module.fcntl, "flock", flock)
        with pytest.raises(type(error)) as caught:
            lock.acquire(blocking=False)
        assert caught.value is error
        assert lock._handle is None
        assert handle.closed
        flock.assert_called_once_with(descriptor, module.fcntl.LOCK_EX | module.fcntl.LOCK_NB)


def test_failed_kernel_unlock_closes_descriptor_and_releases_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "release.lock"
    lock = AdvisoryFileLock(path)
    lock.acquire()
    handle = lock._handle
    assert handle is not None
    error = OSError(errno.EIO, "unlock")
    try:
        with monkeypatch.context() as patch:
            patch.setattr(module.fcntl, "flock", Mock(side_effect=error))
            with pytest.raises(OSError) as caught:
                lock.release()
            assert caught.value is error
            assert lock._handle is None
            assert handle.closed
            lock.release()
        contender = AdvisoryFileLock(path)
        contender.acquire(blocking=False)
        contender.release()
    finally:
        lock.release()


def test_path_confinement_resolves_symlinks(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    (allowed / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="Path traversal"):
        validate_path_within(allowed / "link" / "future.json", allowed)
    assert validate_path_within(allowed / "future.json", allowed) == allowed / "future.json"


def test_installed_package_uses_platform_user_data_and_override_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed = (
        tmp_path
        / "site-packages"
        / "src"
        / "core"
        / "services"
        / "data_services"
        / "path_service.py"
    )
    installed.parent.mkdir(parents=True)
    installed.touch()
    user_data = tmp_path / "platform-user-data"
    monkeypatch.setattr(path_service, "__file__", str(installed))
    provider = Mock(return_value=user_data)
    monkeypatch.setattr(path_service, "user_data_path", provider)
    monkeypatch.delenv("RING5_DATA_DIR", raising=False)
    PathService.reset_caches()
    try:
        assert PathService.get_data_dir() == user_data
        provider.assert_called_once_with("ring5", appauthor=False)
        assert user_data.is_dir()
        assert not (tmp_path / "site-packages" / ".ring5").exists()
        override = tmp_path / "explicit"
        monkeypatch.setenv("RING5_DATA_DIR", str(override))
        PathService.reset_caches()
        assert PathService.get_data_dir() == override
    finally:
        PathService.reset_caches()
