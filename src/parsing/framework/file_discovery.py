"""Recursive stats-file discovery — shared across simulator backends.

One implementation of "find the simulator output files under a directory", used by
the application facade (browse), the scanner (discover variables), and the parse
strategies (enumerate work). Path/pattern sanitisation is reused from
``src.core.common.utils``; this module knows nothing simulator-specific.
"""

from __future__ import annotations

import fnmatch
import os
import time
from pathlib import Path

from src.core.common.security_limits import (
    MAX_DISCOVERED_FILES,
    MAX_DISCOVERY_ENTRIES,
    MAX_DISCOVERY_SECONDS,
)
from src.core.common.utils import normalize_user_path, sanitize_glob_pattern


class FileDiscoveryLimitError(RuntimeError):
    """Filesystem discovery exceeded a configured resource bound."""


def find_stats_files(
    search_path: str,
    pattern: str = "stats.txt",
    *,
    limit: int = 0,
    sort: bool = False,
    raise_if_empty: bool = False,
) -> list[str]:
    """Find files matching ``pattern`` recursively under ``search_path``.

    Args:
        search_path: Base directory to search (recursively).
        pattern: Filename glob pattern (default ``"stats.txt"``).
        limit: Return at most this many files. ``0`` uses the bounded global
            discovery maximum; negative values are rejected.
        sort: Return paths in lexical order. Discovery itself is lexical and
            stops as soon as the requested number of matches is collected.
        raise_if_empty: Raise ``FileNotFoundError`` when the path is missing or no
            file matches; otherwise return an empty list.

    Returns:
        Matching file paths as strings.

    Raises:
        FileNotFoundError: Only when ``raise_if_empty`` is True and nothing is found.
        OSError: The operating system rejects traversal of the search tree.
        FileDiscoveryLimitError: Traversal exceeds a file, entry, or time bound.

    Notes:
        Symlinks are not followed or returned.
    """
    if limit < 0:
        raise ValueError("File discovery limit cannot be negative.")

    base: Path = normalize_user_path(os.path.normpath(search_path) if search_path else ".")
    if not base.exists():
        if raise_if_empty:
            raise FileNotFoundError(f"Stats path does not exist: {search_path}")
        return []

    safe_pattern: str = sanitize_glob_pattern(pattern)

    requested_limit = limit if limit > 0 else MAX_DISCOVERED_FILES + 1
    files: list[Path] = []
    visited_entries = 0
    deadline = time.monotonic() + MAX_DISCOVERY_SECONDS

    # Store directory-entry metadata in the stack so symlinks are never followed.
    # Each directory is materialized only after the global entry budget is checked,
    # giving deterministic lexical traversal without an unbounded full-tree list.
    pending: list[tuple[Path, bool, bool]] = [(base, True, False)]
    while pending:
        if time.monotonic() > deadline:
            raise FileDiscoveryLimitError(
                f"File discovery exceeded {MAX_DISCOVERY_SECONDS:g} seconds under: {search_path}"
            )

        current, is_dir, is_file = pending.pop()
        if is_file:
            if fnmatch.fnmatchcase(current.name, safe_pattern):
                files.append(current)
                if limit == 0 and len(files) > MAX_DISCOVERED_FILES:
                    raise FileDiscoveryLimitError(
                        f"More than {MAX_DISCOVERED_FILES} matching files were found under: "
                        f"{search_path}"
                    )
                if len(files) >= requested_limit:
                    break
            continue
        if not is_dir:
            continue

        entries: list[os.DirEntry[str]] = []
        with os.scandir(current) as iterator:
            for entry in iterator:
                visited_entries += 1
                if visited_entries > MAX_DISCOVERY_ENTRIES:
                    raise FileDiscoveryLimitError(
                        f"File discovery exceeded {MAX_DISCOVERY_ENTRIES} entries under: "
                        f"{search_path}"
                    )
                if time.monotonic() > deadline:
                    raise FileDiscoveryLimitError(
                        f"File discovery exceeded {MAX_DISCOVERY_SECONDS:g} seconds under: "
                        f"{search_path}"
                    )
                entries.append(entry)

        entries.sort(key=lambda entry: entry.name, reverse=True)
        for entry in entries:
            entry_is_dir = entry.is_dir(follow_symlinks=False)
            entry_is_file = entry.is_file(follow_symlinks=False)
            if entry_is_dir or entry_is_file:
                pending.append((Path(entry.path), entry_is_dir, entry_is_file))

    if sort:
        files.sort()

    if not files and raise_if_empty:
        raise FileNotFoundError(f"No files matching '{pattern}' found under: {search_path}")

    return [str(f) for f in files]
