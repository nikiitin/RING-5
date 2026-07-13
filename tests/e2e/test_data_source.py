"""E2E tests for the Data Source page.

Covers page structure, mode switching, Add Variable dialog interactions,
and CSV upload workflow.  All classes use ``tier0_page`` (fresh app at
home page) and the ``xdist_group`` marker to ensure serial execution
within the group.

Test tiers:
- TestDataSourcePageStructure  -- layout, segmented control, mode content
- TestDataSourceVariableDialog -- Add Variable dialog lifecycle & validation
- TestDataSourceCsvUpload      -- CSV upload and data verification
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = pytest.mark.requires_browser


# Tier 0: Page structure and mode switching


@pytest.mark.xdist_group("e2e_data_source")
class TestDataSourcePageStructure:
    """Tier 0: Verify page layout and mode switching."""

    def test_page_loads_with_header(self, tier0_page: Page) -> None:
        """Navigate to Data Source and verify core elements render."""
        ds = DataSourcePage(tier0_page)
        ds.navigate()
        ds.assert_step_header_visible()
        ds.assert_info_box_visible()
        ds.assert_segmented_control_visible()

    def test_parse_mode_can_be_selected(self, tier0_page: Page) -> None:
        """Parse mode can be selected and shows its configuration."""
        ds = DataSourcePage(tier0_page)
        ds.ensure_parse_mode()
        ds.assert_parse_mode_active()
        ds.assert_parser_config_visible()

    def test_all_mode_options_visible(self, tier0_page: Page) -> None:
        """All three mode buttons render in the segmented control."""
        ds = DataSourcePage(tier0_page)
        ds.assert_all_mode_options_visible()

    def test_parser_file_location_visible(self, tier0_page: Page) -> None:
        """File Location section with path and pattern inputs is visible."""
        ds = DataSourcePage(tier0_page)
        ds.ensure_parse_mode()
        ds.assert_file_location_visible()

    def test_parser_strategy_section_visible(self, tier0_page: Page) -> None:
        """Parsing Strategy section with Simple/Config-Aware options is visible."""
        ds = DataSourcePage(tier0_page)
        ds.ensure_parse_mode()
        ds.assert_strategy_section_visible()

    def test_parser_variables_section_visible(self, tier0_page: Page) -> None:
        """Variables to Extract section with scan and add buttons is visible."""
        ds = DataSourcePage(tier0_page)
        ds.ensure_parse_mode()
        ds.assert_variables_section_visible()

    def test_config_preview_and_parse_button(self, tier0_page: Page) -> None:
        """Configuration Preview and Parse button are visible in parse mode."""
        ds = DataSourcePage(tier0_page)
        ds.ensure_parse_mode()
        ds.assert_config_preview_visible()
        ds.assert_parse_button_visible()

    def test_recent_mode_shows_pool(self, tier0_page: Page) -> None:
        """Switching to Recent mode shows pool content and hides parser config."""
        ds = DataSourcePage(tier0_page)
        ds.select_recent_mode()
        ds.assert_recent_mode_content_visible()
        ds.assert_parser_config_hidden()

    def test_mode_switching_round_trip(self, tier0_page: Page) -> None:
        """Cycling parse -> csv -> recent -> parse restores correct content."""
        ds = DataSourcePage(tier0_page)
        # Parse
        ds.select_parse_mode()
        ds.assert_parse_mode_active()
        ds.assert_parser_config_visible()
        # CSV
        ds.select_csv_mode()
        ds.assert_csv_mode_active()
        ds.assert_csv_mode_message_visible()
        # Recent
        ds.select_recent_mode()
        ds.assert_recent_mode_active()
        ds.assert_recent_mode_content_visible()
        # Back to Parse
        ds.select_parse_mode()
        ds.assert_parse_mode_active()
        ds.assert_parser_config_visible()


# Tier 0: Add Variable dialog interactions


@pytest.mark.xdist_group("e2e_data_source")
class TestDataSourceVariableDialog:
    """Tier 0: Add Variable dialog interactions."""

    def test_dialog_opens_and_closes(self, tier0_page: Page) -> None:
        """Open Add Variable dialog with button, close with X."""
        ds = DataSourcePage(tier0_page)
        ds.navigate()
        ds.ensure_parse_mode()
        ds.open_add_variable_dialog()
        ds.assert_dialog_visible()
        ds.close_dialog()
        ds.assert_dialog_hidden()

    def test_dialog_close_with_escape(self, tier0_page: Page) -> None:
        """Dialog can be dismissed with the Escape key."""
        ds = DataSourcePage(tier0_page)
        ds.open_add_variable_dialog()
        ds.assert_dialog_visible()
        ds.close_dialog_with_escape()
        ds.assert_dialog_hidden()

    def test_dialog_close_by_clicking_outside(self, tier0_page: Page) -> None:
        """Dialog can be dismissed by clicking outside the modal."""
        ds = DataSourcePage(tier0_page)
        ds.open_add_variable_dialog()
        ds.assert_dialog_visible()
        ds.close_dialog_by_clicking_outside()
        ds.assert_dialog_hidden()

    def test_dialog_search_mode_can_be_selected(self, tier0_page: Page) -> None:
        """The dialog exposes and selects Search Scanned Variables mode."""
        ds = DataSourcePage(tier0_page)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_search()
        expect(ds.dialog_search_pill).to_be_visible()
        expect(ds.dialog_search_pill).to_be_checked()
        expect(ds.dialog_manual_pill).to_be_visible()
        ds.close_dialog()

    def test_dialog_no_scanned_vars_warning(self, tier0_page: Page) -> None:
        """Search mode shows warning when no variables have been scanned."""
        ds = DataSourcePage(tier0_page)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_search()
        expect(ds.dialog_no_vars_warning).to_be_visible()
        ds.close_dialog()

    def test_dialog_manual_entry_mode(self, tier0_page: Page) -> None:
        """Switching to Manual Entry shows name input and type selector."""
        ds = DataSourcePage(tier0_page)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        expect(ds.dialog_manual_name_input).to_be_visible()
        expect(ds.dialog_manual_type_selectbox).to_be_visible()
        ds.close_dialog()

    def test_dialog_has_advanced_options(self, tier0_page: Page) -> None:
        """Dialog contains an Advanced Options expander in Manual mode."""
        ds = DataSourcePage(tier0_page)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.fill_dialog_manual_name("test_var")
        expect(ds.dialog_advanced_expander).to_be_visible()
        ds.close_dialog()

    def test_dialog_switch_manual_then_search(self, tier0_page: Page) -> None:
        """Switching from Manual back to Search restores search UI."""
        ds = DataSourcePage(tier0_page)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        expect(ds.dialog_manual_name_input).to_be_visible()
        ds.switch_dialog_to_search()
        expect(ds.dialog_no_vars_warning).to_be_visible()
        ds.close_dialog()

    def test_dialog_add_button_visible(self, tier0_page: Page) -> None:
        """Add to Configuration button is visible in Manual mode."""
        ds = DataSourcePage(tier0_page)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.fill_dialog_manual_name("test_var")
        expect(ds.dialog_add_button).to_be_visible()
        ds.close_dialog()

    def test_dialog_add_empty_name_shows_error(self, tier0_page: Page) -> None:
        """Clicking Add without entering a name shows validation error."""
        ds = DataSourcePage(tier0_page)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        # Fill then clear to trigger dirty state
        ds.fill_dialog_manual_name("temp")
        ds.dialog_manual_name_input.fill("")
        ds.dialog_manual_name_input.press("Tab")
        ds.wait_for_streamlit()
        ds.click_dialog_add()
        expect(ds.dialog_name_error).to_be_visible()
        ds.close_dialog()


# Tier 0: CSV load-from-pool workflow


@pytest.mark.xdist_group("e2e_data_source")
class TestDataSourceCsvLoad:
    """Tier 0: CSV load-from-pool workflow.

    The legacy st.file_uploader was removed; CSVs are loaded via the
    'Load from Recent' pool (``DataSourcePage.upload_csv`` stages the file into
    the pool, then loads it). These tests cover the mode message + the real
    load path.
    """

    def test_csv_mode_shows_success_message(self, tier0_page: Page) -> None:
        """CSV mode displays the mode selection success message."""
        ds = DataSourcePage(tier0_page)
        ds.navigate()
        ds.select_csv_mode()
        ds.assert_csv_mode_message_visible()

    def test_csv_mode_hides_parser_config(self, tier0_page: Page) -> None:
        """CSV mode hides the parser configuration section."""
        ds = DataSourcePage(tier0_page)
        ds.navigate()
        ds.select_csv_mode()
        ds.assert_parser_config_hidden()

    def test_csv_load_loads_data(self, tier0_page: Page, e2e_csv_path: Path) -> None:
        """Load the fixture CSV via the Recent pool and verify data is loaded."""
        ds = DataSourcePage(tier0_page)
        ds.navigate()
        ds.upload_csv(e2e_csv_path)
        tier0_page.wait_for_timeout(1000)
        ds.assert_data_loaded()

    def test_csv_load_shows_row_count(self, tier0_page: Page, e2e_csv_path: Path) -> None:
        """The loaded CSV shows the correct row count (18 rows)."""
        ds = DataSourcePage(tier0_page)
        ds.navigate()
        ds.upload_csv(e2e_csv_path)
        ds.assert_data_loaded(row_count=18)
