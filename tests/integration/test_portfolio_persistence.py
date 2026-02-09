import pandas as pd
import pytest

from src.core.services.path_service import PathService
from src.core.services.portfolio_service import PortfolioService
from src.core.state.state_manager import RepositoryStateManager


@pytest.fixture
def clean_portfolio_env():
    # Setup
    state_manager = RepositoryStateManager()
    portfolio_service = PortfolioService(state_manager)

    # Ensure portfolio dir exists
    PathService.get_portfolios_dir().mkdir(parents=True, exist_ok=True)
    yield state_manager, portfolio_service

    # Teardown: Remove test portfolio
    portfolio_service.delete_portfolio("test_persistence")


def test_stats_config_persistence(clean_portfolio_env, tmp_path):
    """Test that stats path, pattern, and scanned variables are saved and restored."""
    state_manager, portfolio_service = clean_portfolio_env

    # 1. Set State
    test_path = str(tmp_path / "gem5/stats/test")
    test_pattern = "*.log"
    test_scanned_vars = [
        {"name": "ipc", "type": "scalar"},
        {"name": "l2_miss_rate", "type": "vector", "entries": ["total", "mean"]},
    ]

    state_manager.set_stats_path(test_path)
    state_manager.set_stats_pattern(test_pattern)
    state_manager.set_scanned_variables(test_scanned_vars)

    # Dummy data needed for portfolio
    dummy_data = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
    state_manager.set_data(dummy_data)

    # 2. Save Portfolio
    portfolio_service.save_portfolio(
        name="test_persistence",
        data=dummy_data,
        plots=[],
        config={},
        plot_counter=0,
        csv_path=str(tmp_path / "dummy.csv"),
        parse_variables=[],
    )

    # 3. Clear State
    state_manager.clear_all()
    # Re-init (create new instance or just plain clear)
    # The new instance in real app works this way, or same instance cleared.

    # 4. Load Portfolio
    portfolio_data = portfolio_service.load_portfolio("test_persistence")

    # 5. Restore State
    state_manager.restore_session(portfolio_data)

    # 6. Verify Restoration - ensure values match what we saved
    assert state_manager.get_stats_path() == test_path
    assert state_manager.get_stats_pattern() == test_pattern

    restored_vars = state_manager.get_scanned_variables()
    assert len(restored_vars) == 2
    assert restored_vars[0]["name"] == "ipc"
    assert restored_vars[1]["entries"] == ["total", "mean"]
