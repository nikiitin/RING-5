"""Visual tests for Data Source page — rendering, segmented control, mode switching.

Split from the monolithic test_data_source.py for maintainability.
Covers:
- Initial rendering & state
- Segmented control interactions
- Mode switching & mutual exclusivity
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = pytest.mark.requires_browser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(page: Page, live_server_url: str) -> DataSourcePage:
    """Navigate to the Data Source page and wait for it to load."""
    ds = DataSourcePage(page)
    ds.goto_and_wait(live_server_url)
    ds.assert_step_header_visible()
    return ds


# ===================================================================
# 1. Rendering & initial state
# ===================================================================


class TestDataSourceRendering:
    """Verify the Data Source page renders all expected elements."""

    def test_page_loads_successfully(self, page: Page, live_server_url: str) -> None:
        """The landing page loads and shows the main app header."""
        ds = DataSourcePage(page)
        ds.goto_and_wait(live_server_url)
        ds.assert_page_loaded()

    def test_data_source_is_default_page(self, page: Page, live_server_url: str) -> None:
        """Data Source is the first page rendered on initial load."""
        ds = _setup(page, live_server_url)
        ds.assert_step_header_visible()

    def test_step_header_text(self, page: Page, live_server_url: str) -> None:
        """The 'Step 1: Choose Data Source' header is displayed."""
        ds = _setup(page, live_server_url)
        expect(ds.step_header).to_contain_text("Step 1")
        expect(ds.step_header).to_contain_text("Choose Data Source")

    def test_info_box_visible(self, page: Page, live_server_url: str) -> None:
        """The informational blue box is visible."""
        ds = _setup(page, live_server_url)
        ds.assert_info_box_visible()

    def test_info_box_describes_three_methods(self, page: Page, live_server_url: str) -> None:
        """The info box mentions all three data input methods."""
        ds = _setup(page, live_server_url)
        expect(ds.info_box).to_contain_text("Parse gem5 Stats Files")
        expect(ds.info_box).to_contain_text("Upload CSV")
        expect(ds.info_box).to_contain_text("Load from Recent")

    def test_segmented_control_rendered(self, page: Page, live_server_url: str) -> None:
        """The three-option segmented control is rendered."""
        ds = _setup(page, live_server_url)
        ds.assert_segmented_control_visible()

    def test_all_three_mode_options_visible(self, page: Page, live_server_url: str) -> None:
        """All three mode buttons appear in the segmented control."""
        ds = _setup(page, live_server_url)
        ds.assert_all_mode_options_visible()

    def test_sidebar_nav_buttons_present(self, page: Page, live_server_url: str) -> None:
        """All five sidebar navigation buttons are present."""
        ds = _setup(page, live_server_url)
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


# ===================================================================
# 2. Segmented control (mode selector)
# ===================================================================


class TestSegmentedControl:
    """Verify the segmented control interactions."""

    def test_parse_mode_is_default_active(self, page: Page, live_server_url: str) -> None:
        """'Parse gem5 Stats Files' is the default selected mode."""
        ds = _setup(page, live_server_url)
        ds.assert_parse_mode_active()

    def test_click_csv_activates_csv(self, page: Page, live_server_url: str) -> None:
        """Clicking 'I already have CSV data' activates CSV mode."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        ds.assert_csv_mode_active()

    def test_click_recent_activates_recent(self, page: Page, live_server_url: str) -> None:
        """Clicking 'Load from Recent' activates Recent mode."""
        ds = _setup(page, live_server_url)
        ds.select_recent_mode()
        ds.assert_recent_mode_active()

    def test_reselect_parse_after_csv(self, page: Page, live_server_url: str) -> None:
        """Switching to CSV then back to Parse reactivates Parse mode."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        ds.assert_csv_mode_active()
        ds.select_parse_mode()
        ds.assert_parse_mode_active()

    def test_mode_cycle_csv_to_recent_to_parse(self, page: Page, live_server_url: str) -> None:
        """Cycling through all three modes updates the active state."""
        ds = _setup(page, live_server_url)

        ds.select_csv_mode()
        ds.assert_csv_mode_active()

        ds.select_recent_mode()
        ds.assert_recent_mode_active()

        ds.select_parse_mode()
        ds.assert_parse_mode_active()


# ===================================================================
# 3. Mode switching & mutual exclusivity
# ===================================================================


class TestModeSwitching:
    """Switching modes shows/hides the correct content sections."""

    def test_parse_mode_shows_parser_config(self, page: Page, live_server_url: str) -> None:
        """Parse mode shows the parser configuration section."""
        ds = _setup(page, live_server_url)
        ds.assert_parser_config_visible()

    def test_csv_mode_hides_parser_config(self, page: Page, live_server_url: str) -> None:
        """CSV mode hides the parser configuration section."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        ds.assert_parser_config_hidden()

    def test_csv_mode_shows_success_message(self, page: Page, live_server_url: str) -> None:
        """CSV mode shows the 'CSV mode selected' success message."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        ds.assert_csv_mode_message_visible()

    def test_recent_mode_hides_parser_config(self, page: Page, live_server_url: str) -> None:
        """Recent mode hides the parser configuration section."""
        ds = _setup(page, live_server_url)
        ds.select_recent_mode()
        ds.assert_parser_config_hidden()

    def test_recent_mode_shows_recent_header(self, page: Page, live_server_url: str) -> None:
        """Recent mode shows the 'Recent CSV Files' heading."""
        ds = _setup(page, live_server_url)
        ds.select_recent_mode()
        ds.assert_recent_header_visible()

    def test_returning_to_parse_restores_config(self, page: Page, live_server_url: str) -> None:
        """Switching away and back to Parse restores the config section."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        ds.assert_parser_config_hidden()
        ds.select_parse_mode()
        ds.assert_parser_config_visible()

    def test_csv_message_disappears_on_mode_switch(self, page: Page, live_server_url: str) -> None:
        """CSV success message goes away when switching to another mode."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        ds.assert_csv_mode_message_visible()
        ds.select_parse_mode()
        ds.assert_csv_mode_message_hidden()
