"""Tests for source-level OpenFastTrace evidence markers."""

from pathlib import Path
from typing import Any

from scripts.oft_evidence import (
    collect_documentation_markers,
    collect_python_markers,
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
