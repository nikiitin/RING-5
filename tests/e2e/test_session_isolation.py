"""Browser-session isolation for mutable application workspaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest
from playwright.sync_api import Browser, BrowserContext

from tests.visual.pages.base_page import BasePage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser


def test_browser_sessions_keep_data_plots_and_reset_isolated(
    browser: Browser,
    browser_context_args: dict[str, object],
    live_server_url: str,
    tmp_path: Path,
) -> None:
    """Independent browser contexts cannot read or reset each other's state."""
    first_csv = tmp_path / "first_session.csv"
    second_csv = tmp_path / "second_session.csv"
    pd.DataFrame({"label": ["a", "b"], "value": [1, 2]}).to_csv(first_csv, index=False)
    pd.DataFrame({"label": ["x", "y", "z"], "value": [10, 20, 30]}).to_csv(second_csv, index=False)

    first_context: BrowserContext = browser.new_context(**cast(Any, browser_context_args))
    second_context: BrowserContext = browser.new_context(**cast(Any, browser_context_args))
    try:
        first_page = first_context.new_page()
        second_page = second_context.new_page()
        BasePage(first_page).goto_and_wait(live_server_url)
        BasePage(second_page).goto_and_wait(live_server_url)

        first_data = DataSourcePage(first_page)
        second_data = DataSourcePage(second_page)
        first_data.upload_csv(first_csv)
        second_data.upload_csv(second_csv)
        first_data.assert_data_loaded(row_count=2)
        second_data.assert_data_loaded(row_count=3)

        first_plots = ManagePlotsPage(first_page)
        second_plots = ManagePlotsPage(second_page)
        first_plots.navigate()
        first_plots.create_plot("First session plot", "bar")
        second_plots.navigate()
        second_plots.assert_plot_pill_not_visible("First session plot")
        second_plots.create_plot("Second session plot", "bar")
        first_plots.assert_plot_pill_not_visible("Second session plot")

        BasePage(first_page).reset_all()
        second_data.navigate()
        second_data.assert_data_loaded(row_count=3)
        second_plots.navigate()
        second_plots.assert_plot_pill_visible("Second session plot")
    finally:
        first_context.close()
        second_context.close()
