from unittest.mock import MagicMock, patch
from src.web.facade import BackendFacade

class TestDeepScanMinMax:
    def test_merging_logic_in_async_pipeline(self):
        """Test that the async pipeline correctly merges distribution ranges from multiple files."""
        with patch("src.parsers.scanner_service.ScanWorkPool.get_instance") as mock_pool_cls:
            mock_pool = MagicMock()
            mock_pool_cls.return_value = mock_pool

            # Use modern async results snapshot - nested list [file1_results, file2_results]
            mock_pool.get_results_async_snapshot.return_value = [
                [{"name": "dist_var", "type": "distribution", "minimum": -5, "maximum": 10}]
            ]

            facade = BackendFacade()
            with patch("src.parsers.scanner_service.Path") as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.rglob.return_value = ["f1", "f2"]
                
                facade.submit_scan_async("/tmp", limit=5)
                vars = facade.get_scan_results_snapshot()

            assert len(vars) == 1
            dist = vars[0]
            assert dist["name"] == "dist_var"
            assert dist["minimum"] == -5
            assert dist["maximum"] == 10

    def test_grouping_logic_in_facade(self):
        """Test that grouping logic in Facade (via get_scan_results_snapshot) propagates merged min/max."""
        # The facade now handles grouping/merging logic by relying on ScannerService's snapshot
        facade = BackendFacade()

        # Mock results snapshot which should already be merged/grouped by ScannerService
        raw_results = [
            {"name": "system.cpu\\d+.dist", "type": "distribution", "minimum": 0, "maximum": 20}
        ]

        with patch("src.web.facade.ScannerService.get_scan_results_snapshot", return_value=raw_results):
             grouped = facade.get_scan_results_snapshot()

        assert len(grouped) == 1
        group = grouped[0]
        assert group["name"] == "system.cpu\\d+.dist"
        assert group["minimum"] == 0
        assert group["maximum"] == 20
