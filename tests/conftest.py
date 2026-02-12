"""Root conftest.py — shared test utilities available to ALL tests.

Provides common helper functions and fixtures used across multiple
test directories (unit, ui_unit, integration).
"""

from typing import Any, Dict, List, Union
from unittest.mock import MagicMock

import pandas as pd
import pytest

# Register helper fixture plugins so they are available everywhere
pytest_plugins = ["tests.helpers.gem5_fixtures"]

# ---------------------------------------------------------------------------
# Shared Helpers
# ---------------------------------------------------------------------------


def columns_side_effect(
    spec: Union[int, list[Any], tuple[Any, ...]], **kwargs: Any
) -> List[MagicMock]:
    """Mock st.columns() behavior — returns a list of MagicMock column objects.

    Mimics Streamlit's columns() API which accepts either an int (number
    of equal-width columns) or a list/tuple (relative widths).

    Args:
        spec: Number of columns (int) or list/tuple of relative widths.
        **kwargs: Absorbed — matches st.columns(gap=..., vertical_alignment=...).

    Returns:
        List of MagicMock objects, one per column.
    """
    if isinstance(spec, int):
        return [MagicMock() for _ in range(spec)]
    elif isinstance(spec, (list, tuple)):
        return [MagicMock() for _ in range(len(spec))]
    return [MagicMock()]


# ---------------------------------------------------------------------------
# Shared Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_api() -> MagicMock:
    """Basic mock ApplicationAPI with state_manager.

    Provides the minimal mock structure used by most UI tests.
    Override in individual test files when extended wiring is needed
    (e.g., api.backend, api.portfolio, api.data_services).
    """
    api = MagicMock()
    api.state_manager = MagicMock()
    return api


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Minimal DataFrame mimicking parsed gem5 CSV output.

    Contains benchmark, config, and a numeric column suitable for
    shaper, plot, and pipeline tests.
    """
    return pd.DataFrame(
        {
            "benchmark_name": ["mcf", "mcf", "omnetpp", "omnetpp", "xalancbmk", "xalancbmk"],
            "config_description": [
                "baseline",
                "optimized",
                "baseline",
                "optimized",
                "baseline",
                "optimized",
            ],
            "simTicks": [
                3210000000,
                2890000000,
                7890000000,
                7120000000,
                5670000000,
                5100000000,
            ],
            "system.cpu.ipc": [2.10, 2.35, 1.45, 1.62, 1.78, 1.98],
        }
    )


@pytest.fixture
def sample_data_extended(sample_data: pd.DataFrame) -> pd.DataFrame:
    """Extended DataFrame with additional numeric columns for manager tests."""
    df = sample_data.copy()
    df["system.cpu.numCycles"] = [321000, 289000, 789000, 712000, 567000, 510000]
    df["system.cpu.committedInsts"] = [674100, 679150, 1144050, 1153440, 1009260, 1009800]
    return df


@pytest.fixture
def sample_pipeline_config() -> List[Dict[str, Any]]:
    """Valid shaper pipeline config exercising the main shaper types."""
    return [
        {
            "type": "columnSelector",
            "columns": ["benchmark_name", "config_description", "simTicks"],
        },
        {
            "type": "normalize",
            "statistic_column": "simTicks",
            "group_column": "benchmark_name",
            "baseline_label": "baseline",
            "label_column": "config_description",
        },
        {
            "type": "sort",
            "sort_column": "benchmark_name",
            "ascending": True,
        },
    ]


@pytest.fixture
def mock_state_manager() -> MagicMock:
    """Mock RepositoryStateManager with all sub-repositories wired.

    Provides the minimal structure expected by services that take
    a StateManager dependency.
    """
    sm = MagicMock()
    sm.get_data.return_value = None
    sm.get_processed_data.return_value = None
    sm.get_config.return_value = {}
    sm.get_plots.return_value = []
    sm.get_csv_pool.return_value = []
    sm.get_saved_configs.return_value = []
    sm.get_parse_variables.return_value = []
    sm.get_manager_history.return_value = []
    sm.get_portfolio_history.return_value = []
    return sm
