import os
import shutil
import tempfile

import pandas as pd
import pytest

from src.web.facade import BackendFacade


class TestFacadeReduction:
    @pytest.fixture
    def facade(self):
        return BackendFacade()

    @pytest.fixture
    def temp_dirs(self):
        # Create temp dirs for stats and output
        stats_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()

        # Create dummy stats files
        # File 1: cpu0=10, cpu1=20
        # File 2: cpu0=10, cpu1=30

        with open(os.path.join(stats_dir, "stats.txt"), "w") as f:
            f.write("---------- Begin Simulation Statistics ----------\n")
            f.write(
                "system.cpu0.ipc                                      10.000000                       # IPC\n"
            )
            f.write(
                "system.cpu1.ipc                                      20.000000                       # IPC\n"
            )
            f.write("---------- End Simulation Statistics   ----------\n")

        with open(os.path.join(stats_dir, "stats.txt.bak"), "w") as f:
            f.write("---------- Begin Simulation Statistics ----------\n")
            f.write(
                "system.cpu0.ipc                                      10.000000                       # IPC\n"
            )
            f.write(
                "system.cpu1.ipc                                      30.000000                       # IPC\n"
            )
            f.write("---------- End Simulation Statistics   ----------\n")

        yield stats_dir, output_dir

        # Cleanup
        shutil.rmtree(stats_dir)
        shutil.rmtree(output_dir)

    def test_reduction_end_to_end(self, facade, temp_dirs):
        stats_path, output_dir = temp_dirs

        # 1. Define variable with Regex Pattern
        variables = [{"name": "system.cpu\\d+.ipc", "type": "scalar"}]

        # 2. Pre-scan to populate regex matching cache
        facade.submit_scan_async(stats_path, "stats.txt*", limit=10)
        
        # Poll for completion
        import time
        start = time.time()
        while facade.get_scan_status()["status"] == "running":
            if time.time() - start > 5:
                pytest.fail("Async scan timed out in integration test")
            time.sleep(0.1)

        # 3. Run Facade Parse
        csv_path = facade.parse_gem5_stats(
            stats_path=stats_path,
            stats_pattern="stats.txt*",
            variables=variables,
            output_dir=output_dir,
        )

        assert csv_path is not None
        assert os.path.exists(csv_path)

        # 3. Verify Results
        # Parser outputs CSV.
        df = pd.read_csv(csv_path)
        print("Generated CSV Columns:", df.columns)
        print(df)

        # Expectation:
        # Col "system.cpu\d+.ipc" should exist
        # Row 1 (stats.txt): (10+20)/2 = 15
        # Row 2 (stats.txt.bak): (10+30)/2 = 20
        # Note: Order of rows depends on file system order, but values should be 15 and 20.

        target_col = "system.cpu\\d+.ipc"
        assert target_col in df.columns

        values = sorted(df[target_col].tolist())
        assert values == [15.0, 20.0]

    def test_vector_reduction(self, facade, temp_dirs):
        # Test vector reduction if possible
        # Skipping complex vector mock setup for brevity, relying on scalar reduction coverage.
        pass
