"""E2E tests for Portfolio save/load and cross-page state persistence.

Covers:
- Full portfolio save/load cycle (save, verify in manage list, load, verify state)
- Cross-page state persistence (data and plots survive navigation)

Fixtures:
- ``tier3_page``: Data loaded + 2 plots ("E2E Bar", "E2E Shaped") with finalized pipelines.
- ``tier2_page``: Data loaded + 1 plot ("E2E Bar") with Sort pipeline finalized.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import E2E_TIMEOUT
from tests.visual.pages.data_managers_page import DataManagersPage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.portfolio_page import PortfolioPage

pytestmark = pytest.mark.requires_browser

PORTFOLIO_NAME = "E2E_Test_Portfolio"


# Tier 3: Full portfolio save/load cycle


@pytest.mark.xdist_group("e2e_portfolio")
class TestPortfolioSaveLoad:
    """Tier 3: Full portfolio save/load cycle (ordered).

    Uses ``tier3_page`` which has data loaded and two plots
    ("E2E Bar" and "E2E Shaped") with finalized pipelines.
    """

    @pytest.mark.order(1)
    def test_01_page_loads(self, tier3_page: Page) -> None:
        """Navigate to Portfolio page, assert header visible."""
        pf = PortfolioPage(tier3_page)
        pf.navigate()
        pf.assert_page_header_visible()

    @pytest.mark.order(2)
    def test_02_save_portfolio(self, tier3_page: Page) -> None:
        # [test->req~ring5.portfolio.environment-metadata~1]
        """Fill portfolio name, click save, verify expander appears."""
        pf = PortfolioPage(tier3_page)
        pf.navigate()
        pf.assert_page_header_visible()

        pf.save_name_input.fill(PORTFOLIO_NAME)
        pf.save_button.click()
        pf.wait_for_streamlit()
        tier3_page.wait_for_timeout(2000)

        # Saved portfolio should appear as an expander in the manage section
        expander = tier3_page.locator("[data-testid='stExpander']").filter(has_text=PORTFOLIO_NAME)
        expect(expander).to_be_visible(timeout=E2E_TIMEOUT)
        pf.assert_environment_match_visible()

    @pytest.mark.order(3)
    def test_03_portfolio_in_manage_list(self, tier3_page: Page) -> None:
        """Verify saved portfolio still appears in manage section after renavigation."""
        pf = PortfolioPage(tier3_page)
        pf.navigate()
        pf.assert_page_header_visible()

        expander = tier3_page.locator("[data-testid='stExpander']").filter(has_text=PORTFOLIO_NAME)
        expect(expander).to_be_visible(timeout=E2E_TIMEOUT)

    @pytest.mark.order(4)
    def test_04_load_portfolio(self, tier3_page: Page) -> None:
        """Select portfolio from dropdown, click Load Portfolio, wait for reload."""
        pf = PortfolioPage(tier3_page)
        pf.navigate()

        # Open the load selector dropdown
        pf.load_selector.get_by_role("button", name="Open").click()

        # Select the saved portfolio from the dropdown
        option = tier3_page.get_by_role("option", name=PORTFOLIO_NAME, exact=True)
        expect(option).to_be_visible(timeout=E2E_TIMEOUT)
        option.click()
        pf.wait_for_streamlit()

        # Click Load Portfolio (scoped to main content to avoid duplicates)
        load_btn = tier3_page.locator("[data-testid='stMainBlockContainer']").get_by_role(
            "button", name="Load Portfolio"
        )
        load_btn.click()
        tier3_page.wait_for_timeout(3000)
        pf.wait_for_streamlit()

    @pytest.mark.order(5)
    def test_05_data_survives_load(self, tier3_page: Page) -> None:
        """After loading portfolio, Data Managers still shows data."""
        dm = DataManagersPage(tier3_page)
        dm.navigate()
        dm.assert_page_header_visible()
        dm.assert_has_data()

    @pytest.mark.order(6)
    def test_06_plots_survive_load(self, tier3_page: Page) -> None:
        """After loading portfolio, Manage Plots shows 'E2E Bar' pill."""
        mp = ManagePlotsPage(tier3_page)
        mp.navigate()
        mp.assert_page_header_visible()
        mp.assert_plot_pill_visible("E2E Bar")


# Tier 2: Cross-page state persistence


@pytest.mark.xdist_group("e2e_cross_page")
class TestCrossPageState:
    """Tier 2: Cross-page state persistence.

    Uses ``tier2_page`` which has data loaded and one plot
    ("E2E Bar") with a Sort pipeline finalized.
    """

    @pytest.mark.order(1)
    def test_data_persists_across_pages(self, tier2_page: Page) -> None:
        """Navigate Data Managers -> Manage Plots -> Data Source -> Data Managers.

        Data should be present at each step where it is expected.
        """
        # Verify data on Data Managers
        dm = DataManagersPage(tier2_page)
        dm.navigate()
        dm.assert_page_header_visible()
        dm.assert_has_data()

        # Navigate to Manage Plots and verify plot exists
        mp = ManagePlotsPage(tier2_page)
        mp.navigate()
        mp.assert_plot_pill_visible("E2E Bar")

        # Navigate to Data Source, then back to Data Managers
        ds = DataSourcePage(tier2_page)
        ds.navigate()
        ds.assert_step_header_visible()

        dm.navigate()
        dm.assert_has_data()

    @pytest.mark.order(2)
    def test_plot_persists_after_navigation(self, tier2_page: Page) -> None:
        """Navigate away from Manage Plots and back; plot pill still visible."""
        mp = ManagePlotsPage(tier2_page)
        mp.navigate()
        mp.assert_plot_pill_visible("E2E Bar")

        # Navigate away to Data Source
        ds = DataSourcePage(tier2_page)
        ds.navigate()
        ds.assert_step_header_visible()

        # Navigate back to Manage Plots
        mp.navigate()
        mp.assert_plot_pill_visible("E2E Bar")

    @pytest.mark.order(3)
    def test_data_managers_tabs_retain_state(self, tier2_page: Page) -> None:
        """Switch tabs on Data Managers, navigate away, return; data persists."""
        dm = DataManagersPage(tier2_page)
        dm.navigate()
        dm.assert_has_data()

        # Switch to Data Visualization tab
        dm.select_tab("Data Visualization")
        dm.assert_dataframe_visible()

        # Navigate away to Manage Plots
        mp = ManagePlotsPage(tier2_page)
        mp.navigate()
        mp.assert_page_header_visible()

        # Return to Data Managers and verify data still present
        dm.navigate()
        dm.assert_has_data()

    @pytest.mark.order(4)
    def test_portfolio_page_accessible_with_data(self, tier2_page: Page) -> None:
        """Portfolio page loads and shows header when data is present."""
        pf = PortfolioPage(tier2_page)
        pf.navigate()
        pf.assert_page_header_visible()

        # Save button should be visible (we have data to save)
        expect(pf.save_button).to_be_visible(timeout=E2E_TIMEOUT)
        expect(pf.save_name_input).to_be_visible(timeout=E2E_TIMEOUT)
