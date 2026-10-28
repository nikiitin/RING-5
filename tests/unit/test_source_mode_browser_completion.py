"""Source-mode helpers retain one native activation and its actual rendered body."""

from unittest.mock import MagicMock, PropertyMock, patch

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pytest

from tests.visual.pages.data_source_page import DataSourcePage


@pytest.mark.parametrize("failure_stage", [None, "action", "completion", "checked", "body"])
def test_source_mode_requires_its_own_checked_control_and_body_without_route_recovery(
    failure_stage: str | None,
) -> None:
    """A mode/body mismatch remains visible without another activation or sibling navigation."""
    page = MagicMock()
    source = DataSourcePage(page)
    option, content, cycle, expectation = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    option.is_checked.return_value = False
    option.locator.return_value.count.return_value = 0
    failure = PlaywrightTimeoutError(f"Source mode failed at {failure_stage}")
    events: list[str] = []

    def stage(name: str) -> None:
        events.append(name)
        if name == failure_stage:
            raise failure

    cycle.__enter__.side_effect = lambda: stage("armed")
    option.press.side_effect = lambda *_args, **_kwargs: stage("action")
    cycle.__exit__.side_effect = lambda *_args: (
        stage("completion") if failure_stage != "action" else None
    )
    expectation.to_be_checked.side_effect = lambda **_kwargs: stage("checked")
    content.wait_for.side_effect = lambda **_kwargs: stage("body")
    with (
        patch.object(source, "expect_script_rerun", return_value=cycle) as observe,
        patch("tests.visual.pages.data_source_page.expect", return_value=expectation),
    ):
        if failure_stage is None:
            source._select_top_level_mode(option, content)
        else:
            with pytest.raises(PlaywrightTimeoutError, match="Source mode failed") as caught:
                source._select_top_level_mode(option, content)
            assert caught.value is failure
    expected = ["armed", "action", "completion", "checked", "body"]
    if failure_stage is not None:
        expected = expected[: expected.index(failure_stage) + 1]
    assert events == expected
    observe.assert_called_once_with()
    option.press.assert_called_once_with("Space", timeout=source.RENDER_TIMEOUT)
    option.click.assert_not_called()
    if failure_stage is None or failure_stage == "body":
        content.wait_for.assert_called_once_with(state="visible", timeout=source.RENDER_TIMEOUT)
    else:
        content.wait_for.assert_not_called()
    page.locator.assert_not_called()
    page.get_by_text.assert_not_called()
    page.wait_for_timeout.assert_not_called()


@pytest.mark.parametrize("body_present", [False, True])
def test_selected_source_mode_requires_its_body_without_reselecting(body_present: bool) -> None:
    """An optimistic checked control alone cannot satisfy the selected source-mode receipt."""
    page = MagicMock()
    source = DataSourcePage(page)
    option, content = MagicMock(), MagicMock()
    option.is_checked.return_value = True
    if not body_present:
        content.wait_for.side_effect = PlaywrightTimeoutError("Selected source body is absent")
    with patch.object(source, "expect_script_rerun") as observe:
        if body_present:
            source._select_top_level_mode(option, content)
        else:
            with pytest.raises(PlaywrightTimeoutError, match="Selected source body is absent"):
                source._select_top_level_mode(option, content)
    content.wait_for.assert_called_once_with(state="visible", timeout=source.RENDER_TIMEOUT)
    option.press.assert_not_called()
    option.click.assert_not_called()
    observe.assert_not_called()
    page.locator.assert_not_called()
    page.get_by_text.assert_not_called()
    page.wait_for_timeout.assert_not_called()


@pytest.mark.parametrize("form_present", [False, True])
def test_remote_source_uses_the_same_single_mode_receipt(form_present: bool) -> None:
    """A failed remote form does not revisit upload mode or another application route."""
    page = MagicMock()
    source = DataSourcePage(page)
    option, content = MagicMock(), MagicMock()
    option.is_checked.return_value = True
    if not form_present:
        content.wait_for.side_effect = PlaywrightTimeoutError("Remote source form is absent")
    with (
        patch.object(source, "select_csv_mode") as upload_mode,
        patch.object(
            DataSourcePage, "remote_source_option", new_callable=PropertyMock, return_value=option
        ),
        patch.object(
            DataSourcePage, "remote_adapter_select", new_callable=PropertyMock, return_value=content
        ),
    ):
        if form_present:
            source.select_remote_source()
        else:
            with pytest.raises(PlaywrightTimeoutError, match="Remote source form is absent"):
                source.select_remote_source()
    upload_mode.assert_called_once_with()
    content.wait_for.assert_called_once_with(state="visible", timeout=source.RENDER_TIMEOUT)
    option.press.assert_not_called()
    option.click.assert_not_called()
    page.locator.assert_not_called()
    page.get_by_text.assert_not_called()
    page.wait_for_timeout.assert_not_called()
