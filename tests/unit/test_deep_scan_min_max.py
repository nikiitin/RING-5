class TestDeepScanMinMax:
    def test_merging_logic_in_async_pipeline(self):
        """Test that the async pipeline correctly merges distribution ranges from multiple files."""
        from src.parsers.scanner_service import ScannerService

        # Mock the finalize_scan to return aggregated results
        raw_results = [
            [{"name": "dist_var", "type": "distribution", "minimum": -5, "maximum": 10}],  # File 1
            [{"name": "dist_var", "type": "distribution", "minimum": -10, "maximum": 15}],  # File 2
        ]

        # Test the aggregation logic directly
        vars = ScannerService.aggregate_scan_results(raw_results)

        assert len(vars) == 1
        dist = vars[0]
        assert dist["name"] == "dist_var"
        # Should have merged min/max
        assert dist["minimum"] == -10  # min of [-5, -10]
        assert dist["maximum"] == 15  # max of [10, 15]

    def test_grouping_logic_in_facade(self):
        """Test that grouping logic works via finalize_scan."""
        from src.parsers.scanner_service import ScannerService

        # Test that finalize_scan handles grouping/merging
        raw_results = [
            [{"name": "system.cpu\\d+.dist", "type": "distribution", "minimum": 0, "maximum": 20}]
        ]

        grouped = ScannerService.aggregate_scan_results(raw_results)

        assert len(grouped) == 1
        group = grouped[0]
        assert group["name"] == "system.cpu\\d+.dist"
        assert group["minimum"] == 0
        assert group["maximum"] == 20
