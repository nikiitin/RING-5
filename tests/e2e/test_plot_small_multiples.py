"""Browser workflow for comparing categorical groups as small multiples."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = [pytest.mark.requires_browser, pytest.mark.xdist_group("e2e_small_multiples")]


def test_small_multiples_keep_configuration_across_both_engines(tier2_page: Page) -> None:
    # [test->req~ring5.plots.small-multiples~1]
    manager = ManagePlotsPage(tier2_page)
    manager.navigate()
    manager.select_plot("E2E Bar")
    manager.open_layout_settings()
    manager.enable_small_multiples()
    manager.add_small_multiples_column("config_description")

    expect(
        tier2_page.get_by_text("3 panels, ordered by their first appearance in the data.")
    ).to_be_visible(timeout=E2E_TIMEOUT)
    manager.refresh_plot()
    manager.assert_chart_visible(timeout=CHART_TIMEOUT)

    frame = manager.plotly_chart.first.content_frame
    for value in ("baseline", "optimized", "aggressive"):
        expect(frame.get_by_text(f"config_description: {value}", exact=True)).to_be_visible(
            timeout=E2E_TIMEOUT
        )
    expect(manager.viz_x_axis_selectbox.get_by_role("combobox")).to_have_value("benchmark_name")

    manager.select_engine("matplotlib")
    manager.assert_matplotlib_chart_visible()
    expect(manager.small_multiples_toggle).to_be_checked(timeout=E2E_TIMEOUT)
