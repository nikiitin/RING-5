"""Real Perl contracts for genuine gem5 singleton output and explicit source records."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import pytest

from src.core.models.parsing_models import ScannedVariable, StatConfig, StatParamValue
from src.core.models.parsing_models import SourceInstance
from src.parsing.gem5.impl.gem5_parser import Gem5Parser

pytestmark = pytest.mark.xdist_group("perl_pool")


def _scan(root: Path, text: str) -> list[ScannedVariable]:
    root.mkdir(parents=True, exist_ok=True)
    (root / "stats.txt").write_text(text, encoding="utf-8")
    result = Gem5Parser.aggregate_scan_results(
        [
            future.result(timeout=30)
            for future in Gem5Parser.submit_scan_async(str(root), "stats.txt")
        ]
    )
    assert not result.failures
    return result.variables


def _parse(
    root: Path, configs: list[StatConfig], scanned: list[ScannedVariable] | None = None
) -> dict[str, str]:
    batch = Gem5Parser.submit_parse_async(
        str(root), "stats.txt", configs, str(root / "out"), scanned_vars=scanned
    )
    output = Gem5Parser.finalize_parsing(
        batch, [future.result(timeout=30) for future in batch.futures]
    )
    assert output is not None
    with Path(output.csv_path).open(encoding="utf-8", newline="") as stream:
        return next(csv.DictReader(stream))


@pytest.mark.parametrize("metadata", ["", "h::bucket_size 1\nh::min_bucket -1\nh::max_bucket 1\n"])
def test_real_singleton_histogram_vector_and_distribution_contexts(
    tmp_path: Path, metadata: str
) -> None:
    text = metadata + (
        "h::samples 12\nh::mean 0.1\nh::gmean 1\nh::stdev 0.3\n"
        "h::-1 2 16.67% 16.67%\nh::0 9 75% 91.67%\nh::1 1 8.33% 100%\n"
        "v::0 5 41.67% 41.67%\nv::1 7 58.33% 100%\nv::total 12\n"
        "d::samples 12\nd::mean 0.5\nd::stdev 0.2\n"
        "d::underflows 0 0% 0%\nd::0 5 41.67% 41.67%\n"
        "d::1 7 58.33% 100%\nd::overflows 0 0% 100%\n"
    )
    scanned = {variable.name: variable for variable in _scan(tmp_path, text)}
    assert scanned["h"].type == "histogram"
    assert {"-1--1", "0-0", "1-1"} <= set(scanned["h"].entries)
    assert scanned["v"].type == "vector"
    assert {"0", "1"} <= set(scanned["v"].entries)
    assert scanned["d"].type == "distribution"
    row = _parse(
        tmp_path,
        [
            StatConfig(
                "h", "histogram", params={"bins": 2, "max_range": 10, "source_type": "histogram"}
            ),
            StatConfig("v", "vector", params={"entries": ["0", "1"], "source_type": "vector"}),
            StatConfig(
                "d",
                "distribution",
                params={"minimum": 0, "maximum": 1, "source_type": "distribution"},
            ),
        ],
    )
    assert {key: row[key] for key in ("h..<0", "h..0-9", "h..10+")} == {
        "h..<0": "2.0",
        "h..0-9": "10.0",
        "h..10+": "0.0",
    }
    assert (row["v..0"], row["v..1"]) == ("5.0", "7.0")
    assert (row["d..0"], row["d..1"], row["d..underflows"], row["d..overflows"]) == (
        "5.0",
        "7.0",
        "0.0",
        "0.0",
    )


def test_explicit_histogram_type_canonicalizes_points_without_inference_markers(
    tmp_path: Path,
) -> None:
    _scan(tmp_path, "h::-1 2\nh::0 9\nh::1 1\n")
    row = _parse(
        tmp_path,
        [
            StatConfig(
                "h", "histogram", params={"entries": ["-1", "0", "1"], "source_type": "vector"}
            )
        ],
    )
    assert row == {"h..-1--1": "2.0", "h..0-0": "9.0", "h..1-1": "1.0"}


def test_histogram_geometry_identifies_points_without_summaries(tmp_path: Path) -> None:
    scanned = _scan(
        tmp_path,
        "h::bucket_size 1\nh::min_bucket -1\nh::max_bucket 1\n"
        "h::-1 2 16.67% 16.67%\nh::0 9 75% 91.67%\nh::1 1 8.33% 100%\n",
    )
    assert len(scanned) == 1
    assert scanned[0].type == "histogram"
    assert set(scanned[0].entries) == {"-1--1", "0-0", "1-1"}
    assert _parse(
        tmp_path, [StatConfig("h", "histogram", params={"source_type": "histogram"})]
    ) == {
        "h..-1--1": "2.0",
        "h..0-0": "9.0",
        "h..1-1": "1.0",
    }


@pytest.mark.parametrize("target", ["vector", "distribution"])
def test_singleton_histogram_preserves_explicit_entry_type_reinterpretation(
    tmp_path: Path, target: str
) -> None:
    _scan(
        tmp_path,
        "h::samples 10\nh::mean 0.1\nh::gmean 1\nh::stdev 0.3\n"
        "h::0 9 90% 90%\nh::1 1 10% 100%\n",
    )
    config = (
        StatConfig("h", target, params={"entries": ["0-0", "1-1"], "source_type": "histogram"})
        if target == "vector"
        else StatConfig(
            "h", target, params={"minimum": 0, "maximum": 1, "source_type": "histogram"}
        )
    )
    if target == "distribution":
        with pytest.raises(TypeError, match="Missing mandatory keys 'underflows' or 'overflows'"):
            _parse(tmp_path, [config])
    else:
        row = _parse(tmp_path, [config])
        assert (row["h..0-0"], row["h..1-1"]) == ("9.0", "1.0")


@pytest.mark.parametrize("target", ["vector", "histogram"])
def test_distribution_preserves_explicit_entry_type_reinterpretation(
    tmp_path: Path, target: str
) -> None:
    scanned = _scan(
        tmp_path,
        "d::samples 10\nd::mean 0.1\nd::stdev 0.3\n"
        "d::underflows 0 0% 0%\nd::0 9 90% 90%\n"
        "d::1 1 10% 100%\nd::overflows 0 0% 100%\n",
    )
    assert scanned[0].type == "distribution"
    row = _parse(
        tmp_path,
        [StatConfig("d", target, params={"entries": ["0", "1"], "source_type": "distribution"})],
    )
    labels = ("0", "1") if target == "vector" else ("0-0", "1-1")
    assert (row[f"d..{labels[0]}"], row[f"d..{labels[1]}"]) == ("9.0", "1.0")


@pytest.mark.parametrize("include_raw_entries", [False, True])
def test_histogram_vector_selection_requires_inclusive_scanned_labels(
    tmp_path: Path, include_raw_entries: bool
) -> None:
    scanned = _scan(
        tmp_path,
        "h::samples 12\nh::mean 0\nh::gmean 1\nh::stdev 1\n"
        "h::-1 2 16.67% 16.67%\nh::0 9 75% 91.67%\nh::1 1 8.33% 100%\n",
    )
    histogram = next(variable for variable in scanned if variable.name == "h")
    assert histogram.type == "histogram"
    values = {"-1--1": "2.0", "0-0": "9.0", "1-1": "1.0"}
    selected = [entry for entry in histogram.entries if entry in values]
    assert set(selected) == set(values)
    expected = {f"h..{entry}": values[entry] for entry in selected}
    if include_raw_entries:
        selected.extend(["-1", "0", "1"])
    config = StatConfig(
        "h", "vector", params={"entries": selected, "source_type": histogram.source_type}
    )
    if include_raw_entries:
        with pytest.raises(ValueError):
            _parse(tmp_path, [config], scanned)
    else:
        assert _parse(tmp_path, [config], scanned) == expected


@pytest.mark.parametrize("source_type", ["vector", "histogram"])
def test_singleton_cast_aliases_do_not_broaden_vector_labels(
    tmp_path: Path, source_type: str
) -> None:
    summaries = "h::gmean 1\n" if source_type == "histogram" else ""
    scanned = _scan(tmp_path, summaries + "h::0 9 90% 90%\nh::1 1 10% 100%\n")
    assert scanned[0].type == source_type
    first = "0-0" if source_type == "histogram" else "0"
    selected = [first, "0-1", "other"]
    if source_type == "vector":
        selected.append("0-0")
    config = StatConfig("h", "vector", params={"entries": selected, "source_type": source_type})
    row = _parse(tmp_path, [config], scanned)
    assert row[f"h..{first}"] == "9.0"
    assert all(row[f"h..{entry}"] == "NaN" for entry in selected if entry != first)


def test_explicit_histogram_handles_suppressed_gmean_with_other_summaries(tmp_path: Path) -> None:
    _scan(
        tmp_path,
        "h::samples 10\nh::mean 0.1\nh::stdev 0.3\n" "h::0 9 90% 90%\nh::1 1 10% 100%\n",
    )
    assert _parse(
        tmp_path,
        [
            StatConfig(
                "h", "histogram", params={"bins": 2, "max_range": 10, "source_type": "distribution"}
            )
        ],
    ) == {
        "h..0-9": "10.0",
        "h..10+": "0.0",
    }


@pytest.mark.parametrize("message", ["", " : phase two"])
def test_dump_boundaries_clear_stale_histogram_geometry(tmp_path: Path, message: str) -> None:
    text = (
        "---------- Begin Simulation Statistics ----------\n"
        "v::bucket_size 1\nv::min_bucket 0\nv::max_bucket 1\n"
        "---------- End Simulation Statistics ----------\n"
        f"---------- Begin Simulation Statistics{message} ----------\n"
        "v::0 3 30% 30%\nv::1 7 70% 100%\n"
        "---------- End Simulation Statistics ----------\n"
    )
    scanned = _scan(tmp_path, text)
    assert len(scanned) == 1
    assert scanned[0].type == "vector"
    assert set(scanned[0].entries) == {"0", "1", "bucket_size", "min_bucket", "max_bucket"}
    assert _parse(
        tmp_path,
        [StatConfig("v", "vector", params={"entries": ["0", "1"], "source_type": "vector"})],
    ) == {
        "v..0": "3.0",
        "v..1": "7.0",
    }


@pytest.mark.parametrize("message", ["", " : phase two"])
def test_dump_boundaries_clear_reserved_type_context_in_both_perl_paths(
    tmp_path: Path, message: str
) -> None:
    text = (
        "---------- Begin Simulation Statistics ----------\n"
        "h::gmean 1\nh::0 2 100% 100%\n"
        "---------- End Simulation Statistics ----------\n"
        f"---------- Begin Simulation Statistics{message} ----------\n"
        "h::0 3 100% 100%\n"
    )
    stats = tmp_path / "stats.txt"
    stats.write_text(text, encoding="utf-8")
    perl_root = Path(__file__).resolve().parents[2] / "src/parsing/gem5/perl"
    printed = subprocess.run(
        ["perl", str(perl_root / "fileParserServer.pl")],
        input=f"PARSE {stats}||h\nSHUTDOWN\n",
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    assert "histogram/h::0/2" in printed
    assert "vector/h::0/3" in printed
    classifier = (
        "use JSON::PP; use TypesFormatRegex; resetLineContext(); "
        "while (my $line = <STDIN>) { chomp $line; my $items = classifyLine($line); "
        'print encode_json($_), "\\n" for @{ $items // [] }; }'
    )
    classified = subprocess.run(
        ["perl", "-I", str(perl_root / "libs"), "-e", classifier],
        input=text,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    entries = [
        record for line in classified.splitlines() if (record := json.loads(line))["type"] != "dump"
    ]
    assert entries[1]["type"] == "histogram"
    assert entries[1]["entry"] == "0"
    assert entries[1]["scan_entry"] == "0-0"
    assert entries[-1]["type"] == "vector"
    assert entries[-1]["entry"] == "0"


def test_named_histogram_dumps_preserve_temporal_mass(tmp_path: Path) -> None:
    text = "".join(
        f"---------- Begin Simulation Statistics : phase {index} ----------\n"
        f"h::samples {count}\nh::mean 0\nh::gmean 1\nh::stdev 0\nh::0 {count} 100% 100%\n"
        "---------- End Simulation Statistics ----------\n"
        for index, count in enumerate((2, 4))
    )
    _scan(tmp_path, text)
    assert _parse(
        tmp_path,
        [
            StatConfig(
                "h",
                "histogram",
                repeat=2,
                params={"bins": 2, "max_range": 10, "source_type": "histogram"},
            )
        ],
    ) == {"h..0-9": "3.0", "h..10+": "0.0"}


@pytest.mark.parametrize(
    "kind,entries",
    [("scalar", None), ("vector", ["0", "1"]), ("vector", ["0"])],
)
def test_explicit_raw_kind_separates_source_instances_from_measurement_entries(
    tmp_path: Path, kind: str, entries: list[str] | None
) -> None:
    text = (
        "system.cpu0.v 2\nsystem.cpu1.v 4\n"
        if kind == "scalar"
        else "system.cpu0.v::0 2\nsystem.cpu0.v::1 4\nsystem.cpu1.v::0 6\nsystem.cpu1.v::1 8\n"
    )
    current = _scan(tmp_path, text)
    params: dict[str, StatParamValue] = {"source_type": kind}
    if entries is not None:
        params["entries"] = entries
    config = StatConfig("V", "vector", source_name=r"system.cpu\d+.v", is_regex=True, params=params)
    row = _parse(tmp_path, [config], current)
    expected = (
        {"V..0": "2.0", "V..1": "4.0"} if kind == "scalar" else {"V..0": "4.0", "V..1": "6.0"}
    )
    assert row == (
        expected if entries is None else {f"V..{key}": expected[f"V..{key}"] for key in entries}
    )


def test_current_vector_source_records_retain_measurement_entry_subsets(tmp_path: Path) -> None:
    text = "".join(
        f"system.cpu{cpu}.v::{entry} {cpu * 4 + entry + 2}\n"
        for cpu in range(2)
        for entry in range(3)
    )
    current = _scan(tmp_path, text)
    config = StatConfig(
        "V",
        "vector",
        source_name=r"system.cpu\d+.v",
        is_regex=True,
        params={"entries": ["0", "1"], "source_type": "vector"},
    )
    assert _parse(tmp_path, [config], current) == {"V..0": "4.0", "V..1": "5.0"}


def test_literal_vector_records_support_a_numeric_pattern_request(tmp_path: Path) -> None:
    _scan(
        tmp_path, "system.cpu0.v::0 2\nsystem.cpu0.v::1 4\nsystem.cpu1.v::0 6\nsystem.cpu1.v::1 8\n"
    )
    physical = [
        ScannedVariable(
            f"system.cpu{index}.v",
            "vector",
            ["0", "1"],
            source_type="vector",
            instances=(SourceInstance(f"system.cpu{index}.v", ()),),
        )
        for index in range(2)
    ]
    config = StatConfig(
        "V",
        "vector",
        source_name=r"system.cpu\d+.v",
        is_regex=True,
        params={"entries": ["0", "1"], "source_type": "vector"},
    )
    assert _parse(tmp_path, [config], physical) == {"V..0": "4.0", "V..1": "6.0"}


@pytest.mark.parametrize("entry", ["min_bucket", "bucket_size", "max_bucket"])
@pytest.mark.parametrize(
    "boundary", ["", "---------- Begin Simulation Statistics : next ----------\n"]
)
def test_geometry_named_vector_measurements_are_not_consumed(
    tmp_path: Path, entry: str, boundary: str
) -> None:
    text = (
        "---------- Begin Simulation Statistics ----------\n"
        f"v::{entry} 12\nv::other 34\n" + boundary
    )
    scanned = _scan(tmp_path, text)
    assert len(scanned) == 1
    assert scanned[0].type == "vector"
    assert set(scanned[0].entries) == {entry, "other"}
    assert _parse(
        tmp_path,
        [StatConfig("v", "vector", params={"entries": [entry, "other"], "source_type": "vector"})],
    ) == {
        f"v..{entry}": "12.0",
        "v..other": "34.0",
    }
