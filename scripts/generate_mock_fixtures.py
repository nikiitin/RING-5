#!/usr/bin/env python3
"""Generate the shaper end-to-end mock CSV fixture by parsing the gem5 stats data.

The shaper e2e tests (``tests/integration/test_e2e_managers_shapers.py``) read one
whitespace-separated CSV:

    tests/data/mock/inputs/csv/configurer/configurer_test_case01.csv

That fixture is not committed (``tests/data/`` is gitignored) and is not part of the
published test-data tarball, which ships only gem5 ``stats.txt`` files. This script
regenerates the fixture from those ``stats.txt`` files so the tests can run, instead
of depending on a lost download.

It parses the per-run identity (``benchmark_name`` and ``config_description_abbrev``,
both ``key=value`` lines in each file's ``[SimulationInfo]`` section) plus ``simTicks``
and ``system.cpu0.branchMispredicts``, then reduces across seeds (arithmetic mean) to
one row per (config, benchmark) — the seed-reduced shape the shaper tests assume.

Run:  ./python_venv/bin/python scripts/generate_mock_fixtures.py   (or: make mock-data)
"""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

import pandas as pd

from src.core.application_api import ApplicationAPI
from src.core.models import StatConfig

logging.basicConfig(level=logging.WARNING)

REPO_ROOT = Path(__file__).resolve().parent.parent
STATS_ROOT = REPO_ROOT / "tests" / "data" / "results-micro26-sens"
OUTPUT_CSV = (
    REPO_ROOT
    / "tests"
    / "data"
    / "mock"
    / "inputs"
    / "csv"
    / "configurer"
    / "configurer_test_case01.csv"
)

# Raw gem5 stat names we ask the parser for, keyed by the canonical fixture column.
COLUMN_SOURCES = {
    "config_description_abbrev": "config_description_abbrev",
    "benchmark_name": "benchmark_name",
    "simTicks": "simTicks",
    "branchMispredicts": "system.cpu0.branchMispredicts",
}
IDENTITY = ["config_description_abbrev", "benchmark_name"]
METRICS = ["simTicks", "branchMispredicts"]
FINAL_ORDER = ["benchmark_name", "config_description_abbrev", "simTicks", "branchMispredicts"]


def _find_column(df: pd.DataFrame, needle: str) -> str:
    """Locate a parser column by substring (the parser may normalise stat names)."""
    if needle in df.columns:
        return needle
    matches = [
        c for c in df.columns if needle in c or needle.replace(".", "") in c.replace(".", "")
    ]
    if not matches:
        raise SystemExit(
            f"expected a column matching {needle!r} in parser output; got {list(df.columns)}"
        )
    # Prefer the shortest match (closest to the bare stat name).
    return min(matches, key=len)


def _parse_to_dataframe() -> pd.DataFrame:
    api = ApplicationAPI()
    stats_files = api.find_stats_files(str(STATS_ROOT), "stats.txt")
    if not stats_files:
        raise SystemExit(f"no stats.txt under {STATS_ROOT}; run `make test-data` first")
    print(f">> parsing {len(stats_files)} stats.txt files from {STATS_ROOT}")

    variables = [
        StatConfig(name=src, type=("scalar" if col in METRICS else "configuration"))
        for col, src in COLUMN_SOURCES.items()
    ]

    with tempfile.TemporaryDirectory() as out_dir:
        batch = api.submit_parse_async(
            stats_path=str(STATS_ROOT),
            stats_pattern="stats.txt",
            variables=variables,
            output_dir=out_dir,
        )
        results = [f.result() for f in batch.futures]
        csv_path = api.finalize_parsing(out_dir, results, var_names=batch.var_names)
        if not csv_path:
            raise SystemExit("parser produced no CSV")
        df = pd.read_csv(csv_path)

    print(f">> raw parser columns: {list(df.columns)}")
    print(f">> raw parser shape: {df.shape}")
    return df


def generate() -> Path:
    """Regenerate the canonical parser fixture from downloaded gem5 data."""
    if not STATS_ROOT.is_dir():
        raise SystemExit(f"gem5 stats data not found at {STATS_ROOT}; run `make test-data` first")

    raw = _parse_to_dataframe()

    # Map parser columns -> canonical fixture names.
    rename = {_find_column(raw, src): col for col, src in COLUMN_SOURCES.items()}
    df = raw.rename(columns=rename)[list(COLUMN_SOURCES.keys())].copy()

    # Metrics must be numeric for the Mean/Normalize shapers.
    for metric in METRICS:
        df[metric] = pd.to_numeric(df[metric], errors="coerce")
    df = df.dropna(subset=METRICS).copy()

    # Reduce across seeds: one row per (config, benchmark), mean of the metrics.
    reduced = df.groupby(IDENTITY, as_index=False)[METRICS].mean().loc[:, FINAL_ORDER].copy()
    reduced = reduced.sort_values(["benchmark_name", "config_description_abbrev"]).reset_index(
        drop=True
    )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    # Whitespace-separated, no index — the test reads with sep=r"\s+".
    reduced.to_csv(OUTPUT_CSV, sep=" ", index=False)

    n_bench = reduced["benchmark_name"].nunique()
    n_conf = reduced["config_description_abbrev"].nunique()
    print(f">> wrote {OUTPUT_CSV.relative_to(REPO_ROOT)}")
    print(f">> rows={len(reduced)}  benchmarks={n_bench}  configs={n_conf}")
    return OUTPUT_CSV


def main() -> int:
    """Generate the fixture when it is absent and return a process exit code."""
    if OUTPUT_CSV.exists():
        print(f">> mock fixture already present: {OUTPUT_CSV.relative_to(REPO_ROOT)} (skipping)")
        return 0
    generate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
