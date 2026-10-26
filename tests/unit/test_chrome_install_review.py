"""Inert regressions for the four independently reviewed installer boundaries."""

from __future__ import annotations

import ctypes
import errno
import io
import os
import stat
import struct
import subprocess
import sys
import threading
import zipfile
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ring5 import _chrome_install as chrome
from ring5 import cli
from ring5.errors import Ring5Error
from tests.unit.test_chrome_install import _inert_layout, _install_fixture, _zip

pytestmark = pytest.mark.public_api


def test_raw_parent_target_cannot_hide_native_escape_through_an_alias(
    tmp_path: Path,
) -> None:
    name = "mac-arm64"
    artifact = chrome._load_manifest()[name]
    root = "chrome-mac-arm64"
    entries = [
        (artifact.executable, b"inert executable", 0o100755),
        (f"{root}/dir/", b"", 0o40755),
        (f"{root}/outside", b"admitted fixture", 0o100644),
        (f"{root}/deep/deeper/alias", b"../../dir", 0o120755),
        (f"{root}/deep/deeper/link", b"alias/../../../outside", 0o120755),
    ]
    sentinel = tmp_path / "outside"
    sentinel.write_bytes(b"foreign sentinel")
    archive = tmp_path / "inert.zip"
    archive.write_bytes(_zip(entries))
    output = tmp_path / "installation"
    output.mkdir()
    with pytest.raises(ValueError, match="link target"):
        chrome._extract(archive, output, artifact)
    assert list(output.iterdir()) == []
    assert sentinel.read_bytes() == b"foreign sentinel"


@pytest.mark.parametrize("target", ["../dir", "alias/../file", "alias/../../../outside"])
def test_parent_components_are_rejected_before_normalization(target: str) -> None:
    with pytest.raises(ValueError, match="link target"):
        chrome._link_target(PurePosixPath("chrome-mac-arm64/deep/link"), target, "chrome-mac-arm64")


@pytest.mark.skipif(sys.platform != "linux", reason="Exercises the actual Linux exclusive syscall.")
@pytest.mark.parametrize(
    "kind", ["empty-directory", "nonempty-directory", "file", "symlink", "broken-symlink"]
)
def test_native_noreplace_preserves_every_existing_destination(
    kind: str,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "inert").write_bytes(b"staged fixture")
    destination = tmp_path / "destination"
    if kind in {"empty-directory", "nonempty-directory"}:
        destination.mkdir(mode=0o700)
        if kind == "nonempty-directory":
            (destination / "foreign").write_bytes(b"foreign bytes")
    elif kind == "file":
        destination.write_bytes(b"foreign bytes")
    else:
        target = tmp_path / "target"
        if kind == "symlink":
            target.mkdir()
            (target / "foreign").write_bytes(b"foreign bytes")
        destination.symlink_to(target, target_is_directory=True)
    before = destination.lstat()
    with pytest.raises(FileExistsError) as failure:
        chrome._publish_noreplace(source, destination)
    assert failure.value.errno == errno.EEXIST
    after = destination.lstat()
    assert (after.st_dev, after.st_ino, after.st_mode) == (
        before.st_dev,
        before.st_ino,
        before.st_mode,
    )
    assert (source / "inert").read_bytes() == b"staged fixture"
    if kind == "file":
        assert destination.read_bytes() == b"foreign bytes"
    elif kind in {"nonempty-directory", "symlink"}:
        assert (destination / "foreign").read_bytes() == b"foreign bytes"
    elif kind == "empty-directory":
        assert list(destination.iterdir()) == []
    else:
        assert destination.is_symlink() and not destination.exists()


@pytest.mark.skipif(sys.platform != "linux", reason="Exercises the actual Linux exclusive syscall.")
def test_native_noreplace_publishes_supported_inert_directory(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "inert").write_bytes(b"inert bytes")
    inode = source.stat().st_ino
    destination = tmp_path / "Zoë published"
    chrome._publish_noreplace(source, destination)
    assert destination.stat().st_ino == inode
    assert (destination / "inert").read_bytes() == b"inert bytes"
    assert not source.exists()


