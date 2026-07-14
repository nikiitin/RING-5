#!/usr/bin/env python3
"""Validate documentation front matter, navigation, routes, redirects, and links."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts import check_doc_links
except ModuleNotFoundError:  # Direct execution adds scripts/, not the repository root, to sys.path.
    import check_doc_links  # type: ignore[import-not-found, no-redef]

ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs"
KEY_PATTERN = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*):(?:\s*(?P<value>.*))?$")
LIST_ITEM_PATTERN = re.compile(r"^\s+-\s+(?P<value>.+?)\s*$")
REQUIRED_FIELDS = ("layout", "title", "permalink")


@dataclass(frozen=True)
class Page:
    """Navigation and route data read from one published Markdown page."""

    path: Path
    title: str
    route: str
    parent: str | None
    grand_parent: str | None
    has_children: bool
    redirects: tuple[str, ...]


def published_markdown(docs_root: Path) -> list[Path]:
    """Return Markdown pages included in the Jekyll site."""
    return sorted(path for path in docs_root.rglob("*.md") if path != docs_root / "README.md")


def _scalar(value: str) -> str:
    """Strip matching YAML quotes from the front-matter subset we support."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_front_matter(path: Path) -> tuple[dict[str, str | list[str]], list[str]]:
    """Parse the scalar/list YAML subset used by documentation front matter."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, [f"{path}: missing opening front matter delimiter"]

    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return {}, [f"{path}: missing closing front matter delimiter"]

    fields: dict[str, str | list[str]] = {}
    failures: list[str] = []
    list_key: str | None = None
    for line_number, line in enumerate(lines[1:end], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item_match = LIST_ITEM_PATTERN.match(line)
        if item_match and list_key is not None:
            current = fields[list_key]
            if isinstance(current, list):
                current.append(_scalar(item_match.group("value")))
            continue

        key_match = KEY_PATTERN.match(line)
        if key_match:
            key = key_match.group("key")
            raw_value = key_match.group("value") or ""
            if raw_value:
                fields[key] = _scalar(raw_value)
                list_key = None
            else:
                fields[key] = []
                list_key = key
            continue

        failures.append(f"{path}:{line_number}: unsupported front matter syntax")
        list_key = None
    return fields, failures


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


def load_pages(docs_root: Path) -> tuple[list[Page], list[str]]:
    """Load published pages and report invalid required front matter."""
    pages: list[Page] = []
    failures: list[str] = []
    for path in published_markdown(docs_root):
        fields, parse_failures = parse_front_matter(path)
        failures.extend(parse_failures)
        if parse_failures:
            continue
        relative = path.relative_to(docs_root)
        missing = [field for field in REQUIRED_FIELDS if not fields.get(field)]
        if missing:
            failures.append(f"{relative}: missing required front matter: {', '.join(missing)}")
            continue
        if any(not isinstance(fields[field], str) for field in REQUIRED_FIELDS):
            failures.append(f"{relative}: required front matter fields must be scalars")
            continue

        redirects_value = fields.get("redirect_from", [])
        if not isinstance(redirects_value, list):
            failures.append(f"{relative}: redirect_from must be a YAML list")
            continue
        parent_value = fields.get("parent")
        grand_parent_value = fields.get("grand_parent")
        if parent_value is not None and not isinstance(parent_value, str):
            failures.append(f"{relative}: parent must be a scalar")
            continue
        if grand_parent_value is not None and not isinstance(grand_parent_value, str):
            failures.append(f"{relative}: grand_parent must be a scalar")
            continue

        pages.append(
            Page(
                path=relative,
                title=str(fields["title"]),
                route=str(fields["permalink"]),
                parent=parent_value,
                grand_parent=grand_parent_value,
                has_children=str(fields.get("has_children", "false")).lower() == "true",
                redirects=tuple(redirects_value),
            )
        )
    return pages, failures


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

    redirect_owners: dict[str, Page] = {}
    for page in pages:
        for redirect in page.redirects:
            route_failure = _route_failure(redirect)
            if route_failure:
                failures.append(f"{page.path}: redirect {redirect!r} {route_failure}")
                continue
            canonical_owner = by_route.get(redirect)
            if canonical_owner:
                failures.append(
                    f"{page.path}: redirect {redirect!r} conflicts with {canonical_owner.path}"
                )
            previous_owner = redirect_owners.get(redirect)
            if previous_owner:
                failures.append(
                    f"{page.path}: duplicate redirect {redirect!r} also used by "
                    f"{previous_owner.path}"
                )
            else:
                redirect_owners[redirect] = page
            if page.route not in by_route:
                failures.append(f"{page.path}: redirect target {page.route!r} is not resolvable")
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
