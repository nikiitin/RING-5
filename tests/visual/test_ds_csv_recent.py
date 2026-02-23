"""Visual tests for Data Source page — CSV mode, Recent mode, cross-mode isolation.

Split from the monolithic test_data_source.py for maintainability.
Covers:
- CSV mode — message & state
- Load from Recent mode
- Cross-mode isolation
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
# CSV mode — message & state
# ===================================================================


class TestCSVMode:
    """Test the 'I already have CSV data' mode."""

    def test_csv_mode_success_message(self, page: Page, live_server_url: str) -> None:
        """CSV mode shows a success message."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        ds.assert_csv_mode_message_visible()

    def test_csv_success_message_text(self, page: Page, live_server_url: str) -> None:
        """CSV success message mentions 'CSV mode selected'."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        expect(ds.csv_success_message).to_contain_text("CSV mode selected")

    def test_csv_mode_no_parser_config(self, page: Page, live_server_url: str) -> None:
        """Parser configuration is NOT visible in CSV mode."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        ds.assert_parser_config_hidden()

    def test_csv_mode_no_parse_button(self, page: Page, live_server_url: str) -> None:
        """Parse button is NOT visible in CSV mode."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        expect(ds.parse_button).not_to_be_visible()

    def test_csv_mode_no_recent_section(self, page: Page, live_server_url: str) -> None:
        """Recent CSV Files section is NOT visible in CSV mode."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        expect(ds.recent_header).not_to_be_visible()


# ===================================================================
# Load from Recent mode
# ===================================================================


class TestRecentMode:
    """Test the 'Load from Recent' mode."""

    def test_recent_mode_header(self, page: Page, live_server_url: str) -> None:
        """Recent mode shows 'Recent CSV Files' heading."""
        ds = _setup(page, live_server_url)
        ds.select_recent_mode()
        ds.assert_recent_header_visible()

    def test_recent_mode_shows_content(self, page: Page, live_server_url: str) -> None:
        """Recent mode shows either empty warning or file cards."""
        ds = _setup(page, live_server_url)
        ds.select_recent_mode()
        ds.assert_recent_mode_content_visible()

    def test_recent_mode_no_parser_config(self, page: Page, live_server_url: str) -> None:
        """Parser configuration is NOT visible in Recent mode."""
        ds = _setup(page, live_server_url)
        ds.select_recent_mode()
        ds.assert_parser_config_hidden()

    def test_recent_mode_no_csv_message(self, page: Page, live_server_url: str) -> None:
        """CSV success message is NOT visible in Recent mode."""
        ds = _setup(page, live_server_url)
        ds.select_recent_mode()
        ds.assert_csv_mode_message_hidden()


# ===================================================================
# Cross-mode isolation
# ===================================================================


class TestCrossModeIsolation:
    """Content from one mode doesn't leak into another."""

    def test_recent_warning_not_in_parse_mode(self, page: Page, live_server_url: str) -> None:
        """Recent mode content doesn't appear in Parse mode."""
        ds = _setup(page, live_server_url)
        ds.select_recent_mode()
        ds.assert_recent_header_visible()
        ds.select_parse_mode()
        expect(ds.recent_header).not_to_be_visible()

    def test_parse_config_not_in_csv_mode(self, page: Page, live_server_url: str) -> None:
        """Parser config doesn't appear in CSV mode."""
        ds = _setup(page, live_server_url)
        ds.assert_parser_config_visible()
        ds.select_csv_mode()
        ds.assert_parser_config_hidden()
        expect(ds.config_json_view).not_to_be_visible()

    def test_csv_message_not_in_recent_mode(self, page: Page, live_server_url: str) -> None:
        """CSV success message doesn't appear in Recent mode."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        ds.assert_csv_mode_message_visible()
        ds.select_recent_mode()
        ds.assert_csv_mode_message_hidden()

    def test_parse_button_only_in_parse_mode(self, page: Page, live_server_url: str) -> None:
        """The primary Parse button exists only in Parse mode."""
        ds = _setup(page, live_server_url)
        ds.assert_parse_button_visible()

        ds.select_csv_mode()
        expect(ds.parse_button).not_to_be_visible()

        ds.select_recent_mode()
        expect(ds.parse_button).not_to_be_visible()

        ds.select_parse_mode()
        ds.assert_parse_button_visible()

    def test_full_round_trip_all_modes(self, page: Page, live_server_url: str) -> None:
        """Full round-trip: Parse -> CSV -> Recent -> Parse verifies isolation."""
        ds = _setup(page, live_server_url)

        # Parse mode
        ds.assert_parser_config_visible()
        ds.assert_parse_button_visible()

        # CSV mode
        ds.select_csv_mode()
        ds.assert_csv_mode_message_visible()
        ds.assert_parser_config_hidden()
        expect(ds.parse_button).not_to_be_visible()
        expect(ds.empty_pool_warning).not_to_be_visible()

        # Recent mode
        ds.select_recent_mode()
        ds.assert_recent_header_visible()
        ds.assert_recent_mode_content_visible()
        ds.assert_csv_mode_message_hidden()
        ds.assert_parser_config_hidden()
        expect(ds.parse_button).not_to_be_visible()

        # Back to Parse
        ds.select_parse_mode()
        ds.assert_parser_config_visible()
        ds.assert_parse_button_visible()
        ds.assert_csv_mode_message_hidden()
        expect(ds.empty_pool_warning).not_to_be_visible()
