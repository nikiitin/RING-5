"""Page Object for the Performance page.

Covers:
- Cache statistics (hit/miss/rate)
- Session state info
- Cache management (clear all)
- Advanced diagnostics
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.visual.pages.base_page import BasePage


class PerformancePage(BasePage):
    """POM for the *Performance* page."""

    PAGE_NAME: str = "Performance"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self) -> None:
        """Open the Performance page via sidebar."""
        self.navigate_to(self.PAGE_NAME)

    # ------------------------------------------------------------------
    # Locators
    # ------------------------------------------------------------------

    @property
    def page_title(self) -> Locator:
        """The 'Performance Monitor' title."""
        return self.page.get_by_text("Performance Monitor")

    @property
    def cache_stats_header(self) -> Locator:
        """The 'Cache Statistics' header."""
        return self.page.get_by_text("Cache Statistics")

    @property
    def clear_caches_button(self) -> Locator:
        """'Clear All Caches' button."""
        return self.page.get_by_role("button", name="Clear All Caches")

    @property
    def advanced_diagnostics(self) -> Locator:
        """The 'Advanced Diagnostics' expander."""
        return self.page.get_by_text("Advanced Diagnostics")

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    def assert_page_title_visible(self) -> None:
        """Assert the performance title is displayed."""
        expect(self.page_title).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_cache_stats_visible(self) -> None:
        """Assert cache statistics section is rendered."""
        expect(self.cache_stats_header).to_be_visible(timeout=self.RENDER_TIMEOUT)
