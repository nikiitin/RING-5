"""Browser workflow for reversible plot-point source-row exploration."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import E2E_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = [pytest.mark.requires_browser, pytest.mark.xdist_group("e2e_plot_drill_down")]


def test_point_drill_down_shows_source_rows_and_returns_with_config(tier2_page: Page) -> None:
    # [test->req~ring5.plots.drill-down~1]
    manager = ManagePlotsPage(tier2_page)
    manager.navigate()
    manager.select_plot("E2E Bar")
    expect(manager.viz_x_axis_selectbox.get_by_role("combobox")).to_have_value("benchmark_name")

    manager.enable_drill_down()
    manager.click_first_plot_point()

    expect(manager.drill_down_panel).to_be_visible(timeout=E2E_TIMEOUT)
    expect(tier2_page.get_by_text("Matching rows", exact=True)).to_be_visible(timeout=E2E_TIMEOUT)
    expect(tier2_page.locator("[data-testid='stDataFrame']").last).to_be_visible(
        timeout=E2E_TIMEOUT
    )

    manager.drill_down_back_button.click()
    manager.wait_for_streamlit(expect_rerun=True)
    expect(manager.drill_down_panel).to_be_hidden(timeout=E2E_TIMEOUT)
    expect(manager.viz_x_axis_selectbox.get_by_role("combobox")).to_have_value("benchmark_name")
