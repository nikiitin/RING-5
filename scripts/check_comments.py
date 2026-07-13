#!/usr/bin/env python3
"""Reject drafting artifacts and assistant-specific language in code comments."""

from __future__ import annotations

import ast
import re
import sys
import tokenize
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (ROOT / "app.py", ROOT / "ring5", ROOT / "scripts", ROOT / "src", ROOT / "tests")

PROHIBITED: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "assistant-specific reference",
        re.compile(r"\b(?:ChatGPT|Claude|Copilot)\b", re.IGNORECASE),
    ),
    (
        "internal milestone label",
        re.compile(
            r"\b(?:Theme-[A-Z]|Phase\s+\d+(?:\.\d+)?|audit\s+[A-Z]\d+|"
            r"Step\s+(?:[1-9]\d+|\d+\s+(?:fields?|features?))|"
            r"[A-Z]\d+\s+forward\s+path)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "drafting slogan",
        re.compile(r"\b(?:zero hallucination|scientific (?:integrity|safety))\b", re.IGNORECASE),
    ),
    (
        "test-process bookkeeping",
        re.compile(
            r"(?:\b(?:coverage[- ]boost|low[- ]coverage|branch coverage|"
            r"additional coverage|for coverage|TDD Ch\.|Rule \d+ compliance|"
            r"for brevity)\b|\d+%\s*(?:→|->)\s*\d+%|"
            r"targets? (?:the following )?(?:files?/)?lines?:)",
            re.IGNORECASE,
        ),
    ),
    (
        "test consolidation bookkeeping",
        re.compile(
            r"\b(?:consolidat(?:ed|es|ing) from|merges? \d+ original|AAA pattern)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "coverage implementation detail",
        re.compile(
            r"\b(?:uncovered (?:lines?|branches?|methods?)|targeting uncovered|"
            r"cover(?:s|ing)? [^.\n]* branches?|lines? \d+(?:[-–>,. ]+\d+)*)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "test scaffolding narration",
        re.compile(
            r"^(?:Arrange|Act|Assert)(?:\s*&\s*(?:Act|Assert))?(?:\s*[-:—].*)?$",
            re.IGNORECASE,
        ),
    ),
    (
        "decorative divider",
        re.compile(r"(?:^[=-]{5,}$|^[─━═]{2,}|[─━═]{3,}$)"),
    ),
    (
        "generated template marker",
        re.compile(
            r"(?:\b(?:Design Patterns|Last Modified|NEW ISSUES|YOU ARE HERE|WITH FIX)\b|"
            r"\b(?:PRIMARY|ONLY) mechanism\b|\bIssue #\d+\b|\bAdheres to SRP\b)",
            re.IGNORECASE,
        ),
    ),
)

PROHIBITED_TEST_SUFFIXES = (
    "_branches",
    "_comprehensive",
    "_coverage",
    "_enhanced",
    "_extras",
    "_new",
)


def source_files() -> Iterator[Path]:
    """Yield Python files in the application and test trees."""
    for source_root in SOURCE_ROOTS:
        if source_root.is_file():
            yield source_root
        else:
            yield from source_root.rglob("*.py")


def comment_tokens(path: Path) -> Iterator[tuple[int, str]]:
    """Yield line numbers and text for comments in *path*."""
    with path.open("rb") as source:
        for token in tokenize.tokenize(source.readline):
            if token.type == tokenize.COMMENT and not token.string.startswith("#!"):
                yield token.start[0], token.string[1:].strip()


def docstring_tokens(path: Path) -> Iterator[tuple[int, str]]:
    """Yield line numbers and text for module, class, and function docstrings."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            docstring = ast.get_docstring(node, clean=False)
            if docstring:
                yield getattr(node, "lineno", 1), docstring


def main() -> int:
    """Report prohibited comments and return a nonzero status when found."""
    failures: list[str] = []
    for path in sorted(source_files()):
        if path.is_relative_to(ROOT / "tests") and path.stem.endswith(PROHIBITED_TEST_SUFFIXES):
            relative = path.relative_to(ROOT)
            failures.append(f"{relative}: behavior-neutral test filename")
        prose = (*comment_tokens(path), *docstring_tokens(path))
        for line_number, comment in prose:
            for description, pattern in PROHIBITED:
                if pattern.search(comment):
                    relative = path.relative_to(ROOT)
                    failures.append(f"{relative}:{line_number}: {description}: {comment}")

    if failures:
        print("Comment audit failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1

    print("Comment audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
