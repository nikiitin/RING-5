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
        "use JSON::PP; use TypesFormatRegex; resetLineContext(); "
        "while (my $line = <STDIN>) { chomp $line; "
        "my $records = classifyLine($line); "
        'print encode_json($_), "\\n" for @{ $records // [] }; } '
        'print encode_json($_), "\\n" for @{finishLineContext()};'
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
        str(root / "out"),
        [future.result(timeout=30) for future in batch.futures],
        var_names=batch.var_names,
    )
    assert output is not None
    with Path(output).open(encoding="utf-8", newline="") as stream:
        return next(csv.DictReader(stream))


def test_semantic_records_preserve_source_values_labels_and_summary_roles(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.variable-scan~1]
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
    assert records[0] == {"type": "dump"}
    assert [
        (record["type"], record["name"], record["entry"], record["scan_entry"], record["value"])
        for record in records[1:]
    ] == [
        ("scalar", "fraction", None, None, "-1.25e-3"),
        ("scalar", "missing", None, None, "nan"),
        ("scalar", "limit", None, None, "-inf"),
        ("configuration", "path", None, None, "/tmp/gem5/run"),
        ("vector", "v", "cpu.0", "cpu.0", "2.5"),
        ("summary", "v", "total", "total", "2.5"),
        ("summary", "h", "gmean", "gmean", "1"),
        ("histogram", "h", "-1", "-1--1", "2"),
        ("distribution", "d", "underflows", "underflows", "0"),
        ("distribution", "d", "0", "0", "4"),
        ("distribution", "d", "overflows", "overflows", "0"),
        ("histogram", "r", "-10--1", "-10--1", "0"),
    ]
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
    assert result.stdout.splitlines() == [
        "READY",
        "dump//",
        "scalar/fraction/-1.25e-3",
        "scalar/missing/nan",
        "scalar/limit/-inf",
        "configuration/path//tmp/gem5/run",
        "vector/v::cpu.0/2.5",
        "summary/v::total/2.5",
        "summary/h::gmean/1",
        "histogram/h::-1/2",
        "distribution/d::underflows/0",
        "distribution/d::0/4",
        "distribution/d::overflows/0",
        "histogram/r::-10--1/0",
        "END_PARSE",
        "GOODBYE",
    ]
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
    assert len(scan.failures) == 1
    assert "histogram" in (scan.failures[0].error or "")
    batch = Gem5Parser.submit_parse_async(
        str(tmp_path),
        "stats.txt",
        [StatConfig("h", "histogram", params={"source_type": "histogram"})],
        str(tmp_path / "out"),
    )
    with pytest.raises(RuntimeError, match="Worker pool parse failed"):
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
    assert scan.variables[0].type == "histogram"


@pytest.mark.parametrize(
    ("geometry", "expected"),
    [
        ("h::bucket_size 1\nh::max_bucket 1\n", {"h..0-0": "2.0", "h..1-1": "0.0"}),
        ("h::bucket_size 1\nh::min_bucket -1\n", {"h..-1--1": "2.0", "h..0-0": "0.0"}),
    ],
)
def test_zero_suppressed_oneline_bounds_are_current_gem5_geometry(
    tmp_path: Path, geometry: str, expected: dict[str, str]
) -> None:
    """ScalarPrint's nozero flag omits zero min_bucket or max_bucket fields."""
    text = geometry + "h |2 100% 100% |0 0% 100%\n"
    assert (
        _parse(tmp_path, text, [StatConfig("h", "histogram", params={"source_type": "histogram"})])
        == expected
    )
    scan = Gem5Parser.aggregate_scan_results(
        [future.result(timeout=30) for future in Gem5Parser.submit_scan_async(str(tmp_path))]
    )
    assert not scan.failures
    assert set(scan.variables[0].entries) == {name.split("..", 1)[1] for name in expected}


def test_zero_suppressed_single_bucket_preserves_its_measured_zero(tmp_path: Path) -> None:
    """Both zero bounds may be absent; the bucket payload still supplies its value."""
    text = "h::bucket_size 1\nh |0\n"
    assert _parse(
        tmp_path, text, [StatConfig("h", "histogram", params={"source_type": "histogram"})]
    ) == {"h..0-0": "0.0"}
    assert _classify(text) == [
        {"type": "histogram", "name": "h", "entry": "0-0", "scan_entry": "0-0", "value": "0"}
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
        "v": "vector",
    }
    assert _parse(
        tmp_path, text, [StatConfig("cycles", "scalar", params={"source_type": "scalar"})]
    ) == {"cycles": "5.0"}
