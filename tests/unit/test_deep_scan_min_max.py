class TestDeepScanMinMax:
    def test_merging_logic_in_async_pipeline(self) -> None:
        """Test that the async pipeline correctly merges distribution ranges from multiple files."""
        from src.core.models.parsing_models import ScannedVariable
        from src.core.parsing.gem5.impl.gem5_scanner import Gem5Scanner as ScannerService

        raw_results = [
            [ScannedVariable(name="dist_var", type="distribution", minimum=-5, maximum=10)],
            [ScannedVariable(name="dist_var", type="distribution", minimum=-10, maximum=15)],
        ]

        vars = ScannerService.aggregate_scan_results(raw_results)

        assert len(vars) == 1
        dist = vars[0]
        assert dist.name == "dist_var"
        assert dist.minimum == -10
        assert dist.maximum == 15

    def test_grouping_logic_in_facade(self) -> None:
        """Test that grouping logic works via finalize_scan."""
        from src.core.models.parsing_models import ScannedVariable
        from src.core.parsing.gem5.impl.gem5_scanner import Gem5Scanner as ScannerService

        raw_results = [
            [
                ScannedVariable(
                    name="system.cpu\\d+.dist", type="distribution", minimum=0, maximum=20
                )
            ]
        ]

        grouped = ScannerService.aggregate_scan_results(raw_results)

        assert len(grouped) == 1
        group = grouped[0]
        assert group.name == "system.cpu\\d+.dist"
        assert group.minimum == 0
        assert group.maximum == 20
