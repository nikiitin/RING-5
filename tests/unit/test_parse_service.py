"""Unit tests for ParseService — orchestration of gem5 stats parsing."""

import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import ParseBatchResult, StatConfig
from src.core.parsing.parse_service import ParseService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeStat:
    """Mimics a Stat object returned by gem5 parsing strategies."""

    reduced_content: Any
    entries: Optional[List[str]] = None

    def balance_content(self) -> None:
        pass

    def reduce_duplicates(self) -> None:
        pass


class TestSubmitParseAsync:
    """Tests for ParseService.submit_parse_async."""

    def test_raises_on_nonexistent_path(self, tmp_path: Path) -> None:
        bad_path = str(tmp_path / "nonexistent")
        with pytest.raises(FileNotFoundError, match="does not exist"):
            ParseService.submit_parse_async(bad_path, "stats.txt", [], str(tmp_path / "out"))

    @patch("src.core.parsing.parse_service.ParseWorkPool")
    @patch("src.core.parsing.parse_service.StrategyFactory")
    def test_returns_empty_batch_when_no_work(
        self, mock_sf: MagicMock, mock_pool: MagicMock, tmp_path: Path
    ) -> None:
        stats_dir = tmp_path / "data"
        stats_dir.mkdir()
        strategy = MagicMock()
        strategy.get_work_items.return_value = []
        mock_sf.create.return_value = strategy

        result = ParseService.submit_parse_async(
            str(stats_dir), "stats.txt", [], str(tmp_path / "out")
        )

        assert result.futures == []
        assert result.var_names == []

    @patch("src.core.parsing.parse_service.ParseWorkPool")
    @patch("src.core.parsing.parse_service.StrategyFactory")
    def test_submits_work_and_returns_batch(
        self, mock_sf: MagicMock, mock_pool: MagicMock, tmp_path: Path
    ) -> None:
        stats_dir = tmp_path / "data"
        stats_dir.mkdir()

        strategy = MagicMock()
        work_items = [MagicMock(), MagicMock()]
        strategy.get_work_items.return_value = work_items
        mock_sf.create.return_value = strategy

        pool_inst = MagicMock()
        futures = [MagicMock(), MagicMock()]
        pool_inst.submit_batch_async.return_value = futures
        mock_pool.get_instance.return_value = pool_inst

        variables = [
            StatConfig(name="system.cpu.ipc", type="scalar"),
            StatConfig(name="simTicks", type="scalar"),
        ]

        result = ParseService.submit_parse_async(
            str(stats_dir), "stats.txt", variables, str(tmp_path / "out")
        )

        assert isinstance(result, ParseBatchResult)
        assert result.var_names == ["system.cpu.ipc", "simTicks"]
        assert len(result.futures) == 2

    @patch("src.core.parsing.parse_service.ParseWorkPool")
    @patch("src.core.parsing.parse_service.StrategyFactory")
    def test_regex_expansion_with_scanned_vars(
        self, mock_sf: MagicMock, mock_pool: MagicMock, tmp_path: Path
    ) -> None:
        stats_dir = tmp_path / "data"
        stats_dir.mkdir()

        strategy = MagicMock()
        strategy.get_work_items.return_value = [MagicMock()]
        mock_sf.create.return_value = strategy

        pool_inst = MagicMock()
        pool_inst.submit_batch_async.return_value = [MagicMock()]
        mock_pool.get_instance.return_value = pool_inst

        # A regex variable with scanned matches
        variables = [StatConfig(name=r"system\.cpu\d+\.ipc", type="scalar", is_regex=True)]

        sv = MagicMock()
        sv.name = r"system\.cpu\d+\.ipc"
        sv.pattern_indices = ["system.cpu0.ipc", "system.cpu1.ipc"]
        scanned = [sv]

        ParseService.submit_parse_async(
            str(stats_dir),
            "stats.txt",
            variables,
            str(tmp_path / "out"),
            scanned_vars=scanned,
        )

        # Strategy should receive configs with parsed_ids injected
        call_args = strategy.get_work_items.call_args[0]
        processed_configs = call_args[2]
        assert "parsed_ids" in processed_configs[0].params


