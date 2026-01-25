from unittest.mock import MagicMock, patch

from src.web.facade import BackendFacade


class TestDeepScanMinMax:
    def test_merging_logic_in_scanner_service(self):
        """Test that ScannerService correctly merges distribution ranges from multiple files."""
        # Setup mock for the pool used inside ScannerService
        # ScannerService imports ParseWorkPool as ScanWorkPool
        with patch("src.parsers.scanner_service.ScanWorkPool.get_instance") as mock_pool_cls:
            mock_pool = MagicMock()
            mock_pool_cls.return_value = mock_pool

            # Simulate results from 2 files
            # File 1: dist_var min=0 max=10
            # File 2: dist_var min=-5 max=5
            results = [
                [
                    {
                        "name": "dist_var",
                        "type": "distribution",
                        "entries": ["0", "10"],
                        "minimum": 0,
                        "maximum": 10,
                    }
                ],
                [
                    {
                        "name": "dist_var",
                        "type": "distribution",
                        "entries": ["-5", "5"],
                        "minimum": -5,
                        "maximum": 5,
                    }
                ],
            ]
            mock_pool.get_results.return_value = results

            facade = BackendFacade()
            # Mock Path and exists to allow execution
            with patch("src.parsers.scanner_service.Path") as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.rglob.return_value = ["f1", "f2"]
                vars = facade.scan_stats_variables("/tmp", limit=5)

            assert len(vars) == 1
            dist = vars[0]
            assert dist["name"] == "dist_var"
            assert dist["minimum"] == -5
            assert dist["maximum"] == 10

    def test_grouping_logic_propagates_min_max(self):
        """Test that grouping logic in ScannerService propagates merged min/max."""
        facade = BackendFacade()

        raw_vars = [
            {"name": "system.cpu0.dist", "type": "distribution", "minimum": 0, "maximum": 10},
            {"name": "system.cpu1.dist", "type": "distribution", "minimum": 10, "maximum": 20},
        ]

        # Patch ScannerService.scan_stats_variables directly to test grouping logic
        with patch(
            "src.parsers.scanner_service.ScannerService.scan_stats_variables", return_value=raw_vars
        ):
            grouped = facade.scan_stats_variables_with_grouping("/tmp")

        assert len(grouped) == 1
        group = grouped[0]
        assert group["name"] == "system.cpu\\d+.dist"
        assert group["minimum"] == 0
        assert group["maximum"] == 20
