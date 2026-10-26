"""Gem5 submission and typed finalization retain the exact scientific values."""

from src.core.models.source_evidence import ResolvedSourceKind


import csv
import math
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.models.parsing_models import ParseBatchResult, ScannedVariable, StatConfig
from src.core.models.parsing_models import SourceInstance
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsed_output_models import (
    ParsedCell,
    ParsedFileResult,
    ParsedOutput,
    ParsedVariableResult,
)
from tests.helpers.parsed_values import completed_future, numeric_file


class TestSubmitParseAsync:
    """Tests for Gem5Parser.submit_parse_async."""

    def test_raises_on_nonexistent_path(self, tmp_path: Path) -> None:
        bad_path = str(tmp_path / "nonexistent")
        with pytest.raises(FileNotFoundError, match="does not exist"):
            Gem5Parser.submit_parse_async(bad_path, "stats.txt", [], str(tmp_path / "out"))

    @patch("src.parsing.gem5.impl.gem5_parser.WorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_raises_when_no_work(
        self, mock_sf: MagicMock, mock_pool: MagicMock, tmp_path: Path
    ) -> None:
        """An empty work list must raise — an empty batch chained through
        finalize_parsing would let a whole parse run 'succeed' silently."""
        stats_dir = tmp_path / "data"
        stats_dir.mkdir()
        strategy = MagicMock()
        strategy.get_work_items.return_value = []
        mock_sf.create.return_value = strategy

        with pytest.raises(FileNotFoundError, match="No parse work generated"):
            Gem5Parser.submit_parse_async(
                str(stats_dir),
                "stats.txt",
                [StatConfig("simTicks", "scalar", params={"source_type": "scalar"})],
                str(tmp_path / "out"),
            )

    def test_raises_on_stats_free_directory(self, tmp_path: Path) -> None:
        """Same raise-if-empty contract as the scan path (real strategy)."""
        stats_dir = tmp_path / "data"
        stats_dir.mkdir()
        (stats_dir / "decoy.log").write_text("not a stats file\n")

        with pytest.raises(FileNotFoundError, match="No files matching"):
            Gem5Parser.submit_parse_async(
                str(stats_dir),
                "stats.txt",
                [StatConfig("simTicks", "scalar", params={"source_type": "scalar"})],
                str(tmp_path / "out"),
            )

    @patch("src.parsing.gem5.impl.gem5_parser.WorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_submits_work_and_returns_batch(
        self, mock_sf: MagicMock, mock_pool: MagicMock, tmp_path: Path
    ) -> None:
        stats_dir = tmp_path / "data"
        stats_dir.mkdir()

        strategy = MagicMock()
        sources = (str(stats_dir / "a.txt"), str(stats_dir / "b.txt"))
        work_items = [
            MagicMock(
                source_path=source,
                return_value=numeric_file(source, {"system.cpu.ipc": 2.1, "simTicks": 100.0}),
            )
            for source in sources
        ]
        strategy.get_work_items.return_value = work_items
        mock_sf.create.return_value = strategy

        pool_inst = MagicMock()
        pool_inst.submit_many.side_effect = lambda tasks: [
            completed_future(task()) for task in tasks
        ]
        mock_pool.get_instance.return_value = pool_inst

        variables = [
            StatConfig(name="system.cpu.ipc", type="scalar", params={"source_type": "scalar"}),
            StatConfig(name="simTicks", type="scalar", params={"source_type": "scalar"}),
        ]

        result = Gem5Parser.submit_parse_async(
            str(stats_dir), "stats.txt", variables, str(tmp_path / "out")
        )

        assert isinstance(result, ParseBatchResult)
        assert result.var_names == ("system.cpu.ipc", "simTicks")
        assert result.source_paths == sources
        assert result.futures[0].result().variables[0].cells[0].value == 2.1
        assert len(result.futures) == 2

    @patch("src.parsing.gem5.impl.gem5_parser.WorkPool")
    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_regex_expansion_with_scanned_vars(
        self, mock_sf: MagicMock, mock_pool: MagicMock, tmp_path: Path
    ) -> None:
        stats_dir = tmp_path / "data"
        stats_dir.mkdir()

        strategy = MagicMock()
        source = str(stats_dir / "stats.txt")
        strategy.get_work_items.return_value = [
            MagicMock(
                source_path=source,
                return_value=numeric_file(source, {r"system\.cpu\d+\.ipc": 2.5}),
            )
        ]
        mock_sf.create.return_value = strategy

        pool_inst = MagicMock()
        pool_inst.submit_many.side_effect = lambda tasks: [
            completed_future(task()) for task in tasks
        ]
        mock_pool.get_instance.return_value = pool_inst

        # A regex variable with scanned matches
        variables = [
            StatConfig(
                name="system\\.cpu\\d+\\.ipc",
                type="scalar",
                is_regex=True,
                params={"source_type": "scalar"},
            )
        ]

        scanned = [
            ScannedVariable(
                name=r"system\.cpu\d+\.ipc",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(
                    SourceInstance("system.cpu0.ipc", ("0",)),
                    SourceInstance("system.cpu1.ipc", ("1",)),
                ),
            )
        ]

        Gem5Parser.submit_parse_async(
            str(stats_dir),
            "stats.txt",
            variables,
            str(tmp_path / "out"),
            scanned_vars=scanned,
        )

        plan = strategy.get_work_items.call_args.args[2]
        assert tuple(plan.routes) == ("system.cpu0.ipc", "system.cpu1.ipc")
        assert all(
            tuple(target.output_name for target in route.targets) == (r"system\.cpu\d+\.ipc",)
            for route in plan.routes.values()
        )
        assert plan.accumulators[0].config.params == {"source_type": "scalar"}


