"""Public API and portable-bundle proof for collaborative analysis review."""

from __future__ import annotations

import pandas as pd
import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_portfolios")]


def test_plot_and_revision_reviews_survive_portfolio_bundle_transfer(portfolios_dir) -> None:
    # [test->req~ring5.workspace.collaborative-review~1]
    data = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 1.2]})
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=data,
            config={"x": "benchmark", "y": "ipc"},
            name="IPC plot",
        )
        session.save_portfolio("reviewed", overwrite=True)
        revision = session.list_portfolio_revisions("reviewed")[-1]
        plot_thread = session.record_analysis_review(
            "plot",
            str(plot.plot_id),
            author_id="alice@example.org",
            comment="Please verify the normalized baseline.",
            status="in-review",
        )
        revision_thread = session.record_analysis_review(
            "portfolio_revision",
            revision.revision_id,
            portfolio_name="reviewed",
            author_id="review-bot",
            comment="Checks completed.",
            status="approved",
        )
        session.save_portfolio("reviewed", overwrite=True)
        bundle = session.export_portfolio_bundle("reviewed")
        session.api.data_services.delete_portfolio("reviewed")

    assert isinstance(plot_thread, ring5.AnalysisReviewThread)
    assert isinstance(plot_thread.events[0], ring5.AnalysisReviewEvent)
    assert revision_thread.portfolio_name == "reviewed"

    with ring5.Session() as restored:
        report = restored.restore_portfolio_bundle(bundle)
        reviews = restored.list_analysis_reviews()
        targets = restored.list_analysis_review_targets()

    assert report.complete
    assert isinstance(reviews, ring5.AnalysisReviewResponse)
    assert isinstance(targets, ring5.AnalysisReviewTargetResponse)
    assert {thread.kind for thread in reviews.threads} == {"plot", "portfolio_revision"}
    by_kind = {thread.kind: thread for thread in reviews.threads}
    assert by_kind["plot"].available is True
    assert by_kind["portfolio_revision"].available is False
    assert by_kind["portfolio_revision"].events[0].author_id == "review-bot"
    assert by_kind["portfolio_revision"].status == "approved"


def test_public_review_errors_are_typed(portfolios_dir) -> None:
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="not currently available"):
            session.record_analysis_review(
                "plot",
                "99",
                author_id="alice",
                comment="Missing plot",
            )
        with pytest.raises(ring5.DataValidationError, match="from 1 through 100"):
            session.list_analysis_reviews(limit=0)
        with pytest.raises(ring5.DataValidationError, match="from 1 through 100"):
            session.list_analysis_review_targets(limit=0)
