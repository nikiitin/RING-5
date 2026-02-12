"""Tests for Gem5Parser — branch coverage for uncovered lines."""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.core.parsing.gem5.impl.gem5_parser import Gem5Parser


@dataclass
class FakeStatConfig:
    name: str
    is_regex: bool = False
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeScannedVar:
    name: str
    pattern_indices: Optional[List[str]] = None


@dataclass
class FakeStat:
    entries: Optional[List[str]] = None
    reduced_content: Any = None

    def balance_content(self) -> None:
        pass

    def reduce_duplicates(self) -> None:
        pass


class TestSubmitParseAsync:
    """Test submit_parse_async branches."""

    @patch("src.core.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.core.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_path_not_found_raises(
        self, mock_factory: MagicMock, mock_pool: MagicMock, tmp_path: Any
    ) -> None:
        with pytest.raises(FileNotFoundError, match="does not exist"):
            Gem5Parser.submit_parse_async(
                str(tmp_path / "nonexistent"),
                "stats.txt",
                [],
                str(tmp_path),
            )

    @patch("src.core.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.core.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_empty_work_items(
        self, mock_factory: MagicMock, mock_pool: MagicMock, tmp_path: Any
    ) -> None:
        stats_dir = tmp_path / "stats"
        stats_dir.mkdir()

        strategy = MagicMock()
        strategy.get_work_items.return_value = []
        mock_factory.create.return_value = strategy

        result = Gem5Parser.submit_parse_async(
            str(stats_dir),
            "stats.txt",
            [],
            str(tmp_path),
        )
        assert result.futures == []

    @patch("src.core.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.core.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_regex_expansion_no_match(
        self, mock_factory: MagicMock, mock_pool: MagicMock, tmp_path: Any
    ) -> None:
        stats_dir = tmp_path / "stats"
        stats_dir.mkdir()

        config = FakeStatConfig(name=r"system\.cpu\d+\.ipc", is_regex=True)
        scanned = [FakeScannedVar(name="system.different.stat")]

        strategy = MagicMock()
        strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = strategy

        pool_instance = MagicMock()
        pool_instance.submit_batch_async.return_value = [MagicMock()]
        mock_pool.get_instance.return_value = pool_instance

        # Should not crash — just log warning
        Gem5Parser.submit_parse_async(
            str(stats_dir),
            "stats.txt",
            [config],  # type: ignore[list-item]
            str(tmp_path),
            scanned_vars=scanned,
        )

    @patch("src.core.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.core.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_regex_expansion_with_pattern_indices(
        self, mock_factory: MagicMock, mock_pool: MagicMock, tmp_path: Any
    ) -> None:
        stats_dir = tmp_path / "stats"
        stats_dir.mkdir()

        config = FakeStatConfig(name=r"system\.cpu\d+\.ipc", is_regex=True)
        scanned = [
            FakeScannedVar(
                name=r"system\.cpu\d+\.ipc", pattern_indices=["system.cpu0.ipc", "system.cpu1.ipc"]
            )
        ]

        strategy = MagicMock()
        strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = strategy

        pool_instance = MagicMock()
        pool_instance.submit_batch_async.return_value = [MagicMock()]
        mock_pool.get_instance.return_value = pool_instance

        Gem5Parser.submit_parse_async(
            str(stats_dir),
            "stats.txt",
            [config],  # type: ignore[list-item]
            str(tmp_path),
            scanned_vars=scanned,
        )

    @patch("src.core.parsing.gem5.impl.gem5_parser.ParseWorkPool")
    @patch("src.core.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_invalid_regex_logs_warning(
        self, mock_factory: MagicMock, mock_pool: MagicMock, tmp_path: Any
    ) -> None:
        stats_dir = tmp_path / "stats"
        stats_dir.mkdir()

        config = FakeStatConfig(name=r"[invalid", is_regex=True)
        scanned = [FakeScannedVar(name="something")]

        strategy = MagicMock()
        strategy.get_work_items.return_value = [MagicMock()]
        mock_factory.create.return_value = strategy

        pool_instance = MagicMock()
        pool_instance.submit_batch_async.return_value = [MagicMock()]
        mock_pool.get_instance.return_value = pool_instance

        # Should not crash — just log warning
        Gem5Parser.submit_parse_async(
            str(stats_dir),
            "stats.txt",
            [config],  # type: ignore[list-item]
            str(tmp_path),
            scanned_vars=scanned,
        )


class TestFinalizeAndConstructCSV:
    """Test finalize_parsing and construct_final_csv branches."""

    @patch("src.core.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_finalize_empty_results(self, mock_factory: MagicMock, tmp_path: Any) -> None:
        result = Gem5Parser.finalize_parsing(str(tmp_path), [])
        assert result is None

    def test_construct_csv_empty(self, tmp_path: Any) -> None:
        result = Gem5Parser.construct_final_csv(str(tmp_path), [])
        assert result is None

    def test_construct_csv_with_entries(self, tmp_path: Any) -> None:
        stat = FakeStat(entries=["0", "1"], reduced_content={"0": 10, "1": 20})
        results = [{"ipc": stat}]

        path = Gem5Parser.construct_final_csv(str(tmp_path), results)
        assert path is not None
        assert os.path.exists(path)
        with open(path) as f:
            lines = f.readlines()
        assert "ipc..0" in lines[0]

    def test_construct_csv_scalar(self, tmp_path: Any) -> None:
        stat = FakeStat(entries=None, reduced_content="42")
        results = [{"cycles": stat}]

        path = Gem5Parser.construct_final_csv(str(tmp_path), results)
        assert path is not None
        with open(path) as f:
            lines = f.readlines()
        assert "cycles" in lines[0]

    def test_construct_csv_missing_var(self, tmp_path: Any) -> None:
        stat = FakeStat(entries=None, reduced_content="42")
        results = [{"cycles": stat}]

        path = Gem5Parser.construct_final_csv(
            str(tmp_path), results, var_names=["cycles", "missing_var"]
        )
        assert path is not None
        with open(path) as f:
            lines = f.readlines()
        # "NaN" should appear for missing var
        assert "NaN" in lines[1]

    def test_construct_csv_raw_data(self, tmp_path: Any) -> None:
        """Test with raw data that lacks balance_content — hits the else branch."""
        # Use a simple object that has entries (for header building)
        # but no balance_content (to hit the raw data branch)
        raw = MagicMock()
        raw.entries = None
        del raw.balance_content  # ensure hasattr(..., "balance_content") is False

        results = [{"benchmark": raw}]
        path = Gem5Parser.construct_final_csv(str(tmp_path), results)
        assert path is not None
        with open(path) as f:
            lines = f.readlines()
        assert "benchmark" in lines[0]
