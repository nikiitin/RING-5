#!/usr/bin/env python3
"""Audit generated documentation routes and local HTML references."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    from scripts.check_doc_structure import DOCS_ROOT, ROOT, load_pages
except ModuleNotFoundError:  # Direct execution adds scripts/ rather than the repository root.
    from check_doc_structure import DOCS_ROOT, ROOT, load_pages

SITE_ROOT = ROOT / "_site"
BASE_URL = "/RING-5"
REFERENCE_ATTRIBUTES = {"href", "src"}


class ReferenceParser(HTMLParser):
    """Collect link and asset references from generated HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record link and asset attributes from one opening HTML tag."""
        for name, value in attrs:
            if name in REFERENCE_ATTRIBUTES and value:
                self.references.append(value)


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
    """Return missing generated routes and broken local-reference failures."""
    failures: list[str] = []
    html_files = generated_html(site_root)
    if not html_files:
        return [f"{site_root}: no generated HTML files found; run make docs-build first"]

    pages, page_failures = load_pages(docs_root)
    failures.extend(page_failures)
    for page in pages:
        for route in (page.route, *page.redirects):
            output = route_output(site_root, route)
            if not output.is_file():
                failures.append(f"{page.path}: generated route {route!r} is missing")

    for page in html_files:
        parser = ReferenceParser()
        parser.feed(page.read_text(encoding="utf-8"))
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
