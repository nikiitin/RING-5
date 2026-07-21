"""Focused browser proof for a human-authored portable plot review."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.analysis_review import AnalysisReview
from tests.visual.pages.manage_plots_page import ManagePlotsPage


@pytest.mark.requires_browser
@pytest.mark.xdist_group("e2e_analysis_review")
class TestAnalysisReview:
    def test_plot_review_retains_author_comment_and_status(self, shared_page: Page) -> None:
        # [test->req~ring5.workspace.collaborative-review~1]
        plots = ManagePlotsPage(shared_page)
        plots.navigate()
        plots.create_plot("Review candidate", "bar")

        review = AnalysisReview(shared_page)
        review.add_update(
            "alice@example.org",
            "Verify the confidence interval.",
            "In review",
        )
        review.open()

        expect(review.expander.get_by_text("Current status: In review")).to_be_visible()
        expect(review.expander.get_by_text("alice@example.org", exact=False)).to_be_visible()
        expect(
            review.expander.get_by_role("paragraph").filter(
                has_text="Verify the confidence interval."
            )
        ).to_be_visible()
