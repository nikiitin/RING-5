#!/usr/bin/env python3
"""Validate documentation front matter, navigation, routes, and links."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts import check_doc_links
from scripts.documentation import DOCS_ROOT, Page, load_pages


def _route_failure(route: str) -> str | None:
    """Return a route-format failure or None."""
    if not route.startswith("/"):
        return "must start with '/'"
    if route != "/" and not route.endswith("/"):
        return "must end with '/'"
    if "//" in route:
        return "must not contain an empty path segment"
    if any(marker in route for marker in ("#", "?", "\\")):
        return "must not contain a fragment, query, or backslash"
    return None


def validate_structure(docs_root: Path = DOCS_ROOT) -> list[str]:
    """Return documentation front-matter, navigation, and route failures."""
    pages, failures = load_pages(docs_root)
    by_title: dict[str, Page] = {}
    by_route: dict[str, Page] = {}

    for page in pages:
        route_failure = _route_failure(page.route)
        if route_failure:
            failures.append(f"{page.path}: permalink {page.route!r} {route_failure}")
        previous_title = by_title.get(page.title)
        if previous_title:
            failures.append(
                f"{page.path}: duplicate title {page.title!r} also used by {previous_title.path}"
            )
        else:
            by_title[page.title] = page
        previous_route = by_route.get(page.route)
        if previous_route:
            failures.append(
                f"{page.path}: duplicate route {page.route!r} also used by {previous_route.path}"
            )
        else:
            by_route[page.route] = page

    for page in pages:
        if page.parent is None:
            if page.grand_parent is not None:
                failures.append(f"{page.path}: grand_parent requires parent")
            continue
        parent = by_title.get(page.parent)
        if parent is None:
            failures.append(f"{page.path}: unknown parent {page.parent!r}")
            continue
        if not parent.has_children:
            failures.append(f"{page.path}: parent {page.parent!r} does not set has_children: true")
        if page.grand_parent != parent.parent:
            failures.append(
                f"{page.path}: grand_parent {page.grand_parent!r} does not match "
                f"parent {page.parent!r}'s parent {parent.parent!r}"
            )

    return failures


def main() -> int:
    """Report structural, local-link, and repository-path failures."""
    failures = validate_structure()
    failures.extend(check_doc_links.collect_failures())
    if failures:
        print("Documentation structure check failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("Documentation structure and link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
