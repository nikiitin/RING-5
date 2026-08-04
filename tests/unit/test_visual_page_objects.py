"""Regression tests for shared Playwright page-object synchronization."""

from unittest.mock import MagicMock

from tests.visual.pages.base_page import BasePage


def test_initial_navigation_does_not_wait_for_network_idle() -> None:
    """Streamlit keeps live connections open, so readiness uses its status widget."""
    page = MagicMock()
    running = MagicMock()
    page.locator.return_value = running

    BasePage(page).goto_and_wait("http://localhost:8501")

    page.goto.assert_called_once_with(
        "http://localhost:8501",
        wait_until="domcontentloaded",
    )
    page.locator.assert_called_once_with("[data-testid='stStatusWidget']")
    running.wait_for.assert_called_once_with(
        state="hidden",
        timeout=BasePage.RENDER_TIMEOUT,
    )
