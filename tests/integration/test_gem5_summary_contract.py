"""Real worker contracts for literal source names and summary entries."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.core.models import StatConfig
from src.parsing.gem5.impl.gem5_parser import Gem5Parser

pytestmark = pytest.mark.xdist_group("perl_pool")


def _parse(root: Path, text: str, configs: list[StatConfig]) -> dict[str, str]:
    (root / "stats.txt").write_text(text, encoding="utf-8")
    batch = Gem5Parser.submit_parse_async(str(root), "stats.txt", configs, str(root / "out"))
    output = Gem5Parser.finalize_parsing(
        str(root / "out"),
        [future.result(timeout=30) for future in batch.futures],
        var_names=batch.var_names,
    )
    assert output is not None
    with Path(output).open(encoding="utf-8", newline="") as stream:
        return next(csv.DictReader(stream))


@pytest.mark.parametrize("kind", ["scalar", "vector"])
def test_literal_summary_suffix_names_keep_their_source_identity(tmp_path: Path, kind: str) -> None:
    # [test->req~ring5.ingestion.parse-integrity~1]
    name = "system.MemDepUnit__0.metric"
    literal = f"{name}__get_summary"
    entry = "::value" if kind == "vector" else ""
    params = {"entries": ["value"]} if kind == "vector" else {}
    row = _parse(
        tmp_path,
        f"{name}{entry} 2\n{literal}{entry} 17\n",
        [StatConfig(name, kind, params=params), StatConfig(literal, kind, params=params)],
    )
    column = "..value" if kind == "vector" else ""
    assert row == {f"{name}{column}": "2.0", f"{literal}{column}": "17.0"}


def test_source_summaries_use_named_entries_and_keep_missing_measurements(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.statistics-only~1]
    text = (
        "v__get_summary::value 7\nv__get_summary::total 7\n"
        "d__get_summary::samples 5\nd__get_summary::mean 2e-3\n"
        "d__get_summary::stdev nan\nd__get_summary::0 5 100% 100%\n"
        "h__get_summary::gmean 2.5\nh__get_summary::mean 3.25\n"
        "h__get_summary::stdev 0\nh__get_summary::0-9 4 100% 100%\n"
    )
    configs = [
        StatConfig(
            "v__get_summary", "vector", statistics_only=True, params={"statistics": ["total"]}
        ),
        StatConfig(
            "d__get_summary",
            "distribution",
            statistics_only=True,
            params={"statistics": ["samples", "mean", "stdev"]},
        ),
        StatConfig(
            "h__get_summary",
            "histogram",
            statistics_only=True,
            params={"statistics": ["gmean", "mean", "stdev", "samples"]},
        ),
    ]
    row = _parse(tmp_path, text, configs)
    expected = {
        "v__get_summary..total": "7.0",
        "d__get_summary..samples": "5.0",
        "d__get_summary..mean": "0.002",
        "d__get_summary..stdev": "NaN",
        "h__get_summary..gmean": "2.5",
        "h__get_summary..mean": "3.25",
        "h__get_summary..stdev": "0.0",
        "h__get_summary..samples": "NaN",
    }
    assert expected.items() <= row.items()
    scan = Gem5Parser.aggregate_scan_results(
        [future.result(timeout=30) for future in Gem5Parser.submit_scan_async(str(tmp_path))]
    )
    assert not scan.failures
    assert {variable.name: variable.type for variable in scan.variables} == {
        "v__get_summary": "vector",
        "d__get_summary": "distribution",
        "h__get_summary": "histogram",
    }


def test_summary_suffix_output_alias_only_requests_its_explicit_source(tmp_path: Path) -> None:
    """An unrelated source matching the output label cannot add an observation."""
    output_name = "metric__get_summary"
    config = StatConfig(
        output_name, "scalar", source_name="source", params={"parsed_ids": ["source"]}
    )
    assert _parse(tmp_path, f"source 3\n{output_name} 99\n", [config]) == {output_name: "3.0"}
