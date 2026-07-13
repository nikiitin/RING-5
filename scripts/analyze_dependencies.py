#!/usr/bin/env python3
"""Compare production imports with dependencies declared in ``pyproject.toml``."""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOTS = (REPOSITORY_ROOT / "ring5", REPOSITORY_ROOT / "src")
SOURCE_FILES = (REPOSITORY_ROOT / "app.py",)
INTERNAL_MODULES = {"ring5", "src"}

# Distribution and import names usually match after replacing dashes with underscores.
# Record the few explicit exceptions here.
IMPORT_NAMES = {
    "pandas-stubs": {"pandas"},
    "pytest-cov": {"pytest_cov"},
    "pytest-xdist": {"xdist"},
    "pytest-playwright": {"pytest_playwright"},
    "types-jsonschema": {"jsonschema"},
}


def production_files() -> list[Path]:
    """Return Python files that form the installed application."""
    files = [path for root in SOURCE_ROOTS for path in root.rglob("*.py")]
    files.extend(path for path in SOURCE_FILES if path.exists())
    return sorted(files)


def imported_modules(path: Path) -> set[str]:
    """Return top-level modules imported by a Python source file.

    Args:
        path: Python source file to parse.

    Raises:
        SyntaxError: The source file cannot be parsed.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module.partition(".")[0])
    return modules


def declared_dependencies() -> set[str]:
    """Return normalized production dependency names from ``pyproject.toml``."""
    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    return {
        re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].strip().lower()
        for requirement in project.get("dependencies", [])
    }


def expected_imports(distribution: str) -> set[str]:
    """Return import names provided by a declared distribution."""
    return IMPORT_NAMES.get(distribution, {distribution.replace("-", "_")})


def main() -> int:
    """Print dependency discrepancies and return a process exit code."""
    files = production_files()
    imported: set[str] = set()
    failures: list[str] = []
    for path in files:
        try:
            imported.update(imported_modules(path))
        except (OSError, SyntaxError) as exc:
            failures.append(f"{path.relative_to(REPOSITORY_ROOT)}: {exc}")

    if failures:
        print("Could not inspect the following files:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 2

    third_party = imported - sys.stdlib_module_names - INTERNAL_MODULES
    declared = declared_dependencies()
    covered = {module for distribution in declared for module in expected_imports(distribution)}
    undeclared = sorted(third_party - covered)

    source_text = "\n".join(path.read_text(encoding="utf-8") for path in files)
    unused = sorted(
        distribution
        for distribution in declared
        if not (expected_imports(distribution) & imported) and distribution not in source_text
    )

    print(f"Inspected {len(files)} production Python files.")
    print(f"Declared runtime dependencies: {', '.join(sorted(declared))}")
    if unused:
        print(f"Potentially unused declarations: {', '.join(unused)}")
    if undeclared:
        print(f"Undeclared third-party imports: {', '.join(undeclared)}", file=sys.stderr)
        return 1
    print("No undeclared production imports found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
