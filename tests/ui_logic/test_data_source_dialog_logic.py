import importlib
from unittest.mock import MagicMock, patch

import pytest

# Defer import of DataSourceComponents to fixture to ensure patching works
import src.web.ui.components.data_source_components as ds_module


@pytest.fixture
def components_bundle():
    """Patch st and reload module to capture decorator."""

    # 1. Patch streamlit.dialog globally so the decorator is intercepted during reload
    # Accept both positional and keyword arguments to handle dismissible parameter
    with patch("streamlit.dialog", side_effect=lambda title=None, **kwargs: lambda func: func):
        importlib.reload(ds_module)

    # 2. Patch the module's st attribute for runtime widget mocking
    with patch("src.web.ui.components.data_source_components.st") as mock_st, patch(
        "src.web.ui.components.variable_editor.st", new=mock_st
    ):

        mock_st.session_state = {}

        # Mock columns
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            return [MagicMock()]

        mock_st.columns.side_effect = columns_side_effect

        # Default return values for widgets to avoid TypeErrors
        mock_st.number_input.return_value = 1
        mock_st.checkbox.return_value = False

        # We don't need to patch dialog here, as the function is already undecorated

        yield mock_st, ds_module.DataSourceComponents


@pytest.fixture
def mock_state_manager():
    with patch("src.web.ui.components.data_source_components.StateManager") as mock_sm:
        mock_sm.get_scanned_variables.return_value = []
        mock_sm.get_parse_variables.return_value = []
        yield mock_sm


def test_variable_config_dialog_manual_entry_scalar(components_bundle, mock_state_manager):
    """Test manual entry of a scalar variable."""
    mock_streamlit, DataSourceComponents = components_bundle

    # Interaction parameters.
    mock_streamlit.radio.return_value = "Manual Entry"
    mock_streamlit.text_input.return_value = "my_var"
    mock_streamlit.selectbox.return_value = "scalar"
    mock_streamlit.button.return_value = True

    DataSourceComponents.variable_config_dialog()

    # Verify StateManager update
    args = mock_state_manager.set_parse_variables.call_args
    assert args is not None
    new_vars = args[0][0]
    assert len(new_vars) == 1
    assert new_vars[0]["name"] == "my_var"
    assert new_vars[0]["type"] == "scalar"

    mock_streamlit.success.assert_called()
    mock_streamlit.rerun.assert_called()


def test_variable_config_dialog_manual_entry_vector(components_bundle, mock_state_manager):
    """Test manual entry of a vector variable."""
    mock_streamlit, DataSourceComponents = components_bundle

    # Added return value for new statistics-only parsing mode radio
    mock_streamlit.radio.side_effect = [
        "Manual Entry",
        "Manual Entry Names",
        "Entries + Statistics",
    ]

    mock_streamlit.text_input.side_effect = ["vec", "cpu0"]

    mock_streamlit.selectbox.return_value = "vector"

    mock_streamlit.button.side_effect = [False, True]

    DataSourceComponents.variable_config_dialog()

    assert mock_state_manager.set_parse_variables.called
    args = mock_state_manager.set_parse_variables.call_args
    assert args is not None
    new_vars = args[0][0]
    assert new_vars[0]["type"] == "vector"
    entries = new_vars[0]["vectorEntries"]
    # VariableEditor stores list of strings
    assert "cpu0" in entries


def test_variable_config_dialog_search_scanned(components_bundle, mock_state_manager):
    """Test adding from scanned variables."""
    mock_streamlit, DataSourceComponents = components_bundle

    scanned = [
        {"name": "system.cpu.ipc", "type": "scalar", "id": "ipc"},
        {"name": "system.l2.misses", "type": "vector", "entries": ["cpu0", "cpu1"]},
    ]
    mock_state_manager.get_scanned_variables.return_value = scanned

    mock_streamlit.radio.return_value = "Search Scanned Variables"
    mock_streamlit.selectbox.side_effect = [0]
    mock_streamlit.text_input.return_value = "IPC"
    mock_streamlit.button.return_value = True

    # Expect 1 call for search index.

    DataSourceComponents.variable_config_dialog()

    args = mock_state_manager.set_parse_variables.call_args
    new_vars = args[0][0]
    assert new_vars[0]["name"] == "IPC"
    assert new_vars[0]["type"] == "scalar"


def test_variable_config_dialog_validation_fail(components_bundle, mock_state_manager):
    """Test validation failure (no name)."""
    mock_streamlit, DataSourceComponents = components_bundle

    mock_streamlit.radio.return_value = "Manual Entry"
    mock_streamlit.text_input.return_value = ""  # Empty name
    mock_streamlit.selectbox.return_value = "scalar"
    mock_streamlit.button.return_value = True

    DataSourceComponents.variable_config_dialog()

    mock_streamlit.error.assert_called_with("Variable name is required.")
    mock_state_manager.set_parse_variables.assert_not_called()
