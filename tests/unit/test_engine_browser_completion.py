"""Connector changes require one activation and its published native chart."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from tests.visual.pages.manage_plots_page import ManagePlotsPage


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("already_selected", [False, True])
def test_engine_selection_waits_for_its_connector_without_reactivating(
    engine: str, already_selected: bool
) -> None:
    page = MagicMock()
    manager = ManagePlotsPage(page)
    controls, pill, previous_chart, cycle = (MagicMock() for _ in range(4))
    controls.get_by_role.return_value = pill
    pill.is_checked.return_value = already_selected
    events: list[str] = []
    cycle.__enter__.side_effect = lambda: events.append("armed")
    pill.click.side_effect = lambda: events.append("activated")
    cycle.__exit__.side_effect = lambda *_args: events.append("app completed")
    pill_expectation, previous_expectation = MagicMock(), MagicMock()
    pill_expectation.to_be_checked.side_effect = lambda **_kwargs: events.append("checked")
    previous_expectation.to_have_count.side_effect = lambda *_args, **_kwargs: events.append(
        "previous connector retired"
    )
    native_method = (
        "assert_chart_visible" if engine == "plotly" else "assert_matplotlib_chart_visible"
    )
    previous_property = "matplotlib_chart" if engine == "plotly" else "plotly_chart"
    with (
        patch.object(
            ManagePlotsPage, "viz_engine_pills", new_callable=PropertyMock, return_value=controls
        ),
        patch.object(
            ManagePlotsPage,
            previous_property,
            new_callable=PropertyMock,
            return_value=previous_chart,
        ),
        patch.object(manager, "expect_script_rerun", return_value=cycle) as observe,
        patch.object(manager, native_method) as native,
        patch(
            "tests.visual.pages.manage_plots_page.expect",
            side_effect={pill: pill_expectation, previous_chart: previous_expectation}.__getitem__,
        ),
    ):
        native.side_effect = lambda: events.append("selected native chart")
        manager.select_engine(engine)

    prefix = [] if already_selected else ["armed", "activated", "app completed", "checked"]
    assert events == prefix + ["previous connector retired", "selected native chart"]
    controls.get_by_role.assert_called_once_with("radio", name=engine)
    if already_selected:
        pill.click.assert_not_called()
        observe.assert_not_called()
    else:
        pill.click.assert_called_once_with()
        observe.assert_called_once_with()
        pill_expectation.to_be_checked.assert_called_once_with(timeout=manager.RENDER_TIMEOUT)
    previous_expectation.to_have_count.assert_called_once_with(0, timeout=manager.RENDER_TIMEOUT)
    native.assert_called_once_with()
    page.wait_for_timeout.assert_not_called()


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_engine_completion_failure_propagates_without_another_activation(engine: str) -> None:
    page = MagicMock()
    manager = ManagePlotsPage(page)
    controls, cycle = MagicMock(), MagicMock()
    pill = controls.get_by_role.return_value
    pill.is_checked.return_value = False
    cycle.__exit__.side_effect = AssertionError("Selected connector did not complete")
    with (
        patch.object(
            ManagePlotsPage, "viz_engine_pills", new_callable=PropertyMock, return_value=controls
        ),
        patch.object(manager, "expect_script_rerun", return_value=cycle),
        patch.object(manager, "assert_chart_visible") as plotly,
        patch.object(manager, "assert_matplotlib_chart_visible") as matplotlib,
        patch("tests.visual.pages.manage_plots_page.expect") as expect,
    ):
        with pytest.raises(AssertionError, match="Selected connector did not complete"):
            manager.select_engine(engine)
    pill.click.assert_called_once_with()
    expect.return_value.to_be_checked.assert_not_called()
    plotly.assert_not_called()
    matplotlib.assert_not_called()
    page.wait_for_timeout.assert_not_called()
