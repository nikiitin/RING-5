"""Regression tests for shared Playwright page-object synchronization."""

import re
from unittest.mock import MagicMock, PropertyMock, call, patch

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
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
    sidebar.get_by_role.assert_called_once_with("button", name="Data Source", exact=True)


def test_navigation_waits_for_the_target_route_after_app_completion() -> None:
    """The first completed run can leave the previous route's buttons rendered."""
    page = MagicMock()
    button = page.locator.return_value.get_by_role.return_value
    button.get_attribute.return_value = "stBaseButton-tertiary"
    base = BasePage(page)
    events: list[str] = []
    cycle = MagicMock()
    cycle.__enter__.side_effect = lambda: events.append("armed")
    button.click.side_effect = lambda: events.append("clicked")
    cycle.__exit__.side_effect = lambda *_args: events.append("app completed")

    with (
        patch.object(base, "expect_script_rerun", return_value=cycle) as observe,
        patch("tests.visual.pages.base_page.expect") as mock_expect,
    ):
        mock_expect.return_value.to_have_attribute.side_effect = lambda *_args, **_kwargs: (
            events.append("target rendered")
        )
        base.navigate_to("Data Source")

    assert events == ["armed", "clicked", "app completed", "target rendered"]
    observe.assert_called_once_with()
    button.click.assert_called_once_with()
    mock_expect.assert_called_once_with(button)
    mock_expect.return_value.to_have_attribute.assert_called_once_with(
        "data-testid", "stBaseButton-primary", timeout=BasePage.RENDER_TIMEOUT
    )


def test_navigation_rejects_an_app_completion_without_the_target_route() -> None:
    """A completed app cycle alone must not report a successful route change."""
    page = MagicMock()
    button = page.locator.return_value.get_by_role.return_value
    button.get_attribute.return_value = "stBaseButton-tertiary"
    base = BasePage(page)
    cycle = MagicMock()

    with (
        patch.object(base, "expect_script_rerun", return_value=cycle) as observe,
        patch("tests.visual.pages.base_page.expect") as mock_expect,
    ):
        mock_expect.return_value.to_have_attribute.side_effect = AssertionError(
            "Target route was not rendered"
        )
        with pytest.raises(AssertionError, match="Target route was not rendered"):
            base.navigate_to("Data Source")

    observe.assert_called_once_with()
    cycle.__exit__.assert_called_once_with(None, None, None)
    button.click.assert_called_once_with()
    mock_expect.return_value.to_have_attribute.assert_called_once_with(
        "data-testid", "stBaseButton-primary", timeout=BasePage.RENDER_TIMEOUT
    )
    page.wait_for_timeout.assert_not_called()


@pytest.mark.parametrize("in_dialog", [False, True])
def test_segmented_control_selection_waits_for_its_own_lifecycle(in_dialog: bool) -> None:
    """Keyboard activation survives headers; dialog updates do not need an app cycle."""
    page = MagicMock()
    option = MagicMock()
    option.is_checked.return_value = False
    option.locator.return_value.count.return_value = int(in_dialog)

    with patch("tests.visual.pages.data_source_page.expect") as mock_expect:
        DataSourcePage(page)._select_mode(option)

    option.press.assert_called_once_with("Space", timeout=DataSourcePage.RENDER_TIMEOUT)
    option.click.assert_not_called()
    assert page.wait_for_function.call_count == 2 * int(not in_dialog)
    page.wait_for_timeout.assert_not_called()
    mock_expect.assert_called_once_with(option)
    mock_expect.return_value.to_be_checked.assert_called_once_with(
        timeout=DataSourcePage.RENDER_TIMEOUT
    )


def test_selected_segmented_control_does_not_enqueue_a_redundant_run() -> None:
    page = MagicMock()
    option = MagicMock()
    option.is_checked.return_value = True

    DataSourcePage(page)._select_mode(option)

    option.press.assert_not_called()
    option.click.assert_not_called()
    page.evaluate.assert_not_called()
    page.wait_for_function.assert_not_called()


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


