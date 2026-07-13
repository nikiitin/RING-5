"""Visual tests for the Manage Plots and Portfolio pages."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.portfolio_page import PortfolioPage

pytestmark = pytest.mark.requires_browser


class TestRemainingPages:
    """Ordered checks for Manage Plots and Portfolio.

    Uses ``shared_page`` (class-scoped) so the browser tab is created once
    and reused across all tests.
    """

    def test_manage_plots_empty(
        self, shared_page: Page, live_server_url: str, shared_screenshot_dir: Path
    ) -> None:
        """Manage Plots page renders with no-plots warning and screenshot.

        - page_renders
        - no_plots_warning
        - capture_screenshot
        """
        mp = ManagePlotsPage(shared_page)
        mp.goto_and_wait(live_server_url)
        mp.navigate()

        mp.assert_page_header_visible()
        mp.assert_no_plots_warning()
        mp.screenshot(shared_screenshot_dir / "manage_plots.png")

    def test_portfolio_page(
        self, shared_page: Page, live_server_url: str, shared_screenshot_dir: Path
    ) -> None:
        """Portfolio page renders with header and screenshot.

        - page_renders
        - capture_screenshot
        """
        pf = PortfolioPage(shared_page)
        pf.goto_and_wait(live_server_url)
        pf.navigate()

        pf.assert_page_header_visible()
        pf.screenshot(shared_screenshot_dir / "portfolio.png")
