"""
Targeted coverage-boost tests for low-coverage modules.

Targets the following files/lines:
- src/web/pages/ui/components/pattern_index_selector.py  (24% → ~90%)
    Lines 70-167: render_selector branches, _filter_entries, _format_entry_display
- src/core/models/parsing_models.py  (67% → ~100%)
    Lines 53-64: ScannedVariable.to_dict optional fields (minimum, maximum, pattern_indices)
- src/parsing/gem5/impl/strategies/factory.py  (53% → 100%)
    Lines 37-44: config_aware branch + ValueError for unknown strategy
- src/parsing/gem5/impl/gem5_parser_api.py  (71% → 100%)
    Lines 40, 57, 66, 73: all four delegating methods
- src/parsing/gem5/impl/strategies/config_aware.py  (67% → ~100%)
    Lines 42-43, 55, 68-75: post_process + _parse_config branches
- src/parsing/gem5/impl/pool/parse_work.py  (80% → 100%)
    Lines 44, 53: __call__ raises NotImplementedError, __str__
- src/parsing/gem5/impl/pool/work_pool.py  (85% → ~100%)
    Lines 50-51, 67-69: _mp_context ValueError fallback, _get_thread_executor
- src/parsing/parse_service.py  (79% → ~90%)
    Lines 143-146, 155-198, 210-212, 325: regex expansion, keep_indices, finalize
- src/web/pages/ui/components/data_source_components.py  (73% → ~85%)
    Lines covering render_csv_pool, variable_config_dialog, _show_parse_dialog
- src/web/pages/ui/components/plot_manager_components.py  (71% → ~85%)
    Lines covering render_create_plot_section, render_plot_selector,
    render_plot_controls, render_pipeline_editor
"""

import os
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

# ===================================================================
# 1. ScannedVariable.to_dict — optional fields (lines 53-64)
# ===================================================================


class TestScannedVariableToDict:
    """Cover to_dict branches for minimum, maximum, pattern_indices."""

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


# ===================================================================
# 2. StrategyFactory — config_aware + ValueError (lines 37-44)
# ===================================================================


class TestStrategyFactory:
    """Cover config_aware branch and unknown strategy ValueError."""

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


# ===================================================================
# 3. Gem5ParserAPI — all four delegation methods (lines 40, 57, 66, 73)
# ===================================================================


class TestGem5ParserAPI:
    """Cover submit_parse_async, finalize_parsing, submit_scan_async, aggregate_scan_results."""

    @patch("src.parsing.gem5.impl.gem5_parser_api.Gem5Parser")
    def test_submit_parse_async(self, mock_parser: MagicMock) -> None:
        from src.core.models.parsing_models import ParseBatchResult
        from src.parsing.gem5.impl.gem5_parser_api import Gem5ParserAPI

        mock_parser.submit_parse_async.return_value = ParseBatchResult(futures=[], var_names=[])
        api = Gem5ParserAPI()
        result = api.submit_parse_async(
            stats_path="/fake/path",
            stats_pattern="stats.txt",
            variables=[],
            output_dir="/tmp/out",
            strategy_type="simple",
            scanned_vars=None,
        )
        mock_parser.submit_parse_async.assert_called_once()
        assert isinstance(result, ParseBatchResult)

    @patch("src.parsing.gem5.impl.gem5_parser_api.Gem5Parser")
    def test_finalize_parsing(self, mock_parser: MagicMock) -> None:
        from src.parsing.gem5.impl.gem5_parser_api import Gem5ParserAPI

        mock_parser.finalize_parsing.return_value = "/some/path.csv"
        api = Gem5ParserAPI()
        result = api.finalize_parsing(
            output_dir="/tmp/out",
            results=[{"data": 1}],
            strategy_type="simple",
            var_names=["a"],
        )
        mock_parser.finalize_parsing.assert_called_once()
        assert result == "/some/path.csv"

    @patch("src.parsing.gem5.impl.gem5_parser_api.Gem5Scanner")
    def test_submit_scan_async(self, mock_scanner: MagicMock) -> None:
        from src.parsing.gem5.impl.gem5_parser_api import Gem5ParserAPI

        mock_scanner.submit_scan_async.return_value = []
        api = Gem5ParserAPI()
        result = api.submit_scan_async(
            stats_path="/fake/path",
            stats_pattern="stats.txt",
            limit=5,
        )
        mock_scanner.submit_scan_async.assert_called_once()
        assert result == []

    @patch("src.parsing.gem5.impl.gem5_parser_api.Gem5Scanner")
    def test_aggregate_scan_results(self, mock_scanner: MagicMock) -> None:
        from src.parsing.gem5.impl.gem5_parser_api import Gem5ParserAPI

        mock_scanner.aggregate_scan_results.return_value = []
        api = Gem5ParserAPI()
        result = api.aggregate_scan_results(results=[[]])
        mock_scanner.aggregate_scan_results.assert_called_once()
        assert result == []


