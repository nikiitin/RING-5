"""
Tests for RepositoryStateManager — currently at 0% coverage.

Covers all delegation methods: data, config, parser, plot, preview, and history
management. Since RepositoryStateManager delegates to SessionRepository, these
tests verify the delegation wiring plus any logic in the manager itself
(type enforcement in set_data, temp dir cleanup in clear_data).
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.core.models.history_models import OperationRecord
from src.core.state.repository_state_manager import RepositoryStateManager


@pytest.fixture
def manager() -> RepositoryStateManager:
    """Fresh RepositoryStateManager instance."""
    return RepositoryStateManager()


class TestInitializeAndClear:
    """Tests for initialization and clearing state."""

    def test_init_creates_session_repo(self, manager: RepositoryStateManager) -> None:
        assert manager._session_repo is not None

    def test_initialize_does_not_overwrite_existing(self, manager: RepositoryStateManager) -> None:
        """initialize_session only sets defaults when data is missing."""
        manager.set_data(pd.DataFrame({"a": [1]}))
        manager.initialize()
        # Data should still be present since it was already set
        assert manager.has_data() is True

    def test_initialize_sets_data_none_when_empty(self, manager: RepositoryStateManager) -> None:
        """When no data, initialize ensures data is set to None."""
        manager.initialize()
        assert manager.get_data() is None

    def test_clear_all(self, manager: RepositoryStateManager) -> None:
        manager.set_config({"x": 1})
        manager.set_csv_path("/some/path.csv")
        manager.clear_all()
        assert manager.get_csv_path() == ""
        assert manager.get_config() == {}


class TestDataManagement:
    """Tests for get/set data and processed data."""

    def test_get_data_default_none(self, manager: RepositoryStateManager) -> None:
        assert manager.get_data() is None

    def test_set_and_get_data(self, manager: RepositoryStateManager) -> None:
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        manager.set_data(df)
        result = manager.get_data()
        assert result is not None
        assert list(result.columns) == ["a", "b"]

    def test_set_data_none(self, manager: RepositoryStateManager) -> None:
        manager.set_data(pd.DataFrame({"a": [1]}))
        manager.set_data(None)
        assert manager.get_data() is None

    def test_set_data_type_enforcement_for_config_vars(
        self, manager: RepositoryStateManager
    ) -> None:
        """Configuration variables should be cast to str."""
        manager.set_parse_variables(
            [
                {"name": "benchmark", "type": "configuration"},
                {"name": "value", "type": "scalar"},
            ]
        )
        df = pd.DataFrame({"benchmark": [1, 2], "value": [3.0, 4.0]})
        manager.set_data(df)
        result = manager.get_data()
        assert result is not None
        assert result["benchmark"].dtype == object  # str type
        assert result["value"].dtype == float  # unchanged

    def test_set_data_with_on_change_callback(self, manager: RepositoryStateManager) -> None:
        callback = MagicMock()
        df = pd.DataFrame({"x": [1]})
        manager.set_data(df, on_change=callback)
        callback.assert_called_once()

    def test_has_data(self, manager: RepositoryStateManager) -> None:
        assert manager.has_data() is False
        manager.set_data(pd.DataFrame({"a": [1]}))
        assert manager.has_data() is True

    def test_get_processed_data_default_none(self, manager: RepositoryStateManager) -> None:
        assert manager.get_processed_data() is None

    def test_set_and_get_processed_data(self, manager: RepositoryStateManager) -> None:
        df = pd.DataFrame({"x": [10, 20]})
        manager.set_processed_data(df)
        result = manager.get_processed_data()
        assert result is not None
        assert len(result) == 2


class TestClearData:
    """Tests for clear_data with temp dir cleanup."""

    def test_clear_data_resets_state(self, manager: RepositoryStateManager) -> None:
        manager.set_data(pd.DataFrame({"a": [1]}))
        manager.set_csv_path("/test.csv")
        manager.clear_data()
        assert manager.get_data() is None
        assert manager.get_csv_path() == ""

    def test_clear_data_removes_temp_dir(self, manager: RepositoryStateManager) -> None:
        """Temp dir should be removed if it exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager.set_temp_dir(tmpdir)
            # Create a file inside to verify cleanup
            (Path(tmpdir) / "test.txt").write_text("test")
            manager.clear_data()
            assert not Path(tmpdir).exists()

    def test_clear_data_nonexistent_temp_dir(self, manager: RepositoryStateManager) -> None:
        """Clearing with non-existent temp dir should not crash."""
        manager.set_temp_dir("/nonexistent/path/12345")
        manager.clear_data()  # Should not raise

    def test_clear_data_clears_plots(self, manager: RepositoryStateManager) -> None:
        plot = MagicMock()
        manager.add_plot(plot)
        manager.clear_data()
        assert manager.get_plots() == []
        assert manager.get_plot_counter() == 0


