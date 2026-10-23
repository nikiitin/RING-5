"""Process lock ownership and the Windows standard-library adapter contract."""

from __future__ import annotations

import errno
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
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


def test_windows_adapter_locks_one_initialized_byte_and_releases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = SimpleNamespace(LK_LOCK=1, LK_NBLCK=2, LK_UNLCK=3, locking=Mock())
    monkeypatch.setattr(module, "_WINDOWS", True)
    monkeypatch.setitem(sys.modules, "msvcrt", adapter)
    path = tmp_path / "windows.lock"
    lock = AdvisoryFileLock(path)
    lock.acquire(blocking=False)
    handle = lock._handle
    assert path.read_bytes() == b"\0"
    assert adapter.locking.call_args.args[1:] == (2, 1)
    lock.release()
    assert handle.closed
    assert adapter.locking.call_args.args[1:] == (3, 1)
    adapter.locking.side_effect = OSError(errno.EACCES, "busy")
    with pytest.raises(BlockingIOError):
        lock.acquire(blocking=False)
    assert lock._handle is None
    adapter.locking.side_effect = OSError(errno.EIO, "device")
    with pytest.raises(OSError) as caught:
        lock.acquire(blocking=False)
    assert caught.value.errno == errno.EIO
    assert lock._handle is None


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
