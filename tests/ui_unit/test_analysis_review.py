"""Presentation coverage for authored analysis review updates."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.core.models import (
    AnalysisReviewResponse,
    AnalysisReviewTarget,
    AnalysisReviewTargetResponse,
)


@patch("src.web.components.analysis_review.st")
def test_render_records_an_authored_status_and_comment(mock_st: MagicMock) -> None:
    # [test->req~ring5.workspace.collaborative-review~1]
    from src.web.components.analysis_review import AnalysisReviewComponent

    target = AnalysisReviewTarget("plot", "7", "IPC plot")
    mock_st.expander.return_value.__enter__.return_value = MagicMock()
    mock_st.selectbox.side_effect = ["Plots", target, "in-review"]
    mock_st.text_input.return_value = "alice@example.org"
    mock_st.text_area.return_value = "Check the confidence interval."
    mock_st.button.return_value = True
    api = MagicMock()
    api.list_analysis_review_targets.return_value = AnalysisReviewTargetResponse(
        targets=(target,),
        total_targets=1,
        returned_targets=1,
        truncated=False,
        available_targets=1,
        indexed_targets=1,
        index_truncated=False,
    )
    api.list_analysis_reviews.return_value = AnalysisReviewResponse(
        threads=(),
        total_threads=0,
        returned_threads=0,
        truncated=False,
        status_counts=(
            ("not-reviewed", 0),
            ("in-review", 0),
            ("changes-requested", 0),
            ("approved", 0),
        ),
    )

    AnalysisReviewComponent.render(api)

    api.list_analysis_review_targets.assert_called_once_with(kind="plot", limit=100)
    api.list_analysis_reviews.assert_called_once_with(kind="plot", limit=100)
    api.record_analysis_review.assert_called_once_with(
        "plot",
        "7",
        author_id="alice@example.org",
        comment="Check the confidence interval.",
        status="in-review",
        portfolio_name=None,
    )
    mock_st.success.assert_called_once()
    mock_st.rerun.assert_called_once()
