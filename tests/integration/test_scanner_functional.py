"""Integration tests for gem5 scanner functionality using futures."""

from pathlib import Path
import pytest
from src.web.facade import BackendFacade
from concurrent.futures import as_completed

class TestScannerFunctional:

    @pytest.fixture
    def test_data_path(self):
        """Path to the test data provided by the user."""
        base_path = Path("/home/vnicolas/workspace/micro26-sens/results-micro26-sens")
        if not base_path.exists():
            pytest.skip(f"Test data not found at {base_path}")
        return str(base_path)

    def test_scan_real_stats(self, test_data_path):
        """
        Test scanning actual gem5 stats files using valid futures.
        """
        facade = BackendFacade()
        
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
        assert "name" in sample_var
        assert "type" in sample_var