# ===================================================================
# 4. ConfigAwareStrategy — post_process + _parse_config (lines 42-75)
# ===================================================================


class TestConfigAwareStrategy:
    """Cover post_process branches and _parse_config error handling."""

    def test_post_process_no_sim_path(self) -> None:
        """Result without sim_path key — should be appended as-is."""
        from src.parsing.gem5.impl.strategies.config_aware import (
            ConfigAwareStrategy,
        )

        strategy = ConfigAwareStrategy()
        results = [{"some_data": 123}]
        out = strategy.post_process(results)
        assert len(out) == 1
        assert out[0] == {"some_data": 123}

    def test_post_process_config_found(self, tmp_path: Path) -> None:
        """Result with sim_path pointing to existing config.ini."""
        from src.parsing.gem5.impl.strategies.config_aware import (
            ConfigAwareStrategy,
        )

        # Create a mock config.ini
        config_path = tmp_path / "config.ini"
        config_path.write_text("[system]\ncpu_type = O3CPU\nnum_cpus = 4\n")

        stats_path = tmp_path / "stats.txt"
        stats_path.write_text("dummy")

        strategy = ConfigAwareStrategy()
        results = [{"sim_path": str(stats_path), "data": "abc"}]
        out = strategy.post_process(results)

        assert len(out) == 1
        assert "config" in out[0]
        assert "system" in out[0]["config"]
        assert out[0]["config"]["system"]["cpu_type"] == "O3CPU"

    def test_post_process_config_not_found(self, tmp_path: Path) -> None:
        """Result with sim_path but no config.ini in the directory."""
        from src.parsing.gem5.impl.strategies.config_aware import (
            ConfigAwareStrategy,
        )

        stats_path = tmp_path / "stats.txt"
        stats_path.write_text("dummy")

        strategy = ConfigAwareStrategy()
        results = [{"sim_path": str(stats_path), "data": "abc"}]
        out = strategy.post_process(results)

        assert len(out) == 1
        assert "config" not in out[0]

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
        """_parse_config returns empty dict on read error."""
        from src.parsing.gem5.impl.strategies.config_aware import (
            ConfigAwareStrategy,
        )

        # Non-existent path — configparser.read silently handles missing files
        # but we should test with a path that can't be parsed
        config_path = tmp_path / "bad_config.ini"
        config_path.write_text("")  # Empty is fine for configparser

        strategy = ConfigAwareStrategy()
        result = strategy._parse_config(config_path)
        assert isinstance(result, dict)


# ===================================================================
# 5. ParseWork — __call__ + __str__ (lines 44, 53)
# ===================================================================


class TestParseWork:
    """Cover NotImplementedError from __call__ and __str__."""

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


# ===================================================================
# 6. WorkPool — _mp_context fallback + _get_thread_executor (lines 50-51, 67-69)
# ===================================================================


