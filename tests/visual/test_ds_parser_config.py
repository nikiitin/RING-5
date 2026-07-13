"""Visual tests for Data Source parser configuration controls."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = pytest.mark.requires_browser


class TestParserConfig:
    """Ordered parser-configuration checks.

    Uses ``shared_page`` (class-scoped) so the browser tab is created once
    and reused across all six tests.  Tests run in definition order.
    """

    def test_file_location_inputs(self, shared_page: Page, live_server_url: str) -> None:
        """File Location section renders correctly and inputs are editable.

        - File Location header visible
        - Stats path label and input visible
        - Stats pattern label and input visible
        - Both inputs side by side
        - Stats path is editable and clearable
        - Stats pattern is editable and changeable
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        # Header and labels
        ds.assert_file_location_visible()
        expect(ds.stats_path_label).to_be_visible()
        expect(ds.stats_pattern_label).to_be_visible()

        # Both inputs visible
        expect(ds.stats_path_input).to_be_visible()
        expect(ds.stats_pattern_input).to_be_visible()

        # Edit stats path
        ds.fill_stats_path("/tmp/test_stats_dir")
        expect(ds.stats_path_input).to_have_value("/tmp/test_stats_dir")

        # Clear stats path
        ds.stats_path_input.fill("")
        ds.stats_path_input.press("Tab")
        ds.wait_for_streamlit()
        expect(ds.stats_path_input).to_have_value("")

        # Edit file pattern
        ds.fill_stats_pattern("custom_stats*.txt")
        expect(ds.stats_pattern_input).to_have_value("custom_stats*.txt")

        # Change pattern again
        ds.fill_stats_pattern("*.txt")
        expect(ds.stats_pattern_input).to_have_value("*.txt")

    def test_parsing_strategy(self, shared_page: Page, live_server_url: str) -> None:
        """Parsing Strategy selector works correctly.

        - Strategy header visible
        - Both Simple and Config-Aware options visible
        - Simple is default strategy
        - Can switch to Config-Aware
        - Can switch back to Simple
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        # Header and options visible
        ds.assert_strategy_section_visible()
        expect(ds.strategy_simple_option).to_be_visible()
        expect(ds.strategy_config_aware_option).to_be_visible()

        # Simple is default
        ds.ensure_simple_strategy()
        expect(ds.strategy_simple_option).to_have_attribute(
            "data-testid", "stBaseButton-segmented_controlActive"
        )

        # Switch to Config-Aware
        ds.select_config_aware_strategy()
        expect(ds.strategy_config_aware_option).to_have_attribute(
            "data-testid", "stBaseButton-segmented_controlActive"
        )

        # Switch back to Simple
        ds.select_simple_strategy()
        expect(ds.strategy_simple_option).to_have_attribute(
            "data-testid", "stBaseButton-segmented_controlActive"
        )

    def test_variables_section(self, shared_page: Page, live_server_url: str) -> None:
        """Variables to Extract section renders all expected elements.

        - Variables header visible
        - Variable type descriptions visible (Scalar, Vector, Distribution, Config)
        - Deep Scan checkbox visible and toggleable
        - Quick Scan button visible
        - Add Variable button visible
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        # Header and description
        ds.assert_variables_section_visible()
        expect(ds.variables_description).to_be_visible()

        # Variable type mentions
        expect(shared_page.get_by_text("Scalar", exact=False).first).to_be_visible()
        expect(shared_page.get_by_text("Vector", exact=False).first).to_be_visible()
        expect(shared_page.get_by_text("Distribution", exact=False).first).to_be_visible()
        expect(shared_page.get_by_text("Configuration", exact=False).first).to_be_visible()

        # Buttons
        expect(ds.quick_scan_button).to_be_visible()
        expect(ds.add_variable_button).to_be_visible()

        # Deep Scan checkbox — toggle on and off
        expect(ds.deep_scan_checkbox).to_be_visible()
        ds.toggle_deep_scan()
        ds.toggle_deep_scan()

    def test_config_preview_static(self, shared_page: Page, live_server_url: str) -> None:
        """Configuration Preview shows expected JSON keys.

        - Config Preview header visible
        - JSON contains 'parser' key
        - JSON contains 'statsPath' key
        - JSON contains 'strategy' key
        - JSON contains 'variables' key
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        ds.assert_config_preview_visible()
        expect(ds.config_json_view).to_contain_text("parser")
        expect(ds.config_json_view).to_contain_text("statsPath")
        expect(ds.config_json_view).to_contain_text("strategy")
        expect(ds.config_json_view).to_contain_text("variables")

    def test_config_preview_dynamic(self, shared_page: Page, live_server_url: str) -> None:
        """Configuration Preview updates when strategy or path changes.

        - Changing strategy updates JSON preview
        - Typing a stats path updates JSON preview
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        # Strategy change reflects in JSON
        ds.select_simple_strategy()
        expect(ds.config_json_view).to_contain_text("simple")
        ds.select_config_aware_strategy()
        expect(ds.config_json_view).to_contain_text("config_aware")

        # Path change reflects in JSON
        ds.fill_stats_path("/my/gem5/output")
        expect(ds.config_json_view).to_contain_text("/my/gem5/output")

    def test_parse_button_behaviour(self, shared_page: Page, live_server_url: str) -> None:
        """Parse button visibility and error validation work correctly.

        - Parse button visible with correct text
        - Parse with empty path shows error
        - Parse with nonexistent path shows error/dialog
        - Parse button NOT visible in CSV mode
        - Parse button NOT visible in Recent mode
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        # Parse button visible with correct text
        ds.assert_parse_button_visible()
        expect(ds.parse_button).to_contain_text("Parse gem5 Stats Files")

        # Empty path shows error
        ds.stats_path_input.fill("")
        ds.stats_path_input.press("Tab")
        ds.wait_for_streamlit()
        ds.click_parse()
        expect(ds.parser_error_message).to_be_visible(timeout=10_000)
        expect(ds.parser_error_message).to_contain_text("Please specify a stats directory path")

        # Not visible in CSV mode
        ds.select_csv_mode()
        expect(ds.parse_button).not_to_be_visible()

        # Not visible in Recent mode
        ds.select_recent_mode()
        expect(ds.parse_button).not_to_be_visible()

        # Back to Parse — visible again
        ds.select_parse_mode()
        ds.assert_parse_button_visible()

        # Nonexistent path shows error
        ds.fill_stats_path("/nonexistent/path/that/should/fail")
        ds.fill_stats_pattern("stats.txt")
        ds.click_parse()
        error_or_dialog = ds.page.locator("[data-testid='stDialog'], [data-testid='stException']")
        expect(error_or_dialog).to_be_visible(timeout=15_000)
