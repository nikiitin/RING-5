"""The incremental contract publishes typed partial rows without promoting their cache."""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.application_api import ApplicationAPI
from src.core.common.input_identity import fingerprint_inputs
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsed_output_models import ParsedFileResult, ParsedOutput
from src.core.models.parsing_models import IncrementalParseBatchResult, IncrementalParseResult
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.parser_protocol import SimulationParser
from tests.helpers.parsed_values import numeric_file, numeric_output


def _batch(root: Path) -> tuple[IncrementalParseBatchResult, dict[str, Path]]:
    sources = {}
    for name, value in [("cached", 100), ("accepted", 200), ("failed", 300)]:
        source = root / "inputs" / name / "stats.txt"
        source.parent.mkdir(parents=True)
        source.write_text(f"simTicks {value}\n", encoding="utf-8")
        sources[name] = source.resolve()
    output = root / "output"
    output.mkdir()
    (output / "results.csv").write_bytes(b"previous-output\n")
    cache = root / "cache.json"
    cache.write_bytes(b"previous-success-cache\n")
    return (
        IncrementalParseBatchResult(
            futures=(Future(), Future()),
            var_names=("simTicks",),
            output_dir=str(output),
            strategy_type="simple",
            cache_path=str(cache),
            configuration_hash="a" * 64,
            fingerprints=fingerprint_inputs([str(path) for path in sources.values()], "simple"),
            cached_results=(numeric_file(str(sources["cached"]), {"simTicks": 100.0}),),
            changed_files=(str(sources["accepted"]), str(sources["failed"])),
            removed_files=(),
        ),
        sources,
    )


def _row(source: Path, value: float) -> ParsedFileResult:
    return numeric_file(str(source), {"simTicks": value})


def _values(output: ParsedOutput) -> list[float]:
    return sorted(ParsedOutputIO.to_frame(output)["simTicks"].tolist())


@pytest.mark.parametrize("complete", [True, False])
def test_complete_mode_alone_promotes_the_cache(tmp_path: Path, complete: bool) -> None:
    batch, sources = _batch(tmp_path)
    before = Path(batch.cache_path).read_bytes()
    result = Gem5Parser.finalize_incremental_parsing(
        batch, [_row(sources["accepted"], 200.0), _row(sources["failed"], 300.0)], complete=complete
    )
    assert _values(result.output) == [100.0, 200.0, 300.0]
    assert (result.parsed_files, result.reused_files, result.removed_files, result.total_files) == (
        2,
        1,
        0,
        3,
    )
    assert (Path(batch.cache_path).read_bytes() != before) is complete


@pytest.mark.parametrize("accepted", [True, False])
def test_partial_mode_retains_reused_rows_and_reports_the_planned_total(
    tmp_path: Path, accepted: bool
) -> None:
    batch, sources = _batch(tmp_path)
    before = Path(batch.cache_path).read_bytes()
    results = [_row(sources["accepted"], 200.0)] if accepted else []
    result = Gem5Parser.finalize_incremental_parsing(batch, results, complete=False)
    assert _values(result.output) == ([100.0, 200.0] if accepted else [100.0])
    assert result.parsed_files == int(accepted)
    assert (result.reused_files, result.total_files) == (1, 3)
    assert Path(batch.cache_path).read_bytes() == before


@pytest.mark.parametrize("complete", [True, False])
@pytest.mark.parametrize("failure", ["missing", "duplicate", "unplanned", "changed"])
def test_invalid_provenance_preserves_output_and_cache(
    tmp_path: Path, complete: bool, failure: str
) -> None:
    batch, sources = _batch(tmp_path)
    results: list[Any] = [_row(sources["accepted"], 200.0), _row(sources["failed"], 300.0)]
    error: type[Exception] = ValueError
    message = "[Dd]uplicate|[Uu]nplanned"
    if failure == "missing":
        results[0] = {"simTicks": 200.0}
        error, message = TypeError, "ParsedFileResult"
    elif failure == "duplicate":
        results[1] = results[0]
    elif failure == "unplanned":
        results[0] = _row(tmp_path / "unplanned.txt", 100.0)
    else:
        sources["accepted"].write_text("simTicks 999\n", encoding="utf-8")
        error, message = RuntimeError, "inputs changed"
    output = Path(batch.output_dir) / "results.csv"
    before = output.read_bytes(), Path(batch.cache_path).read_bytes()
    with pytest.raises(error, match=message):
        Gem5Parser.finalize_incremental_parsing(batch, results, complete=complete)
    assert (output.read_bytes(), Path(batch.cache_path).read_bytes()) == before


def test_default_complete_and_empty_partial_fail_before_publication(tmp_path: Path) -> None:
    batch, sources = _batch(tmp_path)
    output = Path(batch.output_dir) / "results.csv"
    before = output.read_bytes(), Path(batch.cache_path).read_bytes()
    with pytest.raises(ValueError, match="cover every planned source"):
        Gem5Parser.finalize_incremental_parsing(batch, [_row(sources["accepted"], 200.0)])
    all_changed = replace(
        batch,
        cached_results=(),
        changed_files=tuple(path for path, _digest in batch.fingerprints),
        futures=tuple(Future() for _ in batch.fingerprints),
    )
    with pytest.raises(ValueError, match="non-empty file result"):
        Gem5Parser.finalize_incremental_parsing(all_changed, [], complete=False)
    assert (output.read_bytes(), Path(batch.cache_path).read_bytes()) == before


@pytest.mark.parametrize("complete", [None, 1, "partial"])
def test_completion_mode_requires_an_actual_boolean(tmp_path: Path, complete: Any) -> None:
    batch, _ = _batch(tmp_path)
    with pytest.raises(TypeError, match="completion mode must be a boolean"):
        Gem5Parser.finalize_incremental_parsing(batch, [], complete=complete)


@pytest.mark.parametrize("complete", [True, False])
def test_background_adapter_uses_the_same_injected_backend_contract(
    tmp_path: Path, complete: bool
) -> None:
    batch, _ = _batch(tmp_path)
    parser = MagicMock(spec=SimulationParser)
    output = numeric_output(tmp_path / "published.csv", {"simTicks": 100.0})
    parser.finalize_incremental_parsing.return_value = IncrementalParseResult(output, 0, 1, 0, 3)
    api = ApplicationAPI(parser=parser)
    try:
        assert api._finalize_background_parse(batch, [], complete) is output
        assert _values(output) == [100.0]
        parser.finalize_incremental_parsing.assert_called_once_with(batch, [], complete=complete)
        parser.finalize_parsing.assert_not_called()
    finally:
        api.close(wait=True)