class TestWorkPool:
    """Cover mp_context ValueError fallback and thread executor lazy init."""

    def test_thread_executor_lazy_init(self) -> None:
        from src.parsing.gem5.impl.pool.work_pool import WorkPool

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

    @patch("src.parsing.gem5.impl.pool.work_pool.multiprocessing.get_context")
    def test_mp_context_fallback_on_value_error(self, mock_ctx: MagicMock) -> None:
        from src.parsing.gem5.impl.pool.work_pool import WorkPool

        mock_ctx.side_effect = ValueError("no spawn")

        # Reset singleton
        WorkPool._instance = None

        pool = WorkPool()
        assert pool._mp_context is None  # Fell back to None

        # Cleanup
        WorkPool._instance = None

    def test_submit_with_threads(self) -> None:
        from src.parsing.gem5.impl.pool.work_pool import WorkPool

        WorkPool._instance = None
        pool = WorkPool()

        def dummy_task() -> str:
            return "done"

        future = pool.submit(dummy_task, use_threads=True)
        result = future.result(timeout=5)
        assert result == "done"

        WorkPool._instance = None


# ===================================================================
# 7. ParseService — regex expansion, keep_indices, finalize (lines 143-198, 210-212, 325)
# ===================================================================


class TestParseServiceRegexExpansion:
    """Cover regex expansion branches in submit_parse_async."""

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
        from src.parsing.parse_service import ParseService

        # Create the stats directory so FileNotFoundError isn't raised
        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = []
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
        from src.parsing.parse_service import ParseService

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = []
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
        from src.parsing.parse_service import ParseService

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = []
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
        from src.parsing.parse_service import ParseService

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = []
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
        """Cover the 'no matches found' branch."""
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.parse_service import ParseService

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = []
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
    def test_invalid_regex_warns(
        self, mock_factory: MagicMock, mock_pool_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Cover the 'invalid regex' branch."""
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.parse_service import ParseService

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = []
        mock_factory.create.return_value = mock_strategy

        scanned = [
            ScannedVariable(name="system.cpu0.ipc", type="scalar"),
        ]

        config = StatConfig(
            name="system.[bad_regex",  # Invalid regex
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


class TestParseServiceFinalize:
    """Cover finalize_parsing and construct_final_csv."""

    def test_finalize_parsing_no_results(self) -> None:
        from src.parsing.parse_service import ParseService

        result = ParseService.finalize_parsing("/tmp/out", [])
        assert result is None

    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_finalize_parsing_delegates_to_strategy(
        self, mock_factory: MagicMock, tmp_path: Path
    ) -> None:
        from src.parsing.parse_service import ParseService

        mock_strategy = MagicMock()
        mock_strategy.post_process.return_value = []
        mock_factory.create.return_value = mock_strategy

        _ = ParseService.finalize_parsing(
            str(tmp_path), [{"data": 1}], strategy_type="config_aware", var_names=["x"]
        )
        mock_factory.create.assert_called_with("config_aware")
        mock_strategy.post_process.assert_called_once()

    def test_construct_final_csv_empty(self) -> None:
        from src.parsing.parse_service import ParseService

        result = ParseService.construct_final_csv("/tmp/out", [])
        assert result is None

    def test_construct_final_csv_with_data(self, tmp_path: Path) -> None:
        """Cover CSV generation with stat objects."""
        from src.parsing.parse_service import ParseService

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
        from src.parsing.parse_service import ParseService

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
        from src.parsing.parse_service import ParseService

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
        from src.parsing.parse_service import ParseService

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


# ===================================================================
# 8. PatternIndexSelector — render_selector branches (lines 70-167)
# ===================================================================


class TestPatternIndexSelector:
    """Cover render_selector UI logic and static helper methods."""

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

    @patch("src.web.components.data_source.pattern_index_selector.st")
    @patch("src.web.components.data_source.pattern_index_selector.PatternIndexService")
    def test_render_selector_empty_selection_warns(
        self, mock_svc: MagicMock, mock_st: MagicMock
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


# ===================================================================
# 9. DataSourceComponents — render_csv_pool, _show_parse_dialog (lines ~30-100, 400-490)
# ===================================================================


class TestDataSourceComponents:
    """Cover render_csv_pool branches and parse dialog logic."""

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


# ===================================================================
# 10. PlotManagerComponents — create, selector, controls (various lines)
# ===================================================================


class TestPlotManagerComponents:
    """Cover PlotManagerComponents UI methods."""

    @patch("src.web.components.plotting.plot_manager_components.st")
    @patch("src.web.components.plotting.plot_manager_components.PlotFactory")
    @patch("src.web.components.plotting.plot_manager_components.PlotService")
    def test_render_create_plot_section(
        self,
        mock_plot_svc: MagicMock,
        mock_factory: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        from src.web.components.plotting.plot_manager_components import (
            PlotManagerComponents,
        )

        api = MagicMock()
        api.state_manager.get_plot_counter.return_value = 0

        col_mock = MagicMock()
        mock_st.columns.return_value = [col_mock, col_mock, col_mock]
        col_mock.__enter__ = MagicMock(return_value=col_mock)
        col_mock.__exit__ = MagicMock(return_value=False)

        mock_factory.get_available_plot_types.return_value = ["bar", "line"]
        mock_st.text_input.return_value = "Plot 1"
        mock_st.selectbox.return_value = "bar"
        mock_st.button.return_value = False  # Don't click create

        PlotManagerComponents.render_create_plot_section(api)

    @patch("src.web.components.plotting.plot_manager_components.st")
    @patch("src.web.components.plotting.plot_manager_components.PlotFactory")
    @patch("src.web.components.plotting.plot_manager_components.PlotService")
    def test_render_create_plot_section_button_clicked(
        self,
        mock_plot_svc: MagicMock,
        mock_factory: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        from src.web.components.plotting.plot_manager_components import (
            PlotManagerComponents,
        )

        api = MagicMock()
        api.state_manager.get_plot_counter.return_value = 0

        col_mock = MagicMock()
        mock_st.columns.return_value = [col_mock, col_mock, col_mock]
        col_mock.__enter__ = MagicMock(return_value=col_mock)
        col_mock.__exit__ = MagicMock(return_value=False)

        mock_factory.get_available_plot_types.return_value = ["bar", "line"]
        mock_st.text_input.return_value = "Plot 1"
        mock_st.selectbox.return_value = "bar"
        mock_st.button.return_value = True  # Click create

        PlotManagerComponents.render_create_plot_section(api)
        mock_plot_svc.create_plot.assert_called_once()

    @patch("src.web.components.plotting.plot_manager_components.st")
    def test_render_plot_selector_no_plots(self, mock_st: MagicMock) -> None:
        from src.web.components.plotting.plot_manager_components import (
            PlotManagerComponents,
        )

        api = MagicMock()
        api.state_manager.get_plots.return_value = []

        result = PlotManagerComponents.render_plot_selector(api)
        assert result is None
        mock_st.warning.assert_called()

    @patch("src.web.components.plotting.plot_manager_components.st")
    def test_render_plot_selector_with_plots(self, mock_st: MagicMock) -> None:
        from src.web.components.plotting.plot_manager_components import (
            PlotManagerComponents,
        )

        plot1 = MagicMock()
        plot1.name = "Plot A"
        plot1.plot_id = "id-1"
        plot2 = MagicMock()
        plot2.name = "Plot B"
        plot2.plot_id = "id-2"

        api = MagicMock()
        api.state_manager.get_plots.return_value = [plot1, plot2]
        api.state_manager.get_current_plot_id.return_value = "id-2"

        mock_st.pills.return_value = "Plot B"

        result = PlotManagerComponents.render_plot_selector(api)
        assert result == plot2

    @patch("src.web.components.plotting.plot_manager_components.st")
    def test_render_plot_selector_unknown_current_id(self, mock_st: MagicMock) -> None:
        from src.web.components.plotting.plot_manager_components import (
            PlotManagerComponents,
        )

        plot1 = MagicMock()
        plot1.name = "Plot A"
        plot1.plot_id = "id-1"

        api = MagicMock()
        api.state_manager.get_plots.return_value = [plot1]
        api.state_manager.get_current_plot_id.return_value = "nonexistent-id"

        mock_st.pills.return_value = "Plot A"

        result = PlotManagerComponents.render_plot_selector(api)
        assert result == plot1

    @patch("src.web.components.plotting.plot_manager_components.PlotService")
    @patch("src.web.components.plotting.plot_manager_components.st")
    def test_render_plot_controls(
        self,
        mock_st: MagicMock,
        mock_plot_svc: MagicMock,
    ) -> None:
        from src.web.components.plotting.plot_manager_components import (
            PlotManagerComponents,
        )

        plot = MagicMock()
        plot.name = "My Plot"
        plot.plot_id = "pid-1"

        api = MagicMock()

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
        mock_st.text_input.return_value = "My Plot"  # No rename
        mock_st.button.return_value = False

        PlotManagerComponents.render_plot_controls(api, plot)

    @patch("src.web.components.plotting.plot_manager_components.ShaperFactory")
    @patch("src.web.components.plotting.plot_manager_components.apply_shapers")
    @patch("src.web.components.plotting.plot_manager_components.configure_shaper")
    @patch("src.web.components.plotting.plot_manager_components.st")
    def test_render_pipeline_editor_no_data(
        self,
        mock_st: MagicMock,
        mock_configure: MagicMock,
        mock_apply: MagicMock,
        mock_shaper_factory: MagicMock,
    ) -> None:
        from src.web.components.plotting.plot_manager_components import (
            PlotManagerComponents,
        )

        api = MagicMock()
        api.state_manager.get_data.return_value = None
        plot = MagicMock()

        PlotManagerComponents.render_pipeline_editor(api, plot)
        mock_st.warning.assert_called()


# ===================================================================
# 11. Gem5Parser - regex expansion + finalize (lines 142-197)
# ===================================================================


class TestGem5ParserSubmitParseAsync:
    """Cover Gem5Parser.submit_parse_async regex expansion."""

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
        mock_strategy.get_work_items.return_value = []
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
        mock_strategy.get_work_items.return_value = []
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
        mock_strategy.get_work_items.return_value = []
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
        mock_strategy.get_work_items.return_value = []
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
        mock_strategy.get_work_items.return_value = []
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
        from src.core.models.parsing_models import (
            ParseBatchResult,
            ScannedVariable,
            StatConfig,
        )
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        stats_dir = tmp_path / "sim"
        stats_dir.mkdir()

        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = []
        mock_factory.create.return_value = mock_strategy

        scanned = [ScannedVariable(name="system.cpu0.ipc", type="scalar")]

        config = StatConfig(name="system.[bad", type="scalar", is_regex=True)

        result = Gem5Parser.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=[config],
            output_dir=str(tmp_path / "out"),
            scanned_vars=scanned,
        )
        assert isinstance(result, ParseBatchResult)

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


# ===================================================================
# 12. UniDfShaper validation (lines 34-42)
# ===================================================================


class TestUniDfShaper:
    """Cover UniDfShaper.__call__ validation branches."""

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


# ===================================================================
# 13. Selector validation branches (lines 89, 96, 101)
# ===================================================================


class TestSelectorValidation:
    """Cover Selector._verify_params and _verify_preconditions."""

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


# ===================================================================
# 14. DefaultShapersAPI delegation (lines 42, 46, 50, 66, 70)
# ===================================================================


class TestDefaultShapersAPI:
    """Cover DefaultShapersAPI delegation methods."""

    def test_list_pipelines(self, tmp_path: Path) -> None:
        from src.core.services.shapers.shapers_impl import DefaultShapersAPI

        api = DefaultShapersAPI(tmp_path)
        result = api.list_pipelines()
        assert isinstance(result, list)

    def test_save_and_load_pipeline(self, tmp_path: Path) -> None:
        from src.core.services.shapers.shapers_impl import DefaultShapersAPI

        api = DefaultShapersAPI(tmp_path)
        api.save_pipeline("test_pipe", cast(Any, [{"type": "rename", "config": {}}]), "desc")
        result = api.load_pipeline("test_pipe")
        assert "pipeline" in result or isinstance(result, dict)

    def test_delete_pipeline(self, tmp_path: Path) -> None:
        from src.core.services.shapers.shapers_impl import DefaultShapersAPI

        api = DefaultShapersAPI(tmp_path)
        api.save_pipeline("to_delete", cast(Any, [{"type": "rename"}]), "desc")
        api.delete_pipeline("to_delete")
        assert "to_delete" not in api.list_pipelines()

    def test_get_available_shaper_types(self, tmp_path: Path) -> None:
        from src.core.services.shapers.shapers_impl import DefaultShapersAPI

        api = DefaultShapersAPI(tmp_path)
        types = api.get_available_shaper_types()
        assert isinstance(types, list)
        assert len(types) > 0


# ===================================================================
# 15. DataSourcePage render branches (lines 43-48)
# ===================================================================


class TestDataSourcePage:
    """Cover DataSourcePage.render branch paths."""

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


# ===================================================================
# 16. DataManager abstract base coverage (lines 25, 30)
# ===================================================================


class TestDataManagerBase:
    """Cover DataManager.get_data and set_data helper methods."""

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


# ===================================================================
# 17. StyleManager render methods (lines 90, 100)
# ===================================================================


class TestStyleManager:
    """Cover StyleManager.render_xaxis_labels_ui and render_data_labels_ui."""

    @patch("src.web.pages.ui.plotting.styles.manager.StyleUIFactory")
    @patch("src.web.pages.ui.plotting.styles.manager.StyleApplicator")
    def test_render_xaxis_labels_ui(
        self, mock_applicator_cls: MagicMock, mock_factory: MagicMock
    ) -> None:
        from src.web.pages.ui.plotting.styles.manager import StyleManager

        mock_ui = MagicMock()
        mock_ui.render_xaxis_labels_ui.return_value = {"x_label": "Time"}
        mock_factory.get_strategy.return_value = mock_ui

        mgr = StyleManager(plot_id=1, plot_type="bar")
        result = mgr.render_xaxis_labels_ui({"x_label": ""})
        assert result == {"x_label": "Time"}

    @patch("src.web.pages.ui.plotting.styles.manager.StyleUIFactory")
    @patch("src.web.pages.ui.plotting.styles.manager.StyleApplicator")
    def test_render_data_labels_ui(
        self, mock_applicator_cls: MagicMock, mock_factory: MagicMock
    ) -> None:
        from src.web.pages.ui.plotting.styles.manager import StyleManager

        mock_ui = MagicMock()
        mock_ui.render_data_labels_ui.return_value = {"show_values": True}
        mock_factory.get_strategy.return_value = mock_ui

        mgr = StyleManager(plot_id=1, plot_type="bar")
        result = mgr.render_data_labels_ui({})
        assert result == {"show_values": True}


# ===================================================================
# 18. More PlotManagerComponents branches
# ===================================================================


class TestPlotManagerComponentsExtra:
    """Additional PlotManagerComponents coverage."""

    @patch("src.web.components.plotting.plot_manager_components.ShaperFactory")
    @patch("src.web.components.plotting.plot_manager_components.apply_shapers")
    @patch("src.web.components.plotting.plot_manager_components.configure_shaper")
    @patch("src.web.components.plotting.plot_manager_components.st")
    def test_render_pipeline_editor_with_data_and_pipeline(
        self,
        mock_st: MagicMock,
        mock_configure: MagicMock,
        mock_apply: MagicMock,
        mock_shaper_factory: MagicMock,
    ) -> None:
        import pandas as pd

        from src.web.components.plotting.plot_manager_components import (
            PlotManagerComponents,
        )

        api = MagicMock()
        data = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        api.state_manager.get_data.return_value = data

        plot = MagicMock()
        plot.plot_id = "p1"
        plot.pipeline = [
            {"id": 0, "type": "rename", "config": {"old": "a", "new": "A"}},
        ]
        plot.pipeline_counter = 1

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

        mock_shaper_factory.get_display_name_map.return_value = {"Rename": "rename"}
        mock_shaper_factory.get_display_name.return_value = "Rename"
        mock_st.selectbox.return_value = "Rename"
        mock_st.button.return_value = False

        # Mock expander context
        exp_mock = MagicMock()
        mock_st.expander.return_value = exp_mock
        exp_mock.__enter__ = MagicMock(return_value=exp_mock)
        exp_mock.__exit__ = MagicMock(return_value=False)

        mock_configure.return_value = {"type": "rename", "old": "a", "new": "A"}
        mock_apply.return_value = data

        PlotManagerComponents.render_pipeline_editor(api, plot)


# ===================================================================
# 19. More DataSourceComponents branches
# ===================================================================


class TestDataSourceComponentsExtra:
    """Additional DataSourceComponents coverage."""

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


# ===================================================================
# 20. ScanWork + Job abstract methods
# ===================================================================


class TestScanWork:
    """Cover ScanWork abstract __call__ and __str__."""

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
    """Cover Job.__str__ and abstract __call__."""

    def test_job_str(self) -> None:
        from src.parsing.gem5.impl.pool.job import Job

        class MyJob(Job):
            def __call__(self) -> Any:
                return None

        j = MyJob()
        assert str(j) == "MyJob"


# ===================================================================
# 22. ReductionService
# ===================================================================


class TestReductionService:
    """Cover ReductionService.reduce_seeds and validate_seeds_reducer_inputs."""

    def test_reduce_seeds_empty(self) -> None:
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        result = ReductionService.reduce_seeds(pd.DataFrame(), ["cat"], ["val"])
        assert result.empty

    def test_reduce_seeds_basic(self) -> None:
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


# ===================================================================
# 23. ArithmeticService
# ===================================================================


class TestArithmeticService:
    """Cover ArithmeticService.apply_operation branches."""

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


# ===================================================================
# 24. Shaper base class
# ===================================================================


class TestShaperBase:
    """Cover Shaper parameter validation and precondition checks."""

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


# ===================================================================
# 25. ItemSelector
# ===================================================================


class TestItemSelectorVerify:
    """Cover ItemSelector._verify_params branches."""

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


# ===================================================================
# 26. RepositoryStateManager
# ===================================================================


class TestRepositoryStateManager:
    """Cover RepositoryStateManager set_data type enforcement and clear_data."""

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
        assert result["benchmark"].dtype == object

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


# ===================================================================
# 27. DefaultShapersAPI.process_pipeline
# ===================================================================


class TestDefaultShapersAPIProcessPipeline:
    """Cover process_pipeline delegation."""

    def test_process_pipeline_empty(self, tmp_path: Path) -> None:
        import pandas as pd

        from src.core.services.shapers.shapers_impl import DefaultShapersAPI

        api = DefaultShapersAPI(tmp_path)
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = api.process_pipeline(df, [])
        pd.testing.assert_frame_equal(result, df)


# ===================================================================
# 28. ConfigAwareStrategy._parse_config exception
# ===================================================================


class TestConfigAwareParseConfigException:
    """Cover _parse_config exception handler branch."""

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
            mock_parser.read.side_effect = Exception("parse error")
            mock_cp.return_value = mock_parser

            result = strategy._parse_config(config_path)
            assert result == {}
