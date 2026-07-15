#!/usr/bin/env python3
"""Verify that built distributions contain every runtime data file."""

from __future__ import annotations

import sys
import tarfile
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
RUNTIME_FILES = frozenset(
    {
        "src/parsing/gem5/perl/fileParser.pl",
        "src/parsing/gem5/perl/fileParserServer.pl",
        "src/parsing/gem5/perl/statsScanner.pl",
        "src/parsing/gem5/perl/libs/TypesFormatRegex.pm",
        "src/parsing/gem5/perl/libs/Scanning/RegexUtils.pm",
        "src/parsing/gem5/perl/libs/Scanning/Type/Configuration.pm",
        "src/parsing/gem5/perl/libs/Scanning/Type/Distribution.pm",
        "src/parsing/gem5/perl/libs/Scanning/Type/Histogram.pm",
        "src/parsing/gem5/perl/libs/Scanning/Type/Scalar.pm",
        "src/parsing/gem5/perl/libs/Scanning/Type/Summary.pm",
        "src/parsing/gem5/perl/libs/Scanning/Type/Vector.pm",
        "src/web/components/plotting/custom_plotly/index.html",
    }
)


def wheel_members(path: Path) -> set[str]:
    """Return normalized member paths from a wheel archive."""
    with ZipFile(path) as archive:
        return set(archive.namelist())


def sdist_members(path: Path) -> set[str]:
    """Return member paths from an sdist without its release root directory."""
    with tarfile.open(path, "r:gz") as archive:
        normalized: set[str] = set()
        for member in archive.getmembers():
            parts = Path(member.name).parts
            if len(parts) > 1:
                normalized.add(Path(*parts[1:]).as_posix())
        return normalized


def find_single(pattern: str) -> Path:
    """Return the only matching distribution, failing on stale or missing artifacts."""
    matches = sorted(DIST_DIR.glob(pattern))
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one {pattern!r} artifact in {DIST_DIR}, found {len(matches)}."
        )
    return matches[0]


def missing_runtime_files(members: set[str]) -> list[str]:
    """Return required runtime paths absent from an archive member set."""
    return sorted(RUNTIME_FILES - members)


def main() -> int:
    """Check wheel and sdist contents and return a shell-friendly status."""
    try:
        archives = {
            "wheel": wheel_members(find_single("*.whl")),
            "sdist": sdist_members(find_single("*.tar.gz")),
        }
    except (OSError, ValueError, tarfile.TarError) as exc:
        print(f"Package-content check failed: {exc}", file=sys.stderr)
        return 1

    failures = {
        archive_name: missing_runtime_files(members)
        for archive_name, members in archives.items()
        if missing_runtime_files(members)
    }
    if failures:
        print("Package-content check failed:", file=sys.stderr)
        for archive_name, missing in failures.items():
            print(f"  {archive_name} is missing:", file=sys.stderr)
            for path in missing:
                print(f"    {path}", file=sys.stderr)
        return 1

    print(
        f"Package-content check passed: {len(RUNTIME_FILES)} runtime files "
        "are present in the wheel and sdist."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
