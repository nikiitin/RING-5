"""Visual tests for Data Source page — rendering, segmented control, mode switching.

Consolidated from 20 individual tests to 3 workflow-style tests using
a class-scoped ``shared_page`` to avoid redundant browser context creation.

Covers:
- Initial rendering & state (all element visibility in one pass)
- Segmented control cycling through all modes
- Mode switching with content mutual exclusivity
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = pytest.mark.requires_browser


class TestDataSourceRendering:
    """Consolidated rendering, segmented control, and mode switching tests.

    Uses ``shared_page`` (class-scoped) so the browser tab is created once
    and reused across all three tests.  Tests run in definition order.
    """

    def test_initial_rendering(self, shared_page: Page, live_server_url: str) -> None:
        """Page loads and all expected elements render correctly.

        Consolidates 8 original tests:
        - page loads successfully (main header visible)
        - Data Source is default page (step header visible)
        - step header contains 'Step 1' and 'Choose Data Source'
        - info box is visible and describes three input methods
        - segmented control is rendered with all three mode options
        - sidebar navigation buttons are present
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)

        # Main app header
        ds.assert_page_loaded()

        # Step header
        ds.assert_step_header_visible()
        expect(ds.step_header).to_contain_text("Step 1")
        expect(ds.step_header).to_contain_text("Choose Data Source")

        # Info box with three data input methods
        ds.assert_info_box_visible()
        expect(ds.info_box).to_contain_text("Parse gem5 Stats Files")
        expect(ds.info_box).to_contain_text("Upload CSV")
        expect(ds.info_box).to_contain_text("Load from Recent")

        # Segmented control
        ds.assert_segmented_control_visible()
        ds.assert_all_mode_options_visible()

        # Sidebar navigation
        nav_items = [
            "Data Source",
            "Data Managers",
            "Manage Plots",
            "Save/Load Portfolio",
            "Performance",
        ]
        for item in nav_items:
            btn = ds.sidebar.get_by_role("button", name=item)
            expect(btn).to_be_visible()

    def test_segmented_control_cycling(self, shared_page: Page, live_server_url: str) -> None:
        """All segmented control interactions work correctly.

        Consolidates 5 original tests:
        - Parse mode is default active
        - Clicking CSV activates CSV
        - Clicking Recent activates Recent
        - Reselecting Parse after CSV reactivates Parse
        - Full mode cycle: CSV -> Recent -> Parse
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)

        # Parse is default
        ds.assert_parse_mode_active()

        # Switch to CSV
        ds.select_csv_mode()
        ds.assert_csv_mode_active()

        # Switch to Recent
        ds.select_recent_mode()
        ds.assert_recent_mode_active()

        # Back to Parse
        ds.select_parse_mode()
        ds.assert_parse_mode_active()

        # Full cycle again: CSV -> Recent -> Parse
        ds.select_csv_mode()
        ds.assert_csv_mode_active()
        ds.select_recent_mode()
        ds.assert_recent_mode_active()
        ds.select_parse_mode()
        ds.assert_parse_mode_active()

    def test_mode_content_switching(self, shared_page: Page, live_server_url: str) -> None:
        """Switching modes shows/hides correct content sections.

        Consolidates 7 original tests:
        - Parse mode shows parser config
        - CSV mode hides parser config and shows success message
        - Recent mode hides parser config and shows Recent header
        - Returning to Parse restores config
        - CSV message disappears on mode switch
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)

        # Parse mode: config visible
        ds.assert_parser_config_visible()

        # CSV mode: config hidden, success message visible
        ds.select_csv_mode()
        ds.assert_parser_config_hidden()
        ds.assert_csv_mode_message_visible()

        # Recent mode: config hidden, CSV message gone, recent header visible
        ds.select_recent_mode()
        ds.assert_parser_config_hidden()
        ds.assert_csv_mode_message_hidden()
        ds.assert_recent_header_visible()

        # Back to Parse: config restored, CSV message still hidden
        ds.select_parse_mode()
        ds.assert_parser_config_visible()
        ds.assert_csv_mode_message_hidden()
