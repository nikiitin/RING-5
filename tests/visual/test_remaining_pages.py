"""Visual tests for Manage Plots, Portfolio, and Performance pages.

Covers:
- Each page renders correctly after sidebar navigation
- No-data guard messages display properly
- Screenshot capture for documentation
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.performance_page import PerformancePage
from tests.visual.pages.portfolio_page import PortfolioPage

pytestmark = pytest.mark.requires_browser


# ---------------------------------------------------------------------------
# Manage Plots
# ---------------------------------------------------------------------------


class TestManagePlots:
    """Visual tests for the Manage Plots page."""

    def test_page_renders(self, page: Page, live_server_url: str) -> None:
        """Manage Plots page renders after sidebar navigation."""
        mp = ManagePlotsPage(page)
        mp.goto_and_wait(live_server_url)
        mp.navigate()
        mp.assert_page_header_visible()

    def test_no_plots_warning(self, page: Page, live_server_url: str) -> None:
        """Without plots, a warning is shown."""
        mp = ManagePlotsPage(page)
        mp.goto_and_wait(live_server_url)
        mp.navigate()
        mp.assert_no_plots_warning()

    def test_capture_screenshot(
        self, page: Page, live_server_url: str, screenshot_dir: Path
    ) -> None:
        """Capture Manage Plots page for documentation."""
        mp = ManagePlotsPage(page)
        mp.goto_and_wait(live_server_url)
        mp.navigate()
        mp.assert_page_header_visible()
        mp.screenshot(screenshot_dir / "manage_plots.png")


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------


class TestPortfolio:
    """Visual tests for the Portfolio page."""

    def test_page_renders(self, page: Page, live_server_url: str) -> None:
        """Portfolio page renders after sidebar navigation."""
        pf = PortfolioPage(page)
        pf.goto_and_wait(live_server_url)
        pf.navigate()
        pf.assert_page_header_visible()

    def test_capture_screenshot(
        self, page: Page, live_server_url: str, screenshot_dir: Path
    ) -> None:
        """Capture Portfolio page for documentation."""
        pf = PortfolioPage(page)
        pf.goto_and_wait(live_server_url)
        pf.navigate()
        pf.assert_page_header_visible()
        pf.screenshot(screenshot_dir / "portfolio.png")


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


class TestPerformance:
    """Visual tests for the Performance page."""

    def test_page_renders(self, page: Page, live_server_url: str) -> None:
        """Performance page renders after sidebar navigation."""
        perf = PerformancePage(page)
        perf.goto_and_wait(live_server_url)
        perf.navigate()
        perf.assert_page_title_visible()

    def test_cache_stats_visible(self, page: Page, live_server_url: str) -> None:
        """Cache statistics section is rendered."""
        perf = PerformancePage(page)
        perf.goto_and_wait(live_server_url)
        perf.navigate()
        perf.assert_cache_stats_visible()

    def test_capture_screenshot(
        self, page: Page, live_server_url: str, screenshot_dir: Path
    ) -> None:
        """Capture Performance page for documentation."""
        perf = PerformancePage(page)
        perf.goto_and_wait(live_server_url)
        perf.navigate()
        perf.assert_page_title_visible()
        perf.screenshot(screenshot_dir / "performance.png")
