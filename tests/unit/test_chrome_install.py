"""Inert archive proofs for the packaged Stable Chrome installer and CLI."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from ring5 import _chrome_install as chrome
from ring5 import cli
from ring5.errors import Ring5Error

pytestmark = pytest.mark.public_api


class _Response(io.BytesIO):
    def __init__(self, content: bytes, artifact: chrome._Artifact) -> None:
        super().__init__(content)
        self.url = artifact.url
        self.headers = {
            "Content-Length": str(artifact.size),
            "x-goog-generation": artifact.generation,
        }

    def geturl(self) -> str:
        return self.url


def _zip(entries: list[tuple[str, bytes, int]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content, mode in entries:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = mode << 16
            archive.writestr(info, content)
    return output.getvalue()


def _artifact(content: bytes, name: str = "linux64") -> chrome._Artifact:
    return replace(
        chrome._load_manifest()[name],
        size=len(content),
        md5=base64.b64encode(hashlib.md5(content, usedforsecurity=False).digest()).decode(),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def test_packaged_manifest_is_complete_stable_and_uses_exact_official_artifacts() -> None:
    artifacts = chrome._load_manifest()
    assert set(artifacts) == {"linux64", "linux-arm64", "mac-x64", "mac-arm64", "win32", "win64"}
    for name, artifact in artifacts.items():
        assert artifact.version == "156.0.8078.47"
        assert artifact.revision == "1706539"
        assert artifact.platform == name
        assert artifact.executable.startswith(f"chrome-{name}/")
        assert artifact.size > 100_000_000


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Linux", "x86_64", "linux64"),
        ("Linux", "AMD64", "linux64"),
        ("Linux", "aarch64", "linux-arm64"),
        ("Linux", "arm64", "linux-arm64"),
        ("Darwin", "x86_64", "mac-x64"),
        ("Darwin", "arm64", "mac-arm64"),
        ("Windows", "AMD64", "win64"),
        ("Windows", "x86_64", "win64"),
        ("Windows", "x86", "win32"),
        ("Windows", "i386", "win32"),
        ("Windows", "i686", "win32"),
    ],
)
def test_native_platform_mapping(
    system: str, machine: str, expected: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(chrome.platform, "system", lambda: system)
    monkeypatch.setattr(chrome.platform, "machine", lambda: machine)
    assert chrome._host_platform() == expected


@pytest.mark.parametrize(
    ("system", "machine"), [("Windows", "ARM64"), ("Linux", "i686"), ("FreeBSD", "x86_64")]
)
def test_unsupported_platform_never_chooses_emulation(
    system: str, machine: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(chrome.platform, "system", lambda: system)
    monkeypatch.setattr(chrome.platform, "machine", lambda: machine)
    with pytest.raises(Ring5Error, match=f"{system}/{machine.lower()}"):
        chrome._host_platform()


@pytest.mark.parametrize(
    "mutation",
    [
        "not-object",
        "extra-field",
        "version-type",
        "version-format",
        "revision-type",
        "revision-format",
        "schema-bool",
        "schema-version",
        "channel",
        "catalog",
        "integrity",
        "platforms-type",
        "platform-missing",
        "platform-extra",
        "artifact-type",
        "artifact-extra",
        "artifact-url",
        "artifact-executable",
        "size-bool",
        "size-zero",
        "size-large",
        "generation-type",
        "generation-format",
        "sha256-type",
        "sha256-format",
        "md5-type",
        "md5-format",
    ],
)
def test_manifest_rejects_noncanonical_contracts(
    mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from importlib.resources import files

    manifest: Any = json.loads(
        files("ring5").joinpath("resources/chrome-for-testing.json").read_text()
    )
    if mutation == "not-object":
        manifest = []
    elif mutation == "extra-field":
        manifest["unexpected"] = 1
    elif mutation.startswith("version-"):
        manifest["version"] = 156 if mutation.endswith("type") else "156.0"
    elif mutation.startswith("revision-"):
        manifest["revision"] = 1 if mutation.endswith("type") else "../1"
    elif mutation.startswith("schema-"):
        manifest["schema_version"] = True if mutation.endswith("bool") else 2
    elif mutation in {"channel", "catalog", "integrity"}:
        manifest[{"catalog": "catalog_url"}.get(mutation, mutation)] = "Canary"
    elif mutation == "platforms-type":
        manifest["artifacts"] = []
    elif mutation == "platform-missing":
        del manifest["artifacts"]["win64"]
    elif mutation == "platform-extra":
        manifest["artifacts"]["win-arm64"] = {}
    else:
        entry = manifest["artifacts"]["linux64"]
        if mutation == "artifact-type":
            manifest["artifacts"]["linux64"] = []
        elif mutation == "artifact-extra":
            entry["unexpected"] = 1
        elif mutation == "artifact-url":
            entry["url"] = "https://example.invalid/browser.zip"
        elif mutation == "artifact-executable":
            entry["executable"] = "../../chrome"
        elif mutation.startswith("size-"):
            entry["size"] = {"size-bool": True, "size-zero": 0, "size-large": 1024**3}[mutation]
        else:
            key, error = mutation.split("-")
            entry[key] = 12 if error == "type" else "invalid"
    resource = tmp_path / "resources"
    resource.mkdir()
    (resource / "chrome-for-testing.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(chrome, "files", lambda package: tmp_path)
    with pytest.raises(ValueError):
        chrome._load_manifest()


def test_download_checks_transfer_facts_and_reviewed_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"inert archive bytes"
    artifact = _artifact(payload)
    monkeypatch.setattr(chrome, "_open_archive", lambda url: _Response(payload, artifact))
    target = tmp_path / "download.zip"
    chrome._download(artifact, target)
    assert target.read_bytes() == payload


@pytest.mark.parametrize(
    "failure", ["url", "generation", "length", "large", "slow", "truncated", "md5", "sha256"]
)
def test_download_rejects_changed_truncated_or_unbounded_input(
    failure: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # [test->req~ring5.cli.install-chrome~1]
    payload = b"inert archive bytes"
    artifact = _artifact(payload)
    body = payload
    if failure == "large":
        body += b"extra"
    elif failure == "truncated":
        body = payload[:-1]
    elif failure == "md5":
        artifact = replace(artifact, md5="AAAAAAAAAAAAAAAAAAAAAA==")
    elif failure == "sha256":
        artifact = replace(artifact, sha256="0" * 64)
    response = _Response(body, artifact)
    if failure == "url":
        response.url = "http://example.invalid/redirected"
    elif failure == "generation":
        response.headers["x-goog-generation"] = "changed"
    elif failure == "length":
        del response.headers["Content-Length"]
    elif failure == "slow":
        ticks = iter([0.0, chrome._DOWNLOAD_SECONDS + 1.0])
        monkeypatch.setattr(chrome.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(chrome, "_open_archive", lambda url: response)
    with pytest.raises(ValueError):
        chrome._download(artifact, tmp_path / "bad.zip")


def test_download_refuses_redirects() -> None:
    with pytest.raises(ValueError, match="redirects"):
        chrome._NoRedirect().redirect_request(
            None, None, 302, "redirect", {}, "https://example.invalid"
        )


def test_network_opener_uses_bounded_timeout_and_no_redirect_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = MagicMock()
    factory = MagicMock(return_value=opener)
    monkeypatch.setattr(chrome.urllib.request, "build_opener", factory)
    assert (
        chrome._open_archive("https://storage.googleapis.com/example") is opener.open.return_value
    )
    assert isinstance(factory.call_args.args[0], chrome._NoRedirect)
    opener.open.assert_called_once_with("https://storage.googleapis.com/example", timeout=60)


def _inert_layout(name: str) -> list[tuple[str, bytes, int]]:
    executable = chrome._load_manifest()[name].executable
    entries = [(executable, b"inert browser fixture; never execute", 0o100755)]
    root = f"chrome-{name}"
    entries.extend(
        [(f"{root}/", b"", 0o40755), (f"{root}/resources/data.bin", b"fixture data", 0o100644)]
    )
    if name.startswith("mac-"):
        framework = (
            f"{root}/Google Chrome for Testing.app/Contents/Frameworks/"
            "Google Chrome for Testing Framework.framework"
        )
        version = "156.0.8078.47"
        for folder in ("Resources", "Libraries", "Helpers"):
            entries.append(
                (f"{framework}/Versions/{version}/{folder}/data", b"mac fixture", 0o100644)
            )
        entries.append(
            (
                f"{framework}/Versions/{version}/Google Chrome for Testing Framework",
                b"inert framework",
                0o100755,
            )
        )
        # Observed provider order includes links before their chained Current link.
        for link, target in [
            ("Resources", "Versions/Current/Resources"),
            ("Versions/Current", version),
            ("Libraries", "Versions/Current/Libraries"),
            (
                "Google Chrome for Testing Framework",
                "Versions/Current/Google Chrome for Testing Framework",
            ),
            ("Helpers", "Versions/Current/Helpers"),
        ]:
            entries.append((f"{framework}/{link}", target.encode(), 0o120755))
    return entries


def _install_fixture(
    monkeypatch: pytest.MonkeyPatch, content: bytes, name: str = "linux64"
) -> tuple[chrome._Artifact, MagicMock]:
    artifact = _artifact(content, name)
    monkeypatch.setattr(chrome, "_load_manifest", lambda: {name: artifact})
    monkeypatch.setattr(chrome, "_host_platform", lambda: name)
    network = MagicMock(side_effect=lambda url: _Response(content, artifact))
    monkeypatch.setattr(chrome, "_open_archive", network)
    return artifact, network


@pytest.mark.parametrize(
    "name", ["linux64", "linux-arm64", "mac-x64", "mac-arm64", "win32", "win64"]
)
def test_all_platforms_install_inert_observed_layout_and_verify_reuse(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # [test->req~ring5.cli.install-chrome~1]
    content = _zip(_inert_layout(name))
    artifact, network = _install_fixture(monkeypatch, content, name)
    cache = tmp_path / "cache with spaces" / "Zoë"
    executable = chrome.install_chrome(cache_directory=str(cache))
    assert executable.is_absolute()
    assert executable.read_bytes() == b"inert browser fixture; never execute"
    destination = executable.parents[len(Path(artifact.executable).parts) - 1]
    assert destination.parent == cache
    assert (
        json.loads((destination / "receipt.json").read_text())["archive_sha256"] == artifact.sha256
    )
    if name.startswith("mac-"):
        framework = (
            destination / f"chrome-{name}/Google Chrome for Testing.app/Contents/Frameworks/"
            "Google Chrome for Testing Framework.framework"
        )
        assert (framework / "Versions/Current").is_symlink()
        assert (framework / "Versions/Current").readlink() == Path(artifact.version)
        for part in ("Resources", "Libraries", "Helpers"):
            assert (framework / part).is_symlink()
            assert (framework / part / "data").read_bytes() == b"mac fixture"
        assert (framework / "Google Chrome for Testing Framework").is_symlink()
        assert (
            framework / "Google Chrome for Testing Framework"
        ).read_bytes() == b"inert framework"
    assert chrome.install_chrome(cache_directory=str(cache)) == executable
    network.assert_called_once_with(artifact.url)
    assert sorted(p.name for p in cache.iterdir()) == [destination.name]


@pytest.mark.parametrize(
    "bad_path",
    [
        "",
        "/absolute",
        "../escape",
        "chrome-linux64/../escape",
        "chrome-linux64//alias",
        "chrome-linux64/./alias",
        r"chrome-linux64\escape",
        "chrome-linux64/a:b",
        "other/chrome",
        "chrome-linux64/NUL.txt",
        "chrome-linux64/name.",
        "chrome-linux64/name ",
        "chrome-linux64/a?",
        "chrome-linux64/" + "a" * 1025,
    ],
)
def test_archive_member_path_rejections(bad_path: str) -> None:
    with pytest.raises(ValueError):
        chrome._safe_path(bad_path, "chrome-linux64")


@pytest.mark.parametrize(
    "failure",
    [
        "empty",
        "many",
        "expanded",
        "fifo",
        "directory-type",
        "compression",
        "duplicate",
        "case-collision",
        "file-parent",
        "non-mac-link",
        "large-link",
        "many-links",
        "absolute-link",
        "drive-link",
        "backslash-link",
        "nul-link",
        "empty-link",
        "escape-link",
        "cycle-link",
        "missing-link",
        "alias-descendant",
        "link-depth",
    ],
)
def test_invalid_archive_graph_rejected_before_any_member_is_extracted(
    failure: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # [test->req~ring5.cli.install-chrome~1]
    name = "mac-arm64" if "link" in failure or failure == "alias-descendant" else "linux64"
    artifact = chrome._load_manifest()[name]
    root = f"chrome-{name}"
    entries = [(artifact.executable, b"inert", 0o100755)]
    if failure == "empty":
        entries = []
    elif failure == "many":
        monkeypatch.setattr(chrome, "_MAX_MEMBERS", 1)
        entries.append((f"{root}/extra", b"inert", 0o100644))
    elif failure == "expanded":
        monkeypatch.setattr(chrome, "_MAX_EXTRACTED_BYTES", 1)
    elif failure == "fifo":
        entries.append((f"{root}/fifo", b"", 0o010600))
    elif failure == "directory-type":
        entries.append((f"{root}/directory/", b"", 0o100644))
    elif failure == "compression":
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w", compression=zipfile.ZIP_BZIP2) as archive:
            archive.writestr(artifact.executable, b"inert")
        payload = content.getvalue()
    elif failure in {"duplicate", "case-collision"}:
        path = (
            artifact.executable
            if failure == "duplicate"
            else artifact.executable.upper().replace(root.upper(), root)
        )
        entries.append((path, b"extra", 0o100644))
    elif failure == "file-parent":
        entries.extend(
            [(f"{root}/parent", b"file", 0o100644), (f"{root}/parent/child", b"child", 0o100644)]
        )
    else:
        if failure == "non-mac-link":
            name, root = "linux64", "chrome-linux64"
            artifact = chrome._load_manifest()[name]
            entries = [(artifact.executable, b"inert", 0o100755)]
        target = {
            "absolute-link": b"/outside",
            "drive-link": b"C:/outside",
            "backslash-link": b"..\\outside",
            "nul-link": b"bad\x00target",
            "empty-link": b"",
            "escape-link": b"../../outside",
            "cycle-link": b"link",
            "missing-link": b"absent",
            "large-link": b"a" * 4097,
        }.get(failure, Path(artifact.executable).name.encode())
        entries.append((f"{root}/link", target, 0o120755))
        if failure == "alias-descendant":
            entries.append((f"{root}/link/child", b"child", 0o100644))
        elif failure in {"many-links", "link-depth"}:
            for index in range(33):
                entries.append((f"{root}/link{index}", f"link{index + 1}".encode(), 0o120755))
    if failure != "compression":
        payload = _zip(entries)
    archive_path = tmp_path / "bad.zip"
    archive_path.write_bytes(payload)
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ValueError):
        chrome._extract(archive_path, output, artifact)
    assert list(output.iterdir()) == []


@pytest.mark.parametrize(
    "failure", ["missing-exe", "empty-exe", "non-executable", "download", "disk"]
)
def test_failed_install_preserves_existing_good_and_unrelated_cache(
    failure: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entries = _inert_layout("linux64")
    if failure == "missing-exe":
        entries = entries[1:]
    elif failure == "empty-exe":
        entries[0] = (entries[0][0], b"", entries[0][2])
    elif failure == "non-executable":
        entries[0] = (entries[0][0], entries[0][1], 0o100644)
    _, network = _install_fixture(monkeypatch, _zip(entries))
    good = tmp_path / "previous-good-release"
    unrelated = tmp_path / "unrelated"
    good.mkdir()
    unrelated.mkdir()
    (good / "keep.bin").write_bytes(b"good")
    (unrelated / "keep.bin").write_bytes(b"unrelated")
    if failure == "download":
        network.side_effect = OSError("network failed")
    elif failure == "disk":
        monkeypatch.setattr(chrome, "_extract", MagicMock(side_effect=OSError("disk failed")))
    with pytest.raises(Ring5Error, match="Chrome installation failed"):
        chrome.install_chrome(cache_directory=str(tmp_path))
    assert {p.name for p in tmp_path.iterdir()} == {"previous-good-release", "unrelated"}
    assert (good / "keep.bin").read_bytes() == b"good"
    assert (unrelated / "keep.bin").read_bytes() == b"unrelated"


@pytest.mark.parametrize(
    "failure",
    [
        "unowned",
        "receipt",
        "receipt-large",
        "tree",
        "extra",
        "symlink-destination",
        "symlink-receipt",
    ],
)
def test_existing_unowned_or_corrupt_destination_is_never_replaced(
    failure: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = _zip(_inert_layout("linux64"))
    artifact, network = _install_fixture(monkeypatch, content)
    executable = chrome.install_chrome(cache_directory=str(tmp_path))
    destination = executable.parent.parent
    receipt = destination / "receipt.json"
    if failure == "unowned":
        receipt.unlink()
    elif failure == "receipt":
        receipt.write_text("{}")
    elif failure == "receipt-large":
        receipt.write_text("x" * 4097)
    elif failure == "tree":
        executable.write_bytes(b"corrupt browser")
    elif failure == "extra":
        (destination / "unexpected").write_text("extra file")
    elif failure == "symlink-destination":
        relocated = tmp_path / "relocated"
        destination.rename(relocated)
        destination.symlink_to(relocated, target_is_directory=True)
    else:
        other = tmp_path / "external-receipt"
        receipt.rename(other)
        receipt.symlink_to(other)
    before = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    with pytest.raises(Ring5Error):
        chrome.install_chrome(cache_directory=str(tmp_path))
    after = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert before == after
    network.assert_called_once_with(artifact.url)


def test_cli_emits_only_absolute_executable_and_preserves_browser_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # [test->req~ring5.cli.install-chrome~1]
    import os

    _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))
    monkeypatch.setenv("BROWSER_PATH", "")
    assert cli.main(["install-chrome", "--cache-dir", str(tmp_path / "Zoë")]) == 0
    output = capsys.readouterr()
    executable = Path(output.out.rstrip("\n"))
    assert output.out == str(executable) + "\n"
    assert executable.is_absolute() and executable.is_file()
    assert "BROWSER_PATH" in output.err and "does not" in output.err
    assert os.environ["BROWSER_PATH"] == ""


def test_cli_default_cache_and_operational_error_are_public(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))
    monkeypatch.setattr(chrome, "user_cache_path", lambda *args, **kwargs: tmp_path)
    assert cli.main(["install-chrome"]) == 0
    assert Path(capsys.readouterr().out.strip()).is_relative_to(tmp_path / "chrome")
    monkeypatch.setattr(chrome, "_load_manifest", MagicMock(side_effect=ValueError("bad manifest")))
    assert cli.main(["install-chrome"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "error: Chrome installation failed: bad manifest" in output.err


def test_tree_validation_enforces_entry_byte_and_special_file_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    (tmp_path / "content").write_bytes(b"ab")
    monkeypatch.setattr(chrome, "_MAX_MEMBERS", 0)
    with pytest.raises(ValueError, match="too many"):
        chrome._tree_digest(tmp_path)
    monkeypatch.setattr(chrome, "_MAX_MEMBERS", 10)
    monkeypatch.setattr(chrome, "_MAX_EXTRACTED_BYTES", 1)
    with pytest.raises(ValueError, match="size limit"):
        chrome._tree_digest(tmp_path)
    (tmp_path / "content").unlink()
    if hasattr(os, "mkfifo"):
        os.mkfifo(tmp_path / "special")
        with pytest.raises(ValueError, match="special file"):
            chrome._tree_digest(tmp_path)


def test_graph_checks_implicit_case_collisions_and_bounded_link_resolution() -> None:
    from pathlib import PurePosixPath

    artifact = chrome._load_manifest()["mac-arm64"]
    content = _zip(
        [
            ("chrome-mac-arm64/folder/a", b"a", 0o100644),
            ("chrome-mac-arm64/FOLDER/b", b"b", 0o100644),
        ]
    )
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        with pytest.raises(ValueError, match="parent directories"):
            chrome._zip_plan(archive, artifact)
    links = {PurePosixPath(f"chrome-mac-arm64/link{i}"): f"link{i+1}" for i in range(33)}
    with pytest.raises(ValueError, match="excessive link chain"):
        chrome._resolve_link(PurePosixPath("chrome-mac-arm64/link0"), links, "chrome-mac-arm64")


def test_no_browser_execution_or_resolution_is_part_of_installation() -> None:
    import ast

    tree = ast.parse(Path(chrome.__file__).read_text())
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports |= {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not imports.intersection(
        {"subprocess", "choreographer", "kaleido", "src.core.common.browser_selection"}
    )


def test_existing_lock_and_new_unowned_destination_remain_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact, network = _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))
    lock = tmp_path / f".chrome-install-{artifact.sha256}.lock"
    lock.write_text("other installer")
    with pytest.raises(Ring5Error):
        chrome.install_chrome(cache_directory=str(tmp_path))
    assert lock.read_text() == "other installer"
    network.assert_not_called()
    lock.unlink()
    original_extract = chrome._extract
    destination = tmp_path / f"{artifact.version}-{artifact.platform}-{artifact.sha256}"

    def extract_and_create_unowned(
        archive: Path, directory: Path, selected: chrome._Artifact
    ) -> None:
        original_extract(archive, directory, selected)
        destination.mkdir()
        (destination / "unrelated").write_bytes(b"preserve")

    monkeypatch.setattr(chrome, "_extract", extract_and_create_unowned)
    with pytest.raises(Ring5Error, match="owned receipt"):
        chrome.install_chrome(cache_directory=str(tmp_path))
    assert list(destination.iterdir()) == [destination / "unrelated"]
    assert (destination / "unrelated").read_bytes() == b"preserve"
    assert list(tmp_path.iterdir()) == [destination]


def test_receipt_rejects_noncanonical_boolean_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))
    executable = chrome.install_chrome(cache_directory=str(tmp_path))
    receipt = executable.parent.parent / "receipt.json"
    payload = json.loads(receipt.read_text())
    payload["schema_version"] = True
    receipt.write_text(json.dumps(payload))
    with pytest.raises(Ring5Error, match="receipt"):
        chrome.install_chrome(cache_directory=str(tmp_path))


def test_zip_header_flags_and_original_names_rejected_before_extraction() -> None:
    artifact = chrome._load_manifest()["linux64"]
    payload = _zip([(artifact.executable, b"inert", 0o100755)])
    for change in ("encrypted", "nul"):
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            info = archive.infolist()[0]
            if change == "encrypted":
                info.flag_bits |= 1
            else:
                info.orig_filename += "\x00hidden"
            with pytest.raises(ValueError, match="encoding"):
                chrome._zip_plan(archive, artifact)


def test_exact_graph_budget_remains_reusable_and_implicit_dirs_are_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = _zip([("chrome-linux64/chrome", b"inert executable", 0o100755)])
    artifact, network = _install_fixture(monkeypatch, content)
    monkeypatch.setattr(chrome, "_MAX_MEMBERS", 2)
    executable = chrome.install_chrome(cache_directory=str(tmp_path / "valid"))
    assert executable.read_bytes() == b"inert executable"
    assert chrome.install_chrome(cache_directory=str(tmp_path / "valid")) == executable
    network.assert_called_once_with(artifact.url)
    monkeypatch.setattr(chrome, "_MAX_MEMBERS", 1)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        with pytest.raises(ValueError, match="graph limit"):
            chrome._zip_plan(archive, artifact)


def test_member_and_expanded_link_paths_have_explicit_depth_bounds() -> None:
    from pathlib import PurePosixPath

    with pytest.raises(ValueError):
        chrome._safe_path("chrome-linux64/" + "/".join(["nested"] * 32), "chrome-linux64")
    links = {PurePosixPath("chrome-mac-arm64/link"): "/".join(["nested"] * 30)}
    with pytest.raises(ValueError):
        chrome._resolve_link(
            PurePosixPath("chrome-mac-arm64/link/tail/tail"), links, "chrome-mac-arm64"
        )


def test_installed_wheel_verifier_rejects_absent_packaged_manifest(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts import verify_installation

    monkeypatch.setenv("BROWSER_PATH", "")
    monkeypatch.setattr(
        chrome, "_load_manifest", MagicMock(side_effect=FileNotFoundError("manifest"))
    )
    assert verify_installation.main() == 1
    assert "Installation check failed: manifest" in capsys.readouterr().err


@pytest.mark.parametrize("failure", ["http", "deflate"])
def test_partial_http_and_corrupt_compression_are_typed_atomic_failures(
    failure: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from http.client import IncompleteRead

    original = chrome._load_manifest()["linux64"]
    content = io.BytesIO()
    with zipfile.ZipFile(content, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        info = zipfile.ZipInfo(original.executable)
        info.external_attr = 0o100755 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, b"inert browser data")
    payload = bytearray(content.getvalue())
    if failure == "deflate":
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            info = archive.infolist()[0]
            offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
        payload[offset] = 0xFF
    _, network = _install_fixture(monkeypatch, bytes(payload))
    if failure == "http":
        network.side_effect = IncompleteRead(b"partial")
    with pytest.raises(Ring5Error, match="Chrome installation failed"):
        chrome.install_chrome(cache_directory=str(tmp_path))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("separator", ["\r", "\n"])
def test_cli_rejects_multiline_output_paths_without_creating_cache(
    separator: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_fixture(monkeypatch, _zip(_inert_layout("linux64")))
    target = tmp_path / f"line{separator}break"
    assert cli.main(["install-chrome", "--cache-dir", str(target)]) == 2
    output = capsys.readouterr()
    assert output.out == "" and "one output line" in output.err
    assert not target.exists()


def test_archive_members_reject_nonportable_control_characters() -> None:
    with pytest.raises(ValueError):
        chrome._safe_path("chrome-linux64/line\nbreak", "chrome-linux64")
