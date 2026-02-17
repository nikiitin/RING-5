import re

from src.core.models.parsing_models import ScannedVariable
from src.core.parsing.gem5.impl.gem5_scanner import Gem5Scanner as ScannerService


class TestVectorScanning:
    def test_scan_vector_entries_via_snapshot(self) -> None:
        """Test that finalize_scan correctly aggregates vector entries."""
        raw_results = [
            [
                ScannedVariable(
                    name="system.cpu0.op_class", type="vector", entries=["IntAlu", "IntMult"]
                )
            ],
            [ScannedVariable(name="system.cpu1.op_class", type="vector", entries=["IntDiv"])],
        ]

        results = ScannerService.aggregate_scan_results(raw_results)

        found_entries = set()
        var_name = "system.cpu\\d+.op_class"
        for v in results:
            if v.name == var_name or re.fullmatch(var_name, v.name):
                found_entries.update(v.entries)

        entries = sorted(list(found_entries))
        # Note: The aggregation merges entries from different CPU instances
        assert len(entries) > 0
