"""Integration tests for gem5 stats parser functionality."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest


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
        Test parsing actual gem5 stats files using the Backend Facade.
        Verifies the full async pipeline: Submit -> Wait Futures -> Finalize -> Load.
        """
        from concurrent.futures import as_completed

        from src.web.facade import BackendFacade

        with tempfile.TemporaryDirectory() as output_dir:
            # We must reset the singleton to ensure clean state
            from src.parsers.parser import Gem5StatsParser

            Gem5StatsParser.reset()

            facade = BackendFacade()
            variables = [
                {"name": "simTicks", "type": "scalar"},
                {"name": "system.cpu0.ipc", "type": "scalar"},
                {"name": "benchmark_name", "type": "configuration", "onEmpty": "Unknown"},
            ]

            # Trigger async parsing - REFACTORED to return FUTURES
            futures = facade.submit_parse_async(test_data_path, "stats.txt", variables, output_dir)

            assert isinstance(futures, list)
            assert len(futures) > 0

            # Wait for completion (Matching new explicit Wait Mechanism)
            results = []
            for future in as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)

            assert len(results) > 0

            # Finalize
            csv_path = facade.finalize_parsing(output_dir, results)
            assert csv_path and Path(csv_path).exists(), "results.csv was not created"

            # Check content
            df = pd.read_csv(csv_path)

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
