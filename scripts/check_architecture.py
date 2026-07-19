#!/usr/bin/env python3
"""Enforce architecture and unsafe-syntax rules using Python's AST."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_ROOTS = (REPOSITORY_ROOT / "ring5", REPOSITORY_ROOT / "src")


def import_names(node: ast.Import | ast.ImportFrom) -> set[str]:
    """Return absolute module names represented by an import node."""
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names}
    if node.level or not node.module:
        return set()
    return {node.module}


def is_under(path: Path, relative_root: str) -> bool:
    """Whether a source path is below a repository-relative directory."""
    try:
        path.relative_to(REPOSITORY_ROOT / relative_root)
    except ValueError:
        return False
    return True


def inspect_file(path: Path) -> list[str]:
    """Return architecture violations found in one Python file."""
    # [impl->req~ring5.quality.architecture-boundaries~1]
    relative = path.relative_to(REPOSITORY_ROOT)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
    except (OSError, SyntaxError) as exc:
        return [f"{relative}: could not parse: {exc}"]

    issues: list[str] = []
    for node in ast.walk(tree):
        location = f"{relative}:{getattr(node, 'lineno', 1)}"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = import_names(node)
            if is_under(path, "src/core") or is_under(path, "src/parsing"):
                if any(
                    module == "streamlit" or module.startswith("streamlit.") for module in modules
                ):
                    issues.append(f"{location}: domain/data layer imports Streamlit")
                if any(module == "src.web" or module.startswith("src.web.") for module in modules):
                    issues.append(f"{location}: domain/data layer imports src.web")
            if is_under(path, "src/core/models") or is_under(path, "src/parsing"):
                if any(
                    module == "src.core.services" or module.startswith("src.core.services.")
                    for module in modules
                ):
                    issues.append(f"{location}: models/parsing layer imports core services")
            if is_under(path, "src/web") and any(
                module == "src.core.state.repository_state_manager"
                or module.startswith("src.core.state.repository_state_manager.")
                for module in modules
            ):
                issues.append(f"{location}: web imports the concrete repository state manager")

        if isinstance(node, ast.Attribute) and node.attr == "session_state":
            if is_under(path, "src/core") or is_under(path, "src/parsing"):
                issues.append(f"{location}: domain/data layer accesses session_state")
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(f"{location}: bare except clause")
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and node.value.value is Ellipsis
        ):
            issues.append(f"{location}: ellipsis statement; use an explicit contract")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                issues.append(f"{location}: call to {node.func.id}()")
            for keyword in node.keywords:
                if keyword.arg == "inplace" and isinstance(keyword.value, ast.Constant):
                    if keyword.value.value is True:
                        issues.append(f"{location}: call uses inplace=True")
    return issues


def main() -> int:
    """Inspect production sources and return a process exit code."""
    # [impl->req~ring5.quality.architecture-boundaries~1]
    issues = [
        issue
        for root in PRODUCTION_ROOTS
        for path in root.rglob("*.py")
        for issue in inspect_file(path)
    ]
    if issues:
        print("Architecture check failed:", file=sys.stderr)
        for issue in issues:
            print(f"  {issue}", file=sys.stderr)
        return 1
    print("Architecture check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
