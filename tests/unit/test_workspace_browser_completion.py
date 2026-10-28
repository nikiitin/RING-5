"""Workspace publications require app completion and an operation-owned result."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from tests.visual.pages.data_managers_page import DataManagersPage


@pytest.mark.parametrize(
    ("action", "button_name", "result_name"),
    [
        ("undo_workspace_dataset", "workspace_undo_button", "workspace_redo_button"),
        ("redo_workspace_dataset", "workspace_redo_button", "workspace_undo_button"),
        ("apply_comparison", "comparison_apply_button", "comparison_confirm_button"),
    ],
)
@pytest.mark.parametrize("failure_stage", [None, "completion", "result"])
def test_history_and_comparison_actions_observe_completion_before_the_retained_result(
    action: str, button_name: str, result_name: str, failure_stage: str | None
) -> None:
    """A single click cannot succeed on an idle spinner or missing published controls."""
    page = MagicMock()
    manager = DataManagersPage(page)
    button, result, expectation, cycle = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    events: list[str] = []
    cycle.__enter__.side_effect = lambda: events.append("armed")
    button.click.side_effect = lambda: events.append("clicked")
    failure = AssertionError("Required publication was not observed")

    def complete(*_args: object) -> None:
        events.append("completion")
        if failure_stage == "completion":
            raise failure

    def retained(**_kwargs: object) -> None:
        events.append("result")
        if failure_stage == "result":
            raise failure

    cycle.__exit__.side_effect = complete
    expectation.to_be_enabled.side_effect = retained
    expectation.to_be_visible.side_effect = retained
    with (
        patch.object(DataManagersPage, button_name, new_callable=PropertyMock, return_value=button),
        patch.object(DataManagersPage, result_name, new_callable=PropertyMock, return_value=result),
        patch.object(manager, "expect_script_rerun", return_value=cycle) as observe,
        patch("tests.visual.pages.data_managers_page.expect", return_value=expectation) as expected,
    ):
        if failure_stage is None:
            getattr(manager, action)()
        else:
            with pytest.raises(AssertionError, match="Required publication") as caught:
                getattr(manager, action)()
            assert caught.value is failure
    assert events == ["armed", "clicked", "completion"] + (
        [] if failure_stage == "completion" else ["result"]
    )
    observe.assert_called_once_with()
    button.click.assert_called_once_with()
    if failure_stage == "completion":
        expected.assert_not_called()
    else:
        expected.assert_called_once_with(result)
    page.wait_for_timeout.assert_not_called()


@pytest.mark.parametrize("name", ["target", "Yes"])
@pytest.mark.parametrize("published", [False, True])
def test_activation_requires_the_named_dataset_to_be_published_as_active(
    name: str, published: bool
) -> None:
    """Choosing a name before activation is not evidence that the active data changed."""
    page = MagicMock()
    manager = DataManagersPage(page)
    selector, button, row, active, expectation, cycle = (
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    selector.get_by_role.return_value.input_value.return_value = name
    row.locator.return_value = active
    events: list[str] = []
    cycle.__enter__.side_effect = lambda: events.append("armed")
    button.click.side_effect = lambda: events.append("clicked")
    cycle.__exit__.side_effect = lambda *_args: events.append("completed")

    def require_active(*args: object, **_kwargs: object) -> None:
        assert events == ["armed", "clicked", "completed"]
        assert args == ("Yes",)
        if not published:
            raise AssertionError("Chosen dataset is not active")

    expectation.to_have_text.side_effect = require_active
    with (
        patch.object(manager, "select_tab"),
        patch.object(manager, "_open_and_select") as select,
        patch.object(manager, "workspace_dataset_row", return_value=row) as find_row,
        patch.object(
            DataManagersPage,
            "workspace_dataset_selectbox",
            new_callable=PropertyMock,
            return_value=selector,
        ),
        patch.object(
            DataManagersPage,
            "workspace_activate_button",
            new_callable=PropertyMock,
            return_value=button,
        ),
        patch.object(manager, "expect_script_rerun", return_value=cycle),
        patch("tests.visual.pages.data_managers_page.expect", return_value=expectation) as expected,
    ):
        if published:
            manager.activate_workspace_dataset(name)
        else:
            with pytest.raises(AssertionError, match="Chosen dataset is not active"):
                manager.activate_workspace_dataset(name)
    select.assert_called_once_with(selector, name)
    find_row.assert_called_once_with(name)
    row.locator.assert_called_once_with('[role="gridcell"][aria-colindex="4"]')
    row.get_by_role.assert_not_called()
    expected.assert_called_once_with(active)
    button.click.assert_called_once_with()
    page.wait_for_timeout.assert_not_called()
