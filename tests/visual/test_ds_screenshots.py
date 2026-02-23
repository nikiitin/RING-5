"""Visual tests for Data Source page — screenshot capture.

Split from the monolithic test_data_source.py for maintainability.
Captures screenshots of every major Data Source state for documentation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = pytest.mark.requires_browser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(page: Page, live_server_url: str) -> DataSourcePage:
    """Navigate to the Data Source page and wait for it to load."""
    ds = DataSourcePage(page)
    ds.goto_and_wait(live_server_url)
    ds.assert_step_header_visible()
    return ds


# ===================================================================
# Screenshots for documentation
# ===================================================================


class TestDataSourceScreenshots:
    """Capture screenshots of every major state for documentation."""

    def test_capture_initial_state(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the Data Source page in its default (Parse) state."""
        ds = _setup(page, live_server_url)
        ds.screenshot(screenshot_dir / "data_source_initial.png")

    def test_capture_csv_mode(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the CSV mode view."""
        ds = _setup(page, live_server_url)
        ds.select_csv_mode()
        ds.screenshot(screenshot_dir / "data_source_csv_mode.png")

    def test_capture_recent_mode(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the Recent mode view with empty pool."""
        ds = _setup(page, live_server_url)
        ds.select_recent_mode()
        ds.screenshot(screenshot_dir / "data_source_recent_mode.png")

    def test_capture_sidebar(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture sidebar navigation for documentation."""
        ds = _setup(page, live_server_url)
        ds.screenshot_element(ds.sidebar, screenshot_dir / "sidebar.png")

    def test_capture_config_aware_strategy(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the page with Config-Aware strategy selected."""
        ds = _setup(page, live_server_url)
        ds.select_config_aware_strategy()
        ds.screenshot(screenshot_dir / "data_source_config_aware.png")

    def test_capture_add_variable_dialog(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the Add Variable dialog in Search mode."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.screenshot(screenshot_dir / "add_variable_dialog_search.png")

    def test_capture_add_variable_dialog_manual(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the Add Variable dialog in Manual Entry mode."""
        ds = _setup(page, live_server_url)
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.screenshot(screenshot_dir / "add_variable_dialog_manual.png")

    def test_capture_parse_error_empty_path(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the error state when parsing with empty path."""
        ds = _setup(page, live_server_url)
        ds.stats_path_input.fill("")
        ds.stats_path_input.press("Tab")
        ds.wait_for_streamlit()
        ds.click_parse()
        ds.page.wait_for_timeout(2000)
        ds.screenshot(screenshot_dir / "parse_error_empty_path.png")

    def test_capture_filled_paths(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the page with custom stats path and pattern filled in."""
        ds = _setup(page, live_server_url)
        ds.fill_stats_path("/data/gem5_output/simulations")
        ds.fill_stats_pattern("stats.txt")
        ds.screenshot(screenshot_dir / "data_source_paths_filled.png")

    def test_capture_segmented_control(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the segmented control element."""
        ds = _setup(page, live_server_url)
        ds.screenshot_element(
            ds.segmented_control,
            screenshot_dir / "segmented_control.png",
        )
