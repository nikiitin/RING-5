"""Native cache expansion failures remain typed without touching browser state."""

from __future__ import annotations

import pwd
import subprocess
import sys
from pathlib import Path

import pytest

from ring5 import _chrome_install as chrome
from ring5.errors import Ring5Error
from tests.unit.test_chrome_install import _inert_layout, _install_fixture, _zip

pytestmark = pytest.mark.public_api
_MISSING_USER = "ring5_missing_user_7d3c58b46f0a"


@pytest.fixture
def unknown_user_cache() -> str:
    with pytest.raises(KeyError):
        pwd.getpwnam(_MISSING_USER)
    return f"~{_MISSING_USER}/cache"


def test_actual_unknown_user_console_is_typed_before_cache_creation(
    unknown_user_cache: str,
    tmp_path: Path,
) -> None:
    # [test->req~ring5.cli.install-chrome~2]
    result = subprocess.run(
        [sys.executable, "-m", "ring5.cli", "install-chrome", "--cache-dir", unknown_user_cache],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("error: Chrome installation failed:")
    assert "Could not expand Chrome cache directory" in result.stderr
    assert "Traceback" not in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_unknown_user_preserves_good_cache_and_does_not_start_transfer(
    unknown_user_cache: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, network = _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))
    executable = chrome.install_chrome(cache_directory=str(tmp_path / "good-cache"))
    assert executable.read_bytes() == b"inert browser fixture; never execute"
    marker = tmp_path / "unrelated"
    marker.write_bytes(b"preserve unrelated bytes")
    before = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    before_paths = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert len(before) >= 4
    network.reset_mock()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(Ring5Error, match="Could not expand Chrome cache directory") as error:
        chrome.install_chrome(cache_directory=unknown_user_cache)
    assert isinstance(error.value.__cause__, ValueError)
    assert isinstance(error.value.__cause__.__cause__, RuntimeError)
    network.assert_not_called()
    assert before == {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert before_paths == sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert marker.read_bytes() == b"preserve unrelated bytes"


def test_valid_current_home_expansion_uses_only_a_task_local_simulated_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, network = _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))
    home = tmp_path / "simulated-home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    assert Path("~").expanduser() == home == Path.home()
    executable = chrome.install_chrome(cache_directory="~/browser-cache")
    assert executable.is_relative_to(home / "browser-cache")
    assert executable.read_bytes() == b"inert browser fixture; never execute"
    assert network.call_count == 1
    assert sorted(p.name for p in home.iterdir()) == ["browser-cache"]
