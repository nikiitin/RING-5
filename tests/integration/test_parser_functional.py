"""Integration tests for gem5 stats parser functionality."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.parsers.parser import Gem5StatsParser


class TestParserFunctional:

    @pytest.fixture
    def test_data_path(self):
        """Path to the test data provided by the user (subset for speed)."""
        base_path = Path("/home/vnicolas/workspace/micro26-sens/results-micro26-sens")
        if not base_path.exists():
            pytest.skip(f"Test data not found at {base_path}")

        subdirs = [d for d in base_path.iterdir() if d.is_dir()]
        if not subdirs:
            pytest.skip(f"No subdirectories found in {base_path}")

        return str(subdirs[0])

    def test_parse_real_stats(self, test_data_path):
        """
        Test parsing actual gem5 stats files from the provided directory.
        Verifies that simTicks and IPC are correctly extracted.
        """
        with tempfile.TemporaryDirectory() as output_dir:
            # Reset singleton
            Gem5StatsParser.reset()

            # Build parser with variables
            parser = (
                Gem5StatsParser.builder()
                .with_path(test_data_path)
                .with_pattern("stats.txt")
                .with_variable("simTicks", "scalar")
                .with_variable("system.cpu0.ipc", "scalar")
                .with_variable("benchmark_name", "configuration", onEmpty="Unknown")
                .with_output(output_dir)
                .build()
            )

            # Execute parsing
            parser.parse()

            # Verify results
            expected_csv = Path(output_dir) / "results.csv"
            assert expected_csv.exists(), "results.csv was not created"

            # Check content
            df = pd.read_csv(expected_csv)

            # Verify headers
            assert "simTicks" in df.columns
            assert "system.cpu0.ipc" in df.columns

            # Verify we got rows
            assert len(df) > 0, "No data rows were parsed"

            # Verify no NA values in these columns
            assert not df["simTicks"].isnull().any()
            assert not df["system.cpu0.ipc"].isnull().any()

            # Check values are numeric and positive
            sim_ticks = pd.to_numeric(df["simTicks"])
            ipc = pd.to_numeric(df["system.cpu0.ipc"])

            if not (sim_ticks > 0).any():
                print("DEBUG: simTicks head:", df["simTicks"].head())
                pytest.fail("All simTicks are 0 or negative")

            if not (ipc > 0).any():
                print("DEBUG: IPC head:", df["system.cpu0.ipc"].head())
                pytest.fail("All IPC values are 0 or negative")
