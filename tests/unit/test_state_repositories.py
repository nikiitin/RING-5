"""Unit tests for state repository layer.

Tests all 7 state repositories with comprehensive coverage:
- DataRepository
- ConfigRepository
- PlotRepository
- HistoryRepository
- ParserStateRepository
- PreviewRepository
- SessionRepository

Each repository is tested in isolation with no mocking required
(except SessionRepository.restore_from_portfolio which needs BasePlot).
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.history_models import OperationRecord
from src.core.state.repositories.config_repository import ConfigRepository
from src.core.state.repositories.data_repository import DataRepository
from src.core.state.repositories.history_repository import HistoryRepository
from src.core.state.repositories.parser_state_repository import ParserStateRepository
from src.core.state.repositories.plot_repository import PlotRepository
from src.core.state.repositories.preview_repository import PreviewRepository
from src.core.state.repositories.session_repository import SessionRepository

# ===================================================================
# DataRepository
# ===================================================================


class TestDataRepository:
    """Tests for DataRepository — primary + processed data management."""

    @pytest.fixture
    def repo(self) -> DataRepository:
        return DataRepository()

    @pytest.fixture
    def df(self) -> pd.DataFrame:
        return pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

    def test_initial_state_is_none(self, repo: DataRepository) -> None:
        assert repo.get_data() is None
        assert repo.get_processed_data() is None
        assert repo.has_data() is False

    def test_set_and_get_data(self, repo: DataRepository, df: pd.DataFrame) -> None:
        repo.set_data(df)
        result = repo.get_data()
        assert result is not None
        pd.testing.assert_frame_equal(result, df)

    def test_has_data_true_when_non_empty(self, repo: DataRepository, df: pd.DataFrame) -> None:
        repo.set_data(df)
        assert repo.has_data() is True

    def test_has_data_false_for_empty_df(self, repo: DataRepository) -> None:
        repo.set_data(pd.DataFrame())
        assert repo.has_data() is False

    def test_set_data_none_clears(self, repo: DataRepository, df: pd.DataFrame) -> None:
        repo.set_data(df)
        repo.set_data(None)
        assert repo.get_data() is None
        assert repo.has_data() is False

    def test_on_change_callback_fires(self, repo: DataRepository, df: pd.DataFrame) -> None:
        callback = MagicMock()
        repo.set_data(df, on_change=callback)
        callback.assert_called_once()

    def test_on_change_not_called_when_none(self, repo: DataRepository, df: pd.DataFrame) -> None:
        repo.set_data(df, on_change=None)
        # No exception raised

    def test_processed_data_lifecycle(self, repo: DataRepository, df: pd.DataFrame) -> None:
        processed = df.copy()
        processed["c"] = [7, 8, 9]
        repo.set_processed_data(processed)

        result = repo.get_processed_data()
        assert result is not None
        assert "c" in result.columns

    def test_clear_data_clears_both(self, repo: DataRepository, df: pd.DataFrame) -> None:
        repo.set_data(df)
        repo.set_processed_data(df.copy())
        repo.clear_data()

        assert repo.get_data() is None
        assert repo.get_processed_data() is None


# ===================================================================
# ConfigRepository
# ===================================================================


class TestConfigRepository:
    """Tests for ConfigRepository — configuration state management."""

    @pytest.fixture
    def repo(self) -> ConfigRepository:
        return ConfigRepository()

    def test_initial_config_is_empty_dict(self, repo: ConfigRepository) -> None:
        assert repo.get_config() == {}

    def test_set_and_get_config(self, repo: ConfigRepository) -> None:
        config = {"theme": "dark", "font_size": 14}
        repo.set_config(config)
        assert repo.get_config() == config

    def test_update_config_key(self, repo: ConfigRepository) -> None:
        repo.set_config({"a": 1})
        repo.update_config("b", 2)
        assert repo.get_config() == {"a": 1, "b": 2}

    def test_update_config_overwrites_existing(self, repo: ConfigRepository) -> None:
        repo.set_config({"a": 1})
        repo.update_config("a", 99)
        assert repo.get_config_value("a") == 99

    def test_get_config_value_default(self, repo: ConfigRepository) -> None:
        assert repo.get_config_value("missing", "fallback") == "fallback"

    def test_get_config_value_none_default(self, repo: ConfigRepository) -> None:
        assert repo.get_config_value("missing") is None

    def test_clear_config(self, repo: ConfigRepository) -> None:
        repo.set_config({"a": 1, "b": 2})
        repo.clear_config()
        assert repo.get_config() == {}

    def test_temp_dir(self, repo: ConfigRepository) -> None:
        assert repo.get_temp_dir() is None
        repo.set_temp_dir("/tmp/test")
        assert repo.get_temp_dir() == "/tmp/test"

    def test_csv_path(self, repo: ConfigRepository) -> None:
        assert repo.get_csv_path() is None
        repo.set_csv_path("/data/out.csv")
        assert repo.get_csv_path() == "/data/out.csv"

    def test_csv_pool(self, repo: ConfigRepository) -> None:
        assert repo.get_csv_pool() == []
        pool = [{"name": "a.csv", "path": "/a.csv"}]
        repo.set_csv_pool(pool)
        assert repo.get_csv_pool() == pool

    def test_saved_configs(self, repo: ConfigRepository) -> None:
        assert repo.get_saved_configs() == []
        configs = [{"name": "cfg1", "shapers": []}]
        repo.set_saved_configs(configs)
        assert repo.get_saved_configs() == configs


# ===================================================================
# PlotRepository
# ===================================================================


class TestPlotRepository:
    """Tests for PlotRepository — plot lifecycle management."""

    @pytest.fixture
    def repo(self) -> PlotRepository:
        return PlotRepository()

    @staticmethod
    def _make_plot(plot_id: int, plot_type: str = "bar") -> MagicMock:
        plot = MagicMock()
        plot.plot_id = plot_id
        plot.plot_type = plot_type
        return plot

    def test_initial_state(self, repo: PlotRepository) -> None:
        assert repo.get_plots() == []
        assert repo.get_plot_counter() == 0
        assert repo.get_current_plot_id() is None

    def test_add_plot(self, repo: PlotRepository) -> None:
        plot = self._make_plot(1)
        repo.add_plot(plot)
        assert len(repo.get_plots()) == 1
        assert repo.get_plots()[0].plot_id == 1

    def test_set_plots_replaces(self, repo: PlotRepository) -> None:
        repo.add_plot(self._make_plot(1))
        new_plots = [self._make_plot(2), self._make_plot(3)]
        repo.set_plots(new_plots)
        assert len(repo.get_plots()) == 2

    def test_remove_plot_found(self, repo: PlotRepository) -> None:
        repo.add_plot(self._make_plot(1))
        repo.add_plot(self._make_plot(2))
        assert repo.remove_plot(1) is True
        assert len(repo.get_plots()) == 1
        assert repo.get_plots()[0].plot_id == 2

    def test_remove_plot_not_found(self, repo: PlotRepository) -> None:
        repo.add_plot(self._make_plot(1))
        assert repo.remove_plot(99) is False
        assert len(repo.get_plots()) == 1

    def test_clear_plots(self, repo: PlotRepository) -> None:
        repo.add_plot(self._make_plot(1))
        repo.add_plot(self._make_plot(2))
        repo.clear_plots()
        assert repo.get_plots() == []

    def test_plot_counter(self, repo: PlotRepository) -> None:
        repo.set_plot_counter(5)
        assert repo.get_plot_counter() == 5

    def test_increment_plot_counter(self, repo: PlotRepository) -> None:
        assert repo.increment_plot_counter() == 0
        assert repo.increment_plot_counter() == 1
        assert repo.get_plot_counter() == 2

    def test_current_plot_id(self, repo: PlotRepository) -> None:
        repo.set_current_plot_id(42)
        assert repo.get_current_plot_id() == 42
        repo.set_current_plot_id(None)
        assert repo.get_current_plot_id() is None


# ===================================================================
# HistoryRepository
# ===================================================================


class TestHistoryRepository:
    """Tests for HistoryRepository — operation record management."""

    @pytest.fixture
    def repo(self) -> HistoryRepository:
        return HistoryRepository()

    @staticmethod
    def _record(op: str = "test_op") -> OperationRecord:
        return OperationRecord(
            source_columns=["col_a"],
            dest_columns=["col_b"],
            operation=op,
            timestamp="2026-02-11T00:00:00",
        )

    def test_initial_state(self, repo: HistoryRepository) -> None:
        assert repo.get_manager_history() == []
        assert repo.get_portfolio_history() == []

    def test_add_manager_record(self, repo: HistoryRepository) -> None:
        repo.add_manager_record(self._record("op1"))
        assert len(repo.get_manager_history()) == 1
        assert repo.get_manager_history()[0]["operation"] == "op1"

    def test_manager_fifo_cap_at_20(self, repo: HistoryRepository) -> None:
        for i in range(25):
            repo.add_manager_record(self._record(f"op_{i}"))
        history = repo.get_manager_history()
        assert len(history) == 20
        # Oldest evicted → first record should be op_5
        assert history[0]["operation"] == "op_5"
        assert history[-1]["operation"] == "op_24"

    def test_set_manager_history_bulk(self, repo: HistoryRepository) -> None:
        records = [self._record(f"op_{i}") for i in range(3)]
        repo.set_manager_history(records)
        assert len(repo.get_manager_history()) == 3

    def test_clear_manager_history(self, repo: HistoryRepository) -> None:
        repo.add_manager_record(self._record())
        repo.clear_manager_history()
        assert repo.get_manager_history() == []

    def test_portfolio_history_no_cap(self, repo: HistoryRepository) -> None:
        for i in range(50):
            repo.add_portfolio_record(self._record(f"port_{i}"))
        assert len(repo.get_portfolio_history()) == 50

    def test_set_portfolio_history_bulk(self, repo: HistoryRepository) -> None:
        records = [self._record(f"p_{i}") for i in range(5)]
        repo.set_portfolio_history(records)
        assert len(repo.get_portfolio_history()) == 5

    def test_clear_portfolio_history(self, repo: HistoryRepository) -> None:
        repo.add_portfolio_record(self._record())
        repo.clear_portfolio_history()
        assert repo.get_portfolio_history() == []

    def test_remove_manager_record_found(self, repo: HistoryRepository) -> None:
        record = self._record("rm_me")
        repo.add_manager_record(record)
        repo.remove_manager_record(record)
        assert len(repo.get_manager_history()) == 0

    def test_remove_manager_record_not_found(self, repo: HistoryRepository) -> None:
        repo.add_manager_record(self._record("keep"))
        repo.remove_manager_record(self._record("missing"))
        assert len(repo.get_manager_history()) == 1

    def test_remove_portfolio_record_found(self, repo: HistoryRepository) -> None:
        record = self._record("rm_port")
        repo.add_portfolio_record(record)
        repo.remove_portfolio_record(record)
        assert len(repo.get_portfolio_history()) == 0

    def test_remove_portfolio_record_not_found(self, repo: HistoryRepository) -> None:
        repo.add_portfolio_record(self._record("keep"))
        repo.remove_portfolio_record(self._record("missing"))
        assert len(repo.get_portfolio_history()) == 1

    def test_clear_all(self, repo: HistoryRepository) -> None:
        repo.add_manager_record(self._record())
        repo.add_portfolio_record(self._record())
        repo.clear_all()
        assert repo.get_manager_history() == []
        assert repo.get_portfolio_history() == []

    def test_get_returns_copy(self, repo: HistoryRepository) -> None:
        """Verify get_*_history returns a copy, not a reference."""
        repo.add_manager_record(self._record())
        h1 = repo.get_manager_history()
        h1.clear()
        assert len(repo.get_manager_history()) == 1


# ===================================================================
# ParserStateRepository
# ===================================================================


class TestParserStateRepository:
    """Tests for ParserStateRepository — gem5 parser configuration."""

    @pytest.fixture
    def repo(self) -> ParserStateRepository:
        return ParserStateRepository()

    def test_default_parse_variables(self, repo: ParserStateRepository) -> None:
        defaults = repo.get_parse_variables()
        assert len(defaults) == 3
        names = [v["name"] for v in defaults]
        assert "simTicks" in names
        assert "benchmark_name" in names
        assert "config_description" in names

    def test_default_parse_variables_have_ids(self, repo: ParserStateRepository) -> None:
        for var in repo.get_parse_variables():
            assert "_id" in var
            assert isinstance(var["_id"], str)

    def test_set_parse_variables(self, repo: ParserStateRepository) -> None:
        new_vars = [{"name": "ipc", "type": "scalar"}]
        repo.set_parse_variables(new_vars)
        result = repo.get_parse_variables()
        assert len(result) == 1
        assert result[0]["name"] == "ipc"
        # Should auto-assign _id
        assert "_id" in result[0]

    def test_add_parse_variable(self, repo: ParserStateRepository) -> None:
        initial_count = len(repo.get_parse_variables())
        repo.add_parse_variable({"name": "new_var", "type": "vector"})
        assert len(repo.get_parse_variables()) == initial_count + 1

    def test_remove_parse_variable_found(self, repo: ParserStateRepository) -> None:
        var_id = repo.get_parse_variables()[0]["_id"]
        assert repo.remove_parse_variable(var_id) is True
        assert len(repo.get_parse_variables()) == 2

    def test_remove_parse_variable_not_found(self, repo: ParserStateRepository) -> None:
        assert repo.remove_parse_variable("nonexistent-id") is False

    def test_stats_path_default(self, repo: ParserStateRepository) -> None:
        assert repo.get_stats_path() == "/path/to/gem5/stats"

    def test_stats_path_set(self, repo: ParserStateRepository) -> None:
        repo.set_stats_path("/new/path")
        assert repo.get_stats_path() == "/new/path"

    def test_stats_pattern_default(self, repo: ParserStateRepository) -> None:
        assert repo.get_stats_pattern() == "stats.txt"

    def test_stats_pattern_set(self, repo: ParserStateRepository) -> None:
        repo.set_stats_pattern("*.txt")
        assert repo.get_stats_pattern() == "*.txt"

    def test_scanned_variables(self, repo: ParserStateRepository) -> None:
        assert repo.get_scanned_variables() == []
        vars_data = [{"name": "ipc", "type": "scalar"}]
        repo.set_scanned_variables(vars_data)
        assert repo.get_scanned_variables() == vars_data

    def test_using_parser_default_false(self, repo: ParserStateRepository) -> None:
        assert repo.is_using_parser() is False

    def test_set_using_parser(self, repo: ParserStateRepository) -> None:
        repo.set_using_parser(True)
        assert repo.is_using_parser() is True

    def test_parser_strategy_default(self, repo: ParserStateRepository) -> None:
        assert repo.get_parser_strategy() == "simple"

    def test_set_parser_strategy(self, repo: ParserStateRepository) -> None:
        repo.set_parser_strategy("config_aware")
        assert repo.get_parser_strategy() == "config_aware"

    def test_set_parser_strategy_normalizes(self, repo: ParserStateRepository) -> None:
        repo.set_parser_strategy("CONFIG_AWARE")
        assert repo.get_parser_strategy() == "config_aware"

    def test_clear_parser_state(self, repo: ParserStateRepository) -> None:
        repo.set_scanned_variables([{"name": "x"}])
        repo.set_using_parser(True)
        repo.clear_parser_state()
        assert repo.get_scanned_variables() == []
        assert repo.is_using_parser() is False
        # parse_variables should NOT be cleared
        assert len(repo.get_parse_variables()) == 3


# ===================================================================
# PreviewRepository
# ===================================================================


class TestPreviewRepository:
    """Tests for PreviewRepository — temporary preview management."""

    @pytest.fixture
    def repo(self) -> PreviewRepository:
        return PreviewRepository()

    @pytest.fixture
    def preview_df(self) -> pd.DataFrame:
        return pd.DataFrame({"result": [1, 2, 3]})

    def test_initial_state(self, repo: PreviewRepository) -> None:
        assert repo.list_active_previews() == []
        assert repo.has_preview("any") is False

    def test_set_and_get_preview(self, repo: PreviewRepository, preview_df: pd.DataFrame) -> None:
        repo.set_preview("normalize", preview_df)
        result = repo.get_preview("normalize")
        assert result is not None
        pd.testing.assert_frame_equal(result, preview_df)

    def test_has_preview(self, repo: PreviewRepository, preview_df: pd.DataFrame) -> None:
        repo.set_preview("op1", preview_df)
        assert repo.has_preview("op1") is True
        assert repo.has_preview("op2") is False

    def test_set_preview_empty_name_raises(
        self, repo: PreviewRepository, preview_df: pd.DataFrame
    ) -> None:
        with pytest.raises(ValueError, match="empty"):
            repo.set_preview("", preview_df)

    def test_set_preview_none_data_raises(self, repo: PreviewRepository) -> None:
        with pytest.raises(ValueError, match="None"):
            repo.set_preview("op", None)  # type: ignore[arg-type]

    def test_get_preview_empty_name(self, repo: PreviewRepository) -> None:
        assert repo.get_preview("") is None

    def test_clear_preview(self, repo: PreviewRepository, preview_df: pd.DataFrame) -> None:
        repo.set_preview("op1", preview_df)
        repo.clear_preview("op1")
        assert repo.has_preview("op1") is False

    def test_clear_preview_not_found(self, repo: PreviewRepository) -> None:
        repo.clear_preview("nonexistent")  # No error

    def test_clear_all_previews(self, repo: PreviewRepository, preview_df: pd.DataFrame) -> None:
        repo.set_preview("op1", preview_df)
        repo.set_preview("op2", preview_df)
        count = repo.clear_all_previews()
        assert count == 2
        assert repo.list_active_previews() == []

    def test_clear_all_previews_empty(self, repo: PreviewRepository) -> None:
        count = repo.clear_all_previews()
        assert count == 0

    def test_list_active_previews(self, repo: PreviewRepository, preview_df: pd.DataFrame) -> None:
        repo.set_preview("op_a", preview_df)
        repo.set_preview("op_b", preview_df)
        active = repo.list_active_previews()
        assert set(active) == {"op_a", "op_b"}


# ===================================================================
# SessionRepository
# ===================================================================


class TestSessionRepository:
    """Tests for SessionRepository — session lifecycle management."""

    @pytest.fixture
    def repo(self) -> SessionRepository:
        return SessionRepository()

    def test_initialization_creates_sub_repos(self, repo: SessionRepository) -> None:
        assert isinstance(repo.data_repo, DataRepository)
        assert isinstance(repo.plot_repo, PlotRepository)
        assert isinstance(repo.parser_repo, ParserStateRepository)
        assert isinstance(repo.config_repo, ConfigRepository)
        assert isinstance(repo.preview_repo, PreviewRepository)
        assert isinstance(repo.history_repo, HistoryRepository)

    def test_initialize_session(self, repo: SessionRepository) -> None:
        repo.initialize_session()
        # Should not raise; data should remain None
        assert repo.data_repo.get_data() is None

    def test_clear_widget_state_is_noop(self, repo: SessionRepository) -> None:
        repo.clear_widget_state()  # Should not raise

    def test_clear_all(self, repo: SessionRepository) -> None:
        # Populate state
        repo.data_repo.set_data(pd.DataFrame({"a": [1]}))
        repo.config_repo.set_config({"key": "val"})
        repo.plot_repo.set_plot_counter(5)

        record = OperationRecord(
            source_columns=["a"],
            dest_columns=["b"],
            operation="test",
            timestamp="2026-01-01",
        )
        repo.history_repo.add_manager_record(record)

        # Clear everything
        repo.clear_all()

        assert repo.data_repo.get_data() is None
        assert repo.plot_repo.get_plots() == []
        assert repo.plot_repo.get_plot_counter() == 0
        assert repo.plot_repo.get_current_plot_id() is None
        assert repo.config_repo.get_config() == {}
        assert repo.history_repo.get_manager_history() == []
        assert repo.history_repo.get_portfolio_history() == []

    def test_restore_from_portfolio_parser_state(self, repo: SessionRepository) -> None:
        """Test restoring parser-related state from portfolio data."""
        portfolio: dict = {  # type: ignore[type-arg]
            "parse_variables": [{"name": "ipc", "type": "scalar", "_id": "id1"}],
            "stats_path": "/restored/path",
            "stats_pattern": "stats_custom.txt",
            "scanned_variables": [{"name": "x", "type": "vector"}],
            "use_parser": True,
            "config": {"restored": True},
            "csv_path": "/restored.csv",
            "plots": [],
            "plot_counter": 3,
        }

        with patch(
            "src.web.pages.ui.plotting.base_plot.BasePlot.from_dict",
            return_value=None,
        ):
            repo.restore_from_portfolio(portfolio)  # type: ignore[arg-type]

        assert repo.parser_repo.get_stats_path() == "/restored/path"
        assert repo.parser_repo.get_stats_pattern() == "stats_custom.txt"
        assert repo.parser_repo.is_using_parser() is True
        assert repo.config_repo.get_csv_path() == "/restored.csv"
        assert repo.config_repo.get_config() == {"restored": True}

    def test_restore_from_portfolio_with_data_csv(self, repo: SessionRepository) -> None:
        """Test restoring data from CSV string in portfolio."""
        df = pd.DataFrame({"col": [10, 20, 30]})
        csv_str = df.to_csv(index=False)

        portfolio: dict = {  # type: ignore[type-arg]
            "data_csv": csv_str,
            "plots": [],
        }

        with patch(
            "src.web.pages.ui.plotting.base_plot.BasePlot.from_dict",
            return_value=None,
        ):
            repo.restore_from_portfolio(portfolio)  # type: ignore[arg-type]

        restored = repo.data_repo.get_data()
        assert restored is not None
        assert len(restored) == 3
        assert list(restored.columns) == ["col"]

    def test_restore_from_portfolio_with_history(self, repo: SessionRepository) -> None:
        """Test restoring history from portfolio data."""
        record = OperationRecord(
            source_columns=["a"],
            dest_columns=["b"],
            operation="mix",
            timestamp="2026-01-01",
        )
        portfolio: dict = {  # type: ignore[type-arg]
            "manager_history": [record],
            "portfolio_history": [record, record],
            "plots": [],
        }

        with patch(
            "src.web.pages.ui.plotting.base_plot.BasePlot.from_dict",
            return_value=None,
        ):
            repo.restore_from_portfolio(portfolio)  # type: ignore[arg-type]

        assert len(repo.history_repo.get_manager_history()) == 1
        assert len(repo.history_repo.get_portfolio_history()) == 2

    def test_restore_from_portfolio_with_plots(self, repo: SessionRepository) -> None:
        """Test restoring plots from portfolio data."""
        mock_plot = MagicMock()
        mock_plot.plot_id = 1

        portfolio: dict = {  # type: ignore[type-arg]
            "plots": [{"type": "bar", "id": 1}],
            "plot_counter": 5,
        }

        with patch(
            "src.web.pages.ui.plotting.base_plot.BasePlot.from_dict",
            return_value=mock_plot,
        ):
            repo.restore_from_portfolio(portfolio)  # type: ignore[arg-type]

        assert len(repo.plot_repo.get_plots()) == 1
        assert repo.plot_repo.get_plot_counter() == 5
