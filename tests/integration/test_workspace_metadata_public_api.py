"""Public API and portfolio-reuse proof for favorites and tags."""

from __future__ import annotations

import pandas as pd
import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_portfolios")]


def test_public_metadata_covers_every_kind_and_survives_portfolio_reuse(portfolios_dir) -> None:
    # [test->req~ring5.workspace.favorites-tags~1]
    data = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 1.2]})
    with ring5.Session() as session:
        session.api.state_manager.set_parse_variables(
            [{"name": "system.cpu.ipc", "type": "scalar", "_id": "v1"}]
        )
        session.add_dataset("nightly", data)
        plot = session.create_plot(
            "bar",
            data=data,
            config={"x": "benchmark", "y": "ipc"},
            name="IPC plot",
        )
        plot.pipeline = [{"id": 11, "type": "sort", "config": {"columns": ["benchmark"]}}]
        targets = (
            ("variable", "system.cpu.ipc"),
            ("dataset", "nightly"),
            ("plot", str(plot.plot_id)),
            ("pipeline", f"{plot.plot_id}:11"),
        )
        for kind, identifier in targets:
            session.set_workspace_artifact_metadata(
                kind,  # type: ignore[arg-type]
                identifier,
                tags=("Paper", "Nightly"),
                favorite=True,
            )
        session.save_portfolio("organized", overwrite=True)
        session.set_workspace_artifact_metadata(
            "portfolio",
            "organized",
            tags=("paper",),
            favorite=True,
        )

        filtered = session.list_workspace_artifacts(tags=("nightly",), favorites_only=True)

    assert ring5.WorkspaceArtifactResponse is type(filtered)
    assert ring5.WorkspaceArtifact is type(filtered.artifacts[0])
    assert {artifact.kind for artifact in filtered.artifacts} == {
        "variable",
        "dataset",
        "plot",
        "pipeline",
    }

    with ring5.Session() as restored:
        report = restored.load_portfolio("organized")
        restored.add_dataset("nightly", data)
        reused = restored.list_workspace_artifacts(tags=("nightly",))
        portfolio = restored.list_workspace_artifacts(kind="portfolio", favorites_only=True)

    assert report.complete
    assert {artifact.kind for artifact in reused.artifacts} == {
        "variable",
        "dataset",
        "plot",
        "pipeline",
    }
    assert [artifact.identifier for artifact in portfolio.artifacts] == ["organized"]


def test_public_metadata_errors_are_typed(portfolios_dir) -> None:
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="not currently available"):
            session.set_workspace_artifact_metadata("dataset", "missing", tags=("x",))
        with pytest.raises(ring5.DataValidationError, match="may contain"):
            session.set_workspace_artifact_metadata("variable", "missing", tags=("bad!",))
        with pytest.raises(ring5.DataValidationError, match="from 1 through 100"):
            session.list_workspace_artifacts(limit=0)