class TestConfigManagement:
    """Tests for config get/set/update."""

    def test_get_config_default_empty(self, manager: RepositoryStateManager) -> None:
        config = manager.get_config()
        assert isinstance(config, dict)

    def test_set_and_get_config(self, manager: RepositoryStateManager) -> None:
        manager.set_config({"theme": "dark", "dpi": 300})
        config = manager.get_config()
        assert config["theme"] == "dark"
        assert config["dpi"] == 300

    def test_update_config(self, manager: RepositoryStateManager) -> None:
        manager.set_config({"a": 1})
        manager.update_config("b", 2)
        config = manager.get_config()
        assert config["a"] == 1
        assert config["b"] == 2

    def test_temp_dir_management(self, manager: RepositoryStateManager) -> None:
        # Default may be empty string
        manager.set_temp_dir("/tmp/ring5")
        assert manager.get_temp_dir() == "/tmp/ring5"

    def test_csv_path_management(self, manager: RepositoryStateManager) -> None:
        manager.set_csv_path("/data/output.csv")
        assert manager.get_csv_path() == "/data/output.csv"

    def test_csv_pool_management(self, manager: RepositoryStateManager) -> None:
        assert manager.get_csv_pool() == []
        pool = [{"path": "/a.csv", "label": "A"}]
        manager.set_csv_pool(pool)
        assert manager.get_csv_pool() == pool

    def test_saved_configs_management(self, manager: RepositoryStateManager) -> None:
        assert manager.get_saved_configs() == []
        configs = [{"name": "config1", "data": {}}]
        manager.set_saved_configs(configs)
        assert manager.get_saved_configs() == configs


class TestParserManagement:
    """Tests for parser-related state."""

    def test_is_using_parser_default(self, manager: RepositoryStateManager) -> None:
        assert manager.is_using_parser() is False

    def test_set_use_parser(self, manager: RepositoryStateManager) -> None:
        manager.set_use_parser(True)
        assert manager.is_using_parser() is True

    def test_parse_variables(self, manager: RepositoryStateManager) -> None:
        # Default includes simTicks, benchmark_name, config_description
        defaults = manager.get_parse_variables()
        assert len(defaults) >= 3
        variables = [{"name": "cpu.ipc", "type": "scalar"}]
        manager.set_parse_variables(variables)
        result = manager.get_parse_variables()
        assert len(result) == 1
        assert result[0]["name"] == "cpu.ipc"

    def test_stats_path(self, manager: RepositoryStateManager) -> None:
        # Default is "/path/to/gem5/stats"
        manager.set_stats_path("/data/stats.txt")
        assert manager.get_stats_path() == "/data/stats.txt"

    def test_stats_pattern(self, manager: RepositoryStateManager) -> None:
        # Default is "stats.txt"
        assert manager.get_stats_pattern() == "stats.txt"
        manager.set_stats_pattern("stats*.txt")
        assert manager.get_stats_pattern() == "stats*.txt"

    def test_scanned_variables(self, manager: RepositoryStateManager) -> None:
        assert manager.get_scanned_variables() == []
        scanned = [{"name": "cpu.ipc", "entries": ["0", "1"]}]
        manager.set_scanned_variables(scanned)
        assert manager.get_scanned_variables() == scanned

    def test_parser_strategy(self, manager: RepositoryStateManager) -> None:
        # Default is "simple"
        assert manager.get_parser_strategy() == "simple"
        manager.set_parser_strategy("gem5")
        assert manager.get_parser_strategy() == "gem5"


