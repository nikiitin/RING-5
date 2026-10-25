from collections.abc import Generator
from copy import deepcopy
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from src.core.application_api import ApplicationAPI
from src.core.common.security_limits import MAX_SCAN_FILES
from src.core.models.data_models import ParseVariableConfig
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_streamlit() -> Generator[MagicMock, None, None]:
    # Patch st in all 3 modules used
    with (
        patch("src.web.components.common.data_components.st") as mock_st_data,
        patch("src.web.components.common.card_components.st") as mock_st_card,
        patch("src.web.components.data_source.variable_editor.st") as mock_st_var,
    ):

        mock_st = MagicMock()
        mock_st.session_state = {}

        # Connect mocks
        mock_st_data.dataframe = mock_st.dataframe
        mock_st_data.metric = mock_st.metric

        mock_st_card.expander = mock_st.expander
        mock_st_card.button = mock_st.button
        mock_st_card.columns = mock_st.columns

        mock_st_var.text_input = mock_st.text_input
        mock_st_var.selectbox = mock_st.selectbox
        mock_st_var.segmented_control = mock_st.segmented_control
        mock_st_var.pills = mock_st.pills
        mock_st_var.button = mock_st.button
        mock_st_var.rerun = mock_st.rerun
        mock_st_var.success = mock_st.success
        mock_st_var.checkbox = mock_st.checkbox
        mock_st_var.session_state = mock_st.session_state

        # Mock st.dialog as a pass-through decorator, supporting **kwargs like dismissible
        def dialog_mock(title: Any, **kwargs: Any) -> Any:

            def decorator(f: Any) -> None:

                return f

            return decorator

        mock_st_var.dialog.side_effect = dialog_mock

        mock_st.columns.side_effect = columns_side_effect
        mock_st_data.columns = mock_st.columns
        mock_st_var.columns = mock_st.columns

        # Mock expander
        mock_st.expander.return_value.__enter__.return_value = MagicMock()

        # Mock button defaults
        mock_st.button.return_value = False

        yield mock_st


@pytest.fixture
def mock_api() -> Any:
    api = MagicMock(spec=ApplicationAPI)
    api.state_manager = MagicMock()
    api.get_simulator_info.side_effect = ApplicationAPI.get_simulator_info
    api.state_manager.get_simulator.return_value = "gem5"
    api.state_manager.get_scanned_variables.return_value = []
    api.state_manager.get_parse_variables.return_value = []
    return api


def test_variable_editor_render_existing(mock_streamlit: Any, mock_api: Any) -> None:

    # [test->req~ring5.ingestion.variable-editor~1]
    vars_config = cast(list[ParseVariableConfig], [{"name": "v1", "type": "scalar", "_id": "1"}])

    # Setup inputs
    mock_streamlit.text_input.side_effect = ["v1", "ali"]  # Name, Alias
    mock_streamlit.selectbox.return_value = "scalar"

    from src.web.components.data_source.variable_editor import VariableEditor

    updated = VariableEditor.render(mock_api, vars_config)

    assert len(updated) == 1
    assert updated[0]["name"] == "ali"
    assert updated[0].get("source_name") == "v1"
    assert updated[0]["type"] == "scalar"
    assert vars_config[0]["name"] == "v1"
    assert "source_name" not in vars_config[0]


def test_variable_editor_add_manual(mock_streamlit: Any, mock_api: Any) -> None:

    # [test->req~ring5.ingestion.variable-editor~1]
    vars_config: list[ParseVariableConfig] = []

    # Button clicks: X (delete) -> False, Add Selected -> False, Add Manual -> True
    mock_streamlit.button.side_effect = lambda label, **k: label == "+ Add Manual"

    # The add-section persists to state (not the local copy) before the rerun, so the new
    # variable survives — assert it was written via the state manager.
    persisted: list[ParseVariableConfig] = []
    mock_api.state_manager.get_parse_variables.return_value = persisted

    from src.web.components.data_source.variable_editor import VariableEditor

    VariableEditor.render(mock_api, vars_config)

    mock_api.state_manager.set_parse_variables.assert_called_once()
    saved = mock_api.state_manager.set_parse_variables.call_args[0][0]
    assert any(v["name"] == "new_variable" for v in saved)
    mock_streamlit.rerun.assert_called()


