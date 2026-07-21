"""Focused browser proof for the command palette and keyboard shortcuts."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.command_palette import CommandPalette
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.workspace_search import WorkspaceSearch


@pytest.mark.requires_browser
@pytest.mark.xdist_group("e2e_command_palette")
class TestCommandPalette:
    def test_keyboard_palette_discovers_and_runs_a_command(self, shared_page: Page) -> None:
        # [test->req~ring5.workspace.command-palette~1]
        palette = CommandPalette(shared_page)
        palette.open_with_shortcut()

        palette.search("plot pipeline")
        result = palette.command("Go to Manage Plots · Alt+3")
        expect(result).to_be_visible()
        result.click()
        palette.wait_for_streamlit(expect_rerun=True)

        ManagePlotsPage(shared_page).assert_page_header_visible()

        shared_page.keyboard.press("Alt+1")
        palette.wait_for_streamlit(expect_rerun=True)
        DataSourcePage(shared_page).assert_step_header_visible()

        shared_page.keyboard.press("/")
        search = WorkspaceSearch(shared_page)
        expect(search.input).to_be_visible()
        expect(search.input).to_be_focused()