@pytest.mark.parametrize(
    ("scope_kind", "failure"),
    [
        ("page", None),
        ("form", None),
        ("dialog", None),
        ("page", "missing-option"),
    ],
)
def test_single_select_interruption_and_real_failures_remain_distinct(
    scope_kind: str, failure: str | None
) -> None:
    """Retry a replaced popup, preserving exact commits and intact missing-option errors."""
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

    def press_key(key: str, *, timeout: int) -> None:
        nonlocal committed, search
        # Streamlit clears an optional select on Escape after its popup has closed.
        if key == "Escape" and not popup_open:
            committed = search = ""

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

    def require_option(count: int, *, timeout: int) -> None:
        assert count == 1 and popup_open and popup_id == "owned-2"
        if failure == "missing-option":
            raise AssertionError("Option absent from intact popup")

    control.count.return_value = 1
    control.click.side_effect = open_popup
    control.fill.side_effect = fill_search
    control.get_attribute.side_effect = attribute
    control.input_value.side_effect = current_input
    control.press.side_effect = press_key
    widget.get_by_role.side_effect = combobox
    widget.locator.return_value.count.return_value = int(scope_kind != "page")
    page.get_by_role.return_value.and_.return_value = popup
    popup.get_by_role.side_effect = owned_option
    popup_expectation.to_have_count.side_effect = require_popup
    option_expectation.to_have_count.side_effect = require_option
    control_expectation.to_have_value.side_effect = search_value
    closed_expectation.to_have_value.side_effect = closed_value
    option.click.side_effect = choose_bar
    page.wait_for_function.side_effect = AssertionError(
        "A widget commit must not require a global script-running cycle"
    )

    with (
        patch("tests.visual.pages.base_page.expect", side_effect=expectation),
        patch("tests.visual.pages.base_page.time") as clock,
    ):
        clock.monotonic.return_value = 100.0
        if failure == "missing-option":
            with pytest.raises(AssertionError, match="Option absent from intact popup"):
                BasePage(page)._open_and_select(widget, "bar")
        else:
            BasePage(page)._open_and_select(widget, "bar")

    assert openings == 2
    if failure == "missing-option":
        assert committed == "area"
        assert chosen_options == []
    else:
        assert committed == search == "bar"
        assert chosen_options == ["bar"]
    control.press.assert_not_called()
    page.wait_for_function.assert_not_called()
    page.evaluate.assert_not_called()


