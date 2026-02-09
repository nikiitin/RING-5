import importlib
from unittest.mock import MagicMock, patch

import pytest

# Defer import of DataSourceComponents to fixture to ensure patching works
import src.web.pages.ui.components.data_source_components as ds_module


@pytest.fixture
def components_bundle():
    """Patch st and reload module to capture decorator."""

    # 1. Patch streamlit.dialog globally so the decorator is intercepted during reload
    # Accept both positional and keyword arguments to handle dismissible parameter
    with patch("streamlit.dialog", side_effect=lambda title=None, **kwargs: lambda func: func):
        import src.web.pages.ui.components.variable_editor as ve_module

        importlib.reload(ve_module)
        importlib.reload(ds_module)

    # 2. Patch the module's st attribute for runtime widget mocking
    with patch("src.web.pages.ui.components.data_source_components.st") as mock_st, patch(
        "src.web.pages.ui.components.variable_editor.st", new=mock_st
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
def mock_api():
    api = MagicMock()
    api.state_manager = MagicMock()
    api.state_manager.get_scanned_variables.return_value = []
    api.state_manager.get_parse_variables.return_value = []

    # Wire up variable utility methods with realistic behavior
    api.data_services.generate_variable_id.return_value = "test_id"
    api.data_services.parse_comma_separated_entries.side_effect = lambda s: [
        e.strip() for e in s.split(",") if e.strip()
    ]
    api.data_services.format_entries_as_string.side_effect = lambda entries: ", ".join(entries)
    api.data_services.filter_internal_stats.side_effect = lambda entries: entries
    return api


def test_variable_config_dialog_manual_entry_scalar(components_bundle, mock_api):
    """Test manual entry of a scalar variable."""
    mock_streamlit, DataSourceComponents = components_bundle

    # Interaction parameters.
    mock_streamlit.radio.return_value = "Manual Entry"
    mock_streamlit.text_input.return_value = "my_var"
    mock_streamlit.selectbox.return_value = "scalar"
    mock_streamlit.button.return_value = True

    DataSourceComponents.variable_config_dialog(mock_api)

    # Verify StateManager update
    args = mock_api.state_manager.set_parse_variables.call_args
    assert args is not None
    new_vars = args[0][0]
    assert len(new_vars) == 1
    assert new_vars[0]["name"] == "my_var"
    assert new_vars[0]["type"] == "scalar"

    mock_streamlit.success.assert_called()
    mock_streamlit.rerun.assert_called()


def test_variable_config_dialog_manual_entry_vector(components_bundle, mock_api):
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

    DataSourceComponents.variable_config_dialog(mock_api)

    assert mock_api.state_manager.set_parse_variables.called
    args = mock_api.state_manager.set_parse_variables.call_args
    assert args is not None
    new_vars = args[0][0]
    assert new_vars[0]["type"] == "vector"
    entries = new_vars[0]["vectorEntries"]
    # VariableEditor stores list of strings
    assert "cpu0" in entries


def test_variable_config_dialog_search_scanned(components_bundle, mock_api):
    """Test adding from scanned variables."""
    mock_streamlit, DataSourceComponents = components_bundle

    scanned = [
        {"name": "system.cpu.ipc", "type": "scalar", "id": "ipc"},
        {"name": "system.l2.misses", "type": "vector", "entries": ["cpu0", "cpu1"]},
    ]
    mock_api.state_manager.get_scanned_variables.return_value = scanned

    mock_streamlit.radio.return_value = "Search Scanned Variables"
    mock_streamlit.selectbox.side_effect = [0]
    mock_streamlit.text_input.return_value = "IPC"
    mock_streamlit.button.return_value = True

    # Expect 1 call for search index.

    DataSourceComponents.variable_config_dialog(mock_api)

    args = mock_api.state_manager.set_parse_variables.call_args
    new_vars = args[0][0]
    assert new_vars[0]["name"] == "IPC"
    assert new_vars[0]["type"] == "scalar"


def test_variable_config_dialog_validation_fail(components_bundle, mock_api):
    """Test validation failure (no name)."""
    mock_streamlit, DataSourceComponents = components_bundle

    mock_streamlit.radio.return_value = "Manual Entry"
    mock_streamlit.text_input.return_value = ""  # Empty name
    mock_streamlit.selectbox.return_value = "scalar"
    mock_streamlit.button.return_value = True

    DataSourceComponents.variable_config_dialog(mock_api)

    mock_streamlit.error.assert_called_with("Variable name is required.")
    mock_api.state_manager.set_parse_variables.assert_not_called()
