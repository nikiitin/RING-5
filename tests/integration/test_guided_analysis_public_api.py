"""Public API proof for the guided analysis progress contract."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_session_reports_real_progress_through_comparison_render_and_export(
    tmp_path: Path,
) -> None:
    # [test->req~ring5.workspace.guided-analysis~1]
    source = tmp_path / "guided.csv"
    pd.DataFrame(
        {
            "benchmark": ["a", "b", "a", "b"],
            "configuration": ["base", "base", "next", "next"],
            "ipc": [1.0, 2.0, 1.1, 1.8],
        }
    ).to_csv(source, index=False)

    with ring5.Session() as session:
        assert session.guided_analysis_progress().current_stage == "source"
        data = session.load(str(source))
        assert session.guided_analysis_progress().current_stage == "comparison"

        comparison = session.compare(
            data.loc[data["configuration"].eq("base")],
            data.loc[data["configuration"].eq("next")],
            ["benchmark"],
            ["ipc"],
        )
        assert session.guided_analysis_progress().current_stage == "visualization"

        figure = session.plot(
            "bar",
            data=comparison,
            config={"x": "benchmark", "y": "percentage_change"},
        )
        assert session.guided_analysis_progress().current_stage == "export"
        assert session.export_bytes(figure, "html")

        progress = session.guided_analysis_progress()

    assert ring5.GuidedAnalysisProgress is type(progress)
    assert ring5.GuidedAnalysisStage is type(progress.stages[0])
    assert progress.complete is True
    assert progress.percent_complete == 100
