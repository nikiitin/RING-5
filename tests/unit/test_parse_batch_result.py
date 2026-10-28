"""Each asynchronous parse batch owns its immutable variable, source and output plan."""

from concurrent.futures import Future
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsing_models import ParseBatchResult, StatConfig
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from tests.helpers.parsed_values import completed_future, numeric_file


class TestParseBatchResult:
    """The batch validates its complete plan before work can be finalized."""

    def test_frozen_dataclass(self) -> None:
        batch = ParseBatchResult((Future(),), ("a",), ("source",), "output", "simple")
        with pytest.raises(AttributeError):
            batch.var_names = ("b",)  # type: ignore[misc]

    def test_stores_futures_and_var_names(self) -> None:
        result = numeric_file("source", {"system.cpu.ipc": 2.5})
        future = completed_future(result)
        batch = ParseBatchResult((future,), ("system.cpu.ipc",), ("source",), "out", "simple")
        assert len(batch.futures) == 1
        assert batch.futures[0].result() == result
        assert batch.var_names == ("system.cpu.ipc",)
        assert batch.source_paths == ("source",)
        assert batch.output_dir == "out" and batch.strategy_type == "simple"

    def test_empty_batch(self) -> None:
        with pytest.raises(ValueError, match="non-empty plan"):
            ParseBatchResult((), (), (), "out", "simple")


class TestSubmitParseAsyncReturnType:
    """Submission transports typed values under the exact source and variable plan."""

    @patch("src.parsing.gem5.impl.gem5_parser.WorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_gem5_parser_returns_batch_result(
        self, factory: MagicMock, pool: MagicMock, tmp_path: Path
    ) -> None:
        names = ("system.cpu.ipc", "system.cpu.numCycles")
        source = str(tmp_path / "stats.txt")
        Path(source).write_text(f"{names[0]} 2.5\n{names[1]} 100.0\n", encoding="utf-8")
        record = numeric_file(source, {names[0]: 2.5, names[1]: 100.0})
        factory.create.return_value.metadata_columns = ()
        factory.create.return_value.get_work_items.return_value = [
            MagicMock(source_path=source, return_value=record)
        ]
        pool.get_instance.return_value.submit_many.side_effect = lambda tasks: [
            completed_future(task()) for task in tasks
        ]
        result = Gem5Parser.submit_parse_async(
            str(tmp_path),
            "stats.txt",
            [StatConfig(name, "scalar", params={"source_type": "scalar"}) for name in names],
            str(tmp_path / "out"),
        )
        assert isinstance(result, ParseBatchResult)
        assert result.var_names == names
        assert len(result.futures) == 1
        assert result.source_paths == (source,)
        assert result.futures[0].result() == record

    @patch("src.parsing.gem5.impl.gem5_parser.WorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_empty_work_raises(self, factory: MagicMock, pool: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "stats.txt").write_text("test 1.0\n", encoding="utf-8")
        factory.create.return_value.metadata_columns = ()
        factory.create.return_value.get_work_items.return_value = []
        with pytest.raises(
            FileNotFoundError, match="strategy generated no work for selected sources"
        ):
            Gem5Parser.submit_parse_async(
                str(tmp_path),
                "stats.txt",
                [StatConfig("test", "scalar", params={"source_type": "scalar"})],
                str(tmp_path / "out"),
            )
        pool.get_instance.assert_not_called()


class TestConstructFinalCsvVarNames:
    """Finalization uses the submitted variable order without recovering hidden state."""

    def test_var_names_parameter_controls_column_order(self, tmp_path: Path) -> None:
        record = numeric_file("source", {"var_b": 200.0, "var_a": 100.0})
        batch = ParseBatchResult(
            (completed_future(record),), ("var_a", "var_b"), ("source",), str(tmp_path), "simple"
        )
        output = Gem5Parser.finalize_parsing(batch, [record])
        frame = ParsedOutputIO.to_frame(output)
        assert frame.columns.tolist() == ["var_a", "var_b"]
        assert frame.to_dict("list") == {"var_a": [100.0], "var_b": [200.0]}
        assert Path(output.csv_path).read_text().splitlines()[0] == "var_a,var_b"

    def test_missing_variable_plan_rejects_without_inference(self, tmp_path: Path) -> None:
        """An absent variable plan is rejected rather than inferred from a row."""
        record = numeric_file("source", {"only_var": 42.0})
        with pytest.raises(TypeError, match="immutable tuple"):
            ParseBatchResult(
                (completed_future(record),),
                cast(tuple[str, ...], None),
                ("source",),
                str(tmp_path),
                "simple",
            )
        assert not (tmp_path / "results.csv").exists()


class TestBatchIsolation:
    """Concurrent batches retain their own variable names, values and destinations."""

    @patch("src.parsing.gem5.impl.gem5_parser.WorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_concurrent_batches_have_independent_var_names(
        self, factory: MagicMock, pool: MagicMock, tmp_path: Path
    ) -> None:
        source = str(tmp_path / "stats.txt")
        Path(source).write_text("var_alpha 1.25\nvar_beta 2.5\nvar_gamma 0.0\n", encoding="utf-8")
        factory.create.return_value.metadata_columns = ()
        first = numeric_file(source, {"var_alpha": 1.25})
        second = numeric_file(source, {"var_beta": 2.5, "var_gamma": 0.0})
        factory.create.return_value.get_work_items.side_effect = [
            [MagicMock(source_path=source, return_value=record)] for record in (first, second)
        ]
        pool.get_instance.return_value.submit_many.side_effect = lambda tasks: [
            completed_future(task()) for task in tasks
        ]
        batch1 = Gem5Parser.submit_parse_async(
            str(tmp_path),
            "stats.txt",
            [StatConfig("var_alpha", "scalar", params={"source_type": "scalar"})],
            str(tmp_path / "out1"),
        )
        batch2 = Gem5Parser.submit_parse_async(
            str(tmp_path),
            "stats.txt",
            [
                StatConfig(name, "scalar", params={"source_type": "scalar"})
                for name in ("var_beta", "var_gamma")
            ],
            str(tmp_path / "out2"),
        )
        assert batch1.var_names == ("var_alpha",)
        assert batch2.var_names == ("var_beta", "var_gamma")
        assert set(batch1.var_names).isdisjoint(batch2.var_names)
        output1 = Gem5Parser.finalize_parsing(batch1, [batch1.futures[0].result()])
        output2 = Gem5Parser.finalize_parsing(batch2, [batch2.futures[0].result()])
        assert output1.csv_path != output2.csv_path
        assert ParsedOutputIO.to_frame(output1).to_dict("list") == {"var_alpha": [1.25]}
        assert ParsedOutputIO.to_frame(output2).to_dict("list") == {
            "var_beta": [2.5],
            "var_gamma": [0.0],
        }
