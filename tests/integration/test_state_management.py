"""
Integration Test: State Management

Tests the state management and session persistence layer:
1. Portfolio save/load (complete workspace snapshots)
2. Session state recovery after crash
3. Parser state persistence across sessions
4. Configuration versioning and migration

This validates the state management infrastructure for long-running analysis sessions.
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.core.services.paths import PathService
from src.core.services.portfolio_service import PortfolioService
from src.core.state.repositories.parser_state_repository import ParserStateRepository
from src.core.state.state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.types.grouped_bar_plot import GroupedBarPlot


@pytest.fixture
def sample_workspace_data() -> Dict[str, Any]:
    """
    Create sample workspace data for state persistence testing.
    """
    data = pd.DataFrame(
        {
            "benchmark": ["mcf", "omnetpp", "xalancbmk"],
            "config": ["baseline", "baseline", "baseline"],
            "ipc": [1.2, 1.5, 1.8],
        }
    )

    plot_config = {
        "type": "grouped_bar",
        "x_column": "benchmark",
        "y_column": "ipc",
        "group_column": "config",
        "title": "IPC by Benchmark",
    }

    parser_state = {
        "stats_path": "/path/to/gem5/output",
        "stats_pattern": "stats.txt",
        "variables": [{"name": "system.cpu.ipc", "type": "scalar", "params": {}}],
        "scanned_vars": [],
    }

    return {"data": data, "plot_config": plot_config, "parser_state": parser_state}


@pytest.fixture
def mock_session_state():
    """Mock streamlit.session_state as a dictionary."""
    with patch("streamlit.session_state", new_callable=dict) as mock_state:
        yield mock_state


@pytest.fixture
def state_manager(mock_session_state):
    """Initialize RepositoryStateManager with mocked session state."""
    return RepositoryStateManager()


@pytest.fixture
def portfolio_service(state_manager, tmp_path):
    """Create PortfolioService instance."""
    # Mock PathService to return tmp_path for portfolios
    with patch("src.core.services.paths.PathService.get_portfolios_dir", return_value=tmp_path):
        service = PortfolioService(state_manager)
        yield service


class TestStateManagement:
    """Integration tests for state persistence and recovery."""

    def test_portfolio_save_and_load(
        self, sample_workspace_data: Dict[str, Any], portfolio_service: PortfolioService
    ) -> None:
        """
        Test complete portfolio save and load cycle.
        """
        data = sample_workspace_data["data"]

        # Create plot from config with required args
        plot = GroupedBarPlot(plot_id=1, name="test_plot")

        # Save portfolio with correct signature
        portfolio_service.save_portfolio(
            name="test_workspace",
            data=data,
            plots=[plot],
            config={"version": "2.0"},
            plot_counter=1,
        )

        # Verify file was created
        portfolio_file = PathService.get_portfolios_dir() / "test_workspace.json"
        assert portfolio_file.exists()

        # Load portfolio
        loaded = portfolio_service.load_portfolio("test_workspace")

        # Verify data integrity
        assert loaded is not None
        assert "data_csv" in loaded or "data" in loaded
        assert "plots" in loaded
        assert "config" in loaded

        # Verify data matches
        if "data_csv" in loaded:
            import io

            loaded_data = pd.read_csv(io.StringIO(loaded["data_csv"]))
        else:
            loaded_data = loaded["data"]

        pd.testing.assert_frame_equal(
            data.reset_index(drop=True), loaded_data.reset_index(drop=True)
        )

        # Verify plots restored
        assert len(loaded["plots"]) == 1
        assert isinstance(loaded["plots"][0], dict)
        assert loaded["plots"][0]["plot_type"] == "grouped_bar"

    def test_parser_state_persistence(self) -> None:
        """
        Test parser state repository get/set operations (in-memory).
        """
        # ParserStateRepository is now pure in-memory, no Adapter needed
        repo = ParserStateRepository()

        # Set parser state using repository methods
        repo.set_stats_path("/gem5/output")
        repo.set_stats_pattern("*.stats.txt")

        variables = [
            {"name": "system.cpu.ipc", "type": "scalar", "params": {}, "_id": "1"},
            {"name": "system.cpu.numCycles", "type": "scalar", "params": {}, "_id": "2"},
        ]
        repo.set_parse_variables(variables)

        scanned_vars = [
            {"name": "system.cpu.ipc", "type": "scalar"},
            {"name": "system.cpu.numCycles", "type": "scalar"},
        ]
        repo.set_scanned_variables(scanned_vars)

        # Retrieve state using repository methods
        assert repo.get_stats_path() == "/gem5/output"
        assert repo.get_stats_pattern() == "*.stats.txt"
        assert len(repo.get_parse_variables()) == 2
        assert len(repo.get_scanned_variables()) == 2

    def test_session_recovery_after_crash(
        self,
        sample_workspace_data: Dict[str, Any],
        portfolio_service: PortfolioService,
    ) -> None:
        """
        Simulate session crash and recovery workflow.
        """
        data = sample_workspace_data["data"]

        # Simulate working session
        plot = GroupedBarPlot(plot_id=1, name="autosave_plot")

        # Auto-save portfolio
        portfolio_service.save_portfolio(
            name="autosave",
            data=data,
            plots=[plot],
            config={"last_save": "2026-01-27T10:00:00"},
            plot_counter=1,
        )

        # Simulate crash (destroy objects)
        del data
        del plot

        # Simulate recovery (new session)
        recovered = portfolio_service.load_portfolio("autosave")

        # Verify recovery successful
        assert recovered is not None
        assert len(recovered["plots"]) > 0

        # Verify can continue work
        if "data_csv" in recovered:
            import io

            recovered_data = pd.read_csv(io.StringIO(recovered["data_csv"]))
        else:
            recovered_data = recovered["data"]

        new_row = pd.DataFrame({"benchmark": ["lbm"], "config": ["baseline"], "ipc": [2.0]})

        continued_data = pd.concat([recovered_data, new_row], ignore_index=True)
        assert len(continued_data) == len(recovered_data) + 1

    def test_configuration_versioning(self, portfolio_service: PortfolioService) -> None:
        """
        Test configuration version compatibility.
        """
        data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})

        # Save with legacy version metadata
        portfolio_service.save_portfolio(
            name="v1_format",
            data=data,
            plots=[],
            config={"version": "1.0", "format": "legacy"},
            plot_counter=0,
        )

        # Load and verify version is preserved
        loaded = portfolio_service.load_portfolio("v1_format")
        assert loaded["config"]["version"] == "1.0"

        # Create v2.0 portfolio format
        portfolio_service.save_portfolio(
            name="v2_format",
            data=data,
            plots=[],
            config={"version": "2.0", "format": "current"},
            plot_counter=0,
        )

        loaded_v2 = portfolio_service.load_portfolio("v2_format")
        assert loaded_v2["config"]["version"] == "2.0"

    def test_multiple_portfolio_management(
        self, sample_workspace_data: Dict[str, Any], portfolio_service: PortfolioService
    ) -> None:
        """
        Test managing multiple portfolios simultaneously.
        """
        data = sample_workspace_data["data"]

        # Create multiple portfolios
        portfolios = ["baseline_analysis", "transactional_analysis", "comparison"]

        for name in portfolios:
            portfolio_service.save_portfolio(
                name=name, data=data, plots=[], config={"analysis_type": name}, plot_counter=0
            )

        # List all portfolios
        available = portfolio_service.list_portfolios()
        assert len(available) >= len(portfolios)

        # Verify portfolios are in the list
        for name in portfolios:
            assert name in available

        # Load specific portfolio
        loaded = portfolio_service.load_portfolio("comparison")
        assert loaded["config"]["analysis_type"] == "comparison"

        # Delete portfolio
        portfolio_service.delete_portfolio("baseline_analysis")
        updated_list = portfolio_service.list_portfolios()
        assert "baseline_analysis" not in updated_list

    def test_facade_state_integration(self, mock_session_state, tmp_path: Path) -> None:
        """
        Test state management through ApplicationAPI (user-facing API).
        """
        # Mock st.session_state is active via mock_session_state fixture
        facade = ApplicationAPI()

        # Create sample data
        data = pd.DataFrame({"benchmark": ["mcf", "omnetpp"], "ipc": [1.2, 1.5]})

        # Save to CSV pool
        csv_path = tmp_path / "data.csv"
        data.to_csv(csv_path, index=False)
        facade.add_to_csv_pool(str(csv_path))

        # Verify can retrieve
        loaded = facade.load_csv_file(str(csv_path))
        assert loaded is not None
        pd.testing.assert_frame_equal(data, loaded)

        # Verify can load from pool
        pool_data = facade.load_csv_pool()
        assert len(pool_data) > 0

    def test_state_cleanup_on_error(self, portfolio_service: PortfolioService) -> None:
        """
        Test that state management handles errors gracefully.
        """
        # Test save with empty name
        with pytest.raises(ValueError):
            portfolio_service.save_portfolio(
                name="", data=pd.DataFrame(), plots=[], config={}, plot_counter=0
            )

        # Test load non-existent portfolio
        with pytest.raises(FileNotFoundError):
            portfolio_service.load_portfolio("nonexistent")

        # Verify portfolios directory is still valid
        available = portfolio_service.list_portfolios()
        assert isinstance(available, list)
