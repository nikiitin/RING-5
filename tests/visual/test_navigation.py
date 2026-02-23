"""Visual tests for cross-page navigation workflows.

These tests verify complete user journeys across multiple pages
and generate animated GIFs for project documentation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.visual.pages.base_page import BasePage

pytestmark = pytest.mark.requires_browser


class TestNavigationWorkflow:
    """Test full navigation workflow and capture documentation assets."""

    def test_navigate_all_pages(self, page: Page, live_server_url: str) -> None:
        """Navigate to every page via sidebar buttons."""
        bp = BasePage(page)
        bp.goto_and_wait(live_server_url)
        bp.assert_page_loaded()

        for page_name in [
            "Data Source",
            "Data Managers",
            "Manage Plots",
            "Save/Load Portfolio",
            "Performance",
        ]:
            bp.navigate_to(page_name)
            bp.assert_on_page(page_name)

    def test_generate_navigation_gif(
        self, page: Page, live_server_url: str, screenshot_dir: Path
    ) -> None:
        """Capture a GIF showing navigation through all pages."""
        bp = BasePage(page)
        bp.goto_and_wait(live_server_url)

        frames: list[Path] = []
        page_names = [
            "Data Source",
            "Data Managers",
            "Manage Plots",
            "Save/Load Portfolio",
            "Performance",
        ]

        # Capture landing page
        landing = screenshot_dir / "nav_step_0_landing.png"
        bp.screenshot(landing)
        frames.append(landing)

        # Capture each page
        for idx, page_name in enumerate(page_names, start=1):
            bp.navigate_to(page_name)
            frame_path = (
                screenshot_dir
                / f"nav_step_{idx}_{page_name.lower().replace('/', '_').replace(' ', '_')}.png"
            )
            bp.screenshot(frame_path)
            frames.append(frame_path)

        # Generate animated GIF
        gif_path = screenshot_dir / "navigation_workflow.gif"
        BasePage.create_gif(frames, gif_path, duration_ms=1200)
        assert gif_path.exists(), f"GIF was not created at {gif_path}"

    def test_return_to_home(self, page: Page, live_server_url: str) -> None:
        """Navigate away and back to Data Source (home)."""
        bp = BasePage(page)
        bp.goto_and_wait(live_server_url)

        # Go to Performance
        bp.navigate_to("Performance")
        bp.assert_on_page("Performance")

        # Return to Data Source
        bp.navigate_to("Data Source")
        bp.assert_on_page("Data Source")
