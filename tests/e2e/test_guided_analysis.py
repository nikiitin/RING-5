"""Browser proof for guided source-to-export progress."""

from __future__ import annotations

import pytest
from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, expect

from tests.visual.pages.data_managers_page import DataManagersPage
from tests.visual.pages.guided_analysis import GuidedAnalysis
from tests.visual.pages.manage_plots_page import ManagePlotsPage


def _select_dropdown_option(page: Page, selectbox: Locator, text: str) -> None:
    """Select one Streamlit selectbox option despite transient rerenders."""
    option = page.get_by_role("option", name=text, exact=True).first
    for _ in range(3):
        selectbox.get_by_role("combobox").click()
        try:
            option.wait_for(state="visible", timeout=5_000)
            option.click(timeout=5_000)
        except PlaywrightTimeoutError:
            page.keyboard.press("Escape")
            page.wait_for_timeout(250)
            continue
        return
    expect(option).to_be_visible(timeout=30_000)


def _add_multiselect_option(page: Page, multiselect: Locator, text: str) -> None:
    """Add one exact option to a Streamlit multiselect."""
    multiselect.click()
    multiselect.locator("input").fill(text)
    option = page.get_by_role("option", name=text, exact=True).first
    expect(option).to_be_visible(timeout=30_000)
    option.click()
    page.wait_for_timeout(200)


@pytest.mark.requires_browser
@pytest.mark.serial
@pytest.mark.timeout(240)
@pytest.mark.xdist_group("e2e_guided_analysis")
class TestGuidedAnalysis:
    """Follow the guide over a loaded and already-rendered Tier 2 workspace."""

    def test_guides_comparison_then_records_a_real_figure_download(
        self,
        tier2_page: Page,
    ) -> None:
        # [test->req~ring5.workspace.guided-analysis~1]
        guide = GuidedAnalysis(tier2_page)
        guide.open()
        expect(guide.current_step).to_contain_text("Step 3 of 5: Set up a comparison")
        expect(guide.next_action).to_have_text("Configure comparison")
        guide.follow_next_action()

        managers = DataManagersPage(tier2_page)
        managers.select_tab("Compare")
        _select_dropdown_option(
            tier2_page,
            managers.comparison_group_selectbox,
            "config_description",
        )
        managers.wait_for_streamlit()
        _add_multiselect_option(
            tier2_page,
            managers.comparison_metrics_multiselect,
            "system.cpu.ipc",
        )
        managers.wait_for_streamlit()
        _add_multiselect_option(
            tier2_page,
            managers.comparison_keys_multiselect,
            "benchmark_name",
        )
        managers.wait_for_streamlit()
        _add_multiselect_option(tier2_page, managers.comparison_keys_multiselect, "seed")
        tier2_page.keyboard.press("Escape")
        managers.apply_comparison()
        expect(managers.comparison_confirm_button).to_be_visible(timeout=30_000)

        guide.open()
        expect(guide.current_step).to_contain_text("Step 5 of 5: Export the result")
        expect(guide.next_action).to_have_text("Open export controls")
        guide.follow_next_action()

        plots = ManagePlotsPage(tier2_page)
        if not plots.download_expander.locator("[data-testid='stExpanderDetails']").is_visible():
            plots.download_expander.locator("summary").click()
        expect(plots.download_button).to_be_visible(timeout=30_000)
        with tier2_page.expect_download(timeout=30_000):
            plots.download_button.click()
        plots.wait_for_streamlit(expect_rerun=True)

        guide.open()
        expect(guide.completion_message).to_be_visible(timeout=30_000)
