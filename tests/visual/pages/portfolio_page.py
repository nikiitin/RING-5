"""Page Object for the Portfolio page.

Covers:
- Save portfolio
- Load portfolio
- Manage saved portfolios
- Pipeline templates (save / apply)
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.visual.pages.base_page import BasePage


class PortfolioPage(BasePage):
    """POM for the *Save/Load Portfolio* page."""

    PAGE_NAME: str = "Save/Load Portfolio"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self) -> None:
        """Open the Portfolio page via sidebar."""
        self.navigate_to(self.PAGE_NAME)

    # ------------------------------------------------------------------
    # Locators
    # ------------------------------------------------------------------

    @property
    def page_header(self) -> Locator:
        """The 'Portfolio Management' heading."""
        return self.page.get_by_text("Portfolio Management")

    @property
    def save_name_input(self) -> Locator:
        """Text input for portfolio save name."""
        return self.page.get_by_label("Portfolio Name")

    @property
    def save_button(self) -> Locator:
        """'Save Portfolio' button."""
        return self.page.get_by_role("button", name="Save Portfolio")

    @property
    def load_selector(self) -> Locator:
        """Select box for choosing a portfolio to load."""
        return self.page.locator("[data-testid='stSelectbox']").first

    @property
    def load_button(self) -> Locator:
        """'Load Portfolio' button."""
        return self.page.get_by_role("button", name="Load Portfolio")

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    def assert_page_header_visible(self) -> None:
        """Assert the portfolio heading is displayed."""
        expect(self.page_header).to_be_visible(timeout=self.RENDER_TIMEOUT)
