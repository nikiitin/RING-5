"""Public workspace search contract across live session state."""

from __future__ import annotations

import pandas as pd
import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_portfolios")]


def test_public_search_finds_dynamic_and_static_workspace_content(portfolios_dir) -> None:
    # [test->req~ring5.workspace.global-search~1]
    data = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 1.2]})
    with ring5.Session() as session:
        session.add_dataset("nightly experiment", data)
        session.api.state_manager.set_parse_variables(
            [{"name": "system.cpu.ipc", "type": "scalar", "alias": "IPC", "_id": "v1"}]
        )
        session.api.state_manager.set_scanned_variables(
            [{"name": "system.cpu.ipc", "type": "scalar", "entries": []}]
        )
        plot = session.create_plot(
            "bar",
            data=data,
            config={"x": "benchmark", "y": "ipc"},
            name="Nightly IPC",
        )
        plot.pipeline = [{"id": 0, "type": "sort", "config": {"columns": ["benchmark"]}}]
        session.save_portfolio("nightly-search", overwrite=True)

        searches = {
            "variable": session.search_workspace("cpu ipc"),
            "dataset": session.search_workspace("nightly experiment"),
            "plot": session.search_workspace("nightly ipc"),
            "pipeline": session.search_workspace("sort benchmark"),
            "portfolio": session.search_workspace("nightly-search"),
            "command": session.search_workspace("go data managers"),
            "documentation": session.search_workspace("plot types"),
        }

    assert ring5.WorkspaceSearchResponse is type(searches["plot"])
    assert ring5.WorkspaceSearchResult is type(searches["plot"].results[0])
    for expected_kind, response in searches.items():
        assert response.results[0].kind == expected_kind
        assert response.results[0].location
        assert response.index_truncated is False


def test_public_search_validation_is_typed() -> None:
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="exceeds 200"):
            session.search_workspace("x" * 201)
        with pytest.raises(ring5.DataValidationError, match="from 1 through 100"):
            session.search_workspace("plot", limit=0)
