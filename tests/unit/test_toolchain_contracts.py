"""Regression controls for dependency and architecture tooling."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts import check_architecture
from scripts.generate_oft_inventory import ROOT, validate_ci_oft_artifact


@pytest.mark.parametrize("reference", ["v6", "v99.1.0", "a" * 40])
def test_oft_workflow_accepts_action_identity_independently_of_version(
    tmp_path: Path, reference: str
) -> None:
    """New action tags and immutable commits preserve the artifact contract."""
    document = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    for step in document["jobs"]["oft"]["steps"]:
        if "uses" in step:
            step["uses"] = step["uses"].split("@")[0] + "@" + reference
    workflow = tmp_path / ".github/workflows/ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(yaml.safe_dump(document))
    assert validate_ci_oft_artifact(tmp_path) == []


@pytest.mark.parametrize("content", ["[", "null", "jobs: []", "jobs: {oft: {steps: null}}"])
def test_oft_workflow_rejects_malformed_structure(tmp_path: Path, content: str) -> None:
    """Broken YAML and absent job structure produce visible validation errors."""
    workflow = tmp_path / ".github/workflows/ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(content)
    assert validate_ci_oft_artifact(tmp_path)


@pytest.mark.parametrize(
    ("source_path", "source", "violation"),
    [
        ("src/core/example.py", "from src import web", "imports src.web"),
        ("src/core/example.py", "from ..web import pages", "imports src.web"),
        ("src/core/models/example.py", "from ..services import data_service", "core services"),
        ("src/parsing/example.py", "from ..core import services", "core services"),
        (
            "src/web/example.py",
            "from ..core.state import repository_state_manager",
            "concrete repository state manager",
        ),
    ],
)
def test_architecture_gate_resolves_relative_and_from_imports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_path: str,
    source: str,
    violation: str,
) -> None:
    """Equivalent import spellings cannot bypass a dependency boundary."""
    monkeypatch.setattr(check_architecture, "REPOSITORY_ROOT", tmp_path)
    path = tmp_path / source_path
    path.parent.mkdir(parents=True)
    path.write_text(source + "\n")
    assert any(violation in error for error in check_architecture.inspect_file(path))


@pytest.mark.parametrize("failure", [None, "checksum", "download"])
def test_oft_download_publishes_only_verified_content(
    tmp_path: Path, failure: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failed downloads and hashes cannot become trusted cached executables."""
    for command in ("make", "java", "curl", "sha256sum"):
        if shutil.which(command) is None:
            pytest.skip(f"{command} is required to exercise the Make download recipe")
    source = tmp_path / "source.jar"
    payload = b"test artifact, never executed"
    if failure != "download":
        source.write_bytes(payload)
    digest = "0" * 64 if failure == "checksum" else hashlib.sha256(payload).hexdigest()
    cache = tmp_path / "cache"
    foreign = tmp_path / "unrelated.jar"
    foreign.write_bytes(b"unrelated cached tool")
    monkeypatch.setenv("MAKEFLAGS", f"-- OFT_JAR={foreign}")
    result = subprocess.run(
        [
            "make",
            "oft-download",
            f"OFT_URL={source.as_uri()}",
            f"OFT_SHA256={digest}",
            f"OFT_CACHE_DIR={cache}",
            f"OFT_JAR={cache / 'verified.jar'}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert foreign.read_bytes() == b"unrelated cached tool"
    artifacts = list(cache.iterdir())
    if failure is None:
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(artifacts) == 1
        assert artifacts[0].read_bytes() == payload
    else:
        assert result.returncode != 0
        assert artifacts == []
