"""Focused browser proof for human-first workspace search."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.workspace_search import WorkspaceSearch


@pytest.mark.requires_browser
@pytest.mark.xdist_group("e2e_workspace_search")
class TestWorkspaceSearch:
    def test_search_opens_commands_and_links_exact_guides(self, shared_page: Page) -> None:
        # [test->req~ring5.workspace.global-search~1]
        search = WorkspaceSearch(shared_page)
        search.search("plot types")

        guide = search.link_result("Guide · Plot types")
        expect(guide).to_be_visible()
        expect(guide).to_have_attribute(
            "href",
            "https://nikiitin.github.io/RING-5/user-guide/reference/plot-types/",
        )

        search.search("data source")
        command = search.button_result("Command · Go to Data Source")
        expect(command).to_be_visible()
        command.click()
        search.wait_for_streamlit(expect_rerun=True)

        DataSourcePage(shared_page).assert_step_header_visible()
