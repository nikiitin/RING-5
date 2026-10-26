"""In-memory repository state retains data, configuration, and plot identifiers."""

from src.core.common.typed_table_codec import TypedTableCodec
from typing import cast

import pandas as pd

from src.core.models.portfolio_models import PortfolioData
from src.core.state.repository_state_manager import RepositoryStateManager as StateManager


def test_statemanager_initialization() -> None:
    """Verify that StateManager initializes correctly."""
    # StateManager is now an instance, often managed by ApplicationAPI,
    # but strictly speaking RepositoryStateManager can be instantiated directly.
    mgr = StateManager()

    # Scanned variables should be empty list, not None
    assert mgr.get_scanned_variables() == []
    # Parse variables should have defaults
    assert len(mgr.get_parse_variables()) > 0


def test_data_repository_roundtrip() -> None:
    """Verify data storage and retrieval via StateManager."""
    mgr = StateManager()

    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    mgr.set_data(df)

    retrieved_df = mgr.get_data()
    assert retrieved_df is not None
    assert retrieved_df.equals(df)
    assert mgr.has_data()


def test_config_repository_updates() -> None:
    """Verify config management."""
    mgr = StateManager()

    mgr.update_config("test_key", "test_value")
    config = mgr.get_config()

    assert config["test_key"] == "test_value"


def test_plot_lifecycle() -> None:
    """Verify plot counter and plot list management."""
    mgr = StateManager()

    # Counter increments
    id1 = mgr.start_next_plot_id()
    id2 = mgr.start_next_plot_id()
    assert id1 == 0
    assert id2 == 1
    assert mgr.get_plot_counter() == 2

    # Active plot tracking
    mgr.set_current_plot_id(10)
    assert mgr.get_current_plot_id() == 10


def test_session_restoration() -> None:
    """Verify that SessionRepository can restore data."""
    mgr = StateManager()

    portfolio_data = cast(
        PortfolioData,
        {
            "parser_strategy": "simple",
            "loaded_origin": None,
            "simulator": "gem5",
            "csv_path": "/mock/path.csv",
            "plot_counter": 42,
            "config": {"theme": "scientific"},
            "data": TypedTableCodec.encode(pd.DataFrame({"col1": ["val1"], "col2": ["val2"]})),
        },
    )

    mgr.restore_session(portfolio_data)

    assert mgr.get_csv_path() == "/mock/path.csv"
    assert mgr.get_plot_counter() == 42
    assert mgr.get_config()["theme"] == "scientific"

    df = mgr.get_data()
    assert df is not None
    assert len(df) == 1
    assert df.iloc[0]["col1"] == "val1"
