"""Principle compliance: UI strings must use 'Download' not 'Export'.

Step 37 renamed all user-facing 'Export' labels to 'Download'.
This test guards against regressions.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, Tuple

# Files known to have internal/docstring uses of "export" that are acceptable
_INTERNAL_EXPORT_MODULES = {
    "export/__init__.py",
    "export/presets/__init__.py",
    "export/presets/preset_schema.py",
    "export/presets/preset_manager.py",
    "download_section.py",
    "plot_service.py",
    "data_components.py",
    "portfolio_migrator.py",
}


def _is_internal_module(path: Path) -> bool:
    """Check if a file is on the internal-export-use allow-list."""
    posix = path.as_posix()
    return any(posix.endswith(mod) for mod in _INTERNAL_EXPORT_MODULES)


def _find_ui_export_strings(root: Path) -> List[Tuple[Path, int, str]]:
    """Scan web layer Python files for user-facing 'Export' string literals.

    Returns list of (file, line_number, string_content) tuples.
    """
    violations: List[Tuple[Path, int, str]] = []
    # Only check UI-related directories
    ui_dirs = [
        root / "src" / "web" / "pages" / "ui" / "components",
        root / "src" / "web" / "pages" / "ui" / "plotting",
    ]

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

            for node in ast.walk(tree):
                # Check string constants (labels, button text, etc.)
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    value = node.value
                    # Look for "Export" as a user-facing word (not in
                    # variable names or internal identifiers)
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
