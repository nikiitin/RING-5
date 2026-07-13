"""Ensure user-facing UI strings use 'Download' rather than 'Export'."""

from __future__ import annotations

import ast
import re
from pathlib import Path

# Modules where "export" refers to an internal operation rather than a UI label.
_INTERNAL_EXPORT_MODULES = {
    "download_section.py",
    "plot_service.py",
    "data_components.py",
    "portfolio_migrator.py",
}


def _is_internal_module(path: Path) -> bool:
    """Check if a file is on the internal-export-use allow-list."""
    posix = path.as_posix()
    return any(posix.endswith(mod) for mod in _INTERNAL_EXPORT_MODULES)


def _find_ui_export_strings(root: Path) -> list[tuple[Path, int, str]]:
    """Scan web layer Python files for user-facing 'Export' string literals.

    Returns:
        File, line number, and string value for each violation.
    """
    violations: list[tuple[Path, int, str]] = []
    ui_dirs = [root / "src" / "web"]

    for ui_dir in ui_dirs:
        if not ui_dir.exists():
            continue
        for py_file in ui_dir.rglob("*.py"):
            if _is_internal_module(py_file):
                continue
            try:
                source = py_file.read_text()
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue

            docstrings = {
                id(node.body[0].value)
                for node in ast.walk(tree)
                if isinstance(
                    node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                )
                and node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            }
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and id(node) not in docstrings
                ):
                    value = node.value
                    if re.search(r"\bExport\b", value):
                        violations.append((py_file, node.lineno, value[:80]))
    return violations


class TestNoExportUIStrings:
    """Guard against 'Export' appearing in UI-facing strings."""

    def test_no_export_in_ui_labels(self) -> None:
        """UI components must use 'Download' not 'Export' in labels."""
        root = Path(__file__).resolve().parents[2]
        violations = _find_ui_export_strings(root)
        if violations:
            msg_lines = ["Found 'Export' in UI-facing strings:"]
            for path, lineno, text in violations:
                rel = path.relative_to(root)
                msg_lines.append(f"  {rel}:{lineno}: {text!r}")
            raise AssertionError("\n".join(msg_lines))
