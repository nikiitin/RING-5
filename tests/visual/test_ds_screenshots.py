"""Documentation screenshots for the principal Data Source states."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = pytest.mark.requires_browser


class TestDataSourceScreenshots:
    """Ordered screenshot-capture checks.

    Uses ``shared_page`` (class-scoped) so the browser tab is created once
    and reused across all three tests.
    """

    def test_parse_mode_screenshots(
        self,
        shared_page: Page,
        live_server_url: str,
        shared_screenshot_dir: Path,
    ) -> None:
        """Capture Parse mode screenshots: initial, config-aware, paths, error.

        - capture_initial_state
        - capture_config_aware_strategy
        - capture_filled_paths
        - capture_parse_error_empty_path
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        # Initial state
        ds.screenshot(shared_screenshot_dir / "data_source_initial.png")

        # Config-Aware strategy
        ds.select_config_aware_strategy()
        ds.screenshot(shared_screenshot_dir / "data_source_config_aware.png")

        # Filled paths
        ds.select_simple_strategy()
        ds.fill_stats_path("/data/gem5_output/simulations")
        ds.fill_stats_pattern("stats.txt")
        ds.screenshot(shared_screenshot_dir / "data_source_paths_filled.png")

        # Parse error (empty path)
        ds.stats_path_input.fill("")
        ds.stats_path_input.press("Tab")
        ds.wait_for_streamlit()
        ds.click_parse()
        ds.page.wait_for_timeout(2000)
        ds.screenshot(shared_screenshot_dir / "parse_error_empty_path.png")

    def test_other_mode_screenshots(
        self,
        shared_page: Page,
        live_server_url: str,
        shared_screenshot_dir: Path,
    ) -> None:
        """Capture CSV, Recent, sidebar, and segmented control screenshots.

        - capture_csv_mode
        - capture_recent_mode
        - capture_sidebar
        - capture_segmented_control
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        # Segmented control close-up
        ds.screenshot_element(
            ds.segmented_control,
            shared_screenshot_dir / "segmented_control.png",
        )

        # Sidebar close-up
        ds.screenshot_element(ds.sidebar, shared_screenshot_dir / "sidebar.png")

        # CSV mode
        ds.select_csv_mode()
        ds.screenshot(shared_screenshot_dir / "data_source_csv_mode.png")

        # Recent mode
        ds.select_recent_mode()
        ds.screenshot(shared_screenshot_dir / "data_source_recent_mode.png")

    def test_dialog_screenshots(
        self,
        shared_page: Page,
        live_server_url: str,
        shared_screenshot_dir: Path,
    ) -> None:
        """Capture Add Variable dialog screenshots in Search and Manual modes.

        - capture_add_variable_dialog (search mode)
        - capture_add_variable_dialog_manual
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()

        # Search mode dialog
        ds.open_add_variable_dialog()
        ds.screenshot(shared_screenshot_dir / "add_variable_dialog_search.png")

        # Manual mode dialog
        ds.switch_dialog_to_manual()
        ds.screenshot(shared_screenshot_dir / "add_variable_dialog_manual.png")

        ds.close_dialog()
