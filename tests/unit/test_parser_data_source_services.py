"""Tests for parser, pattern-index, work-pool, and data-source services."""

import configparser
import os
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

# Scanned-variable serialization


class TestScannedVariableToDict:
    """Tests for optional scanned-variable fields."""

    def test_to_dict_with_all_optional_fields(self) -> None:
        from src.parsing.gem5.models import Gem5ScannedVariable

        sv = Gem5ScannedVariable(
            name="cpu.ipc",
            type="scalar",
            entries=["0", "1"],
            minimum=0.5,
            maximum=10.0,
            pattern_indices=["cpu0", "cpu1"],
        )
        d = sv.to_dict()
        assert d["name"] == "cpu.ipc"
        assert d["type"] == "scalar"
        assert d["entries"] == ["0", "1"]
        assert d.get("minimum") == 0.5
        assert d.get("maximum") == 10.0
        assert d.get("pattern_indices") == ["cpu0", "cpu1"]

    def test_to_dict_without_optional_fields(self) -> None:
        from src.core.models.parsing_models import ScannedVariable

        sv = ScannedVariable(name="simTicks", type="scalar")
        d = sv.to_dict()
        assert d["name"] == "simTicks"
        assert "minimum" not in d
        assert "maximum" not in d
        assert "pattern_indices" not in d

    def test_to_dict_partial_optional(self) -> None:
        from src.parsing.gem5.models import Gem5ScannedVariable

        sv = Gem5ScannedVariable(name="dist.var", type="distribution", minimum=0.0)
        d = sv.to_dict()
        assert d.get("minimum") == 0.0
        assert "maximum" not in d
        assert "pattern_indices" not in d

    def test_from_dict_roundtrip(self) -> None:
        from src.parsing.gem5.models import Gem5ScannedVariable

        sv = Gem5ScannedVariable(
            name="x", type="vector", entries=["a"], minimum=1.0, maximum=2.0, pattern_indices=["p"]
        )
        d = sv.to_dict()
        sv2 = Gem5ScannedVariable.from_dict(d)
        assert sv2.name == sv.name
        assert sv2.minimum == sv.minimum
        assert sv2.maximum == sv.maximum
        assert sv2.pattern_indices == sv.pattern_indices


# Strategy creation


class TestStrategyFactory:
    """Tests for strategy selection and invalid names."""

    def test_create_simple(self) -> None:
        from src.parsing.gem5.impl.strategies.factory import StrategyFactory

        strategy = StrategyFactory.create("simple")
        assert strategy is not None
        assert strategy.__class__.__name__ == "SimpleStatsStrategy"

    def test_create_config_aware(self) -> None:
        from src.parsing.gem5.impl.strategies.factory import StrategyFactory

        strategy = StrategyFactory.create("config_aware")
        assert strategy is not None
        assert strategy.__class__.__name__ == "ConfigAwareStrategy"

    def test_create_unknown_raises(self) -> None:
        from src.parsing.gem5.impl.strategies.factory import StrategyFactory

        with pytest.raises(ValueError, match="Unknown strategy type"):
            StrategyFactory.create("nonexistent")


# Configuration-aware parsing


class TestConfigAwareStrategy:
    """Tests for configuration discovery and parsing failures."""

    def test_post_process_no_sim_path(self) -> None:
        """Worker results without internal provenance fail visibly."""
        from src.parsing.gem5.impl.strategies.config_aware import (
            ConfigAwareStrategy,
        )

        strategy = ConfigAwareStrategy()
        results = [{"some_data": 123}]
        with pytest.raises(RuntimeError, match="missing simulation provenance"):
            strategy.post_process(results)

    def test_post_process_config_found(self, tmp_path: Path) -> None:
        """Result with sim_path pointing to existing config.ini."""
        from src.parsing.gem5.impl.strategies.config_aware import (
            ConfigAwareStrategy,
        )
        from src.parsing.gem5.impl.strategies.file_parser_strategy import (
            INTERNAL_SIM_PATH_KEY,
        )

        # Create a mock config.ini
        config_path = tmp_path / "config.ini"
        config_path.write_text("[system]\ncpu_type = O3CPU\nnum_cpus = 4\n")

        stats_path = tmp_path / "stats.txt"
        stats_path.write_text("dummy")

        strategy = ConfigAwareStrategy()
        results = [{INTERNAL_SIM_PATH_KEY: str(stats_path), "data": "abc"}]
        out = strategy.post_process(results)

        assert len(out) == 1
        assert out[0]["sim_path"] == str(stats_path)
        assert '"cpu_type":"O3CPU"' in out[0]["config_json"]

    def test_post_process_config_not_found(self, tmp_path: Path) -> None:
        """Result with sim_path but no config.ini in the directory."""
        from src.parsing.gem5.impl.strategies.config_aware import (
            ConfigAwareStrategy,
        )
        from src.parsing.gem5.impl.strategies.file_parser_strategy import (
            INTERNAL_SIM_PATH_KEY,
        )

        stats_path = tmp_path / "stats.txt"
        stats_path.write_text("dummy")

        strategy = ConfigAwareStrategy()
        results = [{INTERNAL_SIM_PATH_KEY: str(stats_path), "data": "abc"}]
        with pytest.raises(FileNotFoundError, match="config.ini not found"):
            strategy.post_process(results)

    def test_parse_config_error_handling(self, tmp_path: Path) -> None:
        """_parse_config handles malformed config gracefully."""
        from src.parsing.gem5.impl.strategies.config_aware import (
            ConfigAwareStrategy,
        )

        # Create a config that will cause parser issues
        config_path = tmp_path / "config.ini"
        config_path.write_text("[section1]\nkey1 = value1\n")

        strategy = ConfigAwareStrategy()
        result = strategy._parse_config(config_path)
        assert isinstance(result, dict)
        assert "section1" in result

    def test_parse_config_unreadable(self, tmp_path: Path) -> None:
        """An empty configuration is rejected rather than silently emitted."""
        from src.parsing.gem5.impl.strategies.config_aware import (
            ConfigAwareStrategy,
        )

        # Non-existent path — configparser.read silently handles missing files
        # but we should test with a path that can't be parsed
        config_path = tmp_path / "bad_config.ini"
        config_path.write_text("")  # Empty is fine for configparser

        strategy = ConfigAwareStrategy()
        with pytest.raises(RuntimeError, match="contains no sections"):
            strategy._parse_config(config_path)