@pytest.mark.skipif(
    sys.platform != "linux", reason="Gates the actual Linux syscall at publication."
)
def test_empty_foreign_directory_created_at_native_boundary_survives_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact, _ = _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))
    destination = tmp_path / f"{artifact.version}-{artifact.platform}-{artifact.sha256}"
    native = ctypes.CDLL(None, use_errno=True).renameat2
    native.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    native.restype = ctypes.c_int
    entered, resume = threading.Event(), threading.Event()
    failures: list[Exception] = []

    def at_native_boundary(*arguments: object) -> int:
        source_encoded = arguments[1]
        assert isinstance(source_encoded, bytes) and os.path.isabs(source_encoded)
        assert arguments == (
            -100,
            source_encoded,
            -100,
            os.fsencode(destination),
            1,
        )
        entered.set()
        assert resume.wait(5), "race controller did not release syscall"
        return int(native(*arguments))

    call = MagicMock(side_effect=at_native_boundary)
    monkeypatch.setattr(
        chrome.ctypes, "CDLL", MagicMock(return_value=SimpleNamespace(renameat2=call))
    )

    def install() -> None:
        try:
            chrome.install_chrome(cache_directory=str(tmp_path))
        except Ring5Error as exc:
            failures.append(exc)

    worker = threading.Thread(target=install)
    worker.start()
    try:
        assert entered.wait(5), "installer did not reach native publication"
        destination.mkdir(mode=0o700)
        original = destination.lstat()
    finally:
        resume.set()
        worker.join(5)
    assert not worker.is_alive()
    assert len(failures) == 1 and isinstance(failures[0].__cause__, FileExistsError)
    after = destination.lstat()
    assert (after.st_ino, stat.S_IMODE(after.st_mode)) == (original.st_ino, 0o700)
    assert list(destination.iterdir()) == []
    assert list(tmp_path.iterdir()) == [destination]
    assert call.call_count == 1


