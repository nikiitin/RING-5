"""Focused browser proof for assigning and reusing workspace organization."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.workspace_organizer import WorkspaceOrganizer


@pytest.mark.requires_browser
@pytest.mark.xdist_group("e2e_workspace_organizer")
class TestWorkspaceOrganizer:
    def test_variable_can_be_favorited_tagged_and_reopened(self, shared_page: Page) -> None:
        # [test->req~ring5.workspace.favorites-tags~1]
        source = DataSourcePage(shared_page)
        source.navigate()
        source.ensure_parse_mode()

        organizer = WorkspaceOrganizer(shared_page)
        organizer.organize("Nightly, paper", favorite=True)
        organizer.open()

        expect(organizer.artifact_select).to_have_value(
            "★ Variable · benchmark_name · nightly, paper"
        )
