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

        variables = facade.scan_stats_variables(str(self.TEST_DATA_DIR), "stats.txt", limit=10)

        assert len(variables) > 0

        # Check for common gem5 stats
        var_names = [v["name"] for v in variables]
        print(f"Discovered variables: {var_names[:10]}...")

        # We expect at least some standard stats
        assert any("simTicks" in name for name in var_names)

    def test_parse_workflow(self, facade, output_dir):
        """Test the full parsing workflow."""
        if not self.TEST_DATA_DIR.exists():
            pytest.skip("Test data not found")

        output_dir.mkdir()

        # 1. Scan for variables
        all_variables = facade.scan_stats_variables(str(self.TEST_DATA_DIR), "stats.txt", limit=10)

        # 2. Select a few scalar variables
        # Filter for scalar types and pick top 5
        selected_vars = [
            v
            for v in all_variables
            if v["type"] == "scalar"
            and "simTicks" in v["name"]
            or "ipc" in v["name"]
            or "cycles" in v["name"]
        ][:5]

        if not selected_vars:
            # Fallback if specific names not found
            selected_vars = [v for v in all_variables if v["type"] == "scalar"][:5]

        print(f"Selected variables for parsing: {[v['name'] for v in selected_vars]}")

        # 3. Run Parser
        csv_path = facade.parse_gem5_stats(
            stats_path=str(self.TEST_DATA_DIR),
            stats_pattern="stats.txt",
            compress=False,
            variables=selected_vars,
            output_dir=str(output_dir),
        )

        assert csv_path is not None
        assert os.path.exists(csv_path)

        # 4. Verify CSV content
        df = pd.read_csv(csv_path)

        print(f"Parsed DataFrame Shape: {df.shape}")
        print(df.head())

        # Check Dimensions
        assert len(df) > 0

        # Check Columns
        # Expect selected variables + standard config columns (from directory structure or config.json if implicit)
        # Note: The Perl parser attempts to extract config from path if config.json not present?
        # Actually without config.json, it might relies on path structure if configured.
        # But 'simTicks' should be there.

        for var in selected_vars:
            assert var["name"] in df.columns

        # Check for inferred columns (benchmark, config, seed)
        # The parser logic usually adds 'benchmark', 'config' etc if it can infer them or if provided in separate config.
        # Let's check what we got.
