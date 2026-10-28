"""Regression tests for shared Playwright page-object synchronization."""

from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

from tests.visual.pages.base_page import BasePage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage


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


def test_interrupted_single_select_requires_an_option_commit() -> None:
    """Typed search text after a popup interruption is not the committed choice."""
    page = MagicMock()
    widget = MagicMock()
    control = MagicMock()
    closed_control = MagicMock()
    popup = MagicMock()
    option = MagicMock()
    control_expectation = MagicMock()
    closed_expectation = MagicMock()
    popup_expectation = MagicMock()
    option_expectation = MagicMock()
    search = "area"
    committed = "area"
    popup_open = False
    popup_id: str | None = None
    openings = 0
    chosen_options: list[str] = []

    def open_popup(*, timeout: int) -> None:
        nonlocal popup_open, popup_id, openings
        openings += 1
        popup_open = True
        popup_id = f"owned-{openings}"

    def fill_search(text: str, *, timeout: int) -> None:
        nonlocal search
        search = text

    def attribute(name: str, *, timeout: int) -> str | None:
        if name == "aria-expanded":
            return "true" if popup_open else "false"
        assert name == "aria-controls"
        return popup_id

    def current_input(*, timeout: int) -> str:
        return search

    def require_popup(count: int, *, timeout: int) -> None:
        nonlocal popup_open, popup_id
        assert count == 1
        if openings == 1:
            popup_open = False
            popup_id = None
            raise AssertionError("Rerun removed the first owned popup")
        assert popup_open and popup_id == "owned-2"

    def choose_bar(*, timeout: int) -> None:
        nonlocal committed, popup_open, popup_id
        assert popup_open and popup_id == "owned-2"
        committed = "bar"
        chosen_options.append(committed)
        search_value("bar", timeout=timeout)
        popup_open = False
        popup_id = None

    def owned_option(role: str, *, name: str, exact: bool) -> MagicMock:
        assert role == "option" and name == "bar" and exact
        return option

    def combobox(role: str, *, expanded: bool | None = None) -> MagicMock:
        assert role == "combobox"
        return closed_control if expanded is False else control

    def search_value(expected: str, *, timeout: int) -> None:
        assert search == expected

    def closed_value(expected: str, *, timeout: int) -> None:
        assert not popup_open
        search_value(expected, timeout=timeout)

    def expectation(locator: object) -> MagicMock:
        if locator is control:
            return control_expectation
        if locator is closed_control:
            return closed_expectation
        if locator is popup:
            return popup_expectation
        assert locator is option
        return option_expectation

    control.count.return_value = 1
    control.click.side_effect = open_popup
    control.fill.side_effect = fill_search
    control.get_attribute.side_effect = attribute
    control.input_value.side_effect = current_input
    widget.get_by_role.side_effect = combobox
    page.get_by_role.return_value.and_.return_value = popup
    popup.get_by_role.side_effect = owned_option
    popup_expectation.to_have_count.side_effect = require_popup
    control_expectation.to_have_value.side_effect = search_value
    closed_expectation.to_have_value.side_effect = closed_value
    option.click.side_effect = choose_bar

    with (
        patch("tests.visual.pages.base_page.expect", side_effect=expectation),
        patch("tests.visual.pages.base_page.time") as clock,
    ):
        clock.monotonic.return_value = 100.0
        BasePage(page)._open_and_select(widget, "bar")

    assert committed == search == "bar"
    assert chosen_options == ["bar"]


def test_download_open_ignores_visible_stale_engine_controls() -> None:
    """An old open Plotly section cannot make the current collapsed PGF visible."""
    page = MagicMock()
    all_owners = MagicMock()
    current = MagicMock()
    old = MagicMock()
    anchor = MagicMock()
    details = MagicMock()
    summary = MagicMock()
    formats = MagicMock()
    stale_formats = MagicMock()
    all_expectation = MagicMock()
    current_expectation = MagicMock()
    details_expectation = MagicMock()
    formats_expectation = MagicMock()
    current_open = False
    old_present = True
    opened: list[str] = []
    anchor_name = ""

    def find_anchor(role: str, *, name: str, exact: bool, include_hidden: bool) -> MagicMock:
        nonlocal anchor_name
        assert role == "radio" and exact and include_hidden
        anchor_name = name
        return anchor

    def owner_with_format(*, has: MagicMock) -> MagicMock:
        assert has is anchor
        if anchor_name in ("pdf", "pgf", "png", "svg"):
            return current
        assert anchor_name == "html"
        return old

    def require_current(count: int, *, timeout: int) -> None:
        assert count == 1
        assert anchor_name == "pgf"

    def settle_owners(count: int, *, timeout: int) -> None:
        nonlocal old_present
        assert count == 1
        old_present = False

    def open_state(name: str, *, timeout: int) -> str | None:
        assert name == "open"
        return "" if current_open else None

    def open_current(*, timeout: int) -> None:
        nonlocal current_open
        assert not old_present and not current_open
        current_open = True
        opened.append("matplotlib")

    def require_open(name: str, value: bool, *, timeout: int) -> None:
        assert name == "open" and value is True
        assert current_open

    def require_formats(*, timeout: int) -> None:
        assert current_open and not old_present

    def expectation(locator: object) -> MagicMock:
        if locator is all_owners:
            return all_expectation
        if locator is current:
            return current_expectation
        if locator is details:
            return details_expectation
        assert locator is formats
        return formats_expectation

    page.get_by_role.side_effect = find_anchor
    all_owners.filter.side_effect = owner_with_format
    all_owners.get_by_role.return_value = stale_formats
    stale_formats.is_visible.return_value = True
    old.locator.return_value = MagicMock()
    current.locator.side_effect = lambda selector: {"details": details, "summary": summary}[
        selector
    ]
    current.get_by_role.return_value = formats
    details.get_attribute.side_effect = open_state
    summary.click.side_effect = open_current
    all_expectation.to_have_count.side_effect = settle_owners
    current_expectation.to_have_count.side_effect = require_current
    details_expectation.to_have_js_property.side_effect = require_open
    formats_expectation.to_be_visible.side_effect = require_formats

    with (
        patch.object(
            ManagePlotsPage,
            "download_expander",
            new_callable=PropertyMock,
            return_value=all_owners,
        ),
        patch("tests.visual.pages.manage_plots_page.expect", side_effect=expectation),
        patch("tests.visual.pages.manage_plots_page.time") as clock,
    ):
        clock.monotonic.return_value = 100.0
        ManagePlotsPage(page).open_download_expander("matplotlib", timeout=60_000)

    assert current_open
    assert opened == ["matplotlib"]
    old.locator.return_value.click.assert_not_called()