@pytest.mark.parametrize("scope_kind", ["page", "form", "dialog"])
@pytest.mark.parametrize("already_selected", [False, True])
@pytest.mark.parametrize("popup_remains_open", [False, True])
def test_multiselect_completion_closes_only_an_open_popup_without_changing_chips(
    scope_kind: str, already_selected: bool, popup_remains_open: bool
) -> None:
    """Tab dismisses the menu and preserves a newly selected or existing chip."""
    page = MagicMock()
    widget = MagicMock()
    control = MagicMock()
    chip = MagicMock()
    popup = MagicMock()
    option = MagicMock()
    control_expectation = MagicMock()
    chip_expectation = MagicMock()
    popup_expectation = MagicMock()
    option_expectation = MagicMock()
    selected = already_selected
    popup_open = already_selected and popup_remains_open
    search_active = False

    def attribute(name: str, *, timeout: int) -> str:
        if name == "aria-expanded":
            return "true" if popup_open else "false"
        assert name == "aria-controls"
        return "owned-multiselect"

    def open_popup(*, timeout: int) -> None:
        nonlocal popup_open
        popup_open = True

    def fill_search(value: str, *, timeout: int) -> None:
        nonlocal search_active
        assert value == "ipc"
        search_active = True

    def choose_option(*, timeout: int) -> None:
        nonlocal selected, popup_open
        assert popup_open
        selected = True
        popup_open = popup_remains_open

    def press_key(key: str, *, timeout: int) -> None:
        nonlocal popup_open, search_active
        assert popup_open, "A closed multiselect needs no keyboard dismissal"
        if key == "Escape" and search_active:
            # Escape can cancel the filter without closing the menu.
            search_active = False
        elif key == "Tab":
            search_active = False
            popup_open = False
        else:
            raise AssertionError(f"Unexpected dismissal key: {key}")

    def require_attribute(name: str, value: object, *, timeout: int) -> None:
        if name == "aria-controls":
            assert popup_open
            assert isinstance(value, re.Pattern) and value.fullmatch("owned-multiselect")
            return
        assert name == "aria-expanded" and value == "false"
        assert not popup_open

    def require_chip(count: int, *, timeout: int) -> None:
        assert count == 1 and selected

    def expectation(locator: object) -> MagicMock:
        if locator is control:
            return control_expectation
        if locator is chip:
            return chip_expectation
        if locator is popup:
            return popup_expectation
        assert locator is option
        return option_expectation

    control.count.return_value = 1
    control.get_attribute.side_effect = attribute
    control.click.side_effect = open_popup
    control.fill.side_effect = fill_search
    control.press.side_effect = press_key
    chip.count.side_effect = lambda: int(selected)
    widget.get_by_role.return_value = control
    widget.locator.return_value.count.return_value = int(scope_kind != "page")
    widget.locator.return_value.filter.return_value = chip
    page.get_by_role.return_value.and_.return_value = popup
    popup.get_by_role.return_value = option
    option.click.side_effect = choose_option
    page.wait_for_function.side_effect = AssertionError(
        "A widget commit must not require a global script-running cycle"
    )
    control_expectation.to_have_attribute.side_effect = require_attribute
    chip_expectation.to_have_count.side_effect = require_chip

    with (
        patch("tests.visual.pages.base_page.expect", side_effect=expectation),
        patch("tests.visual.pages.base_page.time") as clock,
    ):
        clock.monotonic.return_value = 100.0
        BasePage(page)._open_and_select(widget, "ipc", multiple=True)

    assert selected
    assert not popup_open
    if popup_remains_open:
        control.press.assert_called_once_with("Tab", timeout=BasePage.RENDER_TIMEOUT)
    else:
        control.press.assert_not_called()
    assert option.click.call_count == int(not already_selected)
    page.wait_for_function.assert_not_called()
    page.evaluate.assert_not_called()


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


def test_rerun_completion_observation_is_armed_before_the_widget_action() -> None:
    """Drain old events, arm before the action, then observe and disarm its cycle."""
    page = MagicMock()
    page.evaluate.return_value = 4
    ordered = MagicMock()
    ordered.attach_mock(page, "page")
    action = MagicMock()
    ordered.attach_mock(action, "action")
    base = BasePage(page)

    with patch("tests.visual.pages.base_page.time") as clock:
        clock.monotonic.return_value = 100.0
        with base.expect_script_rerun(timeout=1234):
            action()

    events = [item[0] for item in ordered.mock_calls]
    assert events == [
        "page.wait_for_function",
        "page.evaluate",
        "action",
        "page.wait_for_function",
        "page.evaluate",
    ]
    assert ordered.mock_calls.index(call.action()) > next(
        index for index, item in enumerate(ordered.mock_calls) if item[0] == "page.evaluate"
    )
    assert page.wait_for_function.call_args.kwargs["arg"] == 4
    assert 0 < page.wait_for_function.call_args.kwargs["timeout"] <= 1234
    arm = page.evaluate.call_args_list[0].args[0]
    assert "event.source !== window" in arm
    assert "event.origin !== location.origin" in arm
    assert "SCRIPT_RUN_STATE_CHANGED" in arm
    assert "ring5BrowserScriptBarrier" in arm
    assert arm.index("await new Promise") < arm.index("observed.active = ++observed.next")
    assert "scriptRunState === 'running'" in arm
    assert "scriptRunState === 'notRunning' && observed.running" in arm
    assert "data-test-script-state" in page.wait_for_function.call_args.args[0]
    assert "observed.completed === generation" in page.wait_for_function.call_args.args[0]
    assert "observed.active = 0" in page.evaluate.call_args_list[-1].args[0]
    assert page.evaluate.call_args_list[-1].args[1] == 4
    page.wait_for_timeout.assert_not_called()


