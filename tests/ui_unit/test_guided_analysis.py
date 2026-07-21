"""Presentation coverage for workspace-derived guided analysis."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models import GuidedAnalysisStage
from src.core.services.guided_analysis_service import GuidedAnalysisService


@patch("src.web.components.guided_analysis.st")
def test_render_shows_one_next_action_and_navigates(mock_st: MagicMock) -> None:
    # [test->req~ring5.workspace.guided-analysis~1]
    from src.web.components.guided_analysis import GuidedAnalysisComponent

    progress = GuidedAnalysisService.assess(
        pd.DataFrame({"configuration": ["base", "next"], "ipc": [1.0, 1.1]}),
        comparison_ready=False,
        plot_count=0,
        rendered_plot_count=0,
    )
    mock_st.session_state = {}
    mock_st.expander.return_value.__enter__.return_value = MagicMock()
    mock_st.button.return_value = True
    api = MagicMock()
    api.guided_analysis_progress.return_value = progress

    GuidedAnalysisComponent.render(api)

    api.guided_analysis_progress.assert_called_once_with(exported=False)
    assert mock_st.session_state["_nav_page"] == "Data Managers"
    mock_st.button.assert_called_once_with(
        "Configure comparison",
        key="guided_analysis_action_comparison",
        type="primary",
        width="stretch",
    )
    mock_st.rerun.assert_called_once()


@patch("src.web.components.guided_analysis.st")
def test_export_marker_and_navigation_reject_untrusted_values(mock_st: MagicMock) -> None:
    from src.web.components.guided_analysis import GuidedAnalysisComponent

    mock_st.session_state = {}
    GuidedAnalysisComponent.mark_exported()
    assert mock_st.session_state[GuidedAnalysisComponent.EXPORT_STATE_KEY] is True

    with pytest.raises(TypeError, match="GuidedAnalysisStage"):
        GuidedAnalysisComponent.activate(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Unsupported guided destination"):
        GuidedAnalysisComponent.activate(
            GuidedAnalysisStage(
                stage_id="source",
                title="Unsafe",
                description="Unsafe",
                status="current",
                detail="Unsafe",
                action_label="Unsafe",
                destination="Unknown",
            )
        )
