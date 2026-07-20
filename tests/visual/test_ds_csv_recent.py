"""Visual tests for CSV, Recent, and cross-mode state isolation."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = pytest.mark.requires_browser


class TestCSVAndRecentModes:
    """Ordered CSV, Recent, and cross-mode isolation checks.

    Uses ``shared_page`` (class-scoped) so the browser tab is created once
    and reused across all three tests.
    """

    def test_csv_mode_elements(self, shared_page: Page, live_server_url: str) -> None:
        """CSV mode renders correctly with proper element visibility.

        - CSV mode shows success message with correct text
        - Parser config is NOT visible in CSV mode
        - Parse button is NOT visible in CSV mode
        - Recent section is NOT visible in CSV mode
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        ds.select_csv_mode()

        # Success message
        ds.assert_csv_mode_message_visible()
        expect(ds.csv_success_message).to_contain_text("Upload mode selected")

        # Parser config hidden
        ds.assert_parser_config_hidden()

        # Parse button hidden
        expect(ds.parse_button).not_to_be_visible()

        # Recent section hidden
        expect(ds.recent_header).not_to_be_visible()

    def test_recent_mode_elements(self, shared_page: Page, live_server_url: str) -> None:
        """Recent mode renders correctly with proper element visibility.

        - Recent mode shows 'Recent CSV Files' heading
        - Recent mode shows content (empty warning or file cards)
        - Parser config is NOT visible in Recent mode
        - CSV success message is NOT visible in Recent mode
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        ds.select_recent_mode()

        # Header and content
        ds.assert_recent_header_visible()
        ds.assert_recent_mode_content_visible()

        # Parser config hidden
        ds.assert_parser_config_hidden()

        # CSV message hidden
        ds.assert_csv_mode_message_hidden()

    def test_cross_mode_isolation(self, shared_page: Page, live_server_url: str) -> None:
        """Full round-trip through all modes verifies no content leakage.

        - Recent content not in Parse mode
        - Parser config not in CSV mode
        - CSV message not in Recent mode
        - Parse button only in Parse mode
        - Full round-trip: Parse -> CSV -> Recent -> Parse
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        # Parse mode — full check
        ds.assert_parser_config_visible()
        ds.assert_parse_button_visible()
        expect(ds.recent_header).not_to_be_visible()

        # CSV mode — Parse content gone, CSV content present
        ds.select_csv_mode()
        ds.assert_csv_mode_message_visible()
        ds.assert_parser_config_hidden()
        expect(ds.parse_button).not_to_be_visible()
        expect(ds.empty_pool_warning).not_to_be_visible()

        # Recent mode — CSV content gone, Recent content present
        ds.select_recent_mode()
        ds.assert_recent_header_visible()
        ds.assert_recent_mode_content_visible()
        ds.assert_csv_mode_message_hidden()
        ds.assert_parser_config_hidden()
        expect(ds.parse_button).not_to_be_visible()

        # Back to Parse — everything restored
        ds.select_parse_mode()
        ds.assert_parser_config_visible()
        ds.assert_parse_button_visible()
        ds.assert_csv_mode_message_hidden()
        expect(ds.empty_pool_warning).not_to_be_visible()
