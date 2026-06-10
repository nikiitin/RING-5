"""
Tests for ParseBatchResult thread-safety refactoring.

Validates that:
1. ParseBatchResult correctly bundles futures + var_names
2. No shared class-level mutable state exists in Gem5Parser / ParseService
3. Concurrent parse batches maintain independent var_names
"""

from concurrent.futures import Future
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import ParseBatchResult, StatConfig


class TestParseBatchResult:
    """Unit tests for the ParseBatchResult dataclass."""

    def test_frozen_dataclass(self) -> None:
        """ParseBatchResult should be immutable."""
        batch = ParseBatchResult(futures=[], var_names=["a"])
        with pytest.raises(AttributeError):
            batch.var_names = ["b"]  # type: ignore[misc]

    def test_stores_futures_and_var_names(self) -> None:
        """Should contain futures and var_names passed at construction."""
        f: Future[Any] = Future()
        f.set_result({"data": 1})
        batch = ParseBatchResult(futures=[f], var_names=["system.cpu.ipc"])

        assert len(batch.futures) == 1
        assert batch.futures[0].result() == {"data": 1}
        assert batch.var_names == ["system.cpu.ipc"]

    def test_empty_batch(self) -> None:
        """Empty batch should have empty futures and var_names."""
        batch = ParseBatchResult(futures=[], var_names=[])
        assert batch.futures == []
        assert batch.var_names == []


class TestNoClassLevelState:
    """Verify _active_var_names class-level state is removed."""

    def test_gem5_parser_has_no_active_var_names(self) -> None:
        """Gem5Parser should no longer have _active_var_names class attribute."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        assert not hasattr(Gem5Parser, "_active_var_names"), (
            "Gem5Parser should not have _active_var_names class attribute. "
            "Variable names must be returned via ParseBatchResult."
        )

    def test_parse_service_has_no_active_var_names(self) -> None:
        """ParseService should no longer have _active_var_names class attribute."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        assert not hasattr(ParseService, "_active_var_names"), (
            "ParseService should not have _active_var_names class attribute. "
            "Variable names must be returned via ParseBatchResult."
        )


class TestSubmitParseAsyncReturnType:
    """Verify submit_parse_async returns ParseBatchResult."""

    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    @patch("src.parsing.gem5.impl.gem5_parser.normalize_user_path")
    def test_gem5_parser_returns_batch_result(
        self, mock_path: MagicMock, mock_factory: MagicMock, mock_pool: MagicMock
    ) -> None:
        """Gem5Parser.submit_parse_async should return ParseBatchResult."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_strategy = MagicMock()
        mock_work = MagicMock()
        mock_strategy.get_work_items.return_value = [mock_work]
        mock_factory.create.return_value = mock_strategy

        mock_future: Future[Any] = Future()
        mock_future.set_result({"data": 1})
        mock_pool.get_instance.return_value.submit_batch_async.return_value = [mock_future]

        variables = [
            StatConfig(name="system.cpu.ipc", type="scalar"),
            StatConfig(name="system.cpu.numCycles", type="scalar"),
        ]

        result = Gem5Parser.submit_parse_async(
            stats_path="/tmp/stats",
            stats_pattern="stats.txt",
            variables=variables,
            output_dir="/tmp/out",
        )

        assert isinstance(result, ParseBatchResult)
        assert result.var_names == ["system.cpu.ipc", "system.cpu.numCycles"]
        assert len(result.futures) == 1

    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    @patch("src.parsing.gem5.impl.gem5_parser.normalize_user_path")
    def test_empty_work_raises(
        self, mock_path: MagicMock, mock_factory: MagicMock, mock_pool: MagicMock
    ) -> None:
        """An empty work list raises — never an empty batch a script could
        chain through finalize_parsing as a phantom 'success'."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        mock_path.return_value.exists.return_value = True
        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = []
        mock_factory.create.return_value = mock_strategy

        with pytest.raises(FileNotFoundError, match="No parse work generated"):
            Gem5Parser.submit_parse_async(
                stats_path="/tmp/stats",
                stats_pattern="stats.txt",
                variables=[StatConfig(name="test", type="scalar")],
                output_dir="/tmp/out",
            )


class TestConstructFinalCsvVarNames:
    """Verify construct_final_csv uses provided var_names."""

    def test_var_names_parameter_controls_column_order(self, tmp_path: str) -> None:
        """Explicitly provided var_names should control CSV column ordering."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        # Create mock results with known variables
        mock_stat_a = MagicMock()
        mock_stat_a.entries = []
        mock_stat_a.balance_content = MagicMock()
        mock_stat_a.reduce_duplicates = MagicMock()
        mock_stat_a.reduced_content = "100"

        mock_stat_b = MagicMock()
        mock_stat_b.entries = []
        mock_stat_b.balance_content = MagicMock()
        mock_stat_b.reduce_duplicates = MagicMock()
        mock_stat_b.reduced_content = "200"

        results: list[Any] = [{"var_b": mock_stat_b, "var_a": mock_stat_a}]

        # With var_names=["var_a", "var_b"], columns should be a, b
        csv_path = Gem5Parser.construct_final_csv(
            str(tmp_path), results, var_names=["var_a", "var_b"]
        )
        assert csv_path is not None

        with open(csv_path) as f:
            header = f.readline().strip()

        assert header == "var_a,var_b"

    def test_fallback_when_var_names_is_none(self, tmp_path: str) -> None:
        """When var_names is None, should fall back to dict key order."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        mock_stat = MagicMock()
        mock_stat.entries = []
        mock_stat.balance_content = MagicMock()
        mock_stat.reduce_duplicates = MagicMock()
        mock_stat.reduced_content = "42"

        results: list[Any] = [{"only_var": mock_stat}]

        csv_path = Gem5Parser.construct_final_csv(str(tmp_path), results, var_names=None)
        assert csv_path is not None

        with open(csv_path) as f:
            header = f.readline().strip()

        assert header == "only_var"


class TestBatchIsolation:
    """Verify that concurrent batches do not share state."""

    @patch("src.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    @patch("src.parsing.gem5.impl.gem5_parser.normalize_user_path")
    def test_concurrent_batches_have_independent_var_names(
        self, mock_path: MagicMock, mock_factory: MagicMock, mock_pool: MagicMock
    ) -> None:
        """Two consecutive submit_parse_async calls should produce independent var_names."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        mock_path.return_value.exists.return_value = True
        mock_strategy = MagicMock()
        mock_strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = mock_strategy
        mock_pool.get_instance.return_value.submit_batch_async.return_value = []

        # Batch 1
        batch1 = Gem5Parser.submit_parse_async(
            "/tmp/stats",
            "stats.txt",
            [StatConfig(name="var_alpha", type="scalar")],
            "/tmp/out1",
        )

        # Batch 2 with different variables
        batch2 = Gem5Parser.submit_parse_async(
            "/tmp/stats",
            "stats.txt",
            [
                StatConfig(name="var_beta", type="scalar"),
                StatConfig(name="var_gamma", type="scalar"),
            ],
            "/tmp/out2",
        )

        # Each batch should retain its own var_names
        assert batch1.var_names == ["var_alpha"]
        assert batch2.var_names == ["var_beta", "var_gamma"]

        # Crucially, batch1 var_names should NOT have been overwritten by batch2
        assert batch1.var_names != batch2.var_names
