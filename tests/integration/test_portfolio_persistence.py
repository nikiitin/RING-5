import pandas as pd
import pytest

from src.web.services.paths import PathService
from src.web.services.portfolio_service import PortfolioService
from src.web.state_manager import StateManager


@pytest.fixture
def clean_portfolio_env():
    # Setup
    StateManager.initialize()
    # Ensure portfolio dir exists
    PathService.get_portfolios_dir().mkdir(parents=True, exist_ok=True)
    yield
    # Teardown: Remove test portfolio
    PortfolioService.delete_portfolio("test_persistence")


def test_stats_config_persistence(clean_portfolio_env, tmp_path):
    """Test that stats path, pattern, and scanned variables are saved and restored."""

    # 1. Set State
    test_path = str(tmp_path / "gem5/stats/test")
    test_pattern = "*.log"
    test_scanned_vars = [
        {"name": "ipc", "type": "scalar"},
        {"name": "l2_miss_rate", "type": "vector", "entries": ["total", "mean"]},
    ]

    StateManager.set_stats_path(test_path)
    StateManager.set_stats_pattern(test_pattern)
    StateManager.set_scanned_variables(test_scanned_vars)

    # Dummy data needed for portfolio
    dummy_data = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
    StateManager.set_data(dummy_data)

    # 2. Save Portfolio
    PortfolioService.save_portfolio(
        name="test_persistence",
        data=dummy_data,
        plots=[],
        config={},
        plot_counter=0,
        csv_path=str(tmp_path / "dummy.csv"),
        parse_variables=[],
    )

    # 3. Clear State
    StateManager.clear_all()
    # Re-init to default defaults
    StateManager.initialize()

    # Verify defaults are present (different from test values)
    assert StateManager.get_stats_path() == "/path/to/gem5/stats"
    assert StateManager.get_stats_pattern() == "stats.txt"
    assert StateManager.get_scanned_variables() == []

    # 4. Load Portfolio
    portfolio_data = PortfolioService.load_portfolio("test_persistence")

    # 5. Restore State
    StateManager.restore_session_state(portfolio_data)

    # 6. Verify Restoration
    assert StateManager.get_stats_path() == test_path
    assert StateManager.get_stats_pattern() == test_pattern

    restored_vars = StateManager.get_scanned_variables()
    assert len(restored_vars) == 2
    assert restored_vars[0]["name"] == "ipc"
    assert restored_vars[1]["entries"] == ["total", "mean"]