def test_rerun_observer_rechecks_idle_when_a_background_run_starts_before_arming() -> None:
    """A state change during the posted-message barrier cannot arm a busy run."""
    page = MagicMock()
    page.evaluate.side_effect = [None, 5, None]
    action = MagicMock()
    with patch("tests.visual.pages.base_page.time") as clock:
        clock.monotonic.return_value = 100.0
        with BasePage(page).expect_script_rerun(timeout=1234):
            action()
    assert action.call_count == 1
    assert page.wait_for_function.call_count == 3
    assert page.wait_for_function.call_args.kwargs["arg"] == 5
    assert 0 < page.wait_for_function.call_args.kwargs["timeout"] <= 1234
    page.wait_for_timeout.assert_not_called()


def test_rerun_observer_propagates_action_failure_without_waiting_for_another_run() -> None:
    """An unrelated later completion cannot replace a failed action."""
    page = MagicMock()
    page.evaluate.return_value = 4
    failure = PlaywrightTimeoutError("Widget action failed")
    with (
        patch("tests.visual.pages.base_page.time") as clock,
        pytest.raises(PlaywrightTimeoutError, match="Widget action failed") as caught,
    ):
        clock.monotonic.return_value = 100.0
        with BasePage(page).expect_script_rerun(timeout=1234):
            raise failure
    assert caught.value is failure
    assert page.wait_for_function.call_count == 1
    assert page.evaluate.call_count == 2
    assert "observed.active = 0" in page.evaluate.call_args_list[-1].args[0]


@pytest.mark.parametrize("completes", [False, True])
def test_pipeline_finalization_requires_its_fresh_application_cycle(completes: bool) -> None:
    """Finalization explicitly reruns the app; a missed cycle fails without a toast fallback."""
    page = MagicMock()
    page.evaluate.return_value = 4
    button = MagicMock()
    failure = PlaywrightTimeoutError("Finalized application did not complete")
    page.wait_for_function.side_effect = [None, None if completes else failure]

    def finalize() -> None:
        assert page.wait_for_function.call_count == 1
        assert page.evaluate.call_count == 1

    button.click.side_effect = finalize
    with (
        patch.object(
            ManagePlotsPage, "finalize_button", new_callable=PropertyMock, return_value=button
        ),
        patch("tests.visual.pages.base_page.time") as clock,
    ):
        clock.monotonic.return_value = 100.0
        if completes:
            ManagePlotsPage(page).finalize_pipeline()
        else:
            with pytest.raises(
                PlaywrightTimeoutError, match="Finalized application did not complete"
            ):
                ManagePlotsPage(page).finalize_pipeline()
    button.click.assert_called_once_with()
    assert page.wait_for_function.call_count == 2
    assert page.wait_for_function.call_args.kwargs["arg"] == 4
    assert page.evaluate.call_count == 2
    assert "observed.active = 0" in page.evaluate.call_args_list[-1].args[0]
    page.get_by_test_id.assert_not_called()
    page.wait_for_timeout.assert_not_called()


