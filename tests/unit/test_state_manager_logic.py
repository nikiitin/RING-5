"""Repository state preserves data, parser options, and plot identifiers."""

from typing import cast
from unittest.mock import patch

import pandas as pd

from src.core.models.data_models import ParseVariableConfig
from src.core.models.portfolio_models import PortfolioData
from src.core.state.repository_state_manager import RepositoryStateManager as StateManager


def test_initialize_defaults() -> None:
    """Verify default state initialization."""
    mgr = StateManager()

    # Check default variables
    # Default variables key in memory storage should match StateManager enum
    assert len(mgr.get_parse_variables()) > 0


def test_set_data_preserves_frame_types_despite_parser_editor() -> None:
    """Generic frame publication preserves values and types independently of the editor."""
    mgr = StateManager()

    # Setup variables with configuration type
    vars_config = cast(list[ParseVariableConfig], [{"name": "cfg", "type": "configuration"}])
    mgr.set_parse_variables(vars_config)
    editor = mgr.get_parse_variables()

    # Data with numeric "cfg" column
    df = pd.DataFrame({"cfg": [1, 2, 3], "val": [10, 20, 30]})

    mgr.set_data(df)

    stored_df = mgr.get_data()
    assert stored_df is not None
    assert pd.api.types.is_integer_dtype(stored_df["cfg"])
    assert stored_df["cfg"].tolist() == [1, 2, 3]
    pd.testing.assert_frame_equal(stored_df, df)
    assert mgr.get_parse_variables() == editor


def test_update_config() -> None:
    """Verify config updates via facade."""
    mgr = StateManager()

    mgr.update_config("a", 1)
    mgr.update_config("a", 2)
    mgr.update_config("b", 3)

    cfg = mgr.get_config()
    assert cfg["a"] == 2
    assert cfg["b"] == 3


def test_set_parse_variables_generate_ids() -> None:
    """Verify unique ID generation for parse variables."""
    mgr = StateManager()

    # Setup variables without IDs
    vars_config = cast(list[ParseVariableConfig], [{"name": "v1"}])

    with patch("src.core.common.variable_identity.uuid") as mock_uuid:
        mock_uuid.uuid4.return_value = "uuid-1"
        mgr.set_parse_variables(vars_config)

    vars_out = mgr.get_parse_variables()
    assert vars_out[0]["_id"] == "uuid-1"


def test_start_next_plot_id() -> None:
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


def test_restore_session_state() -> None:
    """Verify session restoration logic."""
    mgr = StateManager()

    portfolio_data = cast(
        PortfolioData,
        {
            "parser_strategy": "simple",
            "loaded_origin": None,
            "simulator": "gem5",
            "csv_path": "/mock/test.csv",
            "plot_counter": 5,
            "plots": [],
        },
    )

    mgr.restore_session(portfolio_data)

    assert mgr.get_csv_path() == "/mock/test.csv"
    assert mgr.get_plot_counter() == 5
