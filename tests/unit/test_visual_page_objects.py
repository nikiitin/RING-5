"""Regression tests for shared Playwright page-object synchronization."""

from unittest.mock import MagicMock, patch

from tests.visual.pages.base_page import BasePage
from tests.visual.pages.data_source_page import DataSourcePage


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


def test_navigation_does_not_click_the_already_active_page() -> None:
    """An active navigation button must not enqueue a redundant app rerun."""
    page = MagicMock()
    sidebar = page.locator.return_value
    button = sidebar.get_by_role.return_value
    button.get_attribute.return_value = "stBaseButton-primary"

    BasePage(page).navigate_to("Data Source")

    button.click.assert_not_called()


def test_segmented_control_selection_skips_detach_prone_actionability_waits() -> None:
    """Segmented controls use a forced pointer click before waiting for the rerun."""
    page = MagicMock()
    option = MagicMock()
    option.is_checked.return_value = False

    with patch("tests.visual.pages.data_source_page.expect") as mock_expect:
        DataSourcePage(page)._select_mode(option)

    option.click.assert_called_once_with(force=True)
    page.locator.assert_called_once_with("[data-testid='stStatusWidget']")
    page.wait_for_timeout.assert_called_once_with(250)
    mock_expect.assert_called_once_with(option)
    mock_expect.return_value.to_be_checked.assert_called_once_with(
        timeout=DataSourcePage.RENDER_TIMEOUT
    )
