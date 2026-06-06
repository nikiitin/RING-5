"""Tests for architecture boundary enforcement."""

import ast
from pathlib import Path

import pytest

# Root of the project
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
WEB_SRC_DIR = SRC_DIR / "web"
MODELS_SRC_DIR = SRC_DIR / "core" / "models"
PARSING_SRC_DIR = SRC_DIR / "parsing"


def _imports_with_prefix(file_path: Path, prefix: str) -> list[tuple[int, str]]:
    """Return (lineno, import_string) for every import whose module starts with *prefix*."""
    source = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(prefix):
                    hits.append((node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith(prefix):
                names = ", ".join(alias.name for alias in node.names)
                hits.append((node.lineno, f"from {node.module} import {names}"))
    return hits


def _assert_no_imports(directory: Path, prefix: str, rule: str) -> None:
    """Fail if any .py under *directory* imports a module starting with *prefix*."""
    assert directory.is_dir(), f"Directory not found: {directory}"
    py_files = _collect_py_files(directory)
    assert py_files, f"No .py files found under {directory}"

    violations: list[str] = []
    for py_file in py_files:
        for lineno, import_str in _imports_with_prefix(py_file, prefix):
            violations.append(f"  {py_file.relative_to(PROJECT_ROOT)}:{lineno} -> {import_str}")

    if violations:
        report = "\n".join(violations)
        pytest.fail(f"Architecture violation: {rule}\nFound {len(violations)}:\n{report}")


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


class TestDependencyDirection:
    """Verify the one-directional layer rule (Web -> Core <- Parsing) — the
    subtler edges the simpler greps miss (audit S1/S2/S3)."""

    def test_models_layer_has_no_services_imports(self) -> None:
        """src/core/models is the shared data language and depends on nobody —
        it must never import from src.core.services (audit S1)."""
        _assert_no_imports(
            MODELS_SRC_DIR,
            "src.core.services",
            "models layer must not import from the services layer",
        )

    def test_parsing_layer_has_no_core_services_imports(self) -> None:
        """Parsing (Layer A) must not import core services (Layer B) (audit S2)."""
        _assert_no_imports(
            PARSING_SRC_DIR,
            "src.core.services",
            "parsing layer must not import from core.services",
        )

    def test_web_layer_has_no_concrete_state_manager_imports(self) -> None:
        """Web must depend on the StateManager protocol (via the facade), never on
        the concrete RepositoryStateManager implementation (audit S3)."""
        _assert_no_imports(
            WEB_SRC_DIR,
            "src.core.state.repository_state_manager",
            "web must not import the concrete RepositoryStateManager",
        )
