"""Submission owns exact sources and typed finalization preserves values and missingness."""

import csv
import math
from concurrent.futures import Future
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsed_output_models import ParsedCell, ParsedFileResult, ParsedVariableResult
from src.core.models.parsing_models import (
    ParseBatchResult,
    ScannedVariable,
    SourceInstance,
    StatConfig,
)
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from tests.helpers.parsed_values import completed_future, numeric_file


def _batch(root: Path, names: tuple[str, ...]) -> ParseBatchResult:
    return ParseBatchResult((Future(),), names, ("source",), str(root), "simple")


@pytest.mark.parametrize("keep", [False, True])
def test_submission_passes_one_resolved_plan_and_exact_output_names(
    tmp_path: Path, keep: bool
) -> None:
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
    source = str(tmp_path / "stats.txt")
    name = "cpu1.ipc" if keep else "IPC"
    result = numeric_file(source, {name: 1.25})
    work = MagicMock(source_path=source, return_value=result)
    with (
        patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory") as factory,
        patch("src.parsing.gem5.impl.gem5_parser.WorkPool") as pool,
    ):
        strategy = factory.create.return_value
        strategy.get_work_items.return_value = [work]
        pool.get_instance.return_value.submit_many.side_effect = lambda tasks: [
            completed_future(task()) for task in tasks
        ]
        batch = Gem5Parser.submit_parse_async(
            str(tmp_path), "stats.txt", [config], str(tmp_path / "out"), scanned_vars=metadata
        )
        plan = strategy.get_work_items.call_args.args[2]
        assert set(plan.routes) == {"cpu1.ipc"}
        assert plan.accumulators[0].config == config
        assert batch.var_names == (name,)
        assert batch.source_paths == (source,)
        assert batch.futures[0].result() == result
        pool.get_instance.return_value.submit_many.assert_called_once()


@pytest.mark.parametrize("configs, message", [([], "at least one"), ([{}], "StatConfig")])
def test_invalid_runnable_input_rejects_before_pool(
    tmp_path: Path, configs: Any, message: str
) -> None:
    with patch("src.parsing.gem5.impl.gem5_parser.WorkPool") as pool:
        with pytest.raises((ValueError, TypeError), match=message):
            Gem5Parser.submit_parse_async(
                str(tmp_path), "stats.txt", configs, str(tmp_path / "out")
            )
        pool.get_instance.assert_not_called()


def test_missing_pattern_sources_reject_before_strategy_or_pool(tmp_path: Path) -> None:
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


def test_empty_strategy_work_raises(tmp_path: Path) -> None:
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
    """The submitted plan and finalized cells are the single CSV publication input."""

    def test_finalize_empty_results(self, tmp_path: Path) -> None:
        target = tmp_path / "results.csv"
        target.write_bytes(b"previous-output\n")
        with pytest.raises(ValueError, match="non-empty file result"):
            Gem5Parser.finalize_parsing(_batch(tmp_path, ("x",)), [])
        assert target.read_bytes() == b"previous-output\n"

    def test_construct_csv_empty(self, tmp_path: Path) -> None:
        with pytest.raises(TypeError, match="exact ParseBatchResult"):
            Gem5Parser.finalize_parsing(str(tmp_path), [])  # type: ignore[arg-type]
        assert not (tmp_path / "results.csv").exists()

    def test_construct_csv_with_entries(self, tmp_path: Path) -> None:
        record = ParsedFileResult(
            "source",
            (
                ParsedVariableResult(
                    "ipc",
                    "number",
                    "entries",
                    (ParsedCell("ipc..0", "number", 10.0), ParsedCell("ipc..1", "number", 20.0)),
                ),
            ),
        )
        output = Gem5Parser.finalize_parsing(_batch(tmp_path, ("ipc",)), [record])
        assert Path(output.csv_path).is_file()
        with open(output.csv_path, newline="") as stream:
            rows = list(csv.reader(stream))
        assert rows == [["ipc..0", "ipc..1"], ["10.0", "20.0"]]
        assert ParsedOutputIO.to_frame(output).to_dict("list") == {
            "ipc..0": [10.0],
            "ipc..1": [20.0],
        }

    def test_construct_csv_scalar(self, tmp_path: Path) -> None:
        output = Gem5Parser.finalize_parsing(
            _batch(tmp_path, ("cycles",)), [numeric_file("source", {"cycles": 42.0})]
        )
        assert ParsedOutputIO.to_frame(output).to_dict("list") == {"cycles": [42.0]}

    def test_construct_csv_missing_var(self, tmp_path: Path) -> None:
        record = ParsedFileResult(
            "source",
            (
                ParsedVariableResult(
                    "cycles", "number", "scalar", (ParsedCell("cycles", "number", 42.0),)
                ),
                ParsedVariableResult(
                    "missing_var",
                    "number",
                    "scalar",
                    (ParsedCell("missing_var", "number", math.nan),),
                    missing_measurements=1,
                ),
            ),
        )
        output = Gem5Parser.finalize_parsing(_batch(tmp_path, ("cycles", "missing_var")), [record])
        frame = ParsedOutputIO.to_frame(output)
        assert frame["cycles"].tolist() == [42.0]
        assert math.isnan(float(frame["missing_var"].iloc[0]))
        assert ParsedOutputIO.read(output).missing_variables == ("missing_var",)

    def test_construct_csv_raw_data(self, tmp_path: Path) -> None:
        """An object without a typed declaration never becomes a success row."""
        raw: list[Any] = [{"benchmark": MagicMock()}]
        with pytest.raises(TypeError, match="ParsedFileResult"):
            Gem5Parser.finalize_parsing(_batch(tmp_path, ("benchmark",)), raw)
        assert not (tmp_path / "results.csv").exists()
