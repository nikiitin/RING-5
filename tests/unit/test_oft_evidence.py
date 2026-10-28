"""Tests for source-level OpenFastTrace evidence markers."""

from pathlib import Path
from typing import Any
import zipfile

import pytest

from scripts.oft_evidence import (
    collect_documentation_markers,
    collect_evidence_markers,
    collect_python_markers,
    evidence_source_paths,
    validate_source_evidence,
)


def _source_tag(artifact_type: str) -> str:
    return f"[{artifact_type}->req~ring5.sample.execute~1]"


def test_python_markers_resolve_to_the_smallest_enclosing_symbol(tmp_path: Path) -> None:
    """A marker inside a method resolves to its qualified method name."""
    path = tmp_path / "module.py"
    path.write_text(
        "class Service:\n"
        "    def execute(self):\n"
        f"        # {_source_tag('impl')}\n"
        "        return True\n",
        encoding="utf-8",
    )

    markers = collect_python_markers(tmp_path, path)

    assert len(markers) == 1
    assert markers[0].reference == "module.py::Service.execute"
    assert markers[0].line == 3


def test_documentation_markers_resolve_to_the_preceding_heading(tmp_path: Path) -> None:
    """A hidden user-manual item retains its document section locator."""
    path = tmp_path / "guide.md"
    path.write_text(
        "# Guide\n\n"
        "## Execute safely\n\n"
        "<!--\n"
        "`uman~ring5.sample.execute.documentation~1`\n\n"
        "Covers:\n"
        "- req~ring5.sample.execute~1\n"
        "-->\n",
        encoding="utf-8",
    )

    markers = collect_documentation_markers(tmp_path, path)

    assert len(markers) == 1
    assert markers[0].reference == "guide.md#execute-safely"
    assert markers[0].line == 6


def test_validation_requires_exact_registered_markers(tmp_path: Path) -> None:
    """Every evidence reference must resolve to a matching native marker."""
    (tmp_path / "app.py").write_text(
        "def execute():\n" f"    # {_source_tag('impl')}\n" "    return True\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_execute.py").write_text(
        "def test_execute():\n" f"    # {_source_tag('test')}\n" "    assert True\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "# Guide\n\n"
        "<!--\n"
        "`uman~ring5.sample.execute.documentation~1`\n\n"
        "Covers:\n"
        "- req~ring5.sample.execute~1\n"
        "-->\n",
        encoding="utf-8",
    )
    inventory: dict[str, Any] = {
        "features": [
            {
                "id": "sample.execute",
                "revision": 1,
                "evidence": {
                    "implementation": ["app.py::execute"],
                    "tests": ["tests/test_execute.py::test_execute"],
                    "documentation": ["docs/guide.md#guide"],
                },
            }
        ]
    }

    assert validate_source_evidence(inventory, tmp_path) == []

    inventory["features"][0]["evidence"]["tests"] = ["tests/test_execute.py"]
    errors = validate_source_evidence(inventory, tmp_path)
    assert any("lacks a precise locator" in error for error in errors)
    assert any("unregistered test marker" in error for error in errors)


@pytest.mark.parametrize("suite", ["e2e", "visual"])
def test_diagnostic_archives_and_extracted_sources_never_supply_evidence(
    tmp_path: Path, suite: str
) -> None:
    """Retained browser diagnostics cannot add or replace current evidence."""
    current = tmp_path / "tests" / "current.py"
    current.parent.mkdir()
    current.write_text(f"def test_current():\n    # {_source_tag('test')}\n    pass\n")
    diagnostics = tmp_path / "tests" / suite / "artifacts"
    diagnostics.mkdir(parents=True)
    raw = diagnostics / "historical.py"
    raw.write_text("invalid Python snapshot!\n")
    manual = diagnostics / "historical.md"
    manual.write_text("# Historical diagnostic\n")
    archive = diagnostics / "trace.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("src/historical.py", current.read_text())
    preserved = {path: path.read_bytes() for path in (raw, manual, archive)}

    assert evidence_source_paths(tmp_path) == (current,)
    assert [marker.reference for marker in collect_evidence_markers(tmp_path)] == [
        "tests/current.py::test_current"
    ]
    assert {path: path.read_bytes() for path in preserved} == preserved


def test_current_source_enumeration_works_without_git_and_discovers_new_files(
    tmp_path: Path,
) -> None:
    """Only the current Python/manual roots are used, including newly added files."""
    names = (
        "app.py",
        "ring5/public.py",
        "src/domain.py",
        "scripts/tool.py",
        "tests/unit/artifacts/current.py",
        "docs/guide.md",
        "spec/oft/README.md",
        "spec/oft/discovery-audit.md",
    )
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    (tmp_path / "tests" / "fixture.md").write_text("not a current manual root")
    assert not (tmp_path / ".git").exists()
    assert set(evidence_source_paths(tmp_path)) == {tmp_path / name for name in names}
    added = tmp_path / "src" / "new module.py"
    added.write_text("")
    assert added in evidence_source_paths(tmp_path)
    assert evidence_source_paths(tmp_path) == evidence_source_paths(tmp_path)
