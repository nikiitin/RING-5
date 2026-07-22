"""Browser proof for recovery after replacing an interrupted session."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.autosave_recovery import AutosaveRecovery
from tests.visual.pages.base_page import BasePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage


@pytest.mark.requires_browser
@pytest.mark.xdist_group("e2e_autosave_recovery")
class TestAutosaveRecovery:
    def test_new_browser_session_explicitly_recovers_previous_plot(
        self,
        shared_page: Page,
    ) -> None:
        # [test->req~ring5.workspace.autosave-recovery~1]
        plots = ManagePlotsPage(shared_page)
        plots.navigate()
        plots.create_plot("Interrupted analysis", "bar")
        AutosaveRecovery(shared_page).assert_draft_available()

        replacement = shared_page.context.new_page()
        try:
            BasePage(replacement).goto_and_wait(shared_page.url)
            AutosaveRecovery(replacement).recover()

            recovered_plots = ManagePlotsPage(replacement)
            recovered_plots.navigate()
            expect(recovered_plots.get_plot_pill("Interrupted analysis").first).to_be_visible()
        finally:
            replacement.close()
