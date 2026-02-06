"""Integration tests for gem5 scanner functionality using futures."""

from concurrent.futures import as_completed
from pathlib import Path

import pytest

from src.core.application_api import ApplicationAPI


class TestScannerFunctional:

    @pytest.fixture
    def test_data_path(self):
        """Path to the test data directory."""
        candidates = [
            Path("tests/data/results-micro26-sens"),
            Path("/home/vnicolas/workspace/micro26-sens/results-micro26-sens"),
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        pytest.skip("Test data not found")

    def test_scan_real_stats(self, test_data_path):
        """
        Test scanning actual gem5 stats files using valid futures.
        """
        facade = ApplicationAPI()

        # 1. Submit Scan
        futures = facade.submit_scan_async(test_data_path, "stats.txt", limit=5)

        assert isinstance(futures, list)
        assert len(futures) > 0

        # 2. Consume Futures
        results = []
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

        assert len(results) > 0

        # 3. Finalize/Aggregate
        scanned_vars = facade.finalize_scan(results)

        assert len(scanned_vars) > 0

        # Check integrity of a variable
        sample_var = scanned_vars[0]
        assert sample_var.name is not None
        assert sample_var.type is not None
