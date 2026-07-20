"""Browser workflow for composing and exporting a multi-panel dashboard."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = [pytest.mark.requires_browser, pytest.mark.xdist_group("e2e_dashboard_composer")]


def test_build_and_offer_whole_dashboard_export(tier2_page: Page) -> None:
    # [test->req~ring5.plots.multi-panel-dashboard~1]
    manager = ManagePlotsPage(tier2_page)
    manager.navigate()
    manager.select_plot("E2E Bar")
    manager.duplicate_plot()
    expect(manager.plot_selector_pills.get_by_role("radio")).to_have_count(2, timeout=E2E_TIMEOUT)

    composer = tier2_page.get_by_text("Multi-panel dashboard").last
    expect(composer).to_be_visible(timeout=E2E_TIMEOUT)
    composer.click()

    tier2_page.get_by_role("button", name="Build dashboard").click()
    expect(tier2_page.get_by_role("button", name="Download complete HTML")).to_be_visible(
        timeout=CHART_TIMEOUT
    )