class TestFinalizeParssing:
    """Tests for ParseService.finalize_parsing."""

    @patch("src.core.parsing.parse_service.StrategyFactory")
    def test_returns_none_on_empty_results(self, mock_sf: MagicMock) -> None:
        result = ParseService.finalize_parsing("/tmp/out", [])
        assert result is None

    @patch("src.core.parsing.parse_service.ParseService.construct_final_csv")
    @patch("src.core.parsing.parse_service.StrategyFactory")
    def test_delegates_to_strategy_and_csv(self, mock_sf: MagicMock, mock_csv: MagicMock) -> None:
        strategy = MagicMock()
        strategy.post_process.return_value = [{"a": 1}]
        mock_sf.create.return_value = strategy
        mock_csv.return_value = "/out/results.csv"

        result = ParseService.finalize_parsing("/out", [{"a": 1}], var_names=["a"])

        strategy.post_process.assert_called_once_with([{"a": 1}])
        assert result == "/out/results.csv"


class TestConstructFinalCsv:
    """Tests for ParseService.construct_final_csv."""

    def test_returns_none_on_empty(self, tmp_path: Path) -> None:
        assert ParseService.construct_final_csv(str(tmp_path), []) is None

    def test_scalar_variables(self, tmp_path: Path) -> None:
        results = [
            {
                "ipc": FakeStat(reduced_content=2.1, entries=None),
                "cpi": FakeStat(reduced_content=0.48, entries=None),
            },
            {
                "ipc": FakeStat(reduced_content=1.9, entries=None),
                "cpi": FakeStat(reduced_content=0.53, entries=None),
            },
        ]

        path = ParseService.construct_final_csv(str(tmp_path), results)

        assert path is not None
        assert os.path.exists(path)

        with open(path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == ["ipc", "cpi"]
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0] == ["2.1", "0.48"]

    def test_vector_variables(self, tmp_path: Path) -> None:
        results = [
            {
                "cache_miss": FakeStat(
                    reduced_content={"l1": "0.05", "l2": "0.12"},
                    entries=["l1", "l2"],
                ),
            },
        ]

        path = ParseService.construct_final_csv(str(tmp_path), results)

        assert path is not None
        with open(path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == ["cache_miss..l1", "cache_miss..l2"]

    def test_mixed_stat_types(self, tmp_path: Path) -> None:
        """Handles results with both scalar and vector variables."""
        results = [
            {
                "ipc": FakeStat(reduced_content=2.1, entries=None),
                "cache": FakeStat(
                    reduced_content={"l1": "0.05", "l2": "0.12"},
                    entries=["l1", "l2"],
                ),
            },
        ]

        path = ParseService.construct_final_csv(str(tmp_path), results)

        assert path is not None
        with open(path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == ["ipc", "cache..l1", "cache..l2"]
            row = next(reader)
            assert row == ["2.1", "0.05", "0.12"]

    def test_var_names_ordering(self, tmp_path: Path) -> None:
        """Columns follow var_names order, not dict key order."""
        results = [
            {
                "b_var": FakeStat(reduced_content=2, entries=None),
                "a_var": FakeStat(reduced_content=1, entries=None),
            },
        ]

        path = ParseService.construct_final_csv(
            str(tmp_path), results, var_names=["a_var", "b_var"]
        )

        assert path is not None
        with open(path, newline="") as f:
            header = next(csv.reader(f))
            assert header == ["a_var", "b_var"]

    def test_missing_var_fills_nan(self, tmp_path: Path) -> None:
        """If a var_name is missing from a result row, fill with NaN."""
        results = [
            {"ipc": FakeStat(reduced_content=2.1, entries=None)},
        ]

        path = ParseService.construct_final_csv(
            str(tmp_path), results, var_names=["ipc", "missing_var"]
        )

        assert path is not None
        with open(path, newline="") as f:
            reader = csv.reader(f)
            next(reader)  # header
            row = next(reader)
            assert row == ["2.1", "NaN"]

    def test_output_dir_created(self, tmp_path: Path) -> None:
        """Output directory is created if it doesn't exist."""
        new_dir = str(tmp_path / "deep" / "nesting")
        results = [{"x": FakeStat(reduced_content=1, entries=None)}]

        path = ParseService.construct_final_csv(new_dir, results)
        assert path is not None
        assert os.path.exists(path)
