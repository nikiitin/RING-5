#!/usr/bin/env python3
"""Analyze project dependencies and find unused packages."""

import ast
import sys
from pathlib import Path
from typing import Set

# Mapping from import name to package name
IMPORT_TO_PACKAGE = {
    "pandas": "pandas",
    "pd": "pandas",
    "numpy": "numpy",
    "np": "numpy",
    "matplotlib": "matplotlib",
    "plt": "matplotlib",
    "seaborn": "seaborn",
    "sns": "seaborn",
    "streamlit": "streamlit",
    "st": "streamlit",
    "plotly": "plotly",
    "scipy": "scipy",
    "jsonschema": "jsonschema",
    "tqdm": "tqdm",
    "openpyxl": "openpyxl",
}

# Dev-only packages (used for development, not runtime)
DEV_PACKAGES = {
    "pytest",
    "black",
    "flake8",
    "mypy",
    "pytest-cov",
    "pandas-stubs",
    "types-jsonschema",
    "types-tqdm",
    "scipy-stubs",
}


def extract_imports_from_file(file_path: Path) -> Set[str]:
    """Extract all import statements from a Python file."""
    imports = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get base package (before first dot)
                    base = alias.name.split(".")[0]
                    imports.add(base)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Get base package (before first dot)
                    base = node.module.split(".")[0]
                    imports.add(base)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)
    return imports


def find_all_python_files(root: Path) -> list[Path]:
    """Find all Python files in src/ directory."""
    return list(root.glob("src/**/*.py"))


def map_imports_to_packages(imports: Set[str]) -> Set[str]:
    """Map import names to package names."""
    packages = set()
    for imp in imports:
        # Check if it's a known mapping
        if imp in IMPORT_TO_PACKAGE:
            packages.add(IMPORT_TO_PACKAGE[imp])
        # Check if it's a standard library import (skip those)
        elif imp in [
            "os",
            "sys",
            "re",
            "json",
            "pathlib",
            "typing",
            "logging",
            "subprocess",
            "concurrent",
            "functools",
            "dataclasses",
            "abc",
            "copy",
            "io",
            "tempfile",
            "argparse",
        ]:
            continue
        # Check if it's a project import
        elif imp in ["src", "components_library"]:
            continue
        else:
            # Assume it's a third-party package
            packages.add(imp)
    return packages


def main():
    root = Path(__file__).parent.parent

    # Find all Python files
    python_files = find_all_python_files(root)
    print(f"📂 Analyzing {len(python_files)} Python files...\n")

    # Extract all imports
    all_imports = set()
    for file in python_files:
        imports = extract_imports_from_file(file)
        all_imports.update(imports)

    # Map to package names
    used_packages = map_imports_to_packages(all_imports)

    # Production dependencies from pyproject.toml
    declared_prod = {
        "tqdm",
        "pytest",  # Actually used in tests
        "pandas",
        "scipy",
        "numpy",
        "matplotlib",
        "seaborn",
        "jsonschema",
        "streamlit",
        "openpyxl",
        "plotly",
    }

    print("✅ USED packages (found in code):")
    print("-" * 50)
    for pkg in sorted(used_packages):
        print(f"  • {pkg}")

    print("\n📦 DECLARED production dependencies:")
    print("-" * 50)
    for pkg in sorted(declared_prod):
        status = "✓" if pkg in used_packages else "?"
        print(f"  {status} {pkg}")

    print("\n🔍 Analysis:")
    print("-" * 50)

    # Find potentially unused
    unused = declared_prod - used_packages
    if unused:
        print("\n⚠️  Potentially UNUSED packages:")
        for pkg in sorted(unused):
            print(f"  • {pkg}")
        print("\n  Note: Some packages may be:")
        print("    - Required transitively")
        print("    - Used in tests only")

    # Find undeclared
    undeclared = used_packages - declared_prod - DEV_PACKAGES
    if undeclared:
        print("\n⚠️  Used but NOT declared in pyproject.toml:")
        for pkg in sorted(undeclared):
            print(f"  • {pkg}")
        print("\n  These might be:")
        print("    - Transitive dependencies (installed automatically)")
        print("    - Should be added to pyproject.toml")

    # Special checks
    print("\n💡 Special notes:")
    print("-" * 50)

    if "openpyxl" not in used_packages:
        print("  • openpyxl: Not imported directly (used by pandas for Excel)")

    if "pytest" in used_packages:
        print("  • pytest: Used in test files (keep in dependencies)")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
