#!/usr/bin/env python3
"""Compare the current OFT catalog and native coverage with a Git revision."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, cast

if __package__:
    from scripts.oft_html_report import extract_oft_coverage, inventory_fingerprint
else:
    from oft_html_report import extract_oft_coverage, inventory_fingerprint


INVENTORY_PATH = Path("spec/oft/inventory.json")
REPORT_PATH = Path("spec/oft/generated/report.html")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_MISSING = object()


class OftRequirementDiffError(ValueError):
    """A catalog revision or native OFT report cannot be compared safely."""


@dataclass(frozen=True)
class RequirementChange:
    """One requirement whose catalog fields or evidence graph changed."""

    requirement_id: str
    fields: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""
        return {"id": self.requirement_id, "fields": list(self.fields)}


@dataclass(frozen=True)
class RequirementDiff:
    """Deterministic catalog and native OFT coverage differences."""

    base_revision: str
    added: tuple[str, ...]
    removed: tuple[str, ...]
    changed: tuple[RequirementChange, ...]
    covered: tuple[str, ...]
    uncovered: tuple[str, ...]
    newly_covered: tuple[str, ...]
    newly_uncovered: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return stable machine-readable output."""
        return {
            "base_revision": self.base_revision,
            "summary": {
                "added": len(self.added),
                "removed": len(self.removed),
                "changed": len(self.changed),
                "covered": len(self.covered),
                "uncovered": len(self.uncovered),
                "newly_covered": len(self.newly_covered),
                "newly_uncovered": len(self.newly_uncovered),
            },
            "added": list(self.added),
            "removed": list(self.removed),
            "changed": [change.to_dict() for change in self.changed],
            "covered": list(self.covered),
            "uncovered": list(self.uncovered),
            "newly_covered": list(self.newly_covered),
            "newly_uncovered": list(self.newly_uncovered),
        }


def _changed_fields(base: object, current: object, prefix: str = "") -> tuple[str, ...]:
    if isinstance(base, Mapping) and isinstance(current, Mapping):
        fields: list[str] = []
        for key in sorted(set(base) | set(current)):
            path = f"{prefix}.{key}" if prefix else str(key)
            fields.extend(
                _changed_fields(base.get(key, _MISSING), current.get(key, _MISSING), path)
            )
        return tuple(fields)
    return (prefix,) if base != current else ()