def _finalize(
    root: Path,
    names: tuple[str, ...],
    sources: tuple[str, ...],
    records: list[ParsedFileResult],
) -> ParsedOutput:
    batch = ParseBatchResult(tuple(Future() for _ in sources), names, sources, str(root), "simple")
    return Gem5Parser.finalize_parsing(batch, records)


def _entries(name: str, values: dict[str, float]) -> ParsedVariableResult:
    return ParsedVariableResult(
        name,
        "number",
        "entries",
        tuple(ParsedCell(f"{name}..{entry}", "number", value) for entry, value in values.items()),
    )


class TestFinalizeParsing:
    """Finalization accepts a submitted plan and finalized typed cells."""

    def test_empty_results_reject_before_publication(self, tmp_path: Path) -> None:
        target = tmp_path / "results.csv"
        target.write_bytes(b"previous-output\n")
        with pytest.raises(ValueError, match="non-empty file result"):
            _finalize(tmp_path, ("a",), ("source",), [])
        assert target.read_bytes() == b"previous-output\n"

    def test_delegates_to_strategy_and_csv(self, tmp_path: Path) -> None:
        record = numeric_file("source", {"a": 1.0})
        batch = ParseBatchResult(
            (completed_future(record),), ("a",), ("source",), str(tmp_path), "simple"
        )
        with (
            patch(
                "src.parsing.gem5.impl.gem5_parser.ParsedOutputIO.resolve",
                wraps=ParsedOutputIO.resolve,
            ) as resolve,
            patch(
                "src.parsing.gem5.impl.gem5_parser.ParsedOutputIO.publish",
                wraps=ParsedOutputIO.publish,
            ) as publish,
        ):
            output = Gem5Parser.finalize_parsing(batch, [record])
        resolve.assert_called_once_with(
            [record], batch.var_names, batch.source_paths, complete=True
        )
        publish.assert_called_once()
        assert output.csv_path == str(tmp_path / "results.csv")
        assert ParsedOutputIO.to_frame(output).to_dict("list") == {"a": [1.0]}


