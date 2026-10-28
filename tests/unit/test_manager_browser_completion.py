"""Manager confirmations complete only after the published app view replaces the preview."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from tests.visual.pages.data_managers_page import DataManagersPage


@pytest.mark.parametrize(
    ("method", "button_property"),
    [
        ("confirm_seeds_reducer", "seeds_confirm_button"),
        ("confirm_outlier_remover", "outlier_confirm_button"),
        ("confirm_preprocessor", "preproc_confirm_button"),
        ("confirm_mixer", "mixer_confirm_button"),
    ],
)
def test_manager_confirmation_waits_for_committed_app_and_consumed_preview(
    method: str, button_property: str
) -> None:
    """Arm before publication and reject an idle app that retains the old preview."""
    page = MagicMock()
    manager = DataManagersPage(page)
    button = MagicMock()
    cycle = MagicMock()
    events: list[str] = []
    cycle.__enter__.side_effect = lambda: events.append("armed")
    button.click.side_effect = lambda: events.append("confirmed")
    cycle.__exit__.side_effect = lambda *_args: events.append("app completed")

    with (
        patch.object(
            DataManagersPage, button_property, new_callable=PropertyMock, return_value=button
        ),
        patch.object(manager, "expect_script_rerun", return_value=cycle) as observe,
        patch("tests.visual.pages.data_managers_page.expect") as expect,
    ):
        expect.return_value.to_have_count.side_effect = lambda *_args, **_kwargs: events.append(
            "preview consumed"
        )
        getattr(manager, method)()
        assert events == ["armed", "confirmed", "app completed", "preview consumed"]
        observe.assert_called_once_with()
        button.click.assert_called_once_with()
        expect.assert_called_once_with(button)
        expect.return_value.to_have_count.assert_called_once_with(0, timeout=manager.RENDER_TIMEOUT)

        expect.return_value.to_have_count.side_effect = AssertionError("Preview was not consumed")
        with pytest.raises(AssertionError, match="Preview was not consumed"):
            getattr(manager, method)()

    page.wait_for_timeout.assert_not_called()
