#!/usr/bin/env python3
"""Validate relative links in repository Markdown files."""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOC_ROOTS = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "AGENTS.md",
    ROOT / ".agents",
    ROOT / "docs",
)
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel"}


def markdown_files() -> Iterator[Path]:
    """Yield repository Markdown files covered by documentation checks."""
    for doc_root in DOC_ROOTS:
        if doc_root.is_file():
            yield doc_root
        elif doc_root.exists():
            yield from doc_root.rglob("*.md")


def relative_targets(path: Path) -> Iterator[tuple[int, str]]:
    """Yield line numbers and local link targets from *path*."""
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for match in LINK_PATTERN.finditer(line):
            raw_target = match.group(1).strip()
            if raw_target.startswith("<") and raw_target.endswith(">"):
                raw_target = raw_target[1:-1]
            target = raw_target.split(maxsplit=1)[0]
            parsed = urlsplit(target)
            if parsed.scheme in EXTERNAL_SCHEMES or target.startswith(("#", "/", "{{")):
                continue
            if parsed.path:
                yield line_number, unquote(parsed.path)


def resolves(path: Path, target: str) -> bool:
    """Return whether *target* resolves relative to *path*."""
    candidate = path.parent / target.rstrip("/")
    markdown_candidate = candidate.with_suffix(".md") if not candidate.suffix else candidate
    return candidate.exists() or markdown_candidate.exists() or (candidate / "index.md").exists()


def main() -> int:
    """Report broken relative links and return a nonzero status when found."""
    failures: list[str] = []
    for path in sorted(markdown_files()):
        for line_number, target in relative_targets(path):
            if not resolves(path, target):
                relative = path.relative_to(ROOT)
                failures.append(f"{relative}:{line_number}: missing target {target!r}")

    if failures:
        print("Documentation link check failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1

    print("Documentation link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
