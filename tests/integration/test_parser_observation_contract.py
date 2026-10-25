"""Real Perl scan/parse regressions for observation and CSV contracts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.core.models.parsing_models import ScannedVariable, SourceInstance, StatConfig
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.models import Gem5ScannedVariable

pytestmark = pytest.mark.xdist_group("perl_pool")


def _csv(path: str) -> tuple[list[str], list[dict[str, str]]]:
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def _parse(
    root: Path,
    text: str,
    configs: list[StatConfig],
    *,
    scanned: list[ScannedVariable] | None = None,
    strategy: str = "simple",
) -> tuple[list[str], list[dict[str, str]]]:
    root.mkdir(parents=True, exist_ok=True)
    (root / "stats.txt").write_text(text, encoding="utf-8")
    batch = Gem5Parser.submit_parse_async(
        str(root), "stats.txt", configs, str(root / "output"), strategy, scanned
    )
    results = [future.result(timeout=30) for future in batch.futures]
    path = Gem5Parser.finalize_parsing(str(root / "output"), results, strategy, batch.var_names)
    assert path is not None
    return _csv(path)


def test_perl_missing_frequency_stats_and_summaries_differ_from_measured_zero(
    tmp_path: Path,
) -> None:
    _, rows = _parse(
        tmp_path,
        "zero::underflows 0 0% 0%\nzero::0 0 0% 0%\nzero::1 0 0% 0%\n"
        "zero::overflows 0 0% 0%\nh::0-9 0 0% 0%\n",
        [
            StatConfig(
                "missing",
                "distribution",
                params={"source_type": "distribution", "minimum": 0, "maximum": 1},
            ),
            StatConfig(
                "zero",
                "distribution",
                params={
                    "source_type": "distribution",
                    "minimum": 0,
                    "maximum": 1,
                    "statistics": ["mean"],
                },
            ),
            StatConfig(
                "h",
                "histogram",
                params={
                    "source_type": "histogram",
                    "bins": 2,
                    "max_range": 10,
                    "statistics": ["mean"],
                },
            ),
            StatConfig(
                "absent_h",
                "histogram",
                params={
                    "source_type": "histogram",
                    "bins": 2,
                    "max_range": 10,
                    "statistics": ["mean"],
                },
            ),
        ],
    )
    assert rows[0]["zero..0"] == "0.0"
    assert rows[0]["h..0-9"] == "0.0"
    assert rows[0]["h..10+"] == "0.0"
    assert rows[0]["zero..mean"] == rows[0]["h..mean"] == "NaN"
    assert all(
        value == "NaN"
        for name, value in rows[0].items()
        if name.startswith(("missing..", "absent_h.."))
    )


def test_perl_temporal_vector_samples_match_scalar_average(tmp_path: Path) -> None:
    _, rows = _parse(
        tmp_path,
        "v::a 2\nipc 2\nv::a 4\nipc 4\n",
        [
            StatConfig("v", "vector", repeat=2, params={"source_type": "vector", "entries": ["a"]}),
            StatConfig("ipc", "scalar", repeat=2, params={"source_type": "scalar"}),
        ],
    )
    assert rows == [{"v..a": "3.0", "ipc": "3.0"}]


def test_perl_aliased_scalar_pattern_repeats_selected_indices_and_keep_indices(
    tmp_path: Path,
) -> None:
    text = "system.cpu0.ipc 2\nsystem.cpu1.ipc 4\nsystem.cpu0.ipc 6\nsystem.cpu1.ipc 8\n"
    (tmp_path / "stats.txt").write_text(text, encoding="utf-8")
    scanned = Gem5Parser.aggregate_scan_results(
        [
            future.result(timeout=30)
            for future in Gem5Parser.submit_scan_async(str(tmp_path), "stats.txt")
        ]
    ).variables
    scanned = [ScannedVariable.from_dict(var.to_dict()) for var in scanned]
    source = r"system.cpu\d+.ipc"
    assert any(var.name == source and var.type == "vector" for var in scanned)
    config = StatConfig(
        "IPC",
        "vector",
        source_name=source,
        repeat=2,
        is_regex=True,
        params={"source_type": "scalar"},
    )
    columns, rows = _parse(tmp_path / "all", text, [config], scanned=scanned)
    assert columns == ["IPC..0", "IPC..1"]
    assert rows == [{"IPC..0": "4.0", "IPC..1": "6.0"}]
    for keep_indices in (False, True):
        selected = StatConfig(
            "IPC",
            "vector",
            source_name=source,
            repeat=2,
            is_regex=True,
            keep_indices=keep_indices,
            params={"source_type": "scalar", "selected_sources": ["system.cpu1.ipc"]},
        )
        columns, rows = _parse(
            tmp_path / f"selected-{keep_indices}", text, [selected], scanned=scanned
        )
        assert columns == (["system.cpu1.ipc"] if keep_indices else ["IPC..1"])
        assert list(rows[0].values()) == ["6.0"]


def test_perl_true_vector_pattern_averages_spatial_and_temporal_samples(tmp_path: Path) -> None:
    source = r"system.cpu\d+.v"
    scanned: list[ScannedVariable] = [
        Gem5ScannedVariable(
            source,
            "vector",
            entries=["a"],
            source_type="vector",
            instances=(
                SourceInstance("system.cpu0.v", ("0",)),
                SourceInstance("system.cpu1.v", ("1",)),
            ),
        )
    ]
    text = "system.cpu0.v::a 2\nsystem.cpu1.v::a 4\nsystem.cpu0.v::a 6\nsystem.cpu1.v::a 8\n"
    _, rows = _parse(
        tmp_path,
        text,
        [
            StatConfig(
                "V",
                "vector",
                source_name=source,
                repeat=2,
                is_regex=True,
                params={"source_type": "vector", "entries": ["a"]},
            )
        ],
        scanned=scanned,
    )
    assert rows == [{"V..a": "5.0"}]


def test_perl_missing_expected_pattern_instance_stays_nan(tmp_path: Path) -> None:
    source = r"system.cpu\d+.h"
    scanned: list[ScannedVariable] = [
        Gem5ScannedVariable(
            source,
            "histogram",
            source_type="histogram",
            instances=(
                SourceInstance("system.cpu0.h", ("0",)),
                SourceInstance("system.cpu1.h", ("1",)),
            ),
        )
    ]
    _, rows = _parse(
        tmp_path,
        "system.cpu0.h::0-9 6 100% 100%\n",
        [
            StatConfig(
                "H",
                "histogram",
                source_name=source,
                is_regex=True,
                params={"source_type": "histogram", "bins": 2, "max_range": 10},
            )
        ],
        scanned=scanned,
    )
    assert rows == [{"H..0-9": "NaN", "H..10+": "NaN"}]


@pytest.mark.parametrize(
    "text",
    [
        "h::bucket_size 10\nh::min_bucket -10\nh::max_bucket 9\n"
        "h |5 41.7% 41.7% |7 58.3% 100%\n",
        "h::-10--1 5 41.7% 41.7%\nh::0-9 7 58.3% 100%\n",
    ],
)
def test_perl_signed_histogram_scan_and_rebin(tmp_path: Path, text: str) -> None:
    (tmp_path / "stats.txt").write_text(text, encoding="utf-8")
    scan = Gem5Parser.aggregate_scan_results(
        [
            future.result(timeout=30)
            for future in Gem5Parser.submit_scan_async(str(tmp_path), "stats.txt")
        ]
    )
    assert not scan.failures
    histogram = next(var for var in scan.variables if var.name == "h")
    assert histogram.type == "histogram"
    assert histogram.entries == ["-10--1", "0-9"]
    _, rows = _parse(
        tmp_path / "parse",
        text,
        [
            StatConfig(
                "h", "histogram", params={"source_type": "histogram", "bins": 2, "max_range": 10}
            )
        ],
    )
    assert rows == [{"h..<0": "5.0", "h..0-9": "7.0", "h..10+": "0.0"}]


def test_perl_singleton_oneline_buckets_and_changing_dump_geometry_conserve_counts(
    tmp_path: Path,
) -> None:
    text = (
        "---------- Begin Simulation Statistics ----------\n"
        "h::bucket_size 1\nh::min_bucket 0\nh::max_bucket 1\nh |9 90% 90% |1 10% 100%\n"
        "---------- End Simulation Statistics ----------\n"
        "---------- Begin Simulation Statistics ----------\n"
        "h::bucket_size 2\nh::min_bucket 0\nh::max_bucket 1\nh |20 100% 100%\n"
        "---------- End Simulation Statistics ----------\n"
    )
    _, rows = _parse(
        tmp_path,
        text,
        [
            StatConfig(
                "h",
                "histogram",
                repeat=2,
                params={"source_type": "histogram", "bins": 2, "max_range": 10},
            )
        ],
    )
    assert rows == [{"h..0-9": "15.0", "h..10+": "0.0"}]


def test_perl_full_and_incremental_dynamic_histogram_schemas_match(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    for name, text in (
        ("a", "simTicks 1\n"),
        ("b", "h::0-9 9 100% 100%\n"),
        ("c", "h::0-19 12 100% 100%\n"),
    ):
        run = inputs / name
        run.mkdir(parents=True)
        (run / "stats.txt").write_text(text, encoding="utf-8")
    configs = [StatConfig("h", "histogram", params={"source_type": "histogram"})]
    full = Gem5Parser.submit_parse_async(str(inputs), "stats.txt", configs, str(tmp_path / "full"))
    results = [future.result(timeout=30) for future in full.futures]
    full_path = Gem5Parser.finalize_parsing(
        str(tmp_path / "full"), results, var_names=full.var_names
    )
    incremental = Gem5Parser.submit_incremental_parse_async(
        str(inputs), "stats.txt", configs, str(tmp_path / "incremental")
    )
    incremental_result = Gem5Parser.finalize_incremental_parsing(
        incremental, [future.result(timeout=30) for future in incremental.futures]
    )
    assert full_path is not None
    full_columns, full_rows = _csv(full_path)
    incremental_columns, incremental_rows = _csv(incremental_result.csv_path)
    assert full_columns == incremental_columns == ["h..0-19", "h..0-9"]
    assert sorted(tuple(sorted(row.items())) for row in full_rows) == sorted(
        tuple(sorted(row.items())) for row in incremental_rows
    )


def test_config_aware_preserves_literal_percent_case_paths_and_unicode(tmp_path: Path) -> None:
    (tmp_path / "config.ini").write_text(
        "[system.workload]\nCmd=echo 100% %(unknown)s /tmp/á\\\\path\n", encoding="utf-8"
    )
    _, rows = _parse(
        tmp_path,
        "ipc 2\n",
        [StatConfig("ipc", "scalar", params={"source_type": "scalar"})],
        strategy="config_aware",
    )
    config = json.loads(rows[0]["config_json"])
    assert config == {"system.workload": {"Cmd": "echo 100% %(unknown)s /tmp/á\\\\path"}}


def test_perl_scanned_numeric_vector_entries_retain_vector_source_type(tmp_path: Path) -> None:
    text = "system.cpu0.v::0 2\nsystem.cpu0.v::1 4\nsystem.cpu1.v::0 6\nsystem.cpu1.v::1 8\n"
    (tmp_path / "stats.txt").write_text(text, encoding="utf-8")
    scanned = Gem5Parser.aggregate_scan_results(
        [
            future.result(timeout=30)
            for future in Gem5Parser.submit_scan_async(str(tmp_path), "stats.txt")
        ]
    ).variables
    assert isinstance(scanned[0], Gem5ScannedVariable)
    assert scanned[0].source_type == "vector"
    assert Gem5ScannedVariable.from_dict(scanned[0].to_dict()).source_type == "vector"
    scanned = [ScannedVariable.from_dict(var.to_dict()) for var in scanned]
    for keep_indices in (False, True):
        config = StatConfig(
            "V",
            "vector",
            source_name=r"system.cpu\d+.v",
            is_regex=True,
            keep_indices=keep_indices,
            params={"source_type": "vector", "entries": ["0", "1"]},
        )
        _, rows = _parse(tmp_path / str(keep_indices), text, [config], scanned=scanned)
        if keep_indices:
            assert rows == [
                {
                    "system.cpu0.v..0": "2.0",
                    "system.cpu0.v..1": "4.0",
                    "system.cpu1.v..0": "6.0",
                    "system.cpu1.v..1": "8.0",
                }
            ]
        else:
            assert rows == [{"V..0": "4.0", "V..1": "6.0"}]


def test_perl_scan_and_parse_reset_geometry_before_zero_suppressed_dump(tmp_path: Path) -> None:
    """An omitted zero bound cannot inherit a previous dump's negative minimum."""
    text = (
        "---------- Begin Simulation Statistics ----------\n"
        "h::bucket_size 10\nh::min_bucket -10\nh::max_bucket 9\n"
        "h |5 41.7% 41.7% |7 58.3% 100%\n"
        "---------- End Simulation Statistics ----------\n"
        "---------- Begin Simulation Statistics ----------\n"
        "h::bucket_size 10\nh::max_bucket 9\nh |10 100% 100%\n"
        "---------- End Simulation Statistics ----------\n"
    )
    (tmp_path / "stats.txt").write_text(text, encoding="utf-8")
    scan = Gem5Parser.aggregate_scan_results(
        [
            future.result(timeout=30)
            for future in Gem5Parser.submit_scan_async(str(tmp_path), "stats.txt")
        ]
    )
    assert not scan.failures
    assert next(var for var in scan.variables if var.name == "h").entries == ["-10--1", "0-9"]
    _, rows = _parse(
        tmp_path / "parse",
        text,
        [
            StatConfig(
                "h",
                "histogram",
                repeat=2,
                params={"source_type": "histogram", "bins": 2, "max_range": 10},
            )
        ],
    )
    assert rows == [{"h..<0": "2.5", "h..0-9": "8.5", "h..10+": "0.0"}]
