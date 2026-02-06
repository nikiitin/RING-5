from concurrent.futures import as_completed
from pathlib import Path

import pandas as pd
import pytest

from src.parsers.models import StatConfig
from src.parsers.parser import Gem5StatsParser
from src.web.facade import BackendFacade


class TestParserFunctional:

    @pytest.fixture
    def test_data_path(self):
        """Path to the test data directory."""
        # Try multiple candidate paths
        candidates = [
            Path("tests/data/results-micro26-sens"),
            Path("/home/vnicolas/workspace/micro26-sens/results-micro26-sens"),
        ]

        for p in candidates:
            if p.exists():
                subdirs = [d for d in p.iterdir() if d.is_dir()]
                if subdirs:
                    return str(subdirs[0])

        pytest.skip("Test data not found")

    def test_parse_real_stats(self, test_data_path, tmp_path):
        """
        Test parsing actual gem5 stats files using the Backend Facade.
        """
        # Arrange
        output_dir = str(tmp_path / "parser_func_output")
        Path(output_dir).mkdir()

        Gem5StatsParser.reset()
        facade = BackendFacade()

        variables = [
            StatConfig(name="simTicks", type="scalar"),
            StatConfig(name="system.cpu0.ipc", type="scalar"),
            StatConfig(name="benchmark_name", type="configuration", params={"onEmpty": "Unknown"}),
        ]

        # Act
        futures = facade.submit_parse_async(test_data_path, "stats.txt", variables, output_dir)

        results = []
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

        csv_path = facade.finalize_parsing(output_dir, results)

        # Assert
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
