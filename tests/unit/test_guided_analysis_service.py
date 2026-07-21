"""Unit coverage for deterministic guided-analysis milestones."""

from __future__ import annotations

import pandas as pd
import pytest

from src.core.services.guided_analysis_service import GuidedAnalysisService


def test_progress_is_ordered_and_requires_real_upstream_evidence() -> None:
    # [test->req~ring5.workspace.guided-analysis~1]
    data = pd.DataFrame({"configuration": ["base", "next"], "ipc": [1.0, 1.1]})

    progress = GuidedAnalysisService.assess(
        data,
        comparison_ready=False,
        plot_count=1,
        rendered_plot_count=1,
        exported=True,
    )

    assert progress.completed_stages == 2
    assert progress.percent_complete == 40
    assert progress.current_stage == "comparison"
    assert [stage.status for stage in progress.stages] == [
        "complete",
        "complete",
        "current",
        "blocked",
        "blocked",
    ]


def test_complete_progress_reports_each_workspace_milestone() -> None:
    data = pd.DataFrame({"configuration": ["base", "next"], "ipc": [1.0, 1.1]})

    progress = GuidedAnalysisService.assess(
        data,
        comparison_ready=True,
        plot_count=2,
        rendered_plot_count=1,
        exported=True,
    )

    assert progress.complete is True
    assert progress.current_stage is None
    assert progress.completed_stages == progress.total_stages == 5
    assert progress.percent_complete == 100
    assert all(stage.status == "complete" for stage in progress.stages)


@pytest.mark.parametrize(
    ("data", "detail"),
    [
        (pd.DataFrame({"label": ["a"]}), "numeric metric"),
        (pd.DataFrame([[1.0]], columns=[""]), "non-empty text name"),
        (pd.DataFrame([[1.0, 2.0]], columns=["metric", "metric"]), "unique"),
    ],
)
def test_invalid_table_structure_stays_at_validation(
    data: pd.DataFrame,
    detail: str,
) -> None:
    progress = GuidedAnalysisService.assess(
        data,
        comparison_ready=True,
        plot_count=1,
        rendered_plot_count=1,
        exported=True,
    )

    assert progress.current_stage == "validation"
    assert detail in progress.stages[1].detail


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"comparison_ready": 1}, "comparison_ready must be a boolean"),
        ({"plot_count": True}, "plot_count must be an integer"),
        ({"plot_count": -1}, "plot_count cannot be negative"),
        ({"plot_count": 0, "rendered_plot_count": 1}, "cannot exceed"),
    ],
)
def test_invalid_progress_signals_are_rejected(kwargs: dict[str, object], error: str) -> None:
    inputs: dict[str, object] = {
        "comparison_ready": False,
        "plot_count": 0,
        "rendered_plot_count": 0,
        "exported": False,
    }
    inputs.update(kwargs)

    with pytest.raises((TypeError, ValueError), match=error):
        GuidedAnalysisService.assess(None, **inputs)  # type: ignore[arg-type]
