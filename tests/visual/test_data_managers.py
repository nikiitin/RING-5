"""Visual tests for the Data Managers page.

Consolidated from 11 individual tests (8 functions + 6 parametrized) to
3 workflow-style tests using a class-scoped ``shared_page`` fixture.

Covers:
- No-data state (header + warning)
- All 7 tabs visible and switchable
- Screenshot capture for documentation
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.visual.pages.data_managers_page import DataManagersPage

pytestmark = pytest.mark.requires_browser


class TestDataManagers:
    """Consolidated Data Managers page tests.

    Uses ``shared_page`` (class-scoped) so the browser tab is created once
    and reused across all three tests.
    """

    def test_no_data_state(self, shared_page: Page, live_server_url: str) -> None:
        """Header renders and no-data warning is shown without loaded data.

        Consolidates 2 original tests:
        - page_renders_header
        - shows_no_data_warning
        """
        dm = DataManagersPage(shared_page)
        dm.goto_and_wait(live_server_url)
        dm.navigate()

        dm.assert_page_header_visible()
        dm.assert_no_data_warning()

    def test_tabs_and_switching(self, shared_page: Page, live_server_url: str) -> None:
        """All 7 tabs are present and switching between them works.

        Consolidates 9 original tests (2 function + 6 parametrized + 1):
        - all_tabs_present
        - summary_tab_is_default
        - switch_to_tab (Data Visualization, Seeds Reducer, Outlier Remover,
          Preprocessor, Mixer, Operations History)
        """
        dm = DataManagersPage(shared_page)
        dm.goto_and_wait(live_server_url)
        dm.navigate()

        # All tabs visible
        dm.assert_tabs_visible()

        # Summary is default
        dm.assert_tab_active("Summary")

        # Switch through every other tab
        for tab_name in [
            "Data Visualization",
            "Seeds Reducer",
            "Outlier Remover",
            "Preprocessor",
            "Mixer",
            "Operations History",
        ]:
            dm.select_tab(tab_name)
            dm.assert_tab_active(tab_name)

        # Return to Summary
        dm.select_tab("Summary")
        dm.assert_tab_active("Summary")

    def test_screenshots(
        self,
        shared_page: Page,
        live_server_url: str,
        shared_screenshot_dir: Path,
    ) -> None:
        """Capture Data Managers screenshots for documentation.

        Consolidates 3 original tests:
        - capture_initial_state
        - capture_no_data_warning
        - capture_tabs_overview (each tab)
        """
        dm = DataManagersPage(shared_page)
        dm.goto_and_wait(live_server_url)
        dm.navigate()

        # No-data state
        dm.assert_page_header_visible()
        dm.screenshot(shared_screenshot_dir / "data_managers_no_data.png")

        # No-data warning close-up
        dm.assert_no_data_warning()
        dm.screenshot(shared_screenshot_dir / "data_managers_no_data_warning.png")

        # Each tab
        for tab_name in DataManagersPage.TAB_NAMES:
            dm.select_tab(tab_name)
            safe_name = tab_name.lower().replace(" ", "_")
            dm.screenshot(shared_screenshot_dir / f"dm_tab_{safe_name}.png")
