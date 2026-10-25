"""Read the canonical metadata shared by documentation checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

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

        if "redirect_from" in fields:
            failures.append(f"{relative}: redirect_from is unsupported; use one permalink")
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
            )
        )
    return pages, failures
