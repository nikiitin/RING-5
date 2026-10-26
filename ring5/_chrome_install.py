"""Install the packaged, reviewed Chrome for Testing release without launching it."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import posixpath
import re
import stat
import tempfile
import time
import urllib.request
import zipfile
import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from http.client import HTTPException, HTTPResponse
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Any, cast
from collections.abc import Iterator

from platformdirs import user_cache_path

from ring5.errors import Ring5Error

_MAX_ARCHIVE_BYTES = 512 * 1024**2
_MAX_EXTRACTED_BYTES = 2 * 1024**3
_MAX_MEMBERS = 10_000
_MAX_PATH_PARTS = 32
_MAX_LINKS = 32
_MAX_LINK_BYTES = 4096
_CHUNK_BYTES = 1024**2
_DOWNLOAD_SECONDS = 900
_CATALOG_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "last-known-good-versions-with-downloads.json"
)
_EXECUTABLES = {
    "linux64": "chrome-linux64/chrome",
    "linux-arm64": "chrome-linux-arm64/chrome",
    "mac-x64": "chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/"
    "Google Chrome for Testing",
    "mac-arm64": "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/"
    "Google Chrome for Testing",
    "win32": "chrome-win32/chrome.exe",
    "win64": "chrome-win64/chrome.exe",
}


@dataclass(frozen=True)
class _Artifact:
    platform: str
    version: str
    revision: str
    url: str
    size: int
    generation: str
    md5: str
    sha256: str
    executable: str


def _load_manifest() -> dict[str, _Artifact]:
    """Validate the one packaged manifest before using any download or cache path."""
    payload = files("ring5").joinpath("resources/chrome-for-testing.json").read_text("utf-8")
    manifest = json.loads(payload)
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version",
        "channel",
        "version",
        "revision",
        "catalog_url",
        "integrity",
        "artifacts",
    }:
        raise ValueError("Invalid Chrome manifest fields.")
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["channel"] != "Stable"
        or manifest["catalog_url"] != _CATALOG_URL
        or manifest["integrity"] != "official-https-size-md5-bootstrap-project-sha256"
    ):
        raise ValueError("Unsupported Chrome manifest contract.")
    version, revision = manifest["version"], manifest["revision"]
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        raise ValueError("Invalid Chrome version.")
    if not isinstance(revision, str) or not re.fullmatch(r"\d+", revision):
        raise ValueError("Invalid Chrome revision.")
    entries = manifest["artifacts"]
    if not isinstance(entries, dict) or set(entries) != set(_EXECUTABLES):
        raise ValueError("Chrome manifest must describe every supported platform exactly once.")
    artifacts = {}
    for name, executable in _EXECUTABLES.items():
        entry = entries[name]
        if not isinstance(entry, dict) or set(entry) != {
            "url",
            "size",
            "generation",
            "md5",
            "sha256",
            "executable",
        }:
            raise ValueError("Invalid Chrome artifact fields.")
        expected_url = (
            f"https://storage.googleapis.com/chrome-for-testing-public/"
            f"{version}/{name}/chrome-{name}.zip"
        )
        if entry["url"] != expected_url or entry["executable"] != executable:
            raise ValueError("Chrome artifact URL or executable does not match its platform.")
        if type(entry["size"]) is not int or not 0 < entry["size"] <= _MAX_ARCHIVE_BYTES:
            raise ValueError("Invalid Chrome archive size.")
        for key, pattern in (("generation", r"\d+"), ("sha256", r"[0-9a-f]{64}")):
            if not isinstance(entry[key], str) or not re.fullmatch(pattern, entry[key]):
                raise ValueError(f"Invalid Chrome artifact {key}.")
        if not isinstance(entry["md5"], str) or not re.fullmatch(
            r"[A-Za-z0-9+/]{22}==", entry["md5"]
        ):
            raise ValueError("Invalid Chrome artifact MD5.")
        artifacts[name] = _Artifact(name, version, revision, **entry)
    return artifacts


def _host_platform() -> str:
    """Map a native OS/architecture without silently choosing an emulated browser."""
    system, machine = platform.system(), platform.machine().lower()
    names = {
        ("Linux", "x86_64"): "linux64",
        ("Linux", "amd64"): "linux64",
        ("Linux", "aarch64"): "linux-arm64",
        ("Linux", "arm64"): "linux-arm64",
        ("Darwin", "x86_64"): "mac-x64",
        ("Darwin", "arm64"): "mac-arm64",
        ("Windows", "amd64"): "win64",
        ("Windows", "x86_64"): "win64",
        ("Windows", "x86"): "win32",
        ("Windows", "i386"): "win32",
        ("Windows", "i686"): "win32",
    }
    name = names.get((system, machine))
    if name is None:
        raise Ring5Error(
            f"Chrome for Testing has no supported native artifact for {system}/{machine}. "
            "Set BROWSER_PATH to a separately installed compatible browser."
        )
    return name


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise ValueError("Chrome download redirects are not allowed.")


def _open_archive(url: str) -> HTTPResponse:
    return cast(HTTPResponse, urllib.request.build_opener(_NoRedirect()).open(url, timeout=60))


def _download(artifact: _Artifact, target: Path) -> None:
    """Check the pinned transfer facts and project SHA-256 before opening the ZIP."""
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    received = 0
    started = time.monotonic()
    with _open_archive(artifact.url) as response, target.open("xb") as output:
        if (
            response.geturl() != artifact.url
            or response.headers.get("x-goog-generation") != artifact.generation
            or response.headers.get("Content-Length") != str(artifact.size)
        ):
            raise ValueError(
                "Chrome response does not match the pinned object generation and size."
            )
        while chunk := response.read1(min(_CHUNK_BYTES, artifact.size - received + 1)):
            received += len(chunk)
            if received > artifact.size or time.monotonic() - started > _DOWNLOAD_SECONDS:
                raise ValueError("Chrome download exceeded its size or time limit.")
            sha256.update(chunk)
            md5.update(chunk)
            output.write(chunk)
    if received != artifact.size:
        raise ValueError("Chrome download is incomplete.")
    if base64.b64encode(md5.digest()).decode("ascii") != artifact.md5:
        raise ValueError("Chrome download does not match the provider MD5 transfer checksum.")
    if sha256.hexdigest() != artifact.sha256:
        raise ValueError("Chrome download does not match the reviewed project SHA-256.")


def _safe_path(name: str, root: str) -> PurePosixPath:
    """Accept one canonical portable archive path inside its platform root."""
    if (
        not name
        or len(name.encode("utf-8")) > 1024
        or any(ord(character) < 32 for character in name)
        or any(character in name for character in '\\:\x00<>"|?*')
        or any(part in {"", ".", ".."} for part in name.split("/"))
    ):
        raise ValueError("Unsafe Chrome archive member path.")
    path = PurePosixPath(name)
    if path.is_absolute() or path.parts[0] != root or len(path.parts) > _MAX_PATH_PARTS:
        raise ValueError("Chrome archive member escapes its platform root.")
    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
    if any(
        part.endswith((".", " ")) or part.split(".")[0].casefold() in reserved
        for part in path.parts
    ):
        raise ValueError("Chrome archive member has a nonportable filename.")
    return path


def _link_target(path: PurePosixPath, target: str, root: str) -> PurePosixPath:
    if not target or target.startswith("/") or "\\" in target or ":" in target or "\x00" in target:
        raise ValueError("Unsafe Chrome archive link target.")
    return _safe_path(posixpath.normpath(str(path.parent / target)), root)


def _resolve_link(path: PurePosixPath, links: dict[PurePosixPath, str], root: str) -> PurePosixPath:
    seen: set[PurePosixPath] = set()
    while True:
        for index in range(1, len(path.parts) + 1):
            prefix = PurePosixPath(*path.parts[:index])
            if prefix in links:
                if prefix in seen or len(seen) >= _MAX_LINKS:
                    raise ValueError("Chrome archive has a cyclic or excessive link chain.")
                seen.add(prefix)
                expanded = _link_target(prefix, links[prefix], root).joinpath(*path.parts[index:])
                path = _safe_path(expanded.as_posix(), root)
                break
        else:
            return path


def _zip_plan(
    archive: zipfile.ZipFile, artifact: _Artifact
) -> tuple[list[tuple[zipfile.ZipInfo, PurePosixPath, int]], dict[PurePosixPath, str]]:
    """Validate the complete bounded graph before creating any archive member."""
    infos = archive.infolist()
    if (
        not infos
        or len(infos) > _MAX_MEMBERS
        or sum(i.file_size for i in infos) > _MAX_EXTRACTED_BYTES
    ):
        raise ValueError("Chrome archive exceeds its member or expanded size limit.")
    root = f"chrome-{artifact.platform}"
    entries = []
    kinds: dict[PurePosixPath, int] = {}
    folded: set[str] = set()
    links: dict[PurePosixPath, str] = {}
    for info in infos:
        path = _safe_path(info.filename.removesuffix("/") if info.is_dir() else info.filename, root)
        mode = info.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if (
            kind not in {stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK}
            or (kind == stat.S_IFDIR) != info.is_dir()
            or info.flag_bits & 1
            or info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
            or info.orig_filename != info.filename
        ):
            raise ValueError("Unsupported Chrome archive member type or encoding.")
        if path.as_posix().casefold() in folded:
            raise ValueError("Chrome archive has duplicate or case-colliding paths.")
        folded.add(path.as_posix().casefold())
        kinds[path] = kind
        entries.append((info, path, mode))
        if kind == stat.S_IFLNK:
            if (
                not artifact.platform.startswith("mac-")
                or info.file_size > _MAX_LINK_BYTES
                or len(links) >= _MAX_LINKS
            ):
                raise ValueError("Chrome archive exceeds its supported link policy.")
            links[path] = archive.read(info).decode("utf-8")
    known = set(kinds)
    for path in kinds:
        for parent in path.parents[:-1]:
            if parent in kinds and kinds[parent] != stat.S_IFDIR:
                raise ValueError("Chrome archive member descends through a file or link alias.")
            known.add(parent)
            if len(known) > _MAX_MEMBERS:
                raise ValueError("Chrome archive exceeds its file and directory graph limit.")
    if len({path.as_posix().casefold() for path in known}) != len(known):
        raise ValueError("Chrome archive has case-colliding parent directories.")
    for path in links:
        if _resolve_link(path, links, root) not in known:
            raise ValueError("Chrome archive link has a missing target.")
    return entries, links


def _extract(archive_path: Path, directory: Path, artifact: _Artifact) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        entries, links = _zip_plan(archive, artifact)
        for info, path, mode in entries:
            target = directory / path
            if stat.S_ISDIR(mode):
                target.mkdir(parents=True, exist_ok=True)
            elif stat.S_ISREG(mode):
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("xb") as output:
                    while chunk := source.read(_CHUNK_BYTES):
                        output.write(chunk)
                target.chmod(stat.S_IMODE(mode) & 0o777)
        for path, link_target in links.items():
            location = directory / path
            location.parent.mkdir(parents=True, exist_ok=True)
            location.symlink_to(link_target)


def _tree_digest(directory: Path) -> str:
    """Hash names, file bytes, permissions and literal links without following links."""
    digest = hashlib.sha256()
    total = 0
    paths = []
    for path in directory.rglob("*"):
        if path == directory / "receipt.json":
            continue
        paths.append(path)
        if len(paths) > _MAX_MEMBERS:
            raise ValueError("Chrome installation contains too many entries.")
    for path in sorted(paths):
        relative = path.relative_to(directory).as_posix()
        mode = path.lstat().st_mode
        identity: list[str | int] = [relative, stat.S_IFMT(mode), stat.S_IMODE(mode)]
        if stat.S_ISLNK(mode):
            identity.append(os.readlink(path))
        elif stat.S_ISREG(mode):
            content_hash = hashlib.sha256()
            with path.open("rb") as source:
                while chunk := source.read(_CHUNK_BYTES):
                    total += len(chunk)
                    if total > _MAX_EXTRACTED_BYTES:
                        raise ValueError("Chrome installation exceeds its extracted size limit.")
                    content_hash.update(chunk)
            identity.append(content_hash.hexdigest())
        elif not stat.S_ISDIR(mode):
            raise ValueError("Chrome installation contains a special file.")
        digest.update(json.dumps(identity).encode("utf-8"))
    return digest.hexdigest()


def _identity(artifact: _Artifact) -> dict[str, str | int]:
    return {
        "format": "ring5.chrome-installation",
        "schema_version": 1,
        "version": artifact.version,
        "revision": artifact.revision,
        "platform": artifact.platform,
        "archive_sha256": artifact.sha256,
    }


def _check_executable(directory: Path, artifact: _Artifact) -> Path:
    executable = directory / artifact.executable
    if not executable.is_file() or executable.is_symlink() or executable.stat().st_size == 0:
        raise ValueError("Chrome archive does not contain its expected regular executable.")
    if not artifact.platform.startswith("win") and not os.access(executable, os.X_OK):
        raise ValueError("Chrome executable has no executable permission.")
    return executable


def _reuse(directory: Path, artifact: _Artifact) -> Path:
    """Reuse only an owned installation whose complete tree still matches its receipt."""
    receipt = directory / "receipt.json"
    if directory.is_symlink() or not directory.is_dir() or receipt.is_symlink():
        raise ValueError(f"Chrome destination is not an owned installation: {directory}")
    if not receipt.is_file() or receipt.stat().st_size > 4096:
        raise ValueError(f"Chrome destination has no valid owned receipt: {directory}")
    recorded = json.loads(receipt.read_text("utf-8"))
    expected = {**_identity(artifact), "tree_sha256": _tree_digest(directory)}
    if (
        not isinstance(recorded, dict)
        or type(recorded.get("schema_version")) is not int
        or recorded != expected
    ):
        raise ValueError(f"Chrome installation does not match its receipt: {directory}")
    return _check_executable(directory, artifact)


@contextmanager
def _install_lock(root: Path, artifact: _Artifact) -> Iterator[None]:
    """Serialize cooperating installs without taking over an existing lock."""
    lock = root / f".chrome-install-{artifact.sha256}.lock"
    lock.touch(exist_ok=False)
    try:
        yield
    finally:
        lock.unlink()


def install_chrome(*, cache_directory: str | None = None) -> Path:
    """Install or verify the reviewed native browser, returning its absolute path.

    Args:
        cache_directory: Explicit cache root, or the platform user cache when omitted.

    Returns:
        Absolute browser executable path for explicit ``BROWSER_PATH`` selection.

    Raises:
        Ring5Error: Unsupported platform, network, integrity, archive, cache or disk failure.
    """
    try:
        artifact = _load_manifest()[_host_platform()]
        root = (
            Path(cache_directory).expanduser()
            if cache_directory is not None
            else user_cache_path("ring5", appauthor=False) / "chrome"
        ).resolve()
        if "\n" in str(root) or "\r" in str(root):
            raise ValueError("Chrome cache path must fit on one output line.")
        root.mkdir(parents=True, exist_ok=True)
        destination = root / f"{artifact.version}-{artifact.platform}-{artifact.sha256}"
        if destination.exists() or destination.is_symlink():
            return _reuse(destination, artifact)
        with (
            _install_lock(root, artifact),
            tempfile.TemporaryDirectory(prefix=".chrome-stage-", dir=root) as temporary,
        ):
            stage = Path(temporary)
            archive = stage / "archive.zip"
            _download(artifact, archive)
            installation = stage / "installation"
            installation.mkdir()
            _extract(archive, installation, artifact)
            _check_executable(installation, artifact)
            receipt = {**_identity(artifact), "tree_sha256": _tree_digest(installation)}
            (installation / "receipt.json").write_text(
                json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8"
            )
            if destination.exists() or destination.is_symlink():
                return _reuse(destination, artifact)
            installation.rename(destination)
        return destination / artifact.executable
    except (
        OSError,
        ValueError,
        HTTPException,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        zlib.error,
    ) as exc:
        raise Ring5Error(f"Chrome installation failed: {exc}") from exc
