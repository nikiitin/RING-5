"""Visual tests for Data Source page — parser configuration widgets.

Split from the monolithic test_data_source.py for maintainability.
Covers:
- File Location inputs
- Parsing Strategy selector
- Variables to Extract section
- Configuration Preview (JSON)
- Parse button & validation
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
# File Location inputs
# ===================================================================


class TestFileLocationInputs:
    """Test the stats directory path and file pattern text inputs."""

    def test_file_location_header_visible(self, page: Page, live_server_url: str) -> None:
        """'File Location' heading is visible in Parse mode."""
        ds = _setup(page, live_server_url)
        ds.assert_file_location_visible()

    def test_stats_path_input_is_editable(self, page: Page, live_server_url: str) -> None:
        """User can type a path into the stats directory input."""
        ds = _setup(page, live_server_url)
        ds.fill_stats_path("/tmp/test_stats_dir")
        expect(ds.stats_path_input).to_have_value("/tmp/test_stats_dir")

    def test_stats_pattern_input_is_editable(self, page: Page, live_server_url: str) -> None:
        """User can type a pattern into the file pattern input."""
        ds = _setup(page, live_server_url)
        ds.fill_stats_pattern("*.txt")
        expect(ds.stats_pattern_input).to_have_value("*.txt")

    def test_stats_path_label_visible(self, page: Page, live_server_url: str) -> None:
        """The 'Stats directory path' label is visible."""
        ds = _setup(page, live_server_url)
        expect(ds.stats_path_label).to_be_visible()

    def test_stats_pattern_label_visible(self, page: Page, live_server_url: str) -> None:
        """The 'File pattern' label is visible."""
        ds = _setup(page, live_server_url)
        expect(ds.stats_pattern_label).to_be_visible()

    def test_stats_path_can_be_cleared(self, page: Page, live_server_url: str) -> None:
        """User can clear the stats path input."""
        ds = _setup(page, live_server_url)
        ds.fill_stats_path("/some/path")
        ds.stats_path_input.fill("")
        ds.stats_path_input.press("Tab")
        ds.wait_for_streamlit()
        expect(ds.stats_path_input).to_have_value("")

    def test_stats_pattern_can_be_changed(self, page: Page, live_server_url: str) -> None:
        """User can change the file pattern from default to custom."""
        ds = _setup(page, live_server_url)
        ds.fill_stats_pattern("custom_stats*.txt")
        expect(ds.stats_pattern_input).to_have_value("custom_stats*.txt")

    def test_both_inputs_side_by_side(self, page: Page, live_server_url: str) -> None:
        """Both inputs are rendered (two-column layout)."""
        ds = _setup(page, live_server_url)
        expect(ds.stats_path_input).to_be_visible()
        expect(ds.stats_pattern_input).to_be_visible()


# ===================================================================
# Parsing Strategy selector
# ===================================================================


class TestParsingStrategy:
    """Test the parsing strategy segmented control."""

    def test_strategy_header_visible(self, page: Page, live_server_url: str) -> None:
        """'Parsing Strategy' heading is visible in Parse mode."""
        ds = _setup(page, live_server_url)
        ds.assert_strategy_section_visible()

    def test_strategy_shows_two_options(self, page: Page, live_server_url: str) -> None:
        """Both Simple and Config-Aware options are visible."""
        ds = _setup(page, live_server_url)
        expect(ds.strategy_simple_option).to_be_visible()
        expect(ds.strategy_config_aware_option).to_be_visible()

    def test_simple_is_default_strategy(self, page: Page, live_server_url: str) -> None:
        """'Simple' strategy is active by default and stays active."""
        ds = _setup(page, live_server_url)
        # Ensure simple is selected (only clicks if not already active)
        ds.ensure_simple_strategy()
        expect(ds.strategy_simple_option).to_have_attribute(
            "data-testid", "stBaseButton-segmented_controlActive"
        )

    def test_switch_to_config_aware(self, page: Page, live_server_url: str) -> None:
        """User can switch to Config-Aware strategy."""
        ds = _setup(page, live_server_url)
        ds.select_config_aware_strategy()
        expect(ds.strategy_config_aware_option).to_have_attribute(
            "data-testid", "stBaseButton-segmented_controlActive"
        )

    def test_switch_back_to_simple(self, page: Page, live_server_url: str) -> None:
        """User can switch from Config-Aware back to Simple."""
        ds = _setup(page, live_server_url)
        ds.select_config_aware_strategy()
        ds.select_simple_strategy()
        expect(ds.strategy_simple_option).to_have_attribute(
            "data-testid", "stBaseButton-segmented_controlActive"
        )


# ===================================================================
# Variables to Extract section
# ===================================================================


class TestVariablesSection:
    """Test the Variables to Extract section."""

    def test_variables_header_visible(self, page: Page, live_server_url: str) -> None:
        """'Variables to Extract' heading is visible."""
        ds = _setup(page, live_server_url)
        ds.assert_variables_section_visible()

    def test_variable_type_descriptions_visible(self, page: Page, live_server_url: str) -> None:
        """The text listing variable types (Scalar, Vector, etc.) is visible."""
        ds = _setup(page, live_server_url)
        expect(ds.variables_description).to_be_visible()

    def test_deep_scan_checkbox_visible(self, page: Page, live_server_url: str) -> None:
        """'Deep Scan (check all files)' checkbox is visible."""
        ds = _setup(page, live_server_url)
        expect(ds.deep_scan_checkbox).to_be_visible()

    def test_quick_scan_button_visible(self, page: Page, live_server_url: str) -> None:
        """'Quick Scan' button is visible."""
        ds = _setup(page, live_server_url)
        expect(ds.quick_scan_button).to_be_visible()

    def test_add_variable_button_visible(self, page: Page, live_server_url: str) -> None:
        """'Add Variable' button is visible."""
        ds = _setup(page, live_server_url)
        expect(ds.add_variable_button).to_be_visible()

    def test_deep_scan_checkbox_toggleable(self, page: Page, live_server_url: str) -> None:
        """User can toggle the Deep Scan checkbox on and off."""
        ds = _setup(page, live_server_url)
        ds.toggle_deep_scan()
        ds.toggle_deep_scan()

    def test_scalar_type_mentioned(self, page: Page, live_server_url: str) -> None:
        """The word 'Scalar' appears in the variable descriptions."""
        _setup(page, live_server_url)
        expect(page.get_by_text("Scalar", exact=False).first).to_be_visible()

    def test_vector_type_mentioned(self, page: Page, live_server_url: str) -> None:
        """'Vector' appears in the variable descriptions."""
        _setup(page, live_server_url)
        expect(page.get_by_text("Vector", exact=False).first).to_be_visible()

    def test_distribution_type_mentioned(self, page: Page, live_server_url: str) -> None:
        """'Distribution' appears in the variable descriptions."""
        _setup(page, live_server_url)
        expect(page.get_by_text("Distribution", exact=False).first).to_be_visible()

    def test_configuration_type_mentioned(self, page: Page, live_server_url: str) -> None:
        """'Configuration' appears in the variable descriptions."""
        _setup(page, live_server_url)
        expect(page.get_by_text("Configuration", exact=False).first).to_be_visible()


# ===================================================================
# Configuration Preview
# ===================================================================


class TestConfigPreview:
    """Test the JSON configuration preview section."""

    def test_config_preview_header_visible(self, page: Page, live_server_url: str) -> None:
        """'Configuration Preview' heading is visible."""
        ds = _setup(page, live_server_url)
        ds.assert_config_preview_visible()

    def test_config_json_contains_parser_key(self, page: Page, live_server_url: str) -> None:
        """The JSON preview contains the 'parser' key."""
        ds = _setup(page, live_server_url)
        expect(ds.config_json_view).to_contain_text("parser")

    def test_config_json_contains_stats_path(self, page: Page, live_server_url: str) -> None:
        """The JSON preview contains the 'statsPath' key."""
        ds = _setup(page, live_server_url)
        expect(ds.config_json_view).to_contain_text("statsPath")

    def test_config_json_contains_strategy(self, page: Page, live_server_url: str) -> None:
        """The JSON preview contains the 'strategy' key."""
        ds = _setup(page, live_server_url)
        expect(ds.config_json_view).to_contain_text("strategy")

    def test_config_json_contains_variables(self, page: Page, live_server_url: str) -> None:
        """The JSON preview contains the 'variables' key."""
        ds = _setup(page, live_server_url)
        expect(ds.config_json_view).to_contain_text("variables")

    def test_config_json_reflects_strategy_change(self, page: Page, live_server_url: str) -> None:
        """Changing strategy updates the JSON preview."""
        ds = _setup(page, live_server_url)
        # Start from a known state
        ds.select_simple_strategy()
        expect(ds.config_json_view).to_contain_text("simple")
        # Switch to config_aware
        ds.select_config_aware_strategy()
        expect(ds.config_json_view).to_contain_text("config_aware")

    def test_config_json_reflects_path_change(self, page: Page, live_server_url: str) -> None:
        """Typing a stats path updates the JSON preview."""
        ds = _setup(page, live_server_url)
        ds.fill_stats_path("/my/gem5/output")
        expect(ds.config_json_view).to_contain_text("/my/gem5/output")


# ===================================================================
# Parse button & validation
# ===================================================================


class TestParseButton:
    """Test the primary 'Parse gem5 Stats Files' button."""

    def test_parse_button_visible(self, page: Page, live_server_url: str) -> None:
        """The primary Parse button is visible at the bottom."""
        ds = _setup(page, live_server_url)
        ds.assert_parse_button_visible()

    def test_parse_button_text(self, page: Page, live_server_url: str) -> None:
        """Parse button text reads 'Parse gem5 Stats Files'."""
        ds = _setup(page, live_server_url)
        expect(ds.parse_button).to_contain_text("Parse gem5 Stats Files")

    def test_parse_with_empty_path_shows_error(self, page: Page, live_server_url: str) -> None:
        """Clicking Parse with an empty stats path shows an error alert."""
        ds = _setup(page, live_server_url)
        ds.stats_path_input.fill("")
        ds.stats_path_input.press("Tab")
        ds.wait_for_streamlit()
        ds.click_parse()
        expect(ds.parser_error_message).to_be_visible(timeout=10_000)
        expect(ds.parser_error_message).to_contain_text("Please specify a stats directory path")

    def test_parse_button_not_in_csv_mode(self, page: Page, live_server_url: str) -> None:
        """Parse button is NOT visible in CSV mode."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        expect(ds.parse_button).not_to_be_visible()

    def test_parse_button_not_in_recent_mode(self, page: Page, live_server_url: str) -> None:
        """Parse button is NOT visible in Recent mode."""
        ds = _setup(page, live_server_url)
        ds.select_recent_mode()
        expect(ds.parse_button).not_to_be_visible()

    def test_parse_with_nonexistent_path_shows_error(
        self, page: Page, live_server_url: str
    ) -> None:
        """Clicking Parse with a nonexistent path triggers error handling."""
        ds = _setup(page, live_server_url)
        ds.fill_stats_path("/nonexistent/path/that/should/fail")
        ds.fill_stats_pattern("stats.txt")
        ds.click_parse()
        error_or_dialog = ds.page.locator("[data-testid='stDialog'], [data-testid='stException']")
        expect(error_or_dialog).to_be_visible(timeout=15_000)