# Parse work contract


class TestParseWork:
    """Tests for the abstract parse-work contract."""

    def test_call_raises_not_implemented(self) -> None:
        from src.parsing.gem5.impl.pool.parse_work import ParseWork

        class ConcreteParseWork(ParseWork):
            """Minimal concrete subclass that does NOT override __call__."""

        work = ConcreteParseWork()
        with pytest.raises(NotImplementedError, match="Subclass must implement"):
            work()

    def test_str_returns_class_name(self) -> None:
        from src.parsing.gem5.impl.pool.parse_work import ParseWork

        class MyWork(ParseWork):
            def __call__(self) -> dict[str, Any]:
                return {}

        work = MyWork()
        assert str(work) == "MyWork"


# Work-pool submission


class TestWorkPool:
    # [test->req~ring5.api.process-lifecycle~1]
    """Tests for lazy executor creation and submission."""

    def test_thread_executor_lazy_init(self) -> None:
        from src.parsing.framework.work_pool import WorkPool

        # Reset singleton to force fresh initialization
        WorkPool._instance = None

        pool = WorkPool()
        assert pool._thread_executor is None  # Not yet created

        executor = pool._get_thread_executor()
        assert executor is not None
        assert pool._thread_executor is not None

        # Second call returns the same instance
        executor2 = pool._get_thread_executor()
        assert executor is executor2

        # Cleanup
        WorkPool._instance = None

    def test_submit_runs_on_thread_pool(self) -> None:
        from src.parsing.framework.work_pool import WorkPool

        WorkPool._instance = None
        pool = WorkPool()

        def dummy_task() -> str:
            return "done"

        future = pool.submit(dummy_task)
        result = future.result(timeout=5)
        assert result == "done"

        pool.shutdown(wait=True)
        WorkPool._instance = None

    def test_submit_restarts_executor_after_shutdown(self) -> None:
        from src.parsing.framework.work_pool import WorkPool

        WorkPool._instance = None
        pool = WorkPool()
        assert pool.submit(lambda: "first").result(timeout=5) == "first"
        original_executor = pool._thread_executor

        pool.shutdown(wait=True)

        assert pool._thread_executor is None
        assert pool.submit(lambda: "second").result(timeout=5) == "second"
        assert pool._thread_executor is not original_executor
        pool.shutdown(wait=True)
        WorkPool._instance = None


# Parse-service expansion and finalization


