"""Pipeline import observes upload admission before the full app publication."""

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from tests.visual.pages.manage_plots_page import ManagePlotsPage


@pytest.mark.parametrize("completion_fails", [False, True])
def test_pipeline_import_waits_for_admitted_upload_and_armed_app_completion(
    completion_fails: bool,
) -> None:
    page = MagicMock()
    manager = ManagePlotsPage(page)
    panel, uploader, button = MagicMock(), MagicMock(), MagicMock()
    filename = panel.get_by_title.return_value
    spinner = panel.get_by_test_id.return_value
    filename_expectation, spinner_expectation, button_expectation = (
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    expectations = {
        filename: filename_expectation,
        spinner: spinner_expectation,
        button: button_expectation,
    }
    events: list[str] = []
    uploader.set_input_files.side_effect = lambda *_args: events.append("uploaded")
    filename_expectation.to_be_visible.side_effect = lambda **_kwargs: events.append("filename")
    spinner_expectation.to_have_count.side_effect = lambda *_args, **_kwargs: events.append(
        "upload settled"
    )
    button_expectation.to_be_enabled.side_effect = lambda **_kwargs: events.append("admitted")
    cycle = MagicMock()
    cycle.__enter__.side_effect = lambda: events.append("armed")
    button.click.side_effect = lambda: events.append("imported")

    def complete(*_args: object) -> None:
        if completion_fails:
            raise AssertionError("Import app completion was not observed")
        events.append("app completed")

    cycle.__exit__.side_effect = complete
    with (
        patch.object(manager, "open_pipeline_exchange"),
        patch.object(
            ManagePlotsPage,
            "pipeline_exchange_expander",
            new_callable=PropertyMock,
            return_value=panel,
        ),
        patch.object(
            ManagePlotsPage,
            "pipeline_configuration_uploader",
            new_callable=PropertyMock,
            return_value=uploader,
        ),
        patch.object(
            ManagePlotsPage,
            "pipeline_configuration_import_button",
            new_callable=PropertyMock,
            return_value=button,
        ),
        patch.object(manager, "expect_script_rerun", return_value=cycle) as observe,
        patch("tests.visual.pages.manage_plots_page.expect", side_effect=expectations.__getitem__),
    ):
        if completion_fails:
            with pytest.raises(AssertionError, match="Import app completion was not observed"):
                manager.upload_and_use_pipeline_configuration(Path("portable.json"))
        else:
            manager.upload_and_use_pipeline_configuration(Path("portable.json"))

    assert events == ["uploaded", "filename", "upload settled", "admitted", "armed", "imported"] + (
        [] if completion_fails else ["app completed"]
    )
    uploader.set_input_files.assert_called_once_with("portable.json")
    panel.get_by_title.assert_called_once_with("portable.json", exact=True)
    panel.get_by_test_id.assert_called_once_with("stFileChipIconSpinner")
    spinner_expectation.to_have_count.assert_called_once_with(0, timeout=manager.RENDER_TIMEOUT)
    button_expectation.to_be_enabled.assert_called_once_with(timeout=manager.RENDER_TIMEOUT)
    observe.assert_called_once_with()
    button.click.assert_called_once_with()
    page.wait_for_timeout.assert_not_called()
