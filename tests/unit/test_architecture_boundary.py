"""Tests for architecture boundary enforcement."""

import ast
from pathlib import Path

import pytest

# Root of the project
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_SRC_DIR = PROJECT_ROOT / "src" / "web"


def _collect_py_files(directory: Path) -> list[Path]:
    """Recursively collect all .py files under the given directory."""
    return sorted(directory.rglob("*.py"))


def _extract_imports(file_path: Path) -> list[tuple[int, str]]:
    """Parse a Python file with AST and return all import statements that reference src.parsing.

    Returns:
        List of (line_number, import_string) tuples for offending imports.
    """
    source = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        # If the file has a syntax error, skip it — other tests will catch that.
        return []

    violations: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src.parsing"):
                    violations.append((node.lineno, f"import {alias.name}"))

        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("src.parsing"):
                names = ", ".join(alias.name for alias in node.names)
                violations.append((node.lineno, f"from {node.module} import {names}"))

    return violations


class TestArchitectureBoundary:
    """Verify that the web layer does not directly import from the parsing layer."""

    def test_web_layer_has_no_parsing_imports(self) -> None:
        """Scan every .py file under src/web/ and assert none import from src.parsing."""
        assert WEB_SRC_DIR.is_dir(), f"Web source directory not found: {WEB_SRC_DIR}"

        py_files = _collect_py_files(WEB_SRC_DIR)
        assert py_files, f"No .py files found under {WEB_SRC_DIR}"

        all_violations: list[str] = []

        for py_file in py_files:
            violations = _extract_imports(py_file)
            for lineno, import_str in violations:
                relative = py_file.relative_to(PROJECT_ROOT)
                all_violations.append(f"  {relative}:{lineno} -> {import_str}")

        if all_violations:
            violation_report = "\n".join(all_violations)
            pytest.fail(
                f"Architecture violation: web layer must not import from parsing layer.\n"
                f"Found {len(all_violations)} violation(s):\n{violation_report}"
            )

    def test_web_directory_contains_python_files(self) -> None:
        """Sanity check: src/web/ exists and contains .py files (guards against wrong path)."""
        assert WEB_SRC_DIR.is_dir(), f"Expected directory: {WEB_SRC_DIR}"
        py_files = _collect_py_files(WEB_SRC_DIR)
        assert len(py_files) > 0, f"No Python files found in {WEB_SRC_DIR}"
