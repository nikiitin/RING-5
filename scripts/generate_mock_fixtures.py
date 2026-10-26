#!/usr/bin/env python3
"""Generate the shaper end-to-end mock CSV fixture by parsing the gem5 stats data.

The shaper e2e tests (``tests/integration/test_e2e_managers_shapers.py``) read one
whitespace-separated CSV:

    tests/data/mock/inputs/csv/configurer/configurer_test_case01.csv

The fixture is generated locally from the downloaded gem5 ``stats.txt`` files;
``tests/data/`` is gitignored. Seed means use runs containing both metrics;
incomplete runs are reported and excluded, and non-finite metrics fail visibly.

It parses the per-run identity (``benchmark_name`` and ``config_description_abbrev``,
both ``key=value`` lines in each file's ``[SimulationInfo]`` section) plus ``simTicks``
and ``system.cpu0.branchMispredicts``, then reduces across seeds (arithmetic mean) to
one row per (config, benchmark) — the seed-reduced shape the shaper tests assume.

Run:  ./python_venv/bin/python -m scripts.generate_mock_fixtures   (or: make mock-data)
"""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

import pandas as pd
import numpy as np

from src.core.application_api import ApplicationAPI
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsing_models import StatConfig
from src.parsing.gem5.types.base import population_mean

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


def _seed_mean(values: pd.Series) -> float:
    """Use the parser's overflow-safe population mean for complete seed observations."""
    return population_mean(values.tolist())


def _parse_to_dataframe() -> pd.DataFrame:
    """Parse actual source names into the fixture's explicitly declared output columns."""
    api = ApplicationAPI()
    try:
        stats_files = api.find_stats_files(str(STATS_ROOT), "stats.txt")
        if not stats_files:
            raise SystemExit(f"no stats.txt under {STATS_ROOT}; run `make test-data` first")
        print(f">> parsing {len(stats_files)} stats.txt files from {STATS_ROOT}")

        variables = []
        for column, source in COLUMN_SOURCES.items():
            kind = "scalar" if column in METRICS else "configuration"
            variables.append(
                StatConfig(
                    name=column,
                    source_name=source,
                    type=kind,
                    params={"source_type": kind},
                )
            )

        with tempfile.TemporaryDirectory() as out_dir:
            batch = api.submit_parse_async(
                stats_path=str(STATS_ROOT),
                stats_pattern="stats.txt",
                variables=variables,
                output_dir=out_dir,
            )
            results = [f.result() for f in batch.futures]
            output = api.finalize_parsing(batch, results)
            df = ParsedOutputIO.to_frame(output)

    finally:
        api.close(wait=True)

    print(f">> raw parser columns: {list(df.columns)}")
    print(f">> raw parser shape: {df.shape}")
    return df


def generate() -> Path:
    """Regenerate the canonical parser fixture from downloaded gem5 data."""
    if not STATS_ROOT.is_dir():
        raise SystemExit(f"gem5 stats data not found at {STATS_ROOT}; run `make test-data` first")

    raw = _parse_to_dataframe()

    df = raw.loc[:, list(COLUMN_SOURCES)].copy()
    incomplete = df[METRICS].isna().any(axis=1)
    if incomplete.any():
        logging.warning("Excluding %s incomplete run(s) from fixture seed means.", incomplete.sum())
        df = df.loc[~incomplete].copy()
    if df.empty or not np.isfinite(df[METRICS].to_numpy()).all():
        raise SystemExit("Fixture generation requires complete runs with finite metrics.")

    # Reduce across seeds: one row per (config, benchmark), mean of the metrics.
    reduced = (
        df.groupby(IDENTITY, as_index=False)[METRICS].agg(_seed_mean).loc[:, FINAL_ORDER].copy()
    )
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
