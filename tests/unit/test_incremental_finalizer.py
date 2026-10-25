"""The current incremental contract publishes partial rows without cache promotion."""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.application_api import ApplicationAPI
from src.core.common.input_identity import fingerprint_inputs
from src.core.models.parsing_models import IncrementalParseBatchResult, IncrementalParseResult
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.impl.strategies.file_parser_strategy import INTERNAL_SIM_PATH_KEY
from src.parsing.parser_protocol import SimulationParser


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
            futures=[],
            var_names=["simTicks"],
            output_dir=str(output),
            strategy_type="simple",
            cache_path=str(cache),
            configuration_hash="a" * 64,
            fingerprints=fingerprint_inputs([str(path) for path in sources.values()], "simple"),
            cached_rows=((str(sources["cached"]), (("simTicks", "100"),)),),
            changed_files=(str(sources["accepted"]), str(sources["failed"])),
            removed_files=(),
        ),
        sources,
    )


def _row(source: Path, value: str) -> dict[str, Any]:
    return {INTERNAL_SIM_PATH_KEY: str(source), "simTicks": value}


def _values(path: str) -> list[str]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return sorted(row["simTicks"] for row in csv.DictReader(handle))


@pytest.mark.parametrize("complete", [True, False])
def test_complete_mode_alone_promotes_the_cache(tmp_path, complete):
    batch, sources = _batch(tmp_path)
    before = Path(batch.cache_path).read_bytes()
    result = Gem5Parser.finalize_incremental_parsing(
        batch, [_row(sources["accepted"], "200"), _row(sources["failed"], "300")], complete=complete
    )
    assert _values(result.csv_path) == ["100", "200", "300"]
    assert (result.parsed_files, result.reused_files, result.removed_files, result.total_files) == (
        2,
        1,
        0,
        3,
    )
    assert (Path(batch.cache_path).read_bytes() != before) is complete


@pytest.mark.parametrize("accepted", [True, False])
def test_partial_mode_retains_reused_rows_and_reports_the_planned_total(tmp_path, accepted):
    batch, sources = _batch(tmp_path)
    before = Path(batch.cache_path).read_bytes()
    results = [_row(sources["accepted"], "200")] if accepted else []
    result = Gem5Parser.finalize_incremental_parsing(batch, results, complete=False)
    assert _values(result.csv_path) == (["100", "200"] if accepted else ["100"])
    assert result.parsed_files == int(accepted)
    assert (result.reused_files, result.total_files) == (1, 3)
    assert Path(batch.cache_path).read_bytes() == before


@pytest.mark.parametrize("complete", [True, False])
@pytest.mark.parametrize("failure", ["missing", "duplicate", "unplanned", "changed"])
def test_invalid_provenance_preserves_output_and_cache(tmp_path, complete, failure):
    batch, sources = _batch(tmp_path)
    results = [_row(sources["accepted"], "200"), _row(sources["failed"], "300")]
    if failure == "missing":
        results[0].pop(INTERNAL_SIM_PATH_KEY)
    elif failure == "duplicate":
        results[1] = results[0].copy()
    elif failure == "unplanned":
        results[0] = _row(sources["cached"], "100")
    else:
        sources["accepted"].write_text("simTicks 999\n", encoding="utf-8")
    output = Path(batch.output_dir) / "results.csv"
    before = output.read_bytes(), Path(batch.cache_path).read_bytes()
    with pytest.raises(RuntimeError, match="provenance|duplicate|unplanned|inputs changed"):
        Gem5Parser.finalize_incremental_parsing(batch, results, complete=complete)
    assert (output.read_bytes(), Path(batch.cache_path).read_bytes()) == before


def test_default_complete_and_empty_partial_fail_before_publication(tmp_path):
    batch, sources = _batch(tmp_path)
    output = Path(batch.output_dir) / "results.csv"
    before = output.read_bytes(), Path(batch.cache_path).read_bytes()
    with pytest.raises(RuntimeError, match="1 results for 2 changed files"):
        Gem5Parser.finalize_incremental_parsing(batch, [_row(sources["accepted"], "200")])
    with pytest.raises(RuntimeError, match="no usable rows"):
        Gem5Parser.finalize_incremental_parsing(replace(batch, cached_rows=()), [], complete=False)
    assert (output.read_bytes(), Path(batch.cache_path).read_bytes()) == before


@pytest.mark.parametrize("complete", [None, 1, "partial"])
def test_completion_mode_requires_an_actual_boolean(tmp_path, complete):
    batch, _ = _batch(tmp_path)
    with pytest.raises(TypeError, match="completion mode must be a boolean"):
        Gem5Parser.finalize_incremental_parsing(batch, [], complete=complete)


@pytest.mark.parametrize("complete", [True, False])
def test_background_adapter_uses_the_same_injected_backend_contract(tmp_path, complete):
    batch, _ = _batch(tmp_path)
    parser = MagicMock(spec=SimulationParser)
    parser.finalize_incremental_parsing.return_value = IncrementalParseResult(
        "output.csv", 0, 1, 0, 3
    )
    api = ApplicationAPI()
    api._parser = parser
    try:
        assert (
            api._finalize_background_parse(batch.output_dir, batch, [], complete, "simple")
            == "output.csv"
        )
        parser.finalize_incremental_parsing.assert_called_once_with(batch, [], complete=complete)
        parser.finalize_parsing.assert_not_called()
    finally:
        api.close(wait=True)
