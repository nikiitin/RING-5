"""Immutable portfolio revision storage and comparison tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.core.services.data_services.path_service import PathService
from src.core.services.data_services.portfolio_revision_service import (
    PortfolioRevisionService,
)


@pytest.fixture
def revision_storage(tmp_path: Path) -> tuple[Path, Path]:
    current = tmp_path / "portfolios" / "Study.json"
    current.parent.mkdir()
    revisions = tmp_path / "portfolio_revisions"
    revisions.mkdir()
    with patch.object(PathService, "get_portfolio_revisions_dir", return_value=revisions):
        yield current, revisions


def _payload(
    *,
    timestamp: str,
    parser: bool = False,
    title: str = "Baseline",
    line_width: int = 2,
    step: str = "sort",
    data_value: int = 1,
) -> bytes:
    document: dict[str, Any] = {
        "schema_version": 3,
        "version": "3.0",
        "timestamp": timestamp,
        "data_csv": f"category,value\nA,{data_value}\n",
        "csv_path": None if parser else "/data/results.csv",
        "plots": [
            {
                "id": 1,
                "name": title,
                "plot_type": "bar",
                "processed_data": f"category,value\nA,{data_value}\n",
                "config": {
                    "x": "category",
                    "y": "value",
                    "title": title,
                    "line_width": line_width,
                },
                "pipeline": [{"type": step, "column": "value"}],
                "legend_mappings": {"A": title},
                "figure_spec": {"title": title, "line_width": line_width},
            }
        ],
        "plot_counter": 1,
        "config": {},
        "parse_variables": ([{"name": "ipc", "type": "scalar"}] if parser else []),
        "use_parser": parser,
        "stats_path": "/simulations" if parser else None,
        "stats_pattern": "stats*.txt",
        "scanned_variables": ([{"name": "ipc", "type": "scalar"}] if parser else []),
        "manager_history": [],
        "portfolio_history": [],
    }
    return json.dumps(document, indent=2).encode()


def test_retains_exact_versions_and_identifies_current(
    revision_storage: tuple[Path, Path],
) -> None:
    # [test->req~ring5.portfolio.history-diff~1]
    current, _revisions = revision_storage
    first_payload = _payload(timestamp="2026-07-20T10:00:00", title="First")
    second_payload = _payload(timestamp="2026-07-21T10:00:00", title="Second")

    first_id = PortfolioRevisionService.retain_and_replace(
        "Study", first_payload, current, overwrite=False
    )
    second_id = PortfolioRevisionService.retain_and_replace(
        "Study", second_payload, current, overwrite=True
    )

    revisions = PortfolioRevisionService.list_revisions("Study", current)
    assert [revision.sequence for revision in revisions] == [1, 2]
    assert [revision.revision_id for revision in revisions] == [first_id, second_id]
    assert [revision.active for revision in revisions] == [False, True]
    assert PortfolioRevisionService.load_revision("Study", first_id)["plots"][0]["name"] == "First"
    assert current.read_bytes() == second_payload


def test_exclusive_conflict_does_not_create_a_revision(
    revision_storage: tuple[Path, Path],
) -> None:
    current, _revisions = revision_storage
    first = _payload(timestamp="2026-07-20T10:00:00")
    PortfolioRevisionService.retain_and_replace("Study", first, current, overwrite=False)

    with pytest.raises(FileExistsError):
        PortfolioRevisionService.retain_and_replace(
            "Study",
            _payload(timestamp="2026-07-21T10:00:00"),
            current,
            overwrite=False,
        )

    assert len(PortfolioRevisionService.list_revisions("Study", current)) == 1


def test_existing_portfolio_is_lazily_captured_and_history_is_deleted_exactly(
    revision_storage: tuple[Path, Path],
) -> None:
    current, revisions_root = revision_storage
    current.write_bytes(_payload(timestamp="2026-07-20T10:00:00"))
    unrelated = revisions_root / "keep.txt"
    unrelated.write_text("keep")

    revisions = PortfolioRevisionService.list_revisions("Study", current)
    assert len(revisions) == 1
    assert revisions[0].active

    PortfolioRevisionService.delete_history("Study")
    assert unrelated.read_text() == "keep"
    assert not any(path.is_dir() for path in revisions_root.iterdir())


def test_checksum_and_revision_id_are_validated(
    revision_storage: tuple[Path, Path],
) -> None:
    current, _revisions = revision_storage
    revision_id = PortfolioRevisionService.retain_and_replace(
        "Study",
        _payload(timestamp="2026-07-20T10:00:00"),
        current,
        overwrite=False,
    )
    with pytest.raises(ValueError, match="64 lowercase"):
        PortfolioRevisionService.load_revision("Study", "../bad")

    history_file = PortfolioRevisionService._revision_path("Study", revision_id)
    history_file.write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        PortfolioRevisionService.load_revision("Study", revision_id)


def test_compare_groups_reviewable_changes_and_omits_embedded_rows(
    revision_storage: tuple[Path, Path],
) -> None:
    # [test->req~ring5.portfolio.history-diff~1]
    current, _revisions = revision_storage
    before = PortfolioRevisionService.retain_and_replace(
        "Study",
        _payload(timestamp="2026-07-20T10:00:00", data_value=1),
        current,
        overwrite=False,
    )
    after = PortfolioRevisionService.retain_and_replace(
        "Study",
        _payload(
            timestamp="2026-07-21T10:00:00",
            parser=True,
            title="Reviewed",
            line_width=4,
            step="normalize",
            data_value=999,
        ),
        current,
        overwrite=True,
    )

    difference = PortfolioRevisionService.compare("Study", before, after)
    sections = {entry.section for entry in difference.entries}
    paths = {entry.path for entry in difference.entries}

    assert sections == {"data_sources", "pipelines", "plots", "figure_settings"}
    assert "[0].name" in paths
    assert "[0].steps[0].type" in paths
    assert not any("data_csv" in path or "999" in path for path in paths)
    assert sum(count for _section, count in difference.section_counts) == len(difference.entries)
    assert not difference.truncated


def test_comparison_never_exposes_embedded_data_rows(
    revision_storage: tuple[Path, Path],
) -> None:
    current, _revisions = revision_storage
    before = PortfolioRevisionService.retain_and_replace(
        "Study",
        _payload(timestamp="2026-07-20T10:00:00", data_value=1),
        current,
        overwrite=False,
    )
    after = PortfolioRevisionService.retain_and_replace(
        "Study",
        _payload(timestamp="2026-07-21T10:00:00", data_value=999),
        current,
        overwrite=True,
    )

    difference = PortfolioRevisionService.compare("Study", before, after)

    assert difference.change_count == 0
    assert difference.entries == ()
    assert not difference.truncated


def test_comparison_is_bounded(revision_storage: tuple[Path, Path]) -> None:
    current, _revisions = revision_storage
    before = PortfolioRevisionService.retain_and_replace(
        "Study",
        _payload(timestamp="2026-07-20T10:00:00"),
        current,
        overwrite=False,
    )
    after = PortfolioRevisionService.retain_and_replace(
        "Study",
        _payload(timestamp="2026-07-21T10:00:00", parser=True, title="Changed"),
        current,
        overwrite=True,
    )

    with patch(
        "src.core.services.data_services.portfolio_revision_service.MAX_PORTFOLIO_DIFF_ENTRIES",
        2,
    ):
        difference = PortfolioRevisionService.compare("Study", before, after)

    assert difference.change_count == 2
    assert difference.truncated
