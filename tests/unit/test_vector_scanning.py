from unittest.mock import patch

from src.web.facade import BackendFacade


class TestVectorScanning:
    @patch("src.parsers.scanner_service.ScannerService.scan_stats_variables")
    def test_scan_vector_entries_delegation(self, mock_scan_service):
        """Test that Facade delegates to ScannerService and filters entries correctly."""
        # Setup mock return from ScannerService
        mock_scan_service.return_value = [
            {
                "name": "system.cpu.op_class",
                "type": "vector",
                "entries": ["IntAlu", "IntMult"]
            },
            {
                "name": "other.var",
                "type": "scalar"
            },
            {
                # Duplicate name to test aggregation (if multiple files scanned)
                "name": "system.cpu.op_class",
                "type": "vector",
                "entries": ["IntDiv"]
            }
        ]

        facade = BackendFacade()
        entries = facade.scan_vector_entries("/path/to/stats", "system.cpu.op_class")

        # Verify delegation
        mock_scan_service.assert_called_with("/path/to/stats", "stats.txt", 10)

        # Verify aggregation and sorting
        assert isinstance(entries, list)
        assert sorted(entries) == ["IntAlu", "IntDiv", "IntMult"]

    @patch("src.parsers.scanner_service.ScannerService.scan_stats_variables")
    def test_scan_vector_entries_no_match(self, mock_scan_service):
        """Test scanning when variable is not found."""
        mock_scan_service.return_value = [
            {"name": "other.var", "type": "scalar"}
        ]

        facade = BackendFacade()
        entries = facade.scan_vector_entries("/path", "system.cpu.op_class")

        assert entries == []
