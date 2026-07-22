"""Page object for the persistent guided-analysis sidebar."""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from tests.visual.pages.base_page import BasePage


class GuidedAnalysis(BasePage):
    """Expose guided progress and its single next-step action."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    @property
    def expander(self) -> Locator:
        """Guided-analysis expander in the sidebar."""
        return (
            self.sidebar.locator("[data-testid='stExpander']")
            .filter(has_text=re.compile(r"Guided analysis · \d+%"))
            .first
        )

    @property
    def content(self) -> Locator:
        """Visible guided-analysis content."""
        return self.expander.locator("[data-testid='stExpanderDetails']").first

    @property
    def current_step(self) -> Locator:
        """Current step heading."""
        return self.content.get_by_text(re.compile(r"Step \d+ of 5:"))

    @property
    def next_action(self) -> Locator:
        """Only primary action for the current stage."""
        return self.content.locator("[data-testid='stBaseButton-primary']").first

    @property
    def completion_message(self) -> Locator:
        """Message shown after the actual export milestone."""
        return self.content.get_by_text(re.compile(r"Analysis workflow complete"))

    def open(self) -> None:
        """Expand the guide while preserving an already-open state."""
        if not self.content.is_visible():
            self.expander.locator("summary").first.click()

    def follow_next_action(self) -> None:
        """Use the current stage's direct navigation action."""
        self.open()
        self.next_action.click()
        self.wait_for_streamlit(expect_rerun=True)