def test_variable_editor_deep_scan_submits_through_facade(
    mock_streamlit: Any, mock_api: Any
) -> None:
    # [test->req~ring5.ingestion.scan-presets-progress~1]

    vars_config = cast(list[ParseVariableConfig], [{"name": "vec", "type": "vector", "_id": "1"}])

    mock_streamlit.text_input.return_value = "vec"
    mock_streamlit.selectbox.return_value = "vector"

    # Trigger Deep Scan path: first segmented_control = "Entries Only" (parsing mode),
    # pills = "Select from Discovered Entries" (entry mode)
    mock_streamlit.segmented_control.return_value = "Entries Only"
    mock_streamlit.pills.return_value = "Select from Discovered Entries"

    # Simulate clicking the Deep Scan button
    def button_side_effect(label: Any, key: Any = None, **kwargs: Any) -> int:

        if key and key.startswith("deep_scan"):
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    # Mock Async Pipeline - simulate that scan completed
    mock_future = MagicMock()
    mock_future.result.return_value = [{"name": "vec", "type": "vector", "entries": ["e1", "e2"]}]
    mock_api.submit_scan_async.return_value = [mock_future]

    from src.web.components.data_source.variable_editor import VariableEditor

    with (
        patch.object(VariableEditor, "_show_scan_dialog") as mock_dialog,
        patch(
            "src.web.components.data_source.variable_editor.validate_web_stats_path",
            return_value=Path("/stats"),
        ),
    ):
        VariableEditor.render(
            mock_api,
            vars_config,
            available_variables=[],
            stats_path="/stats",
            stats_pattern="stats*.txt",
        )

        mock_dialog.assert_called_once()
    mock_api.submit_scan_async.assert_called_once_with("/stats", "stats*.txt", limit=MAX_SCAN_FILES)
    assert mock_dialog.call_args.args[3] == [mock_future]


def test_variable_editor_vector_stats_checkboxes(mock_streamlit: Any, mock_api: Any) -> None:

    # [test->req~ring5.ingestion.variable-entry-selection~1]
    vars_config = cast(
        list[ParseVariableConfig],
        [{"name": "vec", "type": "vector", "_id": "1", "params": {"entries": []}}],
    )

    mock_streamlit.text_input.return_value = "vec"
    mock_streamlit.selectbox.return_value = "vector"

    # "Statistics Only" parsing mode triggers statistics checkboxes
    mock_streamlit.segmented_control.return_value = "Statistics Only"

    # Checkboxes: total=True, mean=False
    def checkbox_side_effect(label: Any, **kwargs: Any) -> int:

        if "total" in label:
            return True
        return False

    mock_streamlit.checkbox.side_effect = checkbox_side_effect

    from src.web.components.data_source.variable_editor import VariableEditor

    updated = VariableEditor.render(mock_api, vars_config)

    assert updated[0]["params"].get("statistics") == ["total"]
    assert not updated[0]["params"].get("entries")


def test_disabling_pattern_selection_removes_the_previous_filter(mock_api: Any) -> None:
    from src.web.components.data_source.variable_editor import VariableEditor

    pattern = r"cpu\d+.ipc"
    original: ParseVariableConfig = {
        "name": "IPC",
        "source_name": pattern,
        "type": "scalar",
        "params": {"source_type": "scalar", "selected_sources": ["cpu0.ipc"]},
        "keep_indices": True,
    }
    config = deepcopy(original)
    mock_api.state_manager.get_scanned_variables.return_value = [
        {
            "name": pattern,
            "type": "vector",
            "source_type": "scalar",
            "entries": [],
            "instances": [
                {"source_name": "cpu0.ipc", "indices": ["0"]},
                {"source_name": "cpu1.ipc", "indices": ["1"]},
            ],
        }
    ]
    with (
        patch("src.web.components.data_source.variable_editor.st.checkbox", return_value=True),
        patch(
            "src.web.components.data_source.variable_editor.PatternIndexSelector.render_selector",
            return_value=(False, ["cpu0.ipc", "cpu1.ipc"]),
        ),
    ):
        VariableEditor._render_pattern_index_for_variable(mock_api, config, original, "pattern")
    assert config["keep_indices"] is True
    assert "selected_sources" not in config["params"]
    assert original["params"]["selected_sources"] == ["cpu0.ipc"]
