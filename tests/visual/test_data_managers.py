"""Visual tests for the Data Managers page.

Tests cover:
- Page rendering with and without data
- All 7 tabs are visible and clickable
- Tab switching behavior
- No-data warning guard
- Screenshot capture for documentation
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.visual.pages.data_managers_page import DataManagersPage

pytestmark = pytest.mark.requires_browser


# ---------------------------------------------------------------------------
# Rendering tests — no data
# ---------------------------------------------------------------------------


class TestDataManagersNoData:
    """Verify behaviour when no dataset is loaded."""

    def test_page_renders_header(self, page: Page, live_server_url: str) -> None:
        """The Data Managers header appears after navigation."""
        dm = DataManagersPage(page)
        dm.goto_and_wait(live_server_url)
        dm.navigate()
        dm.assert_page_header_visible()

    def test_shows_no_data_warning(self, page: Page, live_server_url: str) -> None:
        """Without data, a warning message is displayed."""
        dm = DataManagersPage(page)
        dm.goto_and_wait(live_server_url)
        dm.navigate()
        dm.assert_no_data_warning()


# ---------------------------------------------------------------------------
# Tab rendering tests
# ---------------------------------------------------------------------------


class TestDataManagersTabs:
    """Test that all tabs render and can be clicked.

    Tabs are always rendered to provide navigation context, even
    without data loaded (the no-data warning appears inside the
    Summary tab instead of blocking the whole page).
    """

    def test_all_tabs_present(self, page: Page, live_server_url: str) -> None:
        """All 7 tabs are rendered in the tab bar."""
        dm = DataManagersPage(page)
        dm.goto_and_wait(live_server_url)
        dm.navigate()
        dm.assert_tabs_visible()

    def test_summary_tab_is_default(self, page: Page, live_server_url: str) -> None:
        """Summary tab is selected by default."""
        dm = DataManagersPage(page)
        dm.goto_and_wait(live_server_url)
        dm.navigate()
        dm.assert_tab_active("Summary")

    @pytest.mark.parametrize(
        "tab_name",
        [
            "Data Visualization",
            "Seeds Reducer",
            "Outlier Remover",
            "Preprocessor",
            "Mixer",
            "Operations History",
        ],
    )
    def test_switch_to_tab(self, page: Page, live_server_url: str, tab_name: str) -> None:
        """Clicking each tab selects it."""
        dm = DataManagersPage(page)
        dm.goto_and_wait(live_server_url)
        dm.navigate()
        dm.select_tab(tab_name)
        dm.assert_tab_active(tab_name)


# ---------------------------------------------------------------------------
# Screenshot capture
# ---------------------------------------------------------------------------


class TestDataManagersScreenshots:
    """Capture screenshots for documentation."""

    def test_capture_initial_state(
        self, page: Page, live_server_url: str, screenshot_dir: Path
    ) -> None:
        """Capture Data Managers page without data."""
        dm = DataManagersPage(page)
        dm.goto_and_wait(live_server_url)
        dm.navigate()
        dm.assert_page_header_visible()
        dm.screenshot(screenshot_dir / "data_managers_no_data.png")

    def test_capture_no_data_warning(
        self, page: Page, live_server_url: str, screenshot_dir: Path
    ) -> None:
        """Capture Data Managers page showing no-data warning inside Summary tab."""
        dm = DataManagersPage(page)
        dm.goto_and_wait(live_server_url)
        dm.navigate()
        dm.assert_no_data_warning()
        dm.screenshot(screenshot_dir / "data_managers_no_data_warning.png")

    def test_capture_tabs_overview(
        self, page: Page, live_server_url: str, screenshot_dir: Path
    ) -> None:
        """Capture each tab for documentation."""
        dm = DataManagersPage(page)
        dm.goto_and_wait(live_server_url)
        dm.navigate()

        for tab_name in DataManagersPage.TAB_NAMES:
            dm.select_tab(tab_name)
            safe_name = tab_name.lower().replace(" ", "_")
            dm.screenshot(screenshot_dir / f"dm_tab_{safe_name}.png")
