"""Real Perl semantic records shared by discovery and persistent parsing."""

from __future__ import annotations

import csv
import json
import subprocess
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from src.core.models.parsing_models import StatConfig
from src.core.models.source_evidence import source_kind_candidates
from src.parsing.gem5.impl.source_events import SOURCE_WIRE_READY
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.impl.strategies.perl_worker_pool import shutdown_worker_pool

pytestmark = pytest.mark.xdist_group("perl_pool")
PERL_ROOT = Path(__file__).resolve().parents[2] / "src/parsing/gem5/perl"


@pytest.fixture(scope="module", autouse=True)
def cleanup_worker_pool() -> Generator[None, None, None]:
    """Keep expected parse failures out of other modules' pool counters."""
    yield
    shutdown_worker_pool()


def _classify(text: str) -> list[dict[str, Any]]:
    program = (
        "use TypesFormatRegex; resetLineContext(); "
        "while (my $line = <STDIN>) { chomp $line; "
        "my $records = classifyLine($line); "
        'print encodeRecord($_), "\\n" for @{ $records // [] }; } '
        'print encodeRecord($_), "\\n" for @{finishLineContext()};'
    )
    result = subprocess.run(
        ["perl", "-I", str(PERL_ROOT / "libs"), "-e", program],
        input=text,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return [json.loads(line) for line in result.stdout.splitlines()]


def _parse(root: Path, text: str, configs: list[StatConfig]) -> dict[str, str]:
    (root / "stats.txt").write_text(text, encoding="utf-8")
    batch = Gem5Parser.submit_parse_async(str(root), "stats.txt", configs, str(root / "out"))
    output = Gem5Parser.finalize_parsing(
        batch, [future.result(timeout=30) for future in batch.futures]
    )
    assert output is not None
    with Path(output.csv_path).open(encoding="utf-8", newline="") as stream:
        return next(csv.DictReader(stream))


def test_semantic_records_preserve_source_values_labels_and_summary_roles(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.variable-scan~2]
    # [test->req~ring5.ingestion.parse-integrity~1]
    text = (
        "---------- Begin Simulation Statistics : phase one ----------\n"
        "fraction -1.25e-3 # scalar\nmissing nan\nlimit -inf\npath=/tmp/gem5/run\n"
        "v::cpu.0 2.5\nv::total 2.5\n"
        "h::gmean 1\nh::-1 2 100% 100%\n"
        "d::underflows 0\nd::0 4 100% 100%\nd::overflows 0\n"
        "r::-10--1 0\n"
    )
    records = _classify(text)
    assert records[0] == {"event": "dump"}
    measurements = [record for record in records if record["event"] == "measurement"]
    assert [
        (record["shape"], record["name"], record["entry"], record["value"])
        for record in measurements
    ] == [
        ("scalar", "fraction", None, "-1.25e-3"),
        ("scalar", "missing", None, "nan"),
        ("scalar", "limit", None, "-inf"),
        ("configuration", "path", None, "/tmp/gem5/run"),
        ("entry", "v", "cpu.0", "2.5"),
        ("entry", "v", "total", "2.5"),
        ("entry", "h", "gmean", "1"),
        ("entry", "h", "-1", "2"),
        ("entry", "d", "underflows", "0"),
        ("entry", "d", "0", "4"),
        ("entry", "d", "overflows", "0"),
        ("entry", "r", "-10--1", "0"),
    ]
    evidence = {
        record["name"]: record["source_evidence"]
        for record in records
        if record["event"] == "source"
    }
    assert evidence["h"] == {"state": "ambiguous", "candidates": ["histogram", "vector"]}
    assert evidence["d"] == {"state": "ambiguous", "candidates": ["distribution", "vector"]}
    assert evidence["v"] == {"state": "resolved", "kind": "vector", "basis": "wire_contract"}
    stats = tmp_path / "stats.txt"
    stats.write_text(text, encoding="utf-8")
    result = subprocess.run(
        ["perl", str(PERL_ROOT / "fileParserServer.pl")],
        input=f"PARSE {stats}||fraction||missing||limit||path||v||h||d||r\nSHUTDOWN\n",
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    lines = result.stdout.splitlines()
    assert lines[0] == SOURCE_WIRE_READY
    assert lines[-2:] == ["END_PARSE", "GOODBYE"]
    assert [json.loads(line) for line in lines[1:-2]] == records
    assert _parse(
        tmp_path,
        text,
        [
            StatConfig("fraction", "scalar", params={"source_type": "scalar"}),
            StatConfig("missing", "scalar", params={"source_type": "scalar"}),
            StatConfig("limit", "scalar", params={"source_type": "scalar"}),
            StatConfig("path", "configuration", params={"source_type": "configuration"}),
        ],
    ) == {
        "fraction": "-0.00125",
        "missing": "NaN",
        "limit": "-inf",
        "path": "/tmp/gem5/run",
    }


@pytest.mark.parametrize("missing", ["bucket_size", "max_bucket"])
@pytest.mark.parametrize("previous_dump", [False, True])
def test_oneline_requires_consistent_geometry_for_each_dump(
    tmp_path: Path, missing: str, previous_dump: bool
) -> None:
    complete = "h::bucket_size 1\nh::min_bucket 0\nh::max_bucket 1\nh |1 50% 50% |1 50% 100%\n"
    geometry = {"bucket_size": 1, "min_bucket": 0, "max_bucket": 1}
    text = "---------- Begin Simulation Statistics ----------\n" + complete if previous_dump else ""
    text += "---------- Begin Simulation Statistics : current ----------\n"
    text += "".join(f"h::{key} {value}\n" for key, value in geometry.items() if key != missing)
    text += "h |2 100% 100% |0 0% 100%\n"
    stats = tmp_path / "stats.txt"
    stats.write_text(text, encoding="utf-8")
    scan = Gem5Parser.aggregate_scan_results(
        [future.result(timeout=30) for future in Gem5Parser.submit_scan_async(str(tmp_path))]
    )
    assert not scan.failures
    assert scan.variables[0].type is None
    assert "vector" in source_kind_candidates(scan.variables[0].source_evidence)
    batch = Gem5Parser.submit_parse_async(
        str(tmp_path),
        "stats.txt",
        [StatConfig("h", "histogram", params={"source_type": "histogram"})],
        str(tmp_path / "out"),
    )
    with pytest.raises(
        (ValueError, RuntimeError), match="geometry|contradicts actual observations"
    ):
        batch.futures[0].result(timeout=30)
    assert not (tmp_path / "out/results.csv").exists()


@pytest.mark.parametrize(
    "body",
    [
        "h::bucket_size 1\nh::min_bucket 0\nh::max_bucket 1\nh |0 |0\n",
        "h::gmean 1\nh::0-9 0\nh::10-19 0\n",
    ],
)
def test_zero_total_histograms_preserve_measured_zero_without_percentages(
    tmp_path: Path, body: str
) -> None:
    # [test->req~ring5.ingestion.histogram~1]
    text = "---------- Begin Simulation Statistics ----------\n" + body
    row = _parse(
        tmp_path,
        text,
        [
            StatConfig(
                "h", "histogram", params={"bins": 2, "max_range": 20, "source_type": "histogram"}
            )
        ],
    )
    assert row == {"h..0-19": "0.0", "h..20+": "0.0"}
    scan = Gem5Parser.aggregate_scan_results(
        [future.result(timeout=30) for future in Gem5Parser.submit_scan_async(str(tmp_path))]
    )
    assert not scan.failures
    assert scan.variables[0].type is None
    assert "histogram" in source_kind_candidates(scan.variables[0].source_evidence)


@pytest.mark.parametrize(
    ("geometry", "expected"),
    [
        ("h::bucket_size 1\nh::max_bucket 1\n", {"h..0-0": "2.0", "h..1-1": "0.0"}),
        ("h::bucket_size 1\nh::min_bucket -1\n", {"h..-1--1": "2.0", "h..0-0": "0.0"}),
    ],
)
def test_omitted_oneline_bounds_reject_and_explicit_zero_bounds_preserve_counts(
    tmp_path: Path, geometry: str, expected: dict[str, str]
) -> None:
    """ScalarPrint's nozero flag omits zero min_bucket or max_bucket fields."""
    text = geometry + "h |2 100% 100% |0 0% 100%\n"
    with pytest.raises(
        (ValueError, RuntimeError), match="geometry|contradicts actual observations"
    ):
        _parse(tmp_path, text, [StatConfig("h", "histogram", params={"source_type": "histogram"})])
    assert not (tmp_path / "out/results.csv").exists()
    complete = (
        geometry
        + ("h::min_bucket 0\n" if "min_bucket" not in geometry else "h::max_bucket 0\n")
        + "h |2 100% 100% |0 0% 100%\n"
    )
    assert (
        _parse(
            tmp_path, complete, [StatConfig("h", "histogram", params={"source_type": "histogram"})]
        )
        == expected
    )
    scan = Gem5Parser.aggregate_scan_results(
        [future.result(timeout=30) for future in Gem5Parser.submit_scan_async(str(tmp_path))]
    )
    assert not scan.failures
    assert scan.variables[0].type is None
    assert set(scan.variables[0].entries) == {"bucket_size", "min_bucket", "max_bucket"}


def test_omitted_single_bucket_bounds_reject_and_explicit_bounds_preserve_zero(
    tmp_path: Path,
) -> None:
    """Both zero bounds may be absent; the bucket payload still supplies its value."""
    text = "h::bucket_size 1\nh |0\n"
    with pytest.raises(
        (ValueError, RuntimeError), match="geometry|contradicts actual observations"
    ):
        _parse(tmp_path, text, [StatConfig("h", "histogram", params={"source_type": "histogram"})])
    assert not (tmp_path / "out/results.csv").exists()
    complete = "h::min_bucket 0\nh::max_bucket 0\n" + text
    assert _parse(
        tmp_path, complete, [StatConfig("h", "histogram", params={"source_type": "histogram"})]
    ) == {"h..0-0": "0.0"}
    records = _classify(text)
    assert [record for record in records if record.get("shape") == "oneline"] == [
        {
            "event": "measurement",
            "name": "h",
            "shape": "oneline",
            "values": ["0"],
            "reported_geometry": {"bucket_size": "1"},
        }
    ]


def test_oneline_vector_does_not_require_histogram_geometry(tmp_path: Path) -> None:
    """A vector's pipe row does not turn an otherwise valid scan into a failure."""
    text = "cycles 5\nv |1 50% 50% |1 50% 100%\nv::total 2\n"
    (tmp_path / "stats.txt").write_text(text, encoding="utf-8")
    scan = Gem5Parser.aggregate_scan_results(
        [future.result(timeout=30) for future in Gem5Parser.submit_scan_async(str(tmp_path))]
    )
    assert not scan.failures
    assert {variable.name: variable.type for variable in scan.variables} == {
        "cycles": "scalar",
        "v": None,
    }
    assert _parse(
        tmp_path, text, [StatConfig("cycles", "scalar", params={"source_type": "scalar"})]
    ) == {"cycles": "5.0"}
