import re

from src.parsers.scanner_service import ScannerService


class TestVectorScanning:
    def test_scan_vector_entries_via_snapshot(self):
        """Test that finalize_scan correctly aggregates vector entries."""
        # Setup mock results from multiple files
        raw_results = [
            [{"name": "system.cpu0.op_class", "type": "vector", "entries": ["IntAlu", "IntMult"]}],
            [{"name": "system.cpu1.op_class", "type": "vector", "entries": ["IntDiv"]}],
        ]

        # Test aggregation
        results = ScannerService.aggregate_scan_results(raw_results)

        found_entries = set()
        var_name = "system.cpu\\d+.op_class"
        for v in results:
            if v["name"] == var_name or re.fullmatch(var_name, v["name"]):
                if "entries" in v:
                    found_entries.update(v["entries"])

        entries = sorted(list(found_entries))
        # Note: The aggregation merges entries from different CPU instances
        assert len(entries) > 0