class TestConstructFinalCsv:
    """CSV shape, values and missingness come from the declared typed records."""

    def test_missing_batch_context_rejects_before_publication(self, tmp_path: Path) -> None:
        with pytest.raises(TypeError, match="exact ParseBatchResult"):
            Gem5Parser.finalize_parsing(str(tmp_path), [])  # type: ignore[arg-type]
        assert not (tmp_path / "results.csv").exists()

    def test_scalar_variables(self, tmp_path: Path) -> None:
        records = [
            numeric_file("source-a", {"ipc": 2.1, "cpi": 0.48}),
            numeric_file("source-b", {"ipc": 1.9, "cpi": 0.53}),
        ]
        output = _finalize(tmp_path, ("ipc", "cpi"), ("source-a", "source-b"), records)
        assert Path(output.csv_path).is_file()
        with open(output.csv_path, newline="") as stream:
            reader = csv.reader(stream)
            assert next(reader) == ["ipc", "cpi"]
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0] == ["2.1", "0.48"]
            assert rows[1] == ["1.9", "0.53"]
        assert ParsedOutputIO.to_frame(output).to_dict("list") == {
            "ipc": [2.1, 1.9],
            "cpi": [0.48, 0.53],
        }

    def test_vector_variables(self, tmp_path: Path) -> None:
        record = ParsedFileResult("source", (_entries("cache_miss", {"l1": 0.05, "l2": 0.12}),))
        output = _finalize(tmp_path, ("cache_miss",), ("source",), [record])
        with open(output.csv_path, newline="") as stream:
            reader = csv.reader(stream)
            assert next(reader) == ["cache_miss..l1", "cache_miss..l2"]
            assert next(reader) == ["0.05", "0.12"]
        assert ParsedOutputIO.to_frame(output).to_dict("list") == {
            "cache_miss..l1": [0.05],
            "cache_miss..l2": [0.12],
        }

    def test_mixed_stat_types(self, tmp_path: Path) -> None:
        point = numeric_file("source", {"ipc": 2.1}).variables[0]
        record = ParsedFileResult("source", (point, _entries("cache", {"l1": 0.05, "l2": 0.12})))
        output = _finalize(tmp_path, ("ipc", "cache"), ("source",), [record])
        with open(output.csv_path, newline="") as stream:
            reader = csv.reader(stream)
            assert next(reader) == ["ipc", "cache..l1", "cache..l2"]
            assert next(reader) == ["2.1", "0.05", "0.12"]

    def test_var_names_ordering(self, tmp_path: Path) -> None:
        output = _finalize(
            tmp_path,
            ("a_var", "b_var"),
            ("source",),
            [numeric_file("source", {"b_var": 2.0, "a_var": 1.0})],
        )
        assert ParsedOutputIO.to_frame(output).columns.tolist() == ["a_var", "b_var"]
        assert ParsedOutputIO.to_frame(output).to_dict("list") == {"a_var": [1.0], "b_var": [2.0]}

    def test_missing_var_fills_nan(self, tmp_path: Path) -> None:
        """An explicitly missing measurement remains NaN rather than a fabricated zero."""
        record = ParsedFileResult(
            "source",
            (
                numeric_file("source", {"ipc": 2.1}).variables[0],
                ParsedVariableResult(
                    "missing_var",
                    "number",
                    "scalar",
                    (ParsedCell("missing_var", "number", math.nan),),
                    missing_measurements=1,
                ),
            ),
        )
        output = _finalize(tmp_path, ("ipc", "missing_var"), ("source",), [record])
        with open(output.csv_path, newline="") as stream:
            reader = csv.reader(stream)
            assert next(reader) == ["ipc", "missing_var"]
            assert next(reader) == ["2.1", "NaN"]
        frame = ParsedOutputIO.to_frame(output)
        assert frame["ipc"].tolist() == [2.1]
        assert math.isnan(float(frame["missing_var"].iloc[0]))
        assert ParsedOutputIO.read(output).missing_variables == ("missing_var",)

    def test_output_dir_created(self, tmp_path: Path) -> None:
        output = _finalize(
            tmp_path / "deep" / "nesting", ("x",), ("source",), [numeric_file("source", {"x": 1.0})]
        )
        assert Path(output.csv_path).is_file()
        assert ParsedOutputIO.to_frame(output).to_dict("list") == {"x": [1.0]}
