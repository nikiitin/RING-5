#!/usr/bin/env python3
"""Validate public production docstrings and documented parameter names."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOTS = ("ring5", "src", "scripts")
DEFINITION_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
PublicDefinition = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
ARGUMENT_RE = re.compile(r"\s{4}(\*{0,2}[A-Za-z_]\w*):")


def public_definitions(tree: ast.AST) -> list[PublicDefinition]:
    """Return public module members and public class members."""
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, DEFINITION_TYPES)
        and not node.name.startswith("_")
        and isinstance(parents.get(node), (ast.Module, ast.ClassDef))
    ]


def signature_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Return documented parameter names expected for a function signature."""
    parameters = {
        argument.arg
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
        if argument.arg not in {"self", "cls"}
    }
    if node.args.vararg:
        parameters.add(node.args.vararg.arg)
    if node.args.kwarg:
        parameters.add(node.args.kwarg.arg)
    return parameters


def documented_parameters(docstring: str) -> set[str] | None:
    """Return names in a Google-style ``Args`` section, or ``None`` when absent."""
    lines = docstring.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == "Args:") + 1
    except StopIteration:
        return None

    parameters: set[str] = set()
    for line in lines[start:]:
        if line and not line[0].isspace():
            break
        match = ARGUMENT_RE.match(line)
        if match:
            parameters.add(match.group(1).lstrip("*"))
    return parameters


def main() -> int:
    """Validate production sources and return a process exit code."""
    issues: list[str] = []
    for root_name in SOURCE_ROOTS:
        for path in (REPOSITORY_ROOT / root_name).rglob("*.py"):
            relative = path.relative_to(REPOSITORY_ROOT)
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
            except (OSError, SyntaxError) as exc:
                issues.append(f"{relative}: could not parse: {exc}")
                continue

            for node in public_definitions(tree):
                docstring = ast.get_docstring(node)
                location = f"{relative}:{node.lineno} {node.name}"
                if not docstring:
                    issues.append(f"{location}: missing public docstring")
                    continue
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    documented = documented_parameters(docstring)
                    expected = signature_parameters(node)
                    if root_name == "ring5" and expected and documented is None:
                        issues.append(
                            f"{location}: public package function must document Args "
                            f"{sorted(expected)}"
                        )
                        continue
                    if documented is not None:
                        if documented != expected:
                            issues.append(
                                f"{location}: Args documents {sorted(documented)}, "
                                f"signature has {sorted(expected)}"
                            )

    if issues:
        print("Public documentation check failed:", file=sys.stderr)
        for issue in issues:
            print(f"  {issue}", file=sys.stderr)
        return 1
    print("Public documentation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
