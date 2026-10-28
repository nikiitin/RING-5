#!/usr/bin/env python3
"""Audit generated documentation routes, code parameters, and local references."""

from __future__ import annotations

import re
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scripts.documentation import DOCS_ROOT, ROOT, load_pages

SITE_ROOT = ROOT / "_site"
BASE_URL = "/RING-5"
REFERENCE_ATTRIBUTES = {"href", "src"}
PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
FENCE_RE = re.compile(r" {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)")


class ReferenceParser(HTMLParser):
    """Collect references and displayed fenced-code text from generated HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []
        self.code_blocks: list[str] = []
        self._pre_depth = 0
        self._code_depth = 0
        self._code_fragments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record references and enter code blocks without treating spans as text."""
        for name, value in attrs:
            if name in REFERENCE_ATTRIBUTES and value:
                self.references.append(value)
        if tag == "pre":
            self._pre_depth += 1
        elif tag == "code" and self._pre_depth:
            if not self._code_depth:
                self._code_fragments = []
            self._code_depth += 1

    def handle_endtag(self, tag: str) -> None:
        """Finish displayed code while leaving inline code outside the comparison."""
        if tag == "code" and self._code_depth:
            self._code_depth -= 1
            if not self._code_depth:
                self.code_blocks.append("".join(self._code_fragments))
                self._code_fragments = []
        elif tag == "pre" and self._pre_depth:
            self._pre_depth -= 1

    def handle_data(self, data: str) -> None:
        """Join displayed code across syntax-highlighting spans and decoded entities."""
        if self._pre_depth and self._code_depth:
            self._code_fragments.append(data)


def _fenced_code_blocks(markdown: str) -> Iterator[str]:
    """Read backtick and tilde fences using their opening delimiter's type and length."""
    fence: str | None = None
    lines: list[str] = []
    for line in markdown.splitlines():
        if fence is None:
            opening = FENCE_RE.fullmatch(line)
            if opening is None:
                continue
            candidate = opening.group("fence")
            if candidate[0] == "`" and "`" in opening.group("info"):
                continue
            fence = candidate
            lines = []
        elif re.fullmatch(rf" {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*", line):
            yield "\n".join(lines)
            fence = None
        else:
            lines.append(line)
    if fence is not None:
        yield "\n".join(lines)


def _placeholder_counts(code_blocks: Iterable[str]) -> Counter[str]:
    """Count literal unqualified parameters; dotted Jekyll variables remain renderable."""
    return Counter(name for block in code_blocks for name in PLACEHOLDER_RE.findall(block))


def generated_html(site_root: Path = SITE_ROOT) -> list[Path]:
    """Return every generated HTML file."""
    return sorted(site_root.rglob("*.html")) if site_root.exists() else []


def route_output(site_root: Path, route: str) -> Path:
    """Return the expected generated file for a trailing-slash route."""
    relative = route.strip("/")
    return site_root / relative / "index.html" if relative else site_root / "index.html"


def _reference_candidates(page: Path, reference: str, site_root: Path) -> Iterator[Path]:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return
    path = unquote(parsed.path)
    if path.startswith("//"):
        return
    if path.startswith("/"):
        if path == BASE_URL:
            path = "/"
        elif path.startswith(f"{BASE_URL}/"):
            path = path[len(BASE_URL) :]
        else:
            yield site_root / "__outside_baseurl__"
            return
        candidate = site_root / path.lstrip("/")
    else:
        candidate = page.parent / path

    resolved_site = site_root.resolve()
    try:
        candidate.resolve().relative_to(resolved_site)
    except ValueError:
        yield site_root / "__outside_site_root__"
        return

    if path.endswith("/"):
        yield candidate / "index.html"
        return
    yield candidate
    if not candidate.suffix:
        yield candidate.with_suffix(".html")
        yield candidate / "index.html"


def collect_failures(site_root: Path = SITE_ROOT, docs_root: Path = DOCS_ROOT) -> list[str]:
    """Return missing routes, lost code parameters, and broken local references."""
    failures: list[str] = []
    html_files = generated_html(site_root)
    if not html_files:
        return [f"{site_root}: no generated HTML files found; run make docs-build first"]

    pages, page_failures = load_pages(docs_root)
    failures.extend(page_failures)
    expected_placeholders: dict[Path, Counter[str]] = {}
    for source_page in pages:
        output = route_output(site_root, source_page.route)
        if not output.is_file():
            failures.append(f"{source_page.path}: generated route {source_page.route!r} is missing")
        else:
            source = (docs_root / source_page.path).read_text(encoding="utf-8")
            expected_placeholders[output] = _placeholder_counts(_fenced_code_blocks(source))

    for page in html_files:
        parser = ReferenceParser()
        parser.feed(page.read_text(encoding="utf-8"))
        missing = expected_placeholders.get(page, Counter()) - _placeholder_counts(
            parser.code_blocks
        )
        for name, count in sorted(missing.items()):
            relative = page.relative_to(site_root)
            failures.append(
                f"{relative}: generated fenced code lost {count} occurrence(s) "
                f"of literal parameter {{{{{name}}}}}"
            )
        for reference in parser.references:
            if reference.startswith(("#", "data:", "javascript:", "mailto:", "tel:")):
                continue
            candidates = list(_reference_candidates(page, reference, site_root))
            if candidates and not any(candidate.exists() for candidate in candidates):
                relative = page.relative_to(site_root)
                failures.append(f"{relative}: broken generated reference {reference!r}")
    return failures


def main() -> int:
    """Report generated-site failures and return a nonzero status when found."""
    failures = collect_failures()
    if failures:
        print("Generated documentation audit failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    html_files = generated_html()
    reference_count = 0
    for page in html_files:
        parser = ReferenceParser()
        parser.feed(page.read_text(encoding="utf-8"))
        reference_count += len(parser.references)
    print(
        f"Generated documentation audit passed: {len(html_files)} HTML pages, "
        f"{reference_count} references."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
