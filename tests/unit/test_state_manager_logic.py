from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.state_manager import StateManager


@pytest.fixture
def mock_streamlit():
    with patch("src.web.state_manager.st") as mock_st:
        # Crucial: st.session_state behaves like a dict in tests
        mock_st.session_state = {}
        yield mock_st


def test_initialize_defaults(mock_streamlit):
    StateManager.initialize()

    assert StateManager.DATA in mock_streamlit.session_state
    assert StateManager.CONFIG in mock_streamlit.session_state
    assert StateManager.PLOTS_OBJECTS in mock_streamlit.session_state
    # Check default variables
    assert len(mock_streamlit.session_state[StateManager.PARSE_VARIABLES]) == 3


def test_set_data_enforce_config_types(mock_streamlit):
    # Setup variables with configuration type
    vars_config = [{"name": "cfg", "type": "configuration"}]
    mock_streamlit.session_state[StateManager.PARSE_VARIABLES] = vars_config

    # Data with numeric "cfg" column
    df = pd.DataFrame({"cfg": [1, 2, 3], "val": [10, 20, 30]})

    StateManager.set_data(df)

    stored_df = mock_streamlit.session_state[StateManager.DATA]
    # "cfg" should be string/object now
    assert pd.api.types.is_object_dtype(stored_df["cfg"])
    assert stored_df["cfg"].tolist() == ["1", "2", "3"]


def test_update_config(mock_streamlit):
    mock_streamlit.session_state[StateManager.CONFIG] = {"a": 1}

    StateManager.update_config("a", 2)
    StateManager.update_config("b", 3)

    cfg = StateManager.get_config()
    assert cfg["a"] == 2
    assert cfg["b"] == 3


def test_set_parse_variables_generate_ids(mock_streamlit):
    # Setup variables without IDs
    vars_config = [{"name": "v1"}]

    # set_parse_variables should add IDs
    with patch("uuid.uuid4", return_value="uuid-1"):
        StateManager.set_parse_variables(vars_config)

    vars_out = StateManager.get_parse_variables()
    assert vars_out[0]["_id"] == "uuid-1"
    # Verify state was updated
    assert mock_streamlit.session_state[StateManager.PARSE_VARIABLES][0]["_id"] == "uuid-1"


def test_start_next_plot_id(mock_streamlit):
    mock_streamlit.session_state[StateManager.PLOT_COUNTER] = 10

    next_id = StateManager.start_next_plot_id()

    assert next_id == 10
    assert StateManager.get_plot_counter() == 11


def test_restore_session_state(mock_streamlit):
    # Mock BasePlot.from_dict
    with patch("src.plotting.base_plot.BasePlot.from_dict") as mock_from_dict:
        mock_plot = MagicMock()
        mock_from_dict.return_value = mock_plot

        # Initialize defaults so keys exist
        StateManager.initialize()

        portfolio_data = {
            "data_csv": "A,B\n1,2",
            "csv_path": "/path.csv",
            "plot_counter": 5,
            "config": {"theme": "dark"},
            "plots": [{"plot_type": "bar", "processed_data": "x,y\n1,10"}],
        }

        # Add transient key that MUST be cleared
        mock_streamlit.session_state["leg_orient_123"] = "v"

        # Execute restore
        StateManager.restore_session_state(portfolio_data)

        # Check restored data
        assert StateManager.get_csv_path() == "/path.csv"
        assert StateManager.get_plot_counter() == 5
        assert StateManager.get_config()["theme"] == "dark"

        # Check data loading
        stored_df = StateManager.get_data()
        assert len(stored_df) == 1
        assert stored_df.iloc[0]["A"] == 1

        # Check plot loading
        mock_from_dict.assert_called()
        # Verify plots list updated
        assert mock_streamlit.session_state[StateManager.PLOTS_OBJECTS] == [mock_plot]

        # Check cleared keys
        assert "leg_orient_123" not in mock_streamlit.session_state
