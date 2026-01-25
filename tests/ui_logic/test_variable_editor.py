from unittest.mock import MagicMock, patch

import pytest

from src.web.ui.components.variable_editor import VariableEditor


@pytest.fixture
def mock_streamlit():
    # Patch st in all 3 modules used
    with patch("src.web.ui.components.data_components.st") as mock_st_data, patch(
        "src.web.ui.components.card_components.st"
    ) as mock_st_card, patch("src.web.ui.components.variable_editor.st") as mock_st_var:

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
        mock_st_var.radio = mock_st.radio
        mock_st_var.button = mock_st.button
        mock_st_var.rerun = mock_st.rerun
        mock_st_var.success = mock_st.success
        mock_st_var.checkbox = mock_st.checkbox
        mock_st_var.session_state = mock_st.session_state

        # Mock columns to return list of mocks
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]

        mock_st.columns.side_effect = columns_side_effect
        mock_st_data.columns = mock_st.columns
        mock_st_var.columns = mock_st.columns

        # Mock expander
        mock_st.expander.return_value.__enter__.return_value = MagicMock()

        # Mock button defaults
        mock_st.button.return_value = False

        yield mock_st


@pytest.fixture
def mock_facade():
    with patch("src.web.ui.components.variable_editor.BackendFacade") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance


def test_variable_editor_render_existing(mock_streamlit):
    vars_config = [{"name": "v1", "type": "scalar", "_id": "1"}]

    # Setup inputs
    mock_streamlit.text_input.side_effect = ["v1", "ali"]  # Name, Alias
    mock_streamlit.selectbox.return_value = "scalar"

    updated = VariableEditor.render(vars_config)

    assert len(updated) == 1
    assert updated[0]["name"] == "v1"
    assert updated[0]["alias"] == "ali"
    assert updated[0]["type"] == "scalar"


def test_variable_editor_add_manual(mock_streamlit):
    vars_config = []

    # Button clicks: X (delete) -> False, Add Selected -> False, Add Manual -> True
    mock_streamlit.button.side_effect = lambda label, **k: label == "+ Add Manual"

    # Rerun should be called
    VariableEditor.render(vars_config)

    assert len(vars_config) == 1
    assert vars_config[0]["name"] == "new_variable"
    mock_streamlit.rerun.assert_called()


def test_variable_editor_deep_scan(mock_streamlit, mock_facade):
    vars_config = [{"name": "vec", "type": "vector", "_id": "1"}]

    # Inputs:
    # 1. Name ("vec")
    # 2. Alias ("")
    # 3. Type ("vector")

    # 4. Radio Entry Mode -> "Select from Discovered Entries" (to trigger logic checks)
    # Actually logic depends on stats_path etc.

    # Helper for side effects is tricky because of loop.
    # We'll mock specific calls if possible or allow loose matching.

    mock_streamlit.text_input.return_value = "vec"
    mock_streamlit.selectbox.return_value = "vector"

    # Trigger Deep Scan path: requires stats_path, no discovered entries, manual entry mode.

    # Simulate "Select from Discovered Entries" mode to trigger specific path
    mock_streamlit.radio.return_value = "Select from Discovered Entries"

    # Deep Scan Button Click
    # Mocking button interactions using key prefix check
    def button_side_effect(label, key=None, **kwargs):
        if key and key.startswith("deep_scan"):
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    # Mock Facade
    mock_facade.scan_entries_for_variable.return_value = ["e1", "e2"]

    VariableEditor.render(vars_config, available_variables=[], stats_path="/path")

    mock_facade.scan_entries_for_variable.assert_called_with("/path", "vec", "stats.txt")
    # Execution continues because mock rerun doesn't stop it, so we check ANY call
    mock_streamlit.success.assert_any_call("Found 2 entries!")
    mock_streamlit.rerun.assert_called()


def test_variable_editor_vector_stats_checkboxes(mock_streamlit):
    vars_config = [{"name": "vec", "type": "vector", "_id": "1", "vectorEntries": []}]

    mock_streamlit.text_input.return_value = "vec"
    mock_streamlit.selectbox.return_value = "vector"
    mock_streamlit.radio.return_value = "Vector Statistics"

    # Checkboxes: total=True, mean=False
    def checkbox_side_effect(label, **kwargs):
        if "total" in label:
            return True
        return False

    mock_streamlit.checkbox.side_effect = checkbox_side_effect

    updated = VariableEditor.render(vars_config)

    assert updated[0]["useSpecialMembers"] is True
    assert updated[0]["vectorEntries"] == ["total"]
