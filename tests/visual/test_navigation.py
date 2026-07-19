"""Visual tests for cross-page navigation and documentation capture."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.visual.pages.base_page import BasePage

pytestmark = pytest.mark.requires_browser


class TestNavigationWorkflow:
    """Ordered navigation checks.

    Uses ``shared_page`` (class-scoped) so the browser tab is created once
    and reused across both tests.
    """

    def test_navigate_all_pages_and_return(self, shared_page: Page, live_server_url: str) -> None:
        """Navigate to every page via sidebar and return to home.

        - navigate_all_pages
        - return_to_home
        """
        # [test->req~ring5.workspace.navigation~1]
        bp = BasePage(shared_page)
        bp.goto_and_wait(live_server_url)
        bp.assert_page_loaded()

        # Navigate through all pages
        for page_name in [
            "Data Source",
            "Data Managers",
            "Manage Plots",
            "Save/Load Portfolio",
        ]:
            bp.navigate_to(page_name)
            bp.assert_on_page(page_name)

        # Return to home
        bp.navigate_to("Data Source")
        bp.assert_on_page("Data Source")

    def test_generate_navigation_gif(
        self, shared_page: Page, live_server_url: str, shared_screenshot_dir: Path
    ) -> None:
        """Capture a GIF showing navigation through all pages."""
        bp = BasePage(shared_page)
        bp.goto_and_wait(live_server_url)

        frames: list[Path] = []
        page_names = [
            "Data Source",
            "Data Managers",
            "Manage Plots",
            "Save/Load Portfolio",
        ]

        # Capture landing page
        landing = shared_screenshot_dir / "nav_step_0_landing.png"
        bp.screenshot(landing)
        frames.append(landing)

        # Capture each page
        for idx, page_name in enumerate(page_names, start=1):
            bp.navigate_to(page_name)
            frame_path = (
                shared_screenshot_dir
                / f"nav_step_{idx}_{page_name.lower().replace('/', '_').replace(' ', '_')}.png"
            )
            bp.screenshot(frame_path)
            frames.append(frame_path)

        # Generate animated GIF
        gif_path = shared_screenshot_dir / "navigation_workflow.gif"
        BasePage.create_gif(frames, gif_path, duration_ms=1200)
        assert gif_path.exists(), f"GIF was not created at {gif_path}"
