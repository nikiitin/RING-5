import os
from pathlib import Path

import pandas as pd
import pytest

from src.web.facade import BackendFacade


class TestGem5Parsing:
    """Integration tests for parsing real gem5 data."""

    TEST_DATA_DIR = Path("tests/data/results-micro26-sens")

    @pytest.fixture
    def facade(self):
        """Create a BackendFacade instance."""
        return BackendFacade()

    @pytest.fixture
    def output_dir(self, tmp_path):
        """Create a temporary output directory."""
        return tmp_path / "output"

    def test_scan_variables(self, facade):
        """Test scanning variables from real data."""
        if not self.TEST_DATA_DIR.exists():
            pytest.skip("Test data not found")

        # Use async API
        futures = facade.submit_scan_async(str(self.TEST_DATA_DIR), "stats.txt", limit=10)

        # Wait for all futures to complete
        results = []
        for future in futures:
            result = future.result(timeout=10)  # 10 second timeout
            if result:
                results.append(result)

        variables = facade.finalize_scan(results)
        assert len(variables) > 0

        # Check for common gem5 stats
        var_names = [v["name"] for v in variables]
        print(f"Discovered variables: {var_names[:10]}...")

        # We expect at least some standard stats (simTicks or other common gem5 vars)
        # Some test data may have different variable names, so check for multiple options
        common_vars = ["simTicks", "simSeconds", "hostSeconds", "size", "numCycles"]
        assert any(
            any(common_var in name for common_var in common_vars) for name in var_names
        ), f"Expected to find common gem5 variables, but got: {var_names[:5]}"

    def test_parse_workflow(self, facade, output_dir):
        """Test the full parsing workflow."""
        if not self.TEST_DATA_DIR.exists():
            pytest.skip("Test data not found")

        output_dir.mkdir()

        # 1. Scan for variables
        scan_futures = facade.submit_scan_async(str(self.TEST_DATA_DIR), "stats.txt", limit=10)

        # Wait for scan to complete
        scan_results = []
        for future in scan_futures:
            result = future.result(timeout=10)
            if result:
                scan_results.append(result)

        all_variables = facade.finalize_scan(scan_results)

        # 2. Select a few scalar variables
        selected_vars = [
            v
            for v in all_variables
            if v["type"] == "scalar"
            and ("simTicks" in v["name"] or "ipc" in v["name"] or "cycles" in v["name"])
        ][:5]

        if not selected_vars:
            # Fallback if specific names not found
            selected_vars = [v for v in all_variables if v["type"] == "scalar"][:5]

        print(f"Selected variables for parsing: {[v['name'] for v in selected_vars]}")

        # 3. Run Parser
        parse_futures = facade.submit_parse_async(
            stats_path=str(self.TEST_DATA_DIR),
            stats_pattern="stats.txt",
            variables=selected_vars,
            output_dir=str(output_dir),
            scanned_vars=all_variables,
        )

        # Wait for parsing to complete
        parse_results = []
        for future in parse_futures:
            result = future.result(timeout=30)
            if result:
                parse_results.append(result)

        csv_path = facade.finalize_parsing(str(output_dir), parse_results)

        assert csv_path is not None
        assert os.path.exists(csv_path)

        # 4. Verify CSV content
        df = pd.read_csv(csv_path)

        print(f"Parsed DataFrame Shape: {df.shape}")
        print(df.head())

        # Check Dimensions
        assert len(df) > 0

        # Check Columns
        # Expect selected variables + standard config columns (from directory structure or config.json if implicit)  # noqa: E501
        # Note: The Perl parser attempts to extract config from path if config.json not present.
        # Without config.json, it relies on path structure if configured.

        for var in selected_vars:
            assert var["name"] in df.columns

        # Verify presence of inferred columns.

    def test_histogram_parsing(self):
        """Test scanning and parsing a file containing histograms."""
        import shutil
        import tempfile

        # Create a fresh temp dir for this test.

        tmp_dir = Path(tempfile.mkdtemp())
        stats_dir = tmp_dir / "stats"
        output_dir = tmp_dir / "output"
        os.makedirs(stats_dir, exist_ok=True)

        # Create a stats file with a histogram
        # Format: name::range value
        hist_content = """
---------- Begin Simulation Statistics ----------
system.mem.ctrl::0-1023                       5      50.00%      50.00%      # Hist comment
system.mem.ctrl::1024-2047                    5      50.00%     100.00%      # Hist comment
"""
        with open(stats_dir / "stats.txt", "w") as f:
            f.write(hist_content)

        facade = BackendFacade()

        try:
            # 1. Scan
            scan_futures = facade.submit_scan_async(str(stats_dir), "stats.txt", limit=-1)

            # Wait for scan to complete
            scan_results = []
            for future in scan_futures:
                result = future.result(timeout=5)
                if result:
                    scan_results.append(result)

            vars_found = facade.finalize_scan(scan_results)
            hist_var = next((v for v in vars_found if v["name"] == "system.mem.ctrl"), None)

            assert hist_var is not None
            assert hist_var["type"] == "histogram"
            assert "0-1023" in hist_var.get("entries", [])
            assert "1024-2047" in hist_var.get("entries", [])

            # 2. Parse
            # Configure variables
            variables = [{"name": "system.mem.ctrl", "type": "histogram"}]

            parse_futures = facade.submit_parse_async(
                str(stats_dir), "stats.txt", variables, str(output_dir), scanned_vars=vars_found
            )

            # Wait for parsing to complete
            parse_results = []
            for future in parse_futures:
                result = future.result(timeout=10)
                if result:
                    parse_results.append(result)

            csv_path = facade.finalize_parsing(str(output_dir), parse_results)

            assert csv_path is not None
            assert os.path.exists(csv_path)

            # 3. Verify CSV Content
            df = pd.read_csv(csv_path)
            # Columns should be like system.mem.ctrl..0-1023
            assert "system.mem.ctrl..0-1023" in df.columns
            assert "system.mem.ctrl..1024-2047" in df.columns

            # Values should be 5.0 (the count)
            assert df["system.mem.ctrl..0-1023"].iloc[0] == 5.0

        finally:
            shutil.rmtree(tmp_dir)
