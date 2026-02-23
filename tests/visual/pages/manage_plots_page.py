"""Page Object for the Manage Plots page.

Covers:
- Plot creation form
- Plot type selector
- Plot controls (rename, delete, duplicate)
- Shaper pipeline editor
- Plot rendering
- Workspace management
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.visual.pages.base_page import BasePage


class ManagePlotsPage(BasePage):
    """POM for the *Manage Plots* page."""

    PAGE_NAME: str = "Manage Plots"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self) -> None:
        """Open the Manage Plots page via sidebar."""
        self.navigate_to(self.PAGE_NAME)

    # ------------------------------------------------------------------
    # Locators
    # ------------------------------------------------------------------

    @property
    def page_header(self) -> Locator:
        """The 'Manage Plots' heading."""
        return self.page.get_by_text("Manage Plots")

    @property
    def no_plots_warning(self) -> Locator:
        """Warning shown when no plots exist."""
        return self.page.get_by_text("No plots yet")

    @property
    def plot_name_input(self) -> Locator:
        """Text input for new plot name."""
        return self.page.get_by_label("Plot Name")

    @property
    def plot_type_selector(self) -> Locator:
        """Select box for choosing plot type."""
        return self.page.locator("[data-testid='stSelectbox']").first

    @property
    def create_button(self) -> Locator:
        """Button to create a new plot."""
        return self.page.get_by_role("button", name="Create")

    @property
    def plotly_chart(self) -> Locator:
        """The rendered Plotly chart container."""
        return self.page.locator("[data-testid='stPlotlyChart']")

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    def assert_page_header_visible(self) -> None:
        """Assert the manage plots heading is displayed."""
        expect(self.page_header).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_no_plots_warning(self) -> None:
        """Assert the 'no plots' warning is displayed."""
        expect(self.no_plots_warning).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_chart_visible(self) -> None:
        """Assert a Plotly chart is rendered."""
        expect(self.plotly_chart.first).to_be_visible(timeout=self.RENDER_TIMEOUT)
