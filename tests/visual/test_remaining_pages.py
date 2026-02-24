"""Visual tests for Manage Plots, Portfolio, and Performance pages.

Consolidated from 8 individual tests to 3 workflow-style tests using
a class-scoped ``shared_page`` fixture.

Covers:
- Manage Plots page (renders, no-plots warning, screenshot)
- Portfolio page (renders, screenshot)
- Performance page (renders, cache stats, screenshot)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.performance_page import PerformancePage
from tests.visual.pages.portfolio_page import PortfolioPage

pytestmark = pytest.mark.requires_browser


class TestRemainingPages:
    """Consolidated tests for Manage Plots, Portfolio, and Performance pages.

    Uses ``shared_page`` (class-scoped) so the browser tab is created once
    and reused across all three tests.
    """

    def test_manage_plots_empty(
        self, shared_page: Page, live_server_url: str, shared_screenshot_dir: Path
    ) -> None:
        """Manage Plots page renders with no-plots warning and screenshot.

        Consolidates 3 original tests:
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

        Consolidates 2 original tests:
        - page_renders
        - capture_screenshot
        """
        pf = PortfolioPage(shared_page)
        pf.goto_and_wait(live_server_url)
        pf.navigate()

        pf.assert_page_header_visible()
        pf.screenshot(shared_screenshot_dir / "portfolio.png")

    def test_performance_page(
        self, shared_page: Page, live_server_url: str, shared_screenshot_dir: Path
    ) -> None:
        """Performance page renders with cache stats and screenshot.

        Consolidates 3 original tests:
        - page_renders
        - cache_stats_visible
        - capture_screenshot
        """
        perf = PerformancePage(shared_page)
        perf.goto_and_wait(live_server_url)
        perf.navigate()

        perf.assert_page_title_visible()
        perf.assert_cache_stats_visible()
        perf.screenshot(shared_screenshot_dir / "performance.png")
