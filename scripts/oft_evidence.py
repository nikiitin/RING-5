"""Resolve and validate source-level OpenFastTrace evidence markers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, cast

_PYTHON_MARKER = re.compile(
    r"\[(impl|test)->req~ring5\.([a-z0-9]+(?:[.-][a-z0-9]+)*)~([1-9][0-9]*)\]"
)
_DOCUMENTATION_ITEM = re.compile(
    r"`uman~ring5\.([a-z0-9]+(?:[.-][a-z0-9]+)*)\.documentation~([1-9][0-9]*)`"
)
_DOCUMENTATION_COVER = re.compile(r"req~ring5\.([a-z0-9]+(?:[.-][a-z0-9]+)*)~([1-9][0-9]*)")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class EvidenceMarker:
    """A source marker associated with a stable code or documentation locator."""

    artifact_type: str
    requirement_id: str
    revision: int
    path: str
    locator: str
    line: int

    @property
    def reference(self) -> str:
        """Return the inventory reference represented by this marker."""
        separator = "#" if self.artifact_type == "uman" else "::"
        return f"{self.path}{separator}{self.locator}"


def _python_symbols(source: str, path: Path) -> list[tuple[str, int, int]]:
    """Return qualified Python symbols and their source spans."""
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise ValueError(f"cannot parse Python evidence file {path}: {exc}") from exc

    symbols: list[tuple[str, int, int]] = []

    def visit(body: list[ast.stmt], parents: tuple[str, ...] = ()) -> None:
        for node in body:
            if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            qualified = ".".join((*parents, node.name))
            symbols.append((qualified, node.lineno, node.end_lineno or node.lineno))
            visit(node.body, (*parents, node.name))

    visit(tree.body)
    return symbols


def _smallest_enclosing_symbol(symbols: list[tuple[str, int, int]], line_number: int) -> str | None:
    candidates = [symbol for symbol in symbols if symbol[1] <= line_number <= symbol[2]]
    if not candidates:
        return None
    return min(candidates, key=lambda symbol: symbol[2] - symbol[1])[0]


def collect_python_markers(root: Path, path: Path) -> list[EvidenceMarker]:
    """Collect implementation and test markers from one Python file."""
    source = path.read_text(encoding="utf-8")
    symbols = _python_symbols(source, path)
    relative = path.relative_to(root).as_posix()
    markers: list[EvidenceMarker] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        for match in _PYTHON_MARKER.finditer(line):
            locator = _smallest_enclosing_symbol(symbols, line_number)
            if locator is None:
                raise ValueError(
                    f"{relative}:{line_number}: OFT source marker is not inside a Python symbol"
                )
            markers.append(
                EvidenceMarker(
                    artifact_type=match.group(1),
                    requirement_id=match.group(2),
                    revision=int(match.group(3)),
                    path=relative,
                    locator=locator,
                    line=line_number,
                )
            )
    return markers


def _heading_slug(title: str) -> str:
    """Return the stable heading slug used by documentation references."""
    text = re.sub(r"<[^>]+>", "", title).strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"[-\s]+", "-", text).strip("-")


def collect_documentation_markers(root: Path, path: Path) -> list[EvidenceMarker]:
    """Collect hidden user-manual specification items from one Markdown file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    relative = path.relative_to(root).as_posix()
    current_heading: str | None = None
    seen_slugs: dict[str, int] = {}
    markers: list[EvidenceMarker] = []
    for index, line in enumerate(lines):
        heading = _HEADING.match(line)
        if heading:
            base_slug = _heading_slug(heading.group(2))
            count = seen_slugs.get(base_slug, 0)
            seen_slugs[base_slug] = count + 1
            current_heading = base_slug if count == 0 else f"{base_slug}-{count}"
            continue

        item = _DOCUMENTATION_ITEM.search(line)
        if item is None:
            continue
        if current_heading is None:
            raise ValueError(
                f"{relative}:{index + 1}: OFT documentation item has no preceding heading"
            )
        following = "\n".join(lines[index + 1 : index + 8])
        cover = _DOCUMENTATION_COVER.search(following)
        if cover is None or cover.groups() != item.groups():
            raise ValueError(
                f"{relative}:{index + 1}: OFT documentation item must cover "
                "its matching requirement"
            )
        markers.append(
            EvidenceMarker(
                artifact_type="uman",
                requirement_id=item.group(1),
                revision=int(item.group(2)),
                path=relative,
                locator=current_heading,
                line=index + 1,
            )
        )
    return markers


def collect_evidence_markers(root: Path) -> list[EvidenceMarker]:
    """Collect every native OFT evidence marker from tracked source areas."""
    python_roots = [root / "app.py", root / "ring5", root / "src", root / "scripts", root / "tests"]
    markdown_roots = [
        root / "docs",
        root / "spec" / "oft" / "README.md",
        root / "spec" / "oft" / "discovery-audit.md",
    ]
    markers: list[EvidenceMarker] = []
    for source_root in python_roots:
        paths = [source_root] if source_root.is_file() else sorted(source_root.rglob("*.py"))
        for path in paths:
            markers.extend(collect_python_markers(root, path))
    for source_root in markdown_roots:
        paths = [source_root] if source_root.is_file() else sorted(source_root.rglob("*.md"))
        for path in paths:
            markers.extend(collect_documentation_markers(root, path))
    return markers


def validate_source_evidence(inventory: dict[str, Any], root: Path) -> list[str]:
    """Return validation errors for precise references and native source markers."""
    # [impl->req~ring5.trace.inventory-generator~1]
    try:
        markers = collect_evidence_markers(root)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    by_key = {
        (
            marker.artifact_type,
            marker.requirement_id,
            marker.revision,
            marker.reference,
        ): marker
        for marker in markers
    }
    expected_keys: set[tuple[str, str, int, str]] = set()
    errors: list[str] = []
    evidence_types = {
        "implementation": "impl",
        "tests": "test",
        "documentation": "uman",
    }
    for feature in cast(list[dict[str, Any]], inventory["features"]):
        feature_id = str(feature["id"])
        revision = int(feature["revision"])
        evidence = cast(dict[str, list[str]], feature["evidence"])
        for evidence_type, artifact_type in evidence_types.items():
            for reference in evidence[evidence_type]:
                expected_separator = "#" if artifact_type == "uman" else "::"
                if expected_separator not in reference:
                    errors.append(
                        f"{feature_id}.{evidence_type} reference {reference!r} "
                        "lacks a precise locator"
                    )
                    continue
                key = (artifact_type, feature_id, revision, reference)
                expected_keys.add(key)
                if key not in by_key:
                    errors.append(
                        f"{feature_id}.{evidence_type} reference {reference!r} has no matching "
                        "source-level OFT marker"
                    )

    for marker in markers:
        key = (
            marker.artifact_type,
            marker.requirement_id,
            marker.revision,
            marker.reference,
        )
        if key not in expected_keys:
            errors.append(
                f"unregistered {marker.artifact_type} marker for {marker.requirement_id!r} "
                f"at {marker.path}:{marker.line} ({marker.locator})"
            )
    return errors