class TestPlotManagement:
    """Tests for plot-related state."""

    def test_get_plots_default_empty(self, manager: RepositoryStateManager) -> None:
        assert manager.get_plots() == []

    def test_add_and_get_plots(self, manager: RepositoryStateManager) -> None:
        plot1 = MagicMock()
        plot2 = MagicMock()
        manager.add_plot(plot1)
        manager.add_plot(plot2)
        plots = manager.get_plots()
        assert len(plots) == 2

    def test_set_plots(self, manager: RepositoryStateManager) -> None:
        plots = [MagicMock(), MagicMock()]
        manager.set_plots(plots)
        assert len(manager.get_plots()) == 2

    def test_plot_counter(self, manager: RepositoryStateManager) -> None:
        assert manager.get_plot_counter() == 0
        manager.set_plot_counter(5)
        assert manager.get_plot_counter() == 5

    def test_start_next_plot_id(self, manager: RepositoryStateManager) -> None:
        # increment_plot_counter returns current THEN increments
        initial = manager.get_plot_counter()
        next_id = manager.start_next_plot_id()
        assert next_id == initial
        next_id2 = manager.start_next_plot_id()
        assert next_id2 == initial + 1
        assert manager.get_plot_counter() == initial + 2

    def test_current_plot_id(self, manager: RepositoryStateManager) -> None:
        assert manager.get_current_plot_id() is None
        manager.set_current_plot_id(3)
        assert manager.get_current_plot_id() == 3
        manager.set_current_plot_id(None)
        assert manager.get_current_plot_id() is None


class TestPreviewManagement:
    """Tests for preview state."""

    def test_no_preview_by_default(self, manager: RepositoryStateManager) -> None:
        assert manager.has_preview("normalize") is False
        assert manager.get_preview("normalize") is None

    def test_set_and_get_preview(self, manager: RepositoryStateManager) -> None:
        df = pd.DataFrame({"x": [1, 2, 3]})
        manager.set_preview("normalize", df)
        assert manager.has_preview("normalize") is True
        result = manager.get_preview("normalize")
        assert result is not None
        assert len(result) == 3

    def test_clear_preview(self, manager: RepositoryStateManager) -> None:
        manager.set_preview("filter", pd.DataFrame({"x": [1]}))
        manager.clear_preview("filter")
        assert manager.has_preview("filter") is False


class TestHistoryManagement:
    """Tests for operation history."""

    def _make_record(self, operation: str = "test_op") -> OperationRecord:
        return OperationRecord(
            source_columns=["a"],
            dest_columns=["b"],
            operation=operation,
            timestamp="2024-01-01T00:00:00",
        )

    def test_manager_history_default_empty(self, manager: RepositoryStateManager) -> None:
        assert manager.get_manager_history() == []

    def test_add_and_get_manager_history(self, manager: RepositoryStateManager) -> None:
        record = self._make_record()
        manager.add_manager_history_record(record)
        history = manager.get_manager_history()
        assert len(history) == 1
        assert history[0]["operation"] == "test_op"

    def test_remove_manager_history_record(self, manager: RepositoryStateManager) -> None:
        record = self._make_record()
        manager.add_manager_history_record(record)
        manager.remove_manager_history_record(record)
        assert manager.get_manager_history() == []

    def test_portfolio_history(self, manager: RepositoryStateManager) -> None:
        record = self._make_record("portfolio_op")
        manager.add_portfolio_history_record(record)
        assert len(manager.get_portfolio_history()) == 1
        manager.remove_portfolio_history_record(record)
        assert manager.get_portfolio_history() == []


class TestRestoreSession:
    """Tests for portfolio restore."""

    def test_restore_session_from_portfolio(self, manager: RepositoryStateManager) -> None:
        portfolio_data = {
            "parse_variables": [{"name": "ipc", "type": "scalar"}],
            "stats_path": "/data/stats.txt",
            "stats_pattern": "stats*.txt",
            "csv_path": "/output.csv",
            "use_parser": True,
            "scanned_variables": [{"name": "cpu.cycles"}],
            "plots": [],
            "plot_counter": 3,
            "config": {"theme": "dark"},
            "manager_history": [],
            "portfolio_history": [],
        }
        manager.restore_session(portfolio_data)

        assert manager.get_stats_path() == "/data/stats.txt"
        assert manager.get_stats_pattern() == "stats*.txt"
        assert manager.get_csv_path() == "/output.csv"
        assert manager.is_using_parser() is True
        assert len(manager.get_parse_variables()) == 1
        assert manager.get_plot_counter() == 3
