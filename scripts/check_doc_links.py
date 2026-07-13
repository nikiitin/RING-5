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
REPOSITORY_PATH_PATTERN = re.compile(
    r"`((?:src|ring5|tests|scripts|docs|\.agents|\.github)/[^`\s]+)`"
)
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel"}
RAW_PATH_EXEMPT_FILES = {ROOT / "docs/developer-guide/architecture/history.md"}
ILLUSTRATIVE_PATHS = {
    "src/parsing/my_sim/__init__.py",
    "src/parsing/sniper/__init__.py",
    "src/parsing/sniper/impl/sniper_parser_api.py",
    "src/web/components/plotting/settings/watermark_settings.py",
    "src/web/rendering/figure_spec_to_bokeh.py",
    "src/web/rendering/trace_to_bokeh.py",
    "src/core/services/shapers/impl/cumulative_sum.py",
    "src/web/components/shapers/cumulative_sum_config.py",
    "tests/data/synthetic/",
    "tests/ui_unit/test_interpolator_logic.py",
    "tests/ui_unit/test_watermark_settings.py",
    "tests/unit/test_cumulative_sum.py",
    "tests/unit/test_cumulative_sum_config.py",
}
GENERATED_REPOSITORY_PATHS = {
    "tests/data",
    "tests/data/results-micro26-sens",
}


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


def repository_path_targets(path: Path) -> Iterator[tuple[int, str]]:
    """Yield current repository paths written as inline code.

    Architecture history is exempt because it deliberately records removed
    layouts. Wildcards and template placeholders are not concrete paths and
    are ignored.
    """
    if path in RAW_PATH_EXEMPT_FILES:
        return
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for match in REPOSITORY_PATH_PATTERN.finditer(line):
            target = match.group(1).rstrip(".,;:)")
            target = target.split("::", 1)[0]
            target = re.sub(r":\d+.*$", "", target)
            if any(marker in target for marker in ("*", "{", "}", "<", ">", "...")):
                continue
            yield line_number, target


def main() -> int:
    """Report broken relative links and return a nonzero status when found."""
    failures: list[str] = []
    for path in sorted(markdown_files()):
        for line_number, target in relative_targets(path):
            if not resolves(path, target):
                relative = path.relative_to(ROOT)
                failures.append(f"{relative}:{line_number}: missing target {target!r}")
        for line_number, target in repository_path_targets(path):
            candidate = ROOT / target.rstrip("/")
            if target in ILLUSTRATIVE_PATHS or target.rstrip("/") in GENERATED_REPOSITORY_PATHS:
                continue
            if not candidate.exists() and not candidate.with_suffix(".py").exists():
                relative = path.relative_to(ROOT)
                failures.append(f"{relative}:{line_number}: missing repository path {target!r}")

    if failures:
        print("Documentation link check failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1

    print("Documentation link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
