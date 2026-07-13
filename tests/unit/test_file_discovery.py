"""Deterministic recursive statistics-file discovery."""

from pathlib import Path

import pytest

from src.parsing.framework.file_discovery import find_stats_files


@pytest.fixture
def stats_tree(tmp_path: Path) -> Path:
    """Create matching files in an order different from lexical order."""
    for relative in ("z/run/stats.txt", "a/stats.txt", "m/deep/stats.txt"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative)
    return tmp_path


@pytest.mark.parametrize(
    ("limit", "expected"),
    [
        (0, ["a/stats.txt", "m/deep/stats.txt", "z/run/stats.txt"]),
        (1, ["a/stats.txt"]),
        (2, ["a/stats.txt", "m/deep/stats.txt"]),
        (10, ["a/stats.txt", "m/deep/stats.txt", "z/run/stats.txt"]),
    ],
)
def test_sorted_limit_selects_lexical_paths(
    stats_tree: Path,
    limit: int,
    expected: list[str],
) -> None:
    """Sorting happens before slicing, independent of creation order."""
    paths = find_stats_files(str(stats_tree), limit=limit, sort=True)
    relative = [str(Path(path).relative_to(stats_tree)) for path in paths]
    assert relative == expected


def test_empty_and_missing_paths(stats_tree: Path, tmp_path: Path) -> None:
    """No matches are empty by default and typed when requested."""
    assert find_stats_files(str(stats_tree), pattern="missing.txt", sort=True) == []
    with pytest.raises(FileNotFoundError, match="No files matching"):
        find_stats_files(
            str(stats_tree),
            pattern="missing.txt",
            sort=True,
            raise_if_empty=True,
        )
    assert find_stats_files(str(tmp_path / "absent"), sort=True) == []
