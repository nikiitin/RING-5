"""Regression tests for shared Playwright page-object synchronization."""

from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

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


def test_parse_wait_without_submission_rejects_retained_data_and_notices() -> None:
    """Restored or previously parsed rows never arm a fresh completion wait."""
    # [test->req~ring5.ingestion.session-background-parse~1]
    page = MagicMock()
    data_source = DataSourcePage(page)

    with pytest.raises(AssertionError, match="No parse submission is pending"):
        data_source.wait_for_parse_completion(timeout=500)
    with pytest.raises(AssertionError, match="No parse submission is pending"):
        data_source.wait_for_parse_terminal_outcome(timeout=500)

    page.locator.assert_not_called()
    page.get_by_test_id.assert_not_called()


def test_parse_submission_excludes_the_existing_notice_before_clicking() -> None:
    """The fresh-notice query excludes the actual captured job, even for cached rows."""
    page = MagicMock()
    notice = MagicMock()
    notice.count.return_value = 1
    notice.get_attribute.return_value = "stVerticalBlock st-key-parse_completion_" + "a" * 32
    button = MagicMock()
    ordered = MagicMock()
    ordered.attach_mock(notice, "notice")
    ordered.attach_mock(button, "button")
    data_source = DataSourcePage(page)

    with (
        patch.object(
            DataSourcePage,
            "parse_completion_notice",
            new_callable=PropertyMock,
            return_value=notice,
        ),
        patch.object(
            DataSourcePage, "parse_button", new_callable=PropertyMock, return_value=button
        ),
        patch.object(DataSourcePage, "parse_job_heading", new_callable=PropertyMock),
        patch.object(data_source, "wait_for_streamlit"),
        patch("tests.visual.pages.data_source_page.expect"),
    ):
        data_source.click_parse()

    assert ordered.mock_calls.index(call.notice.get_attribute("class")) < ordered.mock_calls.index(
        call.button.click()
    )
    _ = data_source.pending_parse_completion
    page.locator.assert_called_once_with(
        "[class*='st-key-parse_completion_']:not([class~='st-key-parse_completion_"
        + "a" * 32
        + "'])"
    )


def test_a_failed_completion_wait_cannot_reuse_its_pending_attempt() -> None:
    """A timeout leaves neither retained data nor the prior notice armed for reuse."""
    page = MagicMock()
    notice = MagicMock()
    notice.count.return_value = 0
    data_source = DataSourcePage(page)

    with (
        patch.object(
            DataSourcePage,
            "parse_completion_notice",
            new_callable=PropertyMock,
            return_value=notice,
        ),
        patch.object(data_source, "wait_for_streamlit"),
        patch("tests.visual.pages.data_source_page.expect") as expect,
    ):
        data_source.click_parse()
        expect.return_value.to_be_visible.side_effect = AssertionError("no new notice")
        with pytest.raises(AssertionError, match="no new notice"):
            data_source.wait_for_parse_completion(timeout=500)
        with pytest.raises(AssertionError, match="No parse submission is pending"):
            data_source.wait_for_parse_completion(timeout=500)
