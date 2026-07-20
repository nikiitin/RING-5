"""Browser workflow for copying selected plot settings without stale widget overwrite."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = [pytest.mark.requires_browser, pytest.mark.xdist_group("e2e_plot_transfer")]


def test_copy_selected_settings_reloads_destination_widgets(tier2_page: Page) -> None:
    # [test->req~ring5.plots.copy-settings-pipeline~1]
    manager = ManagePlotsPage(tier2_page)
    manager.navigate()
    manager.select_plot("E2E Bar")
    source_title = manager.viz_title_input.input_value()

    manager.duplicate_plot()
    manager.select_plot("E2E Bar (copy)")
    manager.viz_title_input.fill("Destination title")
    manager.refresh_plot()
    expect(manager.viz_title_input).to_have_value("Destination title", timeout=E2E_TIMEOUT)

    manager.copy_default_settings_from_other_plot()

    expect(manager.viz_title_input).to_have_value(source_title, timeout=5_000)
    manager.assert_chart_visible(timeout=CHART_TIMEOUT)