@pytest.mark.parametrize(
    "system,symbol,flags", [("Linux", "renameat2", 1), ("Darwin", "renamex_np", 4)]
)
def test_native_publication_abi_and_filesystem_encoding(
    system: str,
    symbol: str,
    flags: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / os.fsdecode(b"source-\xff")
    destination = tmp_path / "Zoë destination"
    function = MagicMock(return_value=0)
    loader = MagicMock(return_value=SimpleNamespace(**{symbol: function}))
    monkeypatch.setattr(chrome.platform, "system", lambda: system)
    monkeypatch.setattr(chrome.ctypes, "CDLL", loader)
    chrome._publish_noreplace(source, destination)
    loader.assert_called_once_with(None, use_errno=True)
    assert function.restype is ctypes.c_int
    if system == "Linux":
        assert function.argtypes == [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.assert_called_once_with(
            -100, os.fsencode(source), -100, os.fsencode(destination), flags
        )
    else:
        assert function.argtypes == [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        function.assert_called_once_with(os.fsencode(source), os.fsencode(destination), flags)


def test_windows_uses_its_exclusive_unicode_rename_without_loading_posix_symbols(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, destination = tmp_path / "Zoë source", tmp_path / "工具 destination"
    rename = MagicMock()
    loader = MagicMock(side_effect=AssertionError("Windows must not load POSIX symbols"))
    monkeypatch.setattr(chrome.platform, "system", lambda: "Windows")
    monkeypatch.setattr(chrome.os, "rename", rename)
    monkeypatch.setattr(chrome.ctypes, "CDLL", loader)
    chrome._publish_noreplace(source, destination)
    rename.assert_called_once_with(source, destination)
    loader.assert_not_called()
    rename.side_effect = FileExistsError(errno.EEXIST, "foreign destination")
    with pytest.raises(FileExistsError):
        chrome._publish_noreplace(source, destination)


@pytest.mark.parametrize("system,symbol", [("Linux", "renameat2"), ("Darwin", "renamex_np")])
@pytest.mark.parametrize(
    "failure", [errno.ENOSYS, errno.EOPNOTSUPP, errno.EINVAL, errno.EACCES, 0, "missing"]
)
def test_unavailable_native_primitive_or_filesystem_has_no_fallback(
    system: str,
    symbol: str,
    failure: int | str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*arguments: object) -> int:
        ctypes.set_errno(int(failure))
        return -1

    function = MagicMock(side_effect=fail)
    library = SimpleNamespace() if failure == "missing" else SimpleNamespace(**{symbol: function})
    monkeypatch.setattr(chrome.platform, "system", lambda: system)
    monkeypatch.setattr(chrome.ctypes, "CDLL", MagicMock(return_value=library))
    fallback = MagicMock(side_effect=AssertionError("ordinary POSIX rename is forbidden"))
    monkeypatch.setattr(chrome.os, "rename", fallback)
    with pytest.raises(OSError) as error:
        chrome._publish_noreplace(tmp_path / "source", tmp_path / "destination")
    assert error.value.errno == (
        errno.ENOSYS if failure == "missing" else int(failure) or errno.EIO
    )
    fallback.assert_not_called()


def test_unknown_publication_platform_is_explicitly_unsupported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(chrome.platform, "system", lambda: "FreeBSD")
    with pytest.raises(OSError) as error:
        chrome._publish_noreplace(tmp_path / "source", tmp_path / "destination")
    assert error.value.errno == errno.ENOSYS


@pytest.mark.parametrize("bit", [5, 6])
def test_unsupported_zip_flags_fail_whole_graph_and_public_cli_before_extraction(
    bit: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact = chrome._load_manifest()["linux64"]
    payload = bytearray(_zip([(artifact.executable, b"inert", 0o100755)]))
    central = payload.index(b"PK\x01\x02")
    struct.pack_into("<H", payload, 6, 1 << bit)
    struct.pack_into("<H", payload, central + 8, 1 << bit)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        with pytest.raises(ValueError, match="encoding"):
            chrome._zip_plan(archive, artifact)
    _install_fixture(monkeypatch, bytes(payload))
    assert cli.main(["install-chrome", "--cache-dir", str(tmp_path)]) == 2
    output = capsys.readouterr()
    assert output.out == "" and "Unsupported Chrome archive member type or encoding" in output.err
    assert list(tmp_path.iterdir()) == []


def test_actual_symlink_loop_is_typed_and_preserved_before_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, network = _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))
    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    original = loop.lstat()
    assert cli.main(["install-chrome", "--cache-dir", str(loop)]) == 2
    result = capsys.readouterr()
    assert result.out == "" and "error: Chrome installation failed:" in result.err
    assert (loop.lstat().st_ino, loop.readlink()) == (original.st_ino, loop)
    network.assert_not_called()


def test_actual_console_symlink_loop_returns_two_without_traceback(tmp_path: Path) -> None:
    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    result = subprocess.run(
        [sys.executable, "-m", "ring5.cli", "install-chrome", "--cache-dir", str(loop)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == "" and result.stderr.startswith("error: Chrome installation failed:")
    assert "Traceback" not in result.stderr
    assert loop.is_symlink()


@pytest.mark.parametrize("error_kind", ["contextless", "unrelated-os", "later-operation"])
def test_unrelated_runtime_errors_remain_visible(
    error_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))

    def unexpected(*args: object, **kwargs: object) -> None:
        if error_kind == "unrelated-os":
            try:
                raise OSError(errno.EACCES, "not a loop")
            except OSError:
                raise RuntimeError("unexpected programmer failure")
        raise RuntimeError("unexpected programmer failure")

    if error_kind == "later-operation":
        monkeypatch.setattr(chrome, "_extract", unexpected)
    else:
        monkeypatch.setattr(chrome.Path, "resolve", unexpected)
    with pytest.raises(RuntimeError, match="unexpected programmer failure"):
        chrome.install_chrome(cache_directory=str(tmp_path))


def test_windows_documented_loop_context_is_normalized_only_at_resolve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))

    def windows_loop(*args: object, **kwargs: object) -> None:
        try:
            failure = OSError(errno.EINVAL, "native Windows loop")
            setattr(failure, "winerror", 1921)
            raise failure
        except OSError:
            raise RuntimeError("known Path.resolve loop wrapper")

    monkeypatch.setattr(chrome.Path, "resolve", windows_loop)
    with pytest.raises(Ring5Error, match="symlink loop"):
        chrome.install_chrome(cache_directory=str(tmp_path))


@pytest.mark.skipif(os.name == "nt", reason="The negative control uses ordinary POSIX rename.")
def test_wheel_publication_control_detects_a_replacing_primitive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import verify_installation

    monkeypatch.setattr(chrome, "_publish_noreplace", os.rename)
    with pytest.raises(Ring5Error, match="replaced a foreign directory"):
        verify_installation._verify_chrome_publication(tmp_path)


@pytest.mark.parametrize("failure", ["missing-symbol", "unsupported-filesystem", "loader-error"])
def test_unavailable_native_publication_is_typed_and_preserves_other_cache_entries(
    failure: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))
    monkeypatch.setattr(chrome.platform, "system", lambda: "Linux")
    other = tmp_path / "unrelated"
    other.mkdir()
    (other / "keep").write_bytes(b"unrelated bytes")
    if failure == "missing-symbol":
        loader = MagicMock(return_value=SimpleNamespace())
    elif failure == "loader-error":
        loader = MagicMock(side_effect=OSError(errno.EACCES, "native loader refused"))
    else:

        def unsupported(*arguments: object) -> int:
            ctypes.set_errno(errno.EOPNOTSUPP)
            return -1

        loader = MagicMock(
            return_value=SimpleNamespace(renameat2=MagicMock(side_effect=unsupported))
        )
    monkeypatch.setattr(chrome.ctypes, "CDLL", loader)
    assert cli.main(["install-chrome", "--cache-dir", str(tmp_path)]) == 2
    output = capsys.readouterr()
    assert output.out == "" and output.err.startswith("error: Chrome installation failed:")
    assert (other / "keep").read_bytes() == b"unrelated bytes"
    assert list(tmp_path.iterdir()) == [other]
