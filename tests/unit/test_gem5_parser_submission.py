"""Submission resolves explicit sources before pool allocation; finalization preserves lifecycle."""

import os
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.models.parsing_models import ScannedVariable, SourceInstance, StatConfig
from src.parsing.gem5.impl.gem5_parser import Gem5Parser


@dataclass
class FakeStat:
    entries: list[str] | None = None
    reduced_content: Any = None

    def balance_content(self) -> None:
        pass

    def reduce_duplicates(self) -> None:
        pass


@pytest.mark.parametrize("keep", [False, True])
def test_submission_passes_one_resolved_plan_and_exact_output_names(tmp_path, keep):
    config = StatConfig(
        "IPC",
        "scalar",
        source_name=r"cpu\d+.ipc",
        is_regex=True,
        keep_indices=keep,
        params={"source_type": "scalar", "selected_sources": ["cpu1.ipc"]},
    )
    metadata = [
        ScannedVariable(
            r"cpu\d+.ipc",
            "vector",
            [],
            source_type="scalar",
            instances=(SourceInstance("cpu0.ipc", ("0",)), SourceInstance("cpu1.ipc", ("1",))),
        )
    ]
    with (
        patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory") as factory,
        patch("src.parsing.gem5.impl.gem5_parser.WorkPool") as pool,
    ):
        strategy = factory.create.return_value
        strategy.get_work_items.return_value = [MagicMock()]
        pool.get_instance.return_value.submit_many.return_value = [MagicMock()]
        batch = Gem5Parser.submit_parse_async(
            str(tmp_path), "stats.txt", [config], str(tmp_path / "out"), scanned_vars=metadata
        )
        plan = strategy.get_work_items.call_args.args[2]
        assert set(plan.routes) == {"cpu1.ipc"}
        assert plan.accumulators[0].config == config
        assert batch.var_names == (["cpu1.ipc"] if keep else ["IPC"])
        pool.get_instance.return_value.submit_many.assert_called_once()


@pytest.mark.parametrize("configs, message", [([], "at least one"), ([{}], "StatConfig")])
def test_invalid_runnable_input_rejects_before_pool(tmp_path, configs, message):
    with patch("src.parsing.gem5.impl.gem5_parser.WorkPool") as pool:
        with pytest.raises((ValueError, TypeError), match=message):
            Gem5Parser.submit_parse_async(
                str(tmp_path), "stats.txt", configs, str(tmp_path / "out")
            )
        pool.get_instance.assert_not_called()


def test_missing_pattern_sources_reject_before_strategy_or_pool(tmp_path):
    with (
        patch("src.parsing.gem5.impl.gem5_parser.WorkPool") as pool,
        patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory") as factory,
    ):
        with pytest.raises(ValueError, match="source records"):
            Gem5Parser.submit_parse_async(
                str(tmp_path),
                "stats.txt",
                [StatConfig(r"cpu\d+.ipc", "scalar", params={"source_type": "scalar"})],
                str(tmp_path / "out"),
            )
        pool.get_instance.assert_not_called()
        factory.create.assert_not_called()


def test_empty_strategy_work_raises(tmp_path):
    with patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory") as factory:
        factory.create.return_value.get_work_items.return_value = []
        with pytest.raises(FileNotFoundError, match="No parse work generated"):
            Gem5Parser.submit_parse_async(
                str(tmp_path),
                "stats.txt",
                [StatConfig("ipc", "scalar", params={"source_type": "scalar"})],
                str(tmp_path / "out"),
            )


class TestFinalizeAndConstructCSV:
    """Test finalize_parsing and construct_final_csv branches."""

    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
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
