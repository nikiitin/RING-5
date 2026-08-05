"""Unit coverage for the bounded workspace-wide inverted index."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.core.models import DatasetInfo, WorkspaceSearchEntry
from src.core.services import workspace_search_service as search_module
from src.core.services.workspace_search_service import WorkspaceSearchService


def _state() -> MagicMock:
    state = MagicMock()
    state.get_parse_variables.return_value = [
        {"name": "system.cpu.ipc", "type": "scalar", "alias": "IPC", "_id": "v1"}
    ]
    state.get_scanned_variables.return_value = [
        {"name": "system.cpu.ipc", "type": "scalar", "entries": []},
        {"name": "system.cache.misses", "type": "vector", "entries": ["l1", "l2"]},
    ]
    state.list_datasets.return_value = (DatasetInfo("experiment results", 42, 5, True),)
    state.get_plots.return_value = [
        SimpleNamespace(
            plot_id=7,
            name="Latency overview",
            plot_type="grouped_bar",
            config={"x": "benchmark", "y": "latency", "palette": "safe"},
            pipeline=[
                {"id": 0, "type": "sort", "config": {"columns": ["benchmark"]}},
            ],
        )
    ]
    return state


@pytest.mark.parametrize(
    ("query", "kind", "title"),
    [
        ("CPU IPC", "variable", "system.cpu.ipc"),
        ("l2 vector", "variable", "system.cache.misses"),
        ("experiment 42", "dataset", "experiment results"),
        ("latency bar", "plot", "Latency overview"),
        ("sort benchmark", "pipeline", "Latency overview · step 1: Sort"),
        ("paper draft", "portfolio", "paper draft"),
        ("go manage plots", "command", "Go to Manage Plots"),
        ("open documentation", "documentation", "Open Documentation"),
        ("plot types", "documentation", "Plot types"),
    ],
)
def test_every_workspace_source_is_indexed_and_actionable(
    query: str, kind: str, title: str
) -> None:
    """Return an actionable top result from each indexed workspace source."""
    # [test->req~ring5.workspace.global-search~1]
    response = WorkspaceSearchService.search_workspace(
        _state(),
        ["paper draft"],
        query,
    )

    assert response.results[0].kind == kind
    assert response.results[0].title == title
    assert response.results[0].matched_terms
    assert response.returned_matches <= response.total_matches
    assert response.indexed_entries == response.available_entries
    assert response.index_truncated is False


def test_ranking_is_deterministic_and_prefers_exact_titles() -> None:
    entries = (
        WorkspaceSearchEntry("plot", "IPC detail", "Contains IPC", "Manage Plots", "2"),
        WorkspaceSearchEntry("dataset", "IPC", "Exact dataset", "Data Managers", "ipc"),
        WorkspaceSearchEntry("variable", "system.ipc", "IPC statistic", "Data Source", "ipc"),
    )

    first = WorkspaceSearchService.search(entries, "  iPc  ")
    second = WorkspaceSearchService.search(tuple(reversed(entries)), "IPC")

    assert [result.title for result in first.results] == ["IPC", "IPC detail", "system.ipc"]
    assert [result.title for result in second.results] == ["IPC", "IPC detail", "system.ipc"]
    assert first.query == second.query == "ipc"


def test_terms_use_and_semantics_and_blank_queries_are_empty() -> None:
    entries = (
        WorkspaceSearchEntry("plot", "Fast IPC", "candidate", "Manage Plots", "1"),
        WorkspaceSearchEntry("plot", "Fast latency", "baseline", "Manage Plots", "2"),
    )

    matched = WorkspaceSearchService.search(entries, "fast candidate")
    blank = WorkspaceSearchService.search(entries, " \t\n ")

    assert [result.identifier for result in matched.results] == ["1"]
    assert blank.results == ()
    assert blank.total_matches == 0


def test_result_and_per_kind_index_bounds_are_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(search_module, "MAX_WORKSPACE_SEARCH_ENTRIES_PER_KIND", 2)
    entries = tuple(
        WorkspaceSearchEntry("dataset", f"dataset {index}", "shared", "Data Managers", str(index))
        for index in range(4)
    )

    response = WorkspaceSearchService.search(entries, "dataset", limit=1)

    assert response.available_entries == 4
    assert response.indexed_entries == 2
    assert response.index_truncated is True
    assert response.total_matches == 2
    assert response.returned_matches == 1
    assert response.results_truncated is True


@pytest.mark.parametrize(
    ("query", "limit", "message"),
    [
        ("x" * 201, 20, "exceeds 200"),
        ("bad\x00query", 20, "control characters"),
        ("valid", True, "from 1 through 100"),
        ("valid", 0, "from 1 through 100"),
        ("valid", 101, "from 1 through 100"),
    ],
)
def test_invalid_query_and_limits_are_rejected(query: str, limit: object, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        WorkspaceSearchService.search((), query, limit=limit)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="query must be text"):
        WorkspaceSearchService.search((), 3)  # type: ignore[arg-type]


def test_invalid_entries_and_duplicates_do_not_create_ambiguous_results() -> None:
    duplicate = WorkspaceSearchEntry("dataset", "same", "first", "Data Managers", "same")
    response = WorkspaceSearchService.search((duplicate, duplicate), "same")
    assert response.total_matches == 1

    with pytest.raises(TypeError, match="instances"):
        WorkspaceSearchService.search((object(),), "item")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="title must not be empty"):
        WorkspaceSearchService.search(
            (WorkspaceSearchEntry("dataset", "", "empty", "Data Managers"),),
            "item",
        )
    with pytest.raises(ValueError, match="Unsupported"):
        WorkspaceSearchService.search(
            (
                WorkspaceSearchEntry(
                    "unknown",  # type: ignore[arg-type]
                    "item",
                    "bad kind",
                    "Data Managers",
                ),
            ),
            "item",
        )