class TestParseServiceRegexExpansion:
    """Tests for regex expansion during asynchronous submission."""

    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_regex_expansion_with_scanned_vars(
        self, mock_factory: MagicMock, mock_pool_cls: MagicMock, tmp_path: Path
    ) -> None:
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        # Create the stats directory so FileNotFoundError isn't raised
        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        scanned = [
            ScannedVariable(name="system.cpu0.ipc", type="scalar"),
            ScannedVariable(name="system.cpu1.ipc", type="scalar"),
        ]

        config = StatConfig(
            name=r"system\.cpu\d+\.ipc",
            type="scalar",
            is_regex=True,
        )

        result = ParseService.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=[config],
            output_dir=str(tmp_path / "out"),
            scanned_vars=scanned,
        )
        assert isinstance(result, ParseBatchResult)

    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_regex_expansion_with_pattern_indices(
        self, mock_factory: MagicMock, mock_pool_cls: MagicMock, tmp_path: Path
    ) -> None:
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        scanned = [
            ScannedVariable(
                name=r"system\.cpu\d+\.ipc",
                type="scalar",
                pattern_indices=["system.cpu0.ipc", "system.cpu1.ipc"],
            ),
        ]

        config = StatConfig(
            name=r"system\.cpu\d+\.ipc",
            type="scalar",
            is_regex=True,
        )

        result = ParseService.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=[config],
            output_dir=str(tmp_path / "out"),
            scanned_vars=scanned,
        )
        assert isinstance(result, ParseBatchResult)

    @patch("src.parsing.gem5.impl.gem5_parser.PatternIndexService")
    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_keep_indices_expansion(
        self,
        mock_factory: MagicMock,
        mock_pool_cls: MagicMock,
        mock_pattern_svc: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        mock_pool = MagicMock()
        mock_pool.submit_batch_async.return_value = []
        mock_pool_cls.get_instance.return_value = mock_pool

        mock_pattern_svc.reconstruct_concrete_name.side_effect = lambda pattern, nid: (
            f"system.cpu{nid}.ipc"
        )

        scanned = [
            ScannedVariable(
                name=r"system\.cpu\d+\.ipc",
                type="scalar",
                pattern_indices=["system.cpu0.ipc", "system.cpu1.ipc"],
            ),
        ]

        config = StatConfig(
            name=r"system\.cpu\d+\.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=True,
        )

        result = ParseService.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=[config],
            output_dir=str(tmp_path / "out"),
            scanned_vars=scanned,
        )
        assert isinstance(result, ParseBatchResult)

    @patch("src.parsing.gem5.impl.gem5_parser.PatternIndexService")
    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_keep_indices_with_numeric_ids(
        self,
        mock_factory: MagicMock,
        mock_pool_cls: MagicMock,
        mock_pattern_svc: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Cover the numeric ID path (IDs don't contain '.')."""
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        mock_pool = MagicMock()
        mock_pool.submit_batch_async.return_value = []
        mock_pool_cls.get_instance.return_value = mock_pool

        mock_pattern_svc.reconstruct_concrete_name.side_effect = lambda pattern, nid: (
            f"system.cpu{nid}.ipc"
        )

        scanned = [
            ScannedVariable(
                name=r"system\.cpu\d+\.ipc",
                type="scalar",
                pattern_indices=["0", "1"],
            ),
        ]

        config = StatConfig(
            name=r"system\.cpu\d+\.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=True,
            params={"parsed_ids": ["0"]},
        )

        result = ParseService.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=[config],
            output_dir=str(tmp_path / "out"),
            scanned_vars=scanned,
        )
        assert isinstance(result, ParseBatchResult)

    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_regex_no_match_warns(
        self, mock_factory: MagicMock, mock_pool_cls: MagicMock, tmp_path: Path
    ) -> None:
        """A regex without matches still returns a valid batch."""
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        scanned = [
            ScannedVariable(name="system.mem.bandwidth", type="scalar"),
        ]

        config = StatConfig(
            name=r"system\.cpu\d+\.ipc",
            type="scalar",
            is_regex=True,
        )

        result = ParseService.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=[config],
            output_dir=str(tmp_path / "out"),
            scanned_vars=scanned,
        )
        assert isinstance(result, ParseBatchResult)

    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_invalid_regex_is_rejected(
        self, mock_factory: MagicMock, mock_pool_cls: MagicMock, tmp_path: Path
    ) -> None:
        """An invalid regex fails before parser work is queued."""
        from src.core.models.parsing_models import (
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        scanned = [
            ScannedVariable(name="system.cpu0.ipc", type="scalar"),
        ]

        config = StatConfig(
            name="system.[bad_regex",  # Invalid regex
            type="scalar",
            is_regex=True,
        )

        with pytest.raises(ValueError, match="Unsafe regex"):
            ParseService.submit_parse_async(
                stats_path=str(stats_dir),
                stats_pattern="stats.txt",
                variables=[config],
                output_dir=str(tmp_path / "out"),
                scanned_vars=scanned,
            )


class TestParseServiceFinalize:
    """Tests for parse finalization and CSV construction."""

    def test_finalize_parsing_no_results(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        result = ParseService.finalize_parsing("/tmp/out", [])
        assert result is None

    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_finalize_parsing_delegates_to_strategy(
        self, mock_factory: MagicMock, tmp_path: Path
    ) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        mock_strategy = MagicMock()
        mock_strategy.post_process.return_value = []
        mock_factory.create.return_value = mock_strategy

        _ = ParseService.finalize_parsing(
            str(tmp_path), [{"data": 1}], strategy_type="config_aware", var_names=["x"]
        )
        mock_factory.create.assert_called_with("config_aware")
        mock_strategy.post_process.assert_called_once()

    def test_construct_final_csv_empty(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        result = ParseService.construct_final_csv("/tmp/out", [])
        assert result is None

    def test_construct_final_csv_with_data(self, tmp_path: Path) -> None:
        """Cover CSV generation with stat objects."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        # Create mock stat objects with the expected interface
        mock_var = MagicMock()
        mock_var.entries = ["e0", "e1"]
        mock_var.balance_content = MagicMock()
        mock_var.reduce_duplicates = MagicMock()
        mock_var.reduced_content = {"e0": "1.0", "e1": "2.5"}

        results = [{"varA": mock_var}]
        csv_path = ParseService.construct_final_csv(str(tmp_path), results, var_names=["varA"])
        assert csv_path is not None
        assert os.path.exists(csv_path)

        # Check CSV content
        with open(csv_path) as f:
            content = f.read()
        assert "varA..e0" in content
        assert "varA..e1" in content
        assert "1.0" in content

    def test_construct_final_csv_scalar_no_entries(self, tmp_path: Path) -> None:
        """Cover scalar variable path (no entries)."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        mock_var = MagicMock()
        mock_var.entries = []
        mock_var.balance_content = MagicMock()
        mock_var.reduce_duplicates = MagicMock()
        mock_var.reduced_content = "42"

        results = [{"scalarVar": mock_var}]
        csv_path = ParseService.construct_final_csv(str(tmp_path), results, var_names=["scalarVar"])
        assert csv_path is not None

        with open(csv_path) as f:
            content = f.read()
        assert "scalarVar" in content
        assert "42" in content

    def test_construct_final_csv_missing_var_in_result(self, tmp_path: Path) -> None:
        """Cover NaN path when variable is absent from a result."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        mock_var = MagicMock()
        mock_var.entries = []
        mock_var.balance_content = MagicMock()
        mock_var.reduce_duplicates = MagicMock()
        mock_var.reduced_content = "10"

        results = [{"a": mock_var}]
        csv_path = ParseService.construct_final_csv(
            str(tmp_path), results, var_names=["a", "missing_var"]
        )
        assert csv_path is not None

        with open(csv_path) as f:
            content = f.read()
        assert "NaN" in content

    def test_construct_final_csv_raw_data(self, tmp_path: Path) -> None:
        """Cover raw data path (no balance_content attribute)."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        # Raw data still needs 'entries' for header construction,
        # but lacks 'balance_content' triggering the raw-data row path.
        class RawVar:
            entries: list[str] = []

            def __str__(self) -> str:
                return "benchmark_x"

        raw_var = RawVar()

        results = [{"configVar": raw_var}]
        csv_path = ParseService.construct_final_csv(str(tmp_path), results, var_names=["configVar"])
        assert csv_path is not None

        with open(csv_path) as f:
            content = f.read()
        assert "benchmark_x" in content


# Pattern-index selection


class TestPatternIndexSelector:
    """Tests for pattern-index controls and helpers."""

    @patch("src.web.components.data_source.pattern_index_selector.st")
    @patch("src.web.components.data_source.pattern_index_selector.PatternIndexService")
    def test_render_selector_not_pattern_variable(
        self, mock_svc: MagicMock, mock_st: MagicMock
    ) -> None:
        from src.web.components.data_source.pattern_index_selector import (
            PatternIndexSelector,
        )

        mock_svc.is_pattern_variable.return_value = False

        use_filter, entries = PatternIndexSelector.render_selector(
            var_name="system.cpu.ipc",
            entries=["0", "1"],
            var_id="v1",
        )
        assert use_filter is False
        assert entries == ["0", "1"]

    @patch("src.web.components.data_source.pattern_index_selector.st")
    @patch("src.web.components.data_source.pattern_index_selector.PatternIndexService")
    def test_render_selector_no_positions(self, mock_svc: MagicMock, mock_st: MagicMock) -> None:
        from src.web.components.data_source.pattern_index_selector import (
            PatternIndexSelector,
        )

        mock_svc.is_pattern_variable.return_value = True
        mock_svc.extract_index_positions.return_value = []
        mock_svc.parse_entry_indices.return_value = {}

        use_filter, entries = PatternIndexSelector.render_selector(
            var_name=r"system.cpu\d+.ipc",
            entries=["0", "1"],
            var_id="v2",
        )
        assert use_filter is False
        assert entries == ["0", "1"]

    @patch("src.web.components.data_source.pattern_index_selector.st")
    @patch("src.web.components.data_source.pattern_index_selector.PatternIndexService")
    def test_render_selector_no_filter(self, mock_svc: MagicMock, mock_st: MagicMock) -> None:
        from src.web.components.data_source.pattern_index_selector import (
            PatternIndexSelector,
        )

        mock_svc.is_pattern_variable.return_value = True
        mock_svc.extract_index_positions.return_value = ["cpu"]
        mock_svc.parse_entry_indices.return_value = {0: {"0", "1"}}

        mock_st.checkbox.return_value = False  # use_filter = False

        use_filter, entries = PatternIndexSelector.render_selector(
            var_name=r"system.cpu\d+.ipc",
            entries=["0", "1"],
            var_id="v3",
        )
        assert use_filter is False
        mock_st.info.assert_called()

    @patch("src.web.components.data_source.pattern_index_selector.st")
    @patch("src.web.components.data_source.pattern_index_selector.PatternIndexService")
    def test_render_selector_with_filter_and_selection(
        self, mock_svc: MagicMock, mock_st: MagicMock
    ) -> None:
        from src.web.components.data_source.pattern_index_selector import (
            PatternIndexSelector,
        )

        mock_svc.is_pattern_variable.return_value = True
        mock_svc.extract_index_positions.return_value = ["cpu"]
        mock_svc.parse_entry_indices.return_value = {0: {"0", "1", "2"}}
        mock_svc.filter_entries.return_value = ["0", "1"]
        mock_svc.format_entry_display.return_value = "cpu0"

        mock_st.checkbox.return_value = True  # use_filter = True

        # Mock columns context manager
        col_mock = MagicMock()
        mock_st.columns.return_value = [col_mock, col_mock]
        col_mock.__enter__ = MagicMock(return_value=col_mock)
        col_mock.__exit__ = MagicMock(return_value=False)

        mock_st.multiselect.return_value = ["0", "1"]

        # Mock expander
        expander_mock = MagicMock()
        mock_st.expander.return_value = expander_mock
        expander_mock.__enter__ = MagicMock(return_value=expander_mock)
        expander_mock.__exit__ = MagicMock(return_value=False)

        use_filter, entries = PatternIndexSelector.render_selector(
            var_name=r"system.cpu\d+.ipc",
            entries=["0", "1", "2"],
            var_id="v4",
        )
        assert use_filter is True
        assert entries == ["0", "1"]
        mock_st.success.assert_called()

    @patch(
        "src.web.components.data_source.pattern_index_selector.filtered_multiselect",
        return_value=[],
    )
    @patch("src.web.components.data_source.pattern_index_selector.st")
    @patch("src.web.components.data_source.pattern_index_selector.PatternIndexService")
    def test_render_selector_empty_selection_warns(
        self, mock_svc: MagicMock, mock_st: MagicMock, mock_filtered: MagicMock
    ) -> None:
        from src.web.components.data_source.pattern_index_selector import (
            PatternIndexSelector,
        )

        mock_svc.is_pattern_variable.return_value = True
        mock_svc.extract_index_positions.return_value = ["cpu"]
        mock_svc.parse_entry_indices.return_value = {0: {"0", "1"}}
        mock_svc.filter_entries.return_value = []

        mock_st.checkbox.return_value = True

        col_mock = MagicMock()
        mock_st.columns.return_value = [col_mock, col_mock]
        col_mock.__enter__ = MagicMock(return_value=col_mock)
        col_mock.__exit__ = MagicMock(return_value=False)

        mock_st.multiselect.return_value = []  # empty selection

        use_filter, entries = PatternIndexSelector.render_selector(
            var_name=r"system.cpu\d+.ipc",
            entries=["0", "1"],
            var_id="v5",
        )
        assert use_filter is True
        assert entries == []
        mock_st.warning.assert_called()
        mock_st.error.assert_called()

    @patch("src.web.components.data_source.pattern_index_selector.st")
    @patch("src.web.components.data_source.pattern_index_selector.PatternIndexService")
    def test_render_selector_with_current_selection(
        self, mock_svc: MagicMock, mock_st: MagicMock
    ) -> None:
        from src.web.components.data_source.pattern_index_selector import (
            PatternIndexSelector,
        )

        mock_svc.is_pattern_variable.return_value = True
        mock_svc.extract_index_positions.return_value = ["cpu"]
        mock_svc.parse_entry_indices.return_value = {0: {"0", "1", "2"}}
        mock_svc.filter_entries.return_value = ["0"]
        mock_svc.format_entry_display.return_value = "cpu0"

        mock_st.checkbox.return_value = True

        col_mock = MagicMock()
        mock_st.columns.return_value = [col_mock, col_mock]
        col_mock.__enter__ = MagicMock(return_value=col_mock)
        col_mock.__exit__ = MagicMock(return_value=False)

        mock_st.multiselect.return_value = ["0"]

        expander_mock = MagicMock()
        mock_st.expander.return_value = expander_mock
        expander_mock.__enter__ = MagicMock(return_value=expander_mock)
        expander_mock.__exit__ = MagicMock(return_value=False)

        use_filter, entries = PatternIndexSelector.render_selector(
            var_name=r"system.cpu\d+.ipc",
            entries=["0", "1", "2"],
            var_id="v6",
            current_selection={0: ["0"]},
        )
        assert use_filter is True
        assert entries == ["0"]

    def test_static_filter_entries_delegates(self) -> None:
        with patch(
            "src.web.components.data_source.pattern_index_selector.PatternIndexService"
        ) as mock_svc:
            from src.web.components.data_source.pattern_index_selector import (
                PatternIndexSelector,
            )

            mock_svc.filter_entries.return_value = ["0"]
            result = PatternIndexSelector._filter_entries(["0", "1"], {0: ["0"]})
            assert result == ["0"]

    def test_static_format_entry_display_delegates(self) -> None:
        with patch(
            "src.web.components.data_source.pattern_index_selector.PatternIndexService"
        ) as mock_svc:
            from src.web.components.data_source.pattern_index_selector import (
                PatternIndexSelector,
            )

            mock_svc.format_entry_display.return_value = "cpu0_cntrl1"
            result = PatternIndexSelector._format_entry_display("0_1", ["cpu", "cntrl"])
            assert result == "cpu0_cntrl1"


# Data-source components


class TestDataSourceComponents:
    """Tests for recent CSV controls and parse dialogs."""

    @patch("src.web.components.data_source.data_source_components.st")
    def test_render_csv_pool_empty(self, mock_st: MagicMock) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = []
        api.load_csv_pool.return_value = []

        DataSourceComponents.render_csv_pool(api)
        mock_st.warning.assert_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_with_files(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (False, False, False)

        DataSourceComponents.render_csv_pool(api)
        mock_st.info.assert_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_file_not_exists(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [
            {"path": "/nonexistent/file.csv", "name": "file.csv"}
        ]
        mock_card.file_info_card.return_value = (False, False, False)

        DataSourceComponents.render_csv_pool(api)
        mock_st.error.assert_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_load_clicked(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        import pandas as pd

        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (True, False, False)  # load_clicked=True
        api.load_csv_file.return_value = pd.DataFrame({"a": [1], "b": [2]})

        DataSourceComponents.render_csv_pool(api)
        api.load_csv_file.assert_called_once()
        mock_st.success.assert_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_load_exception(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (True, False, False)
        api.load_csv_file.side_effect = RuntimeError("read error")

        DataSourceComponents.render_csv_pool(api)
        mock_st.exception.assert_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_preview_clicked(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        import pandas as pd

        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (False, True, False)  # preview_clicked
        api.load_csv_file.return_value = pd.DataFrame({"a": [1]})

        DataSourceComponents.render_csv_pool(api)
        mock_st.dataframe.assert_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_delete_clicked(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (False, False, True)  # delete_clicked
        api.delete_from_csv_pool.return_value = True

        DataSourceComponents.render_csv_pool(api)
        api.delete_from_csv_pool.assert_called_once()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_delete_failed(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (False, False, True)
        api.delete_from_csv_pool.return_value = False

        DataSourceComponents.render_csv_pool(api)
        mock_st.error.assert_called()


# gem5 parser expansion and finalization


class TestGem5ParserSubmitParseAsync:
    """Tests for gem5 regex expansion during submission."""

    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_regex_expansion_with_scanned_vars(
        self, mock_factory: MagicMock, mock_pool_cls: MagicMock, tmp_path: Path
    ) -> None:
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        scanned = [
            ScannedVariable(name="system.cpu0.ipc", type="scalar"),
            ScannedVariable(name="system.cpu1.ipc", type="scalar"),
        ]

        config = StatConfig(
            name=r"system\.cpu\d+\.ipc",
            type="scalar",
            is_regex=True,
        )

        result = Gem5Parser.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=[config],
            output_dir=str(tmp_path / "out"),
            scanned_vars=scanned,
        )
        assert isinstance(result, ParseBatchResult)

    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_regex_with_pattern_indices(
        self, mock_factory: MagicMock, mock_pool_cls: MagicMock, tmp_path: Path
    ) -> None:
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        scanned = [
            ScannedVariable(
                name=r"system\.cpu\d+\.ipc",
                type="scalar",
                pattern_indices=["system.cpu0.ipc", "system.cpu1.ipc"],
            ),
        ]

        config = StatConfig(
            name=r"system\.cpu\d+\.ipc",
            type="scalar",
            is_regex=True,
        )

        result = Gem5Parser.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=[config],
            output_dir=str(tmp_path / "out"),
            scanned_vars=scanned,
        )
        assert isinstance(result, ParseBatchResult)

    @patch("src.parsing.gem5.impl.gem5_parser.PatternIndexService")
    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_keep_indices_expansion(
        self,
        mock_factory: MagicMock,
        mock_pool_cls: MagicMock,
        mock_pattern_svc: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        mock_pool = MagicMock()
        mock_pool.submit_batch_async.return_value = []
        mock_pool_cls.get_instance.return_value = mock_pool

        mock_pattern_svc.reconstruct_concrete_name.side_effect = lambda pat, nid: (
            f"system.cpu{nid}.ipc"
        )

        scanned = [
            ScannedVariable(
                name=r"system\.cpu\d+\.ipc",
                type="scalar",
                pattern_indices=["system.cpu0.ipc", "system.cpu1.ipc"],
            ),
        ]

        config = StatConfig(
            name=r"system\.cpu\d+\.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=True,
        )

        result = Gem5Parser.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=[config],
            output_dir=str(tmp_path / "out"),
            scanned_vars=scanned,
        )
        assert isinstance(result, ParseBatchResult)

    @patch("src.parsing.gem5.impl.gem5_parser.PatternIndexService")
    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_keep_indices_numeric_ids(
        self,
        mock_factory: MagicMock,
        mock_pool_cls: MagicMock,
        mock_pattern_svc: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        mock_pool = MagicMock()
        mock_pool.submit_batch_async.return_value = []
        mock_pool_cls.get_instance.return_value = mock_pool

        mock_pattern_svc.reconstruct_concrete_name.side_effect = lambda pat, nid: (
            f"system.cpu{nid}.ipc"
        )

        scanned = [
            ScannedVariable(
                name=r"system\.cpu\d+\.ipc",
                type="scalar",
                pattern_indices=["0", "1"],
            ),
        ]

        config = StatConfig(
            name=r"system\.cpu\d+\.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=True,
            params={"parsed_ids": ["0"]},
        )

        result = Gem5Parser.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=[config],
            output_dir=str(tmp_path / "out"),
            scanned_vars=scanned,
        )
        assert isinstance(result, ParseBatchResult)

    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_regex_no_match(
        self, mock_factory: MagicMock, mock_pool_cls: MagicMock, tmp_path: Path
    ) -> None:
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        scanned = [ScannedVariable(name="system.mem.bw", type="scalar")]

        config = StatConfig(name=r"system\.cpu\d+\.ipc", type="scalar", is_regex=True)

        result = Gem5Parser.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=[config],
            output_dir=str(tmp_path / "out"),
            scanned_vars=scanned,
        )
        assert isinstance(result, ParseBatchResult)

    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_invalid_regex(
        self, mock_factory: MagicMock, mock_pool_cls: MagicMock, tmp_path: Path
    ) -> None:
        from src.core.models.parsing_models import ScannedVariable, StatConfig
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy

        scanned = [ScannedVariable(name="system.cpu0.ipc", type="scalar")]

        config = StatConfig(name="system.[bad", type="scalar", is_regex=True)

        with pytest.raises(ValueError, match="Unsafe regex"):
            Gem5Parser.submit_parse_async(
                stats_path=str(stats_dir),
                stats_pattern="stats.txt",
                variables=[config],
                output_dir=str(tmp_path / "out"),
                scanned_vars=scanned,
            )

    def test_finalize_no_results(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        result = Gem5Parser.finalize_parsing("/tmp/out", [])
        assert result is None

    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_finalize_with_strategy(self, mock_factory: MagicMock, tmp_path: Path) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        mock_strategy = MagicMock()
        mock_strategy.post_process.return_value = []
        mock_factory.create.return_value = mock_strategy

        _ = Gem5Parser.finalize_parsing(
            str(tmp_path), [{"data": 1}], strategy_type="config_aware", var_names=["x"]
        )
        mock_factory.create.assert_called_with("config_aware")

    def test_construct_final_csv_empty(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        result = Gem5Parser.construct_final_csv("/tmp/out", [])
        assert result is None

    def test_construct_final_csv_with_data(self, tmp_path: Path) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        mock_var = MagicMock()
        mock_var.entries = ["e0"]
        mock_var.balance_content = MagicMock()
        mock_var.reduce_duplicates = MagicMock()
        mock_var.reduced_content = {"e0": "5.0"}

        results = [{"v": mock_var}]
        csv_path = Gem5Parser.construct_final_csv(str(tmp_path), results, var_names=["v"])
        assert csv_path is not None
        assert os.path.exists(csv_path)

    def test_submit_parse_async_path_not_found(self) -> None:
        from src.core.models.parsing_models import StatConfig
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        config = StatConfig(name="x", type="scalar")
        with pytest.raises(FileNotFoundError):
            Gem5Parser.submit_parse_async("/nonexistent/path", "stats.txt", [config], "/tmp/out")


# Dataframe shaper validation


class TestUniDfShaper:
    """Tests for dataframe input validation."""

    def test_none_input_raises(self) -> None:
        from src.core.services.shapers.uni_df_shaper import UniDfShaper

        class DummyShaper(UniDfShaper):
            def _verify_params(self) -> bool:
                return True

            def _transform(self, data_frame: Any) -> Any:
                return data_frame

        shaper = DummyShaper({"type": "dummy"})
        with pytest.raises(ValueError, match="cannot be None"):
            shaper(cast(Any, None))

    def test_non_dataframe_input_raises(self) -> None:
        from src.core.services.shapers.uni_df_shaper import UniDfShaper

        class DummyShaper(UniDfShaper):
            def _verify_params(self) -> bool:
                return True

            def _transform(self, data_frame: Any) -> Any:
                return data_frame

        shaper = DummyShaper({"type": "dummy"})
        with pytest.raises(ValueError, match="Expected pandas DataFrame"):
            shaper(cast(Any, "not a dataframe"))


# Selector validation


class TestSelectorValidation:
    """Tests for selector parameters and preconditions."""

    def test_missing_column_raises(self) -> None:
        from src.core.services.shapers.impl.selector import Selector

        with pytest.raises((ValueError, KeyError)):
            Selector({"not_column": "x"})

    def test_empty_column_raises(self) -> None:
        from src.core.services.shapers.impl.selector import Selector

        with pytest.raises((ValueError, KeyError)):
            Selector({"column": ""})

    def test_column_not_in_dataframe_raises(self) -> None:
        import pandas as pd

        from src.core.services.shapers.impl.selector import Selector

        class ConcreteSelector(Selector):
            def _transform(self, data_frame: Any) -> Any:
                return data_frame

        selector = ConcreteSelector({"column": "nonexistent"})
        with pytest.raises(ValueError, match="not found in dataframe"):
            selector(pd.DataFrame({"a": [1]}))


# Shaper API delegation


class TestDefaultShapersAPI:
    """Tests for shaper API delegation."""

    def test_get_available_shaper_types(self) -> None:
        from src.core.services.shapers.shapers_impl import DefaultShapersAPI

        api = DefaultShapersAPI()
        types = api.get_available_shaper_types()
        assert isinstance(types, list)
        assert len(types) > 0


# Data-source page modes


class TestDataSourcePage:
    """Tests for data-source page modes."""

    @patch("src.web.pages.data_source.st")
    @patch("src.web.pages.data_source.DataSourceComponents")
    def test_render_parse_mode(self, mock_dsc: MagicMock, mock_st: MagicMock) -> None:
        from src.web.pages.data_source import DataSourcePage

        api = MagicMock()
        api.state_manager.is_using_parser.return_value = False

        mock_st.segmented_control.return_value = "Parse gem5 Stats Files"
        page = DataSourcePage(api)
        page.render()
        mock_dsc.render_parser_config.assert_called_once()

    @patch("src.web.pages.data_source.st")
    @patch("src.web.pages.data_source.DataSourceComponents")
    def test_render_load_recent(self, mock_dsc: MagicMock, mock_st: MagicMock) -> None:
        from src.web.pages.data_source import DataSourcePage

        api = MagicMock()
        mock_st.segmented_control.return_value = "Load from Recent"
        page = DataSourcePage(api)
        page.render()
        mock_dsc.render_csv_pool.assert_called_once()

    @patch("src.web.pages.data_source.st")
    @patch("src.web.pages.data_source.DataSourceComponents")
    def test_render_csv_mode(self, mock_dsc: MagicMock, mock_st: MagicMock) -> None:
        from src.web.pages.data_source import DataSourcePage

        api = MagicMock()
        api.state_manager.is_using_parser.return_value = True
        mock_st.segmented_control.return_value = "I already have CSV data"
        page = DataSourcePage(api)
        page.render()
        api.state_manager.set_use_parser.assert_called_with(False)
        mock_st.success.assert_called()


# DataManager abstract contract


class TestDataManagerBase:
    """Tests for dataframe access through a data manager."""

    def test_get_data_delegates(self) -> None:
        import pandas as pd

        from src.web.components.data_managers.data_manager import DataManager

        class ConcreteManager(DataManager):
            @property
            def name(self) -> str:
                return "test"

            def render(self) -> None:
                pass

        api = MagicMock()
        df = pd.DataFrame({"a": [1]})
        api.state_manager.get_data.return_value = df

        mgr = ConcreteManager(api)
        result = mgr.get_data()
        assert result is not None
        api.state_manager.get_data.assert_called()

    def test_set_data_delegates(self) -> None:
        import pandas as pd

        from src.web.components.data_managers.data_manager import DataManager

        class ConcreteManager(DataManager):
            @property
            def name(self) -> str:
                return "test"

            def render(self) -> None:
                pass

        api = MagicMock()
        df = pd.DataFrame({"a": [1]})
        mgr = ConcreteManager(api)
        mgr.set_data(df)
        api.state_manager.set_data.assert_called_once_with(df)


# Additional data-source actions


class TestDataSourceComponentsExtra:
    """Data-source component error and empty-state behavior."""

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_preview_exception(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (False, True, False)
        api.load_csv_file.side_effect = RuntimeError("preview error")

        DataSourceComponents.render_csv_pool(api)
        mock_st.exception.assert_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.VariableEditor")
    def test_render_parser_config(self, mock_editor: MagicMock, mock_st: MagicMock) -> None:
        """Cover render_parser_config fragment (partially)."""
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        api = MagicMock()
        api.state_manager.get_simulator.return_value = "gem5"
        api.state_manager.get_stats_path.return_value = "/tmp/stats"
        api.state_manager.get_stats_pattern.return_value = "stats.txt"
        api.state_manager.get_parser_strategy.return_value = "simple"
        api.state_manager.get_scanned_variables.return_value = []
        api.state_manager.get_parse_variables.return_value = []

        # Mock the fragment decorator to just call the function
        def fragment_bypass(func: Any) -> Any:
            return func

        mock_st.fragment = fragment_bypass

        def _make_cols(n: Any) -> list[MagicMock]:
            count = len(n) if isinstance(n, list) else int(n)
            cols = []
            for _ in range(count):
                c = MagicMock()
                c.__enter__ = MagicMock(return_value=c)
                c.__exit__ = MagicMock(return_value=False)
                cols.append(c)
            return cols

        mock_st.columns.side_effect = _make_cols
        mock_st.text_input.return_value = "/tmp/stats"
        mock_st.segmented_control.return_value = "simple"
        mock_st.checkbox.return_value = False
        mock_st.button.return_value = False

        mock_editor.render.return_value = []

        DataSourceComponents.render_parser_config(api)


# Scan-work and job contracts


class TestScanWork:
    """Tests for the abstract scan-work contract."""

    def test_call_raises_not_implemented(self) -> None:
        from src.parsing.gem5.impl.pool.scan_work import ScanWork

        class ConcreteScanWork(ScanWork):
            pass

        work = ConcreteScanWork()
        with pytest.raises(NotImplementedError):
            work()

    def test_str_returns_class_name(self) -> None:
        from src.parsing.gem5.impl.pool.scan_work import ScanWork

        class MyScanWork(ScanWork):
            def __call__(self) -> Any:
                return []

        work = MyScanWork()
        assert str(work) == "MyScanWork"


class TestJobBase:
    """Tests for the abstract job contract."""

    def test_job_str(self) -> None:
        from src.parsing.framework.job import Job

        class MyJob(Job):
            def __call__(self) -> Any:
                return None

        j = MyJob()
        assert str(j) == "MyJob"


# Seed reduction


class TestReductionService:
    """Tests for seed reduction and input validation."""

    def test_reduce_seeds_empty(self) -> None:
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        result = ReductionService.reduce_seeds(pd.DataFrame(), ["cat"], ["val"])
        assert result.empty

    def test_reduce_seeds_basic(self) -> None:
        # [test->req~ring5.data.seed-reduction~1]
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        df = pd.DataFrame(
            {
                "bench": ["a", "a", "b", "b"],
                "ipc": [1.0, 2.0, 3.0, 4.0],
            }
        )
        result = ReductionService.reduce_seeds(df, ["bench"], ["ipc"])
        assert "ipc" in result.columns
        assert "ipc.sd" in result.columns
        assert len(result) == 2

    def test_validate_no_categorical(self) -> None:
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        errors = ReductionService.validate_seeds_reducer_inputs(pd.DataFrame({"a": [1]}), [], ["a"])
        assert any("categorical" in e.lower() for e in errors)

    def test_validate_no_statistic(self) -> None:
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        errors = ReductionService.validate_seeds_reducer_inputs(pd.DataFrame({"a": [1]}), ["a"], [])
        assert any("statistic" in e.lower() for e in errors)

    def test_validate_missing_columns(self) -> None:
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        errors = ReductionService.validate_seeds_reducer_inputs(
            pd.DataFrame({"a": [1]}), ["missing_cat"], ["missing_stat"]
        )
        assert len(errors) >= 2

    def test_validate_non_numeric_stat(self) -> None:
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        errors = ReductionService.validate_seeds_reducer_inputs(
            pd.DataFrame({"cat": ["a"], "val": ["text"]}), ["cat"], ["val"]
        )
        assert any("numeric" in e.lower() for e in errors)


# Arithmetic operations


class TestArithmeticService:
    """Tests for arithmetic operation dispatch."""

    # [test->req~ring5.data.arithmetic~1]

    def test_division(self) -> None:
        import pandas as pd

        from src.core.services.managers.arithmetic_service import ArithmeticService

        df = pd.DataFrame({"a": [10.0], "b": [2.0]})
        result = ArithmeticService.apply_operation(df, "Division", "a", "b", "c")
        assert result["c"].iloc[0] == 5.0

    def test_sum(self) -> None:
        import pandas as pd

        from src.core.services.managers.arithmetic_service import ArithmeticService

        df = pd.DataFrame({"a": [10.0], "b": [2.0]})
        result = ArithmeticService.apply_operation(df, "Sum", "a", "b", "c")
        assert result["c"].iloc[0] == 12.0

    def test_subtraction(self) -> None:
        import pandas as pd

        from src.core.services.managers.arithmetic_service import ArithmeticService

        df = pd.DataFrame({"a": [10.0], "b": [2.0]})
        result = ArithmeticService.apply_operation(df, "Subtraction", "a", "b", "c")
        assert result["c"].iloc[0] == 8.0

    def test_multiplication(self) -> None:
        import pandas as pd

        from src.core.services.managers.arithmetic_service import ArithmeticService

        df = pd.DataFrame({"a": [10.0], "b": [2.0]})
        result = ArithmeticService.apply_operation(df, "Multiplication", "a", "b", "c")
        assert result["c"].iloc[0] == 20.0

    def test_unknown_op_raises(self) -> None:
        import pandas as pd

        from src.core.services.managers.arithmetic_service import ArithmeticService

        df = pd.DataFrame({"a": [10.0], "b": [2.0]})
        with pytest.raises(ValueError, match="Unknown operation"):
            ArithmeticService.apply_operation(df, "Modulo", "a", "b", "c")


# Shaper validation


class TestShaperBase:
    """Tests for base shaper parameters and preconditions."""

    def test_non_dict_params_raises(self) -> None:
        from src.core.services.shapers.shaper import Shaper

        class DummyShaper(Shaper):
            def _verify_params(self) -> bool:
                return super()._verify_params()

        with pytest.raises(ValueError, match="must be a dictionary"):
            DummyShaper("not_a_dict")  # type: ignore[arg-type]

    def test_preconditions_none_df(self) -> None:
        from src.core.services.shapers.shaper import Shaper

        class DummyShaper(Shaper):
            def _verify_params(self) -> bool:
                return True

        shaper = DummyShaper({"type": "dummy"})
        with pytest.raises(ValueError, match="cannot be None"):
            shaper._verify_preconditions(None)  # type: ignore[arg-type]

    def test_preconditions_empty_df(self) -> None:
        import pandas as pd

        from src.core.services.shapers.shaper import Shaper

        class DummyShaper(Shaper):
            def _verify_params(self) -> bool:
                return True

        shaper = DummyShaper({"type": "dummy"})
        with pytest.raises(ValueError, match="empty"):
            shaper._verify_preconditions(pd.DataFrame())

    def test_call_delegates_to_preconditions(self) -> None:
        import pandas as pd

        from src.core.services.shapers.shaper import Shaper

        class DummyShaper(Shaper):
            def _verify_params(self) -> bool:
                return True

        shaper = DummyShaper({"type": "dummy"})
        df = pd.DataFrame({"a": [1]})
        result = shaper(df)
        pd.testing.assert_frame_equal(result, df)


# Item selection


class TestItemSelectorVerify:
    """Tests for item-selector parameter validation."""

    def test_missing_strings_raises(self) -> None:
        from src.core.services.shapers.impl.selector_algorithms.item_selector import (
            ItemSelector,
        )

        with pytest.raises(ValueError, match="'strings'"):
            ItemSelector({"column": "x"})

    def test_non_list_strings_raises(self) -> None:
        from src.core.services.shapers.impl.selector_algorithms.item_selector import (
            ItemSelector,
        )

        with pytest.raises(TypeError, match="must be a list"):
            ItemSelector({"column": "x", "strings": "not_a_list"})

    def test_valid_params(self) -> None:
        from src.core.services.shapers.impl.selector_algorithms.item_selector import (
            ItemSelector,
        )

        sel = ItemSelector({"column": "a", "strings": ["x", "y"]})
        assert sel.column == "a"
        assert sel.strings == ["x", "y"]


# Repository state


class TestRepositoryStateManager:
    """Tests for repository data validation and clearing."""

    def test_set_data_type_enforcement(self) -> None:
        """Config variable columns should be cast to str."""
        import pandas as pd

        from src.core.state.repository_state_manager import RepositoryStateManager

        mgr = RepositoryStateManager()
        mgr._session_repo.parser_repo.set_parse_variables(
            cast(Any, [{"name": "benchmark", "type": "configuration"}])
        )

        df = pd.DataFrame({"benchmark": [1, 2, 3], "ipc": [1.0, 2.0, 3.0]})
        mgr.set_data(df)

        result = mgr.get_data()
        assert result is not None
        assert pd.api.types.is_string_dtype(result["benchmark"])  # config vars cast to string

    def test_set_data_skip_same_object(self) -> None:
        """Setting the same DataFrame object again should be a no-op."""
        import pandas as pd

        from src.core.state.repository_state_manager import RepositoryStateManager

        mgr = RepositoryStateManager()
        df = pd.DataFrame({"a": [1]})
        mgr.set_data(df)
        mgr.set_data(df)  # No error expected

    def test_clear_data_with_temp_dir(self, tmp_path: Path) -> None:
        """clear_data removes temp directory."""
        import pandas as pd

        from src.core.state.repository_state_manager import RepositoryStateManager

        mgr = RepositoryStateManager()
        temp_dir = tmp_path / "temp_parsed"
        temp_dir.mkdir()

        mgr._session_repo.config_repo.set_temp_dir(str(temp_dir))
        mgr.set_data(pd.DataFrame({"a": [1]}))

        mgr.clear_data()
        assert mgr.get_data() is None

    def test_clear_data_no_temp_dir(self) -> None:
        """clear_data when no temp dir exists."""
        import pandas as pd

        from src.core.state.repository_state_manager import RepositoryStateManager

        mgr = RepositoryStateManager()
        mgr.set_data(pd.DataFrame({"a": [1]}))
        mgr.clear_data()
        assert mgr.get_data() is None


# Pipeline delegation


class TestDefaultShapersAPIProcessPipeline:
    """Tests for pipeline delegation."""

    def test_process_pipeline_empty(self) -> None:
        import pandas as pd

        from src.core.services.shapers.shapers_impl import DefaultShapersAPI

        api = DefaultShapersAPI()
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = api.process_pipeline(df, [])
        pd.testing.assert_frame_equal(result, df)


# Configuration parsing failures


class TestConfigAwareParseConfigException:
    """Tests for configuration parsing failures."""

    def test_parse_config_with_exception(self, tmp_path: Path) -> None:
        from src.parsing.gem5.impl.strategies.config_aware import (
            ConfigAwareStrategy,
        )

        config_path = tmp_path / "config.ini"
        config_path.write_text("[section]\nkey = val\n")

        strategy = ConfigAwareStrategy()
        with patch(
            "src.parsing.gem5.impl.strategies.config_aware.configparser.ConfigParser"
        ) as mock_cp:
            mock_parser = MagicMock()
            mock_parser.read.side_effect = configparser.Error("parse error")
            mock_cp.return_value = mock_parser

            with pytest.raises(RuntimeError, match="parse error"):
                strategy._parse_config(config_path)
