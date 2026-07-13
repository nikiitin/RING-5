"""Recursive stats-file discovery — shared across simulator backends.

One implementation of "find the simulator output files under a directory", used by
the application facade (browse), the scanner (discover variables), and the parse
strategies (enumerate work). Path/pattern sanitisation is reused from
``src.core.common.utils``; this module knows nothing simulator-specific.
"""

from __future__ import annotations

import os
from pathlib import Path

from src.core.common.utils import normalize_user_path, sanitize_glob_pattern


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
        limit: Return at most this many files (``0`` = unlimited). With
            ``sort=False``, discovery stops at the limit. With ``sort=True``,
            the complete tree is sorted before selecting the first N paths.
        sort: Return paths in lexical order. Combined with ``limit``, this
            deterministically selects the first N matching paths.
        raise_if_empty: Raise ``FileNotFoundError`` when the path is missing or no
            file matches; otherwise return an empty list.

    Returns:
        Matching file paths as strings.

    Raises:
        FileNotFoundError: Only when ``raise_if_empty`` is True and nothing is found.
        OSError: The operating system rejects traversal of the search tree.

    Notes:
        Directory symlinks are not followed by ``Path.rglob``. Matching file
        symlinks are returned when the platform reports them as files.
    """
    base: Path = normalize_user_path(os.path.normpath(search_path) if search_path else ".")
    if not base.exists():
        if raise_if_empty:
            raise FileNotFoundError(f"Stats path does not exist: {search_path}")
        return []

    safe_pattern: str = sanitize_glob_pattern(pattern)

    if limit > 0 and not sort:
        collected: list[Path] = []
        for f in base.rglob(safe_pattern):
            if not f.is_file():
                continue
            collected.append(f)
            if len(collected) >= limit:
                break
        files = collected
    else:
        files = [path for path in base.rglob(safe_pattern) if path.is_file()]

    if sort:
        files = sorted(files)
        if limit > 0:
            files = files[:limit]

    if not files and raise_if_empty:
        raise FileNotFoundError(f"No files matching '{pattern}' found under: {search_path}")

    return [str(f) for f in files]
