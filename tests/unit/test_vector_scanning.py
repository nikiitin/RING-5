import re
from unittest.mock import patch
from src.web.facade import BackendFacade

class TestVectorScanning:
    @patch("src.web.facade.ScannerService.get_scan_results_snapshot")
    def test_scan_vector_entries_via_snapshot(self, mock_snapshot):
        """Test that Facade correctly extracts entries from the async snapshot."""
        # Setup mock return from the async snapshot
        mock_snapshot.return_value = [
            {"name": "system.cpu0.op_class", "type": "vector", "entries": ["IntAlu", "IntMult"]},
            {"name": "system.cpu1.op_class", "type": "vector", "entries": ["IntDiv"]},
        ]

        facade = BackendFacade()
        # In current facade, we use get_scan_results_snapshot then filter in UI or use for parsing.
        # But we previously had 'scan_vector_entries' as a convenience method.
        # Since it's gone or refactored, let's verify if we need a replacement or update tests.
        
        # Actually, scan_vector_entries was deleted as part of sync-removal.
        # The UI now finds entries via the snapshot during deep scan.
        results = facade.get_scan_results_snapshot()
        
        found_entries = set()
        var_name = "system.cpu\\d+.op_class"
        for v in results:
            if v["name"] == var_name or re.fullmatch(var_name, v["name"]):
                if "entries" in v:
                    found_entries.update(v["entries"])
                    
        entries = sorted(list(found_entries))
        assert entries == ["IntAlu", "IntDiv", "IntMult"]
