"""
Refactored unit tests for StateManager logic.
Uses mocks instead of MemoryStorageAdapter.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from src.core.state.state_manager import StateManager


@pytest.fixture
def mock_session_state():
    """Mock streamlit.session_state as a dictionary."""
    with patch("streamlit.session_state", new_callable=dict) as mock_state:
        yield mock_state


def test_initialize_defaults(mock_session_state):
    """Verify default state initialization."""
    mgr = StateManager()

    # Check default variables
    # Default variables key in memory storage should match StateManager enum
    assert len(mgr.get_parse_variables()) > 0


def test_set_data_enforce_config_types(mock_session_state):
    """Verify that set_data enforces string types for configuration variables."""
    mgr = StateManager()

    # Setup variables with configuration type
    vars_config = [{"name": "cfg", "type": "configuration"}]
    mgr.set_parse_variables(vars_config)

    # Data with numeric "cfg" column
    df = pd.DataFrame({"cfg": [1, 2, 3], "val": [10, 20, 30]})

    mgr.set_data(df)

    stored_df = mgr.get_data()
    assert stored_df is not None
    # "cfg" should be string/object now
    assert pd.api.types.is_string_dtype(stored_df["cfg"]) or pd.api.types.is_object_dtype(
        stored_df["cfg"]
    )
    assert stored_df["cfg"].tolist() == ["1", "2", "3"]


def test_update_config(mock_session_state):
    """Verify config updates via facade."""
    mgr = StateManager()

    mgr.update_config("a", 1)
    mgr.update_config("a", 2)
    mgr.update_config("b", 3)

    cfg = mgr.get_config()
    assert cfg["a"] == 2
    assert cfg["b"] == 3


def test_set_parse_variables_generate_ids(mock_session_state):
    """Verify unique ID generation for parse variables."""
    mgr = StateManager()

    # Setup variables without IDs
    vars_config = [{"name": "v1"}]

    with patch("src.core.state.repositories.parser_state_repository.uuid") as mock_uuid:
        mock_uuid.uuid4.return_value = "uuid-1"
        mgr.set_parse_variables(vars_config)

    vars_out = mgr.get_parse_variables()
    assert vars_out[0]["_id"] == "uuid-1"


def test_start_next_plot_id(mock_session_state):
    """Verify plot ID generation increments correctly."""
    mgr = StateManager()

    # We need to access plot repo directly or use public API if available to set counter
    # StateManager doesn't expose set_plot_counter directly in AbstractStateManager protocol maybe?
    # Let's check src.core.state.state_manager.py
    # Yes, it does: def set_plot_counter(self, counter: int) -> None: ...
    mgr.set_plot_counter(10)

    next_id = mgr.start_next_plot_id()

    assert next_id == 10
    assert mgr.get_plot_counter() == 11


def test_restore_session_state(mock_session_state):
    """Verify session restoration logic."""
    mgr = StateManager()

    portfolio_data = {"csv_path": "/mock/test.csv", "plot_counter": 5, "plots": []}

    mgr.restore_session(portfolio_data)

    assert mgr.get_csv_path() == "/mock/test.csv"
    assert mgr.get_plot_counter() == 5