def _feature_map(inventory: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    features = inventory.get("features")
    if not isinstance(features, list):
        raise OftRequirementDiffError("Inventory features must be a list.")
    result: dict[str, dict[str, Any]] = {}
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or not isinstance(feature.get("id"), str):
            raise OftRequirementDiffError(f"Inventory feature {index} has no string ID.")
        feature_id = str(feature["id"])
        if feature_id in result:
            raise OftRequirementDiffError(
                f"Inventory contains duplicate feature ID {feature_id!r}."
            )
        result[feature_id] = cast(dict[str, Any], feature)
    return result


def compare_requirement_states(
    base_inventory: Mapping[str, Any],
    current_inventory: Mapping[str, Any],
    base_coverage: Mapping[str, bool],
    current_coverage: Mapping[str, bool],
    *,
    base_revision: str,
) -> RequirementDiff:
    """Compare catalog fields, evidence edges, and authoritative OFT outcomes."""
    # [impl->req~ring5.trace.requirement-diff~1]
    base = _feature_map(base_inventory)
    current = _feature_map(current_inventory)
    if set(base_coverage) != set(base):
        raise OftRequirementDiffError("Base OFT coverage does not match the base inventory.")
    if set(current_coverage) != set(current):
        raise OftRequirementDiffError("Current OFT coverage does not match the current inventory.")

    common = set(base) & set(current)
    changed = tuple(
        RequirementChange(requirement_id, fields)
        for requirement_id in sorted(common)
        if (fields := _changed_fields(base[requirement_id], current[requirement_id]))
    )
    covered = tuple(sorted(key for key, value in current_coverage.items() if value))
    uncovered = tuple(sorted(key for key, value in current_coverage.items() if not value))
    return RequirementDiff(
        base_revision=base_revision,
        added=tuple(sorted(set(current) - set(base))),
        removed=tuple(sorted(set(base) - set(current))),
        changed=changed,
        covered=covered,
        uncovered=uncovered,
        newly_covered=tuple(
            sorted(key for key in common if not base_coverage[key] and current_coverage[key])
        ),
        newly_uncovered=tuple(
            sorted(key for key in common if base_coverage[key] and not current_coverage[key])
        ),
    )


def _parse_inventory(document: str, source: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise OftRequirementDiffError(f"{source} contains duplicate JSON key {key!r}.")
            result[key] = value
        return result

    try:
        inventory = json.loads(document, object_pairs_hook=reject_duplicates)
    except json.JSONDecodeError as exc:
        raise OftRequirementDiffError(f"Could not parse {source}: {exc}") from exc
    if not isinstance(inventory, dict):
        raise OftRequirementDiffError(f"{source} must contain a JSON object.")
    return cast(dict[str, Any], inventory)


def _run_git(repository: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise OftRequirementDiffError(f"Could not run Git: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise OftRequirementDiffError(detail)
    return result.stdout


def _resolve_revision(repository: Path, revision: str) -> str:
    if not revision or "\x00" in revision:
        raise OftRequirementDiffError("Git revision must be non-empty.")
    resolved = _run_git(
        repository,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{revision}^{{commit}}",
    ).strip()
    if _COMMIT_PATTERN.fullmatch(resolved) is None:
        raise OftRequirementDiffError("Git did not resolve the base to one commit.")
    return resolved


def _git_file(repository: Path, revision: str, path: Path) -> str:
    return _run_git(repository, "show", f"{revision}:{path.as_posix()}")


def _native_coverage(inventory: Mapping[str, Any], report: str, source: str) -> dict[str, bool]:
    expected = (
        '<meta name="ring5-inventory-sha256" ' f'content="{inventory_fingerprint(inventory)}">'
    )
    if expected not in report:
        raise OftRequirementDiffError(f"{source} does not match its inventory fingerprint.")
    try:
        return extract_oft_coverage(report, inventory)
    except ValueError as exc:
        raise OftRequirementDiffError(
            f"Could not read native OFT coverage from {source}: {exc}"
        ) from exc


def build_requirement_diff(repository: Path, revision: str) -> RequirementDiff:
    """Load current and Git-stored OFT states, then return their diff."""
    # [impl->req~ring5.trace.requirement-diff~1]
    repository = repository.resolve()
    resolved = _resolve_revision(repository, revision)
    try:
        current_inventory_text = repository.joinpath(INVENTORY_PATH).read_text(encoding="utf-8")
        current_report = repository.joinpath(REPORT_PATH).read_text(encoding="utf-8")
    except OSError as exc:
        raise OftRequirementDiffError(f"Could not read current OFT state: {exc}") from exc
    base_inventory_text = _git_file(repository, resolved, INVENTORY_PATH)
    base_report = _git_file(repository, resolved, REPORT_PATH)
    base_inventory = _parse_inventory(base_inventory_text, f"{resolved}:{INVENTORY_PATH}")
    current_inventory = _parse_inventory(current_inventory_text, str(INVENTORY_PATH))
    base_coverage = _native_coverage(base_inventory, base_report, "base OFT report")
    current_coverage = _native_coverage(current_inventory, current_report, "current OFT report")
    return compare_requirement_states(
        base_inventory,
        current_inventory,
        base_coverage,
        current_coverage,
        base_revision=resolved,
    )


def _text_section(title: str, values: tuple[str, ...]) -> list[str]:
    return [f"{title} ({len(values)})", *([f"- {value}" for value in values] or ["- None"])]


def render_text(diff: RequirementDiff) -> str:
    """Render a concise human-first requirement diff."""
    # [impl->req~ring5.trace.requirement-diff~1]
    changed = tuple(
        f"{change.requirement_id}: {', '.join(change.fields)}" for change in diff.changed
    )
    lines = ["OFT requirement diff", f"Base commit: {diff.base_revision}", ""]
    sections = (
        ("Added", diff.added),
        ("Removed", diff.removed),
        ("Changed", changed),
        ("Covered now (native OFT)", diff.covered),
        ("Uncovered now (native OFT)", diff.uncovered),
        ("Newly covered", diff.newly_covered),
        ("Newly uncovered", diff.newly_uncovered),
    )
    for title, values in sections:
        lines.extend([*_text_section(title, values), ""])
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision", help="Git commit, tag, or branch to compare against")
    parser.add_argument(
        "--repository", type=Path, default=Path.cwd(), help="repository containing spec/oft"
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Compare revisions and return a process-style status code."""
    # [impl->req~ring5.trace.requirement-diff~1]
    args = build_parser().parse_args(argv)
    try:
        diff = build_requirement_diff(args.repository, args.revision)
    except OftRequirementDiffError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(diff.to_dict(), indent=2, sort_keys=True))
    else:
        print(render_text(diff), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