def test_adding_a_shaper_requires_the_new_numbered_backend_step() -> None:
    """An added step's count and type identify completion inside the pipeline fragment."""
    page = MagicMock()
    manager = ManagePlotsPage(page)
    steps = MagicMock()
    steps.count.return_value = 2
    button = MagicMock()
    add_widget = MagicMock()
    step = MagicMock()
    summary = step.locator.return_value.first
    label = summary.get_by_text.return_value
    clicked = False

    def add() -> None:
        nonlocal clicked
        clicked = True

    def count_is(expected: int, *, timeout: int) -> None:
        assert clicked and expected == 3

    def visible(*, timeout: int) -> None:
        assert clicked
        summary.get_by_text.assert_called_once_with("3. Sort", exact=True)

    count_expectation = MagicMock()
    count_expectation.to_have_count.side_effect = count_is
    label_expectation = MagicMock()
    label_expectation.to_be_visible.side_effect = visible
    button.click.side_effect = add
    with (
        patch.object(
            ManagePlotsPage, "pipeline_steps", new_callable=PropertyMock, return_value=steps
        ),
        patch.object(
            ManagePlotsPage,
            "add_to_pipeline_button",
            new_callable=PropertyMock,
            return_value=button,
        ),
        patch.object(
            ManagePlotsPage,
            "add_transformation_selectbox",
            new_callable=PropertyMock,
            return_value=add_widget,
        ),
        patch.object(manager, "_open_and_select") as select,
        patch.object(manager, "get_pipeline_step", return_value=step) as find_step,
        patch.object(manager, "expect_script_rerun", side_effect=AssertionError("Fragment")),
        patch("tests.visual.pages.manage_plots_page.expect") as mock_expect,
    ):
        mock_expect.side_effect = lambda locator: (
            count_expectation if locator is steps else label_expectation
        )
        manager.add_shaper("Sort")
        select.assert_called_once_with(add_widget, "Sort")
        find_step.assert_called_once_with(2)
        assert mock_expect.call_args_list == [call(steps), call(label)]


def test_multiselect_replacement_preserves_order_without_requiring_an_app_cycle() -> None:
    """Backspace removes the changed suffix before new selected chips are appended."""
    page = MagicMock()
    manager = ManagePlotsPage(page)
    widget = MagicMock()
    tags = widget.locator.return_value
    control = tags.first
    values = ["workload", "unused", "other"]
    tags.all_text_contents.side_effect = lambda: list(values)

    def press(key: str) -> None:
        if key == "Backspace":
            values.pop()
        else:
            assert key == "Escape"

    def select(owner: object, value: str, *, multiple: bool) -> None:
        assert owner is widget and multiple
        values.append(value)

    def count_is(expected: int, *, timeout: int) -> None:
        assert len(values) == expected

    control.press.side_effect = press
    with (
        patch.object(manager, "_open_and_select", side_effect=select),
        patch.object(manager, "expect_script_rerun", side_effect=AssertionError("Fragment")),
        patch("tests.visual.pages.manage_plots_page.expect") as mock_expect,
    ):
        mock_expect.return_value.to_have_count.side_effect = count_is
        manager.set_multiselect_values(widget, ["workload", "configuration", "a"])
    assert values == ["workload", "configuration", "a"]
    assert control.press.call_args_list == [call("Backspace"), call("Backspace"), call("Escape")]


def test_full_app_rerun_completion_failure_propagates_and_disarms_the_observer() -> None:
    """Root actions still fail when their fresh global cycle never completes."""
    page = MagicMock()
    page.evaluate.return_value = 4
    failure = PlaywrightTimeoutError("Full application script did not complete")
    page.wait_for_function.side_effect = [None, failure]
    action = MagicMock()
    with (
        patch("tests.visual.pages.base_page.time") as clock,
        pytest.raises(
            PlaywrightTimeoutError, match="Full application script did not complete"
        ) as caught,
    ):
        clock.monotonic.return_value = 100.0
        with BasePage(page).expect_script_rerun(timeout=1234):
            action()
    assert caught.value is failure
    action.assert_called_once_with()
    assert page.wait_for_function.call_count == 2
    assert page.evaluate.call_count == 2
    assert "observed.active = 0" in page.evaluate.call_args_list[-1].args[0]
