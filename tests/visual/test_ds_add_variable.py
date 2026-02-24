"""Visual tests for Data Source page — Add Variable dialog.

Consolidated from 18 individual tests to 4 workflow-style tests using
a class-scoped ``shared_page`` fixture.

Covers:
- Dialog lifecycle (open, close, reopen, escape, pills)
- Search mode (warnings, pill state)
- Manual Entry workflow (switch, fill, config, advanced, add, switch back)
- Validation and submission (empty name error, successful add)
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = pytest.mark.requires_browser


class TestAddVariableDialog:
    """Consolidated Add Variable dialog tests.

    Uses ``shared_page`` (class-scoped) so the browser tab is created once
    and reused across all four tests.
    """

    def test_dialog_lifecycle(self, shared_page: Page, live_server_url: str) -> None:
        """Dialog opens, closes (X button & Escape), and reopens correctly.

        Consolidates 6 original tests:
        - Dialog opens on click
        - Dialog title says 'Add Variable'
        - Dialog closes with X button
        - Dialog closes with Escape
        - Dialog reopens after close
        - Dialog has both 'Search Scanned Variables' and 'Manual Entry' pills
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        # Open dialog
        ds.open_add_variable_dialog()
        ds.assert_dialog_visible()
        expect(ds.dialog_title).to_be_visible()

        # Both pills present
        expect(ds.dialog_search_pill).to_be_visible()
        expect(ds.dialog_manual_pill).to_be_visible()

        # Close with X button
        ds.close_dialog()
        ds.assert_dialog_hidden()

        # Reopen
        ds.open_add_variable_dialog()
        ds.assert_dialog_visible()

        # Close with Escape
        ds.close_dialog_with_escape()
        ds.assert_dialog_hidden()

    def test_search_mode(self, shared_page: Page, live_server_url: str) -> None:
        """Search mode shows warning when no variables are scanned.

        Consolidates 3 original tests:
        - No vars warning when empty
        - Warning text mentions scan/Run
        - Search pill is active/visible
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        ds.open_add_variable_dialog()

        # Search pill active by default
        expect(ds.dialog_search_pill).to_be_visible()

        # Warning about no scanned variables
        expect(ds.dialog_no_vars_warning).to_be_visible(timeout=10_000)
        expect(ds.dialog_no_vars_warning).to_contain_text("Run")

        ds.close_dialog()

    def test_manual_entry_workflow(self, shared_page: Page, live_server_url: str) -> None:
        """Manual Entry mode: switch, fill name, see config & advanced, switch back.

        Consolidates 7 original tests:
        - Switch to Manual Entry mode
        - Name input is editable
        - Type selectbox visible
        - Typing name reveals configuration section
        - Advanced Options expander present
        - 'Add to Configuration' button visible
        - Can switch back to Search mode
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()

        # Name input visible and editable
        expect(ds.dialog_manual_name_input).to_be_visible()
        ds.fill_dialog_manual_name("simTicks")
        expect(ds.dialog_manual_name_input).to_have_value("simTicks")

        # Type selectbox visible
        expect(ds.dialog_manual_type_selectbox).to_be_visible()

        # Filling a name reveals configuration section and advanced options
        ds.dialog_manual_name_input.fill("")
        ds.fill_dialog_manual_name("myVar")
        expect(ds.dialog_overlay.get_by_text("Configuration:")).to_be_visible(timeout=10_000)
        expect(ds.dialog_advanced_expander).to_be_visible(timeout=10_000)
        expect(ds.dialog_add_button).to_be_visible(timeout=10_000)

        # Switch back to Search mode
        ds.switch_dialog_to_search()
        expect(ds.dialog_no_vars_warning).to_be_visible(timeout=10_000)

        ds.close_dialog()

    def test_validation_and_add(self, shared_page: Page, live_server_url: str) -> None:
        """Validation errors and successful manual add work correctly.

        Consolidates 2 original tests:
        - Add without name shows error
        - Successful manual add closes the dialog
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        # Empty name shows error
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.fill_dialog_manual_name("temp")
        ds.dialog_manual_name_input.fill("")
        ds.dialog_manual_name_input.press("Tab")
        ds.wait_for_streamlit()
        ds.click_dialog_add()
        expect(ds.dialog_name_error).to_be_visible(timeout=10_000)
        ds.close_dialog()

        # Successful add closes dialog
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.fill_dialog_manual_name("system.cpu.numCycles")
        ds.click_dialog_add()
        ds.assert_dialog_hidden()
