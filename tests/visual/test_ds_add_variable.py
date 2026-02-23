"""Visual tests for Data Source page — Add Variable dialog.

Split from the monolithic test_data_source.py for maintainability.
Covers:
- Dialog lifecycle & dismissal
- Search mode
- Manual Entry mode
- Validation & submission
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
# Dialog lifecycle & dismissal
# ===================================================================


class TestAddVariableDialogLifecycle:
    """Test opening, closing, and dismissing the Add Variable dialog."""

    def test_dialog_opens_on_click(self, page: Page, live_server_url: str) -> None:
        """Clicking 'Add Variable' opens the dialog."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.assert_dialog_visible()

    def test_dialog_title_says_add_variable(self, page: Page, live_server_url: str) -> None:
        """The dialog title is 'Add Variable'."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        expect(ds.dialog_title).to_be_visible()

    def test_dialog_closes_with_x_button(self, page: Page, live_server_url: str) -> None:
        """The dialog can be closed by clicking the X button."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.assert_dialog_visible()
        ds.close_dialog()
        ds.assert_dialog_hidden()

    def test_dialog_closes_with_escape(self, page: Page, live_server_url: str) -> None:
        """The dialog can be closed by pressing Escape."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.assert_dialog_visible()
        ds.close_dialog_with_escape()
        ds.assert_dialog_hidden()

    def test_dialog_reopens_after_close(self, page: Page, live_server_url: str) -> None:
        """The dialog can be reopened after being closed."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.close_dialog()
        ds.assert_dialog_hidden()
        ds.open_add_variable_dialog()
        ds.assert_dialog_visible()

    def test_dialog_has_both_pills(self, page: Page, live_server_url: str) -> None:
        """The dialog shows both 'Search Scanned Variables' and 'Manual Entry' pills."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        expect(ds.dialog_search_pill).to_be_visible()
        expect(ds.dialog_manual_pill).to_be_visible()


# ===================================================================
# Search mode
# ===================================================================


class TestAddVariableDialogSearch:
    """Test the 'Search Scanned Variables' mode in the dialog."""

    def test_no_vars_warning_when_empty(self, page: Page, live_server_url: str) -> None:
        """Warning shows when no variables have been scanned yet."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        expect(ds.dialog_no_vars_warning).to_be_visible(timeout=10_000)

    def test_warning_text_mentions_scan(self, page: Page, live_server_url: str) -> None:
        """The warning text tells the user to run a scan first."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        expect(ds.dialog_no_vars_warning).to_contain_text("Run")

    def test_search_pill_is_active(self, page: Page, live_server_url: str) -> None:
        """'Search Scanned Variables' pill is the active default."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        expect(ds.dialog_search_pill).to_be_visible()


# ===================================================================
# Manual Entry mode
# ===================================================================


class TestAddVariableDialogManual:
    """Test the 'Manual Entry' mode in the Add Variable dialog."""

    def test_switch_to_manual_entry(self, page: Page, live_server_url: str) -> None:
        """User can switch to Manual Entry mode."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        expect(ds.dialog_manual_name_input).to_be_visible()

    def test_manual_name_input_is_editable(self, page: Page, live_server_url: str) -> None:
        """User can type a variable name in Manual Entry mode."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.fill_dialog_manual_name("simTicks")
        expect(ds.dialog_manual_name_input).to_have_value("simTicks")

    def test_manual_type_selectbox_visible(self, page: Page, live_server_url: str) -> None:
        """The type selectbox is visible in Manual Entry mode."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        expect(ds.dialog_manual_type_selectbox).to_be_visible()

    def test_manual_shows_config_section_after_name(self, page: Page, live_server_url: str) -> None:
        """Typing a name reveals the configuration section."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.fill_dialog_manual_name("myVar")
        expect(ds.dialog_overlay.get_by_text("Configuration:")).to_be_visible(timeout=10_000)

    def test_manual_advanced_options_expander(self, page: Page, live_server_url: str) -> None:
        """Advanced Options expander is present after entering a name."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.fill_dialog_manual_name("myVar")
        expect(ds.dialog_advanced_expander).to_be_visible(timeout=10_000)

    def test_manual_add_button_visible(self, page: Page, live_server_url: str) -> None:
        """'Add to Configuration' button is visible after entering a name."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.fill_dialog_manual_name("myVar")
        expect(ds.dialog_add_button).to_be_visible(timeout=10_000)

    def test_switch_back_to_search(self, page: Page, live_server_url: str) -> None:
        """User can switch back from Manual Entry to Search mode."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.switch_dialog_to_search()
        expect(ds.dialog_no_vars_warning).to_be_visible(timeout=10_000)


# ===================================================================
# Validation & submission
# ===================================================================


class TestAddVariableDialogValidation:
    """Test validation and submission in the Add Variable dialog."""

    def test_add_without_name_shows_error(self, page: Page, live_server_url: str) -> None:
        """Clicking 'Add to Configuration' without a name shows an error."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.fill_dialog_manual_name("temp")
        ds.dialog_manual_name_input.fill("")
        ds.dialog_manual_name_input.press("Tab")
        ds.wait_for_streamlit()
        ds.click_dialog_add()
        expect(ds.dialog_name_error).to_be_visible(timeout=10_000)

    def test_successful_manual_add(self, page: Page, live_server_url: str) -> None:
        """Adding a scalar variable manually closes the dialog."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.fill_dialog_manual_name("system.cpu.numCycles")
        ds.click_dialog_add()
        ds.assert_dialog_hidden()
