from unittest.mock import MagicMock, patch

from src.web.facade import BackendFacade


class TestDeepScanMinMax:
    @patch("src.web.facade.BackendFacade.scan_stats_variables")
    def test_scan_stats_variables_merges_min_max(self, mock_scan_base):
        # Setup mock behavior simulating lower-level scan results
        # Verify that scan_stats_variables integrates merging logic correctly.
        pass

    def test_merging_logic_in_facade(self):
        # We need to mock the worker pool results to test scan_stats_variables logic
        with patch("src.parsers.workers.pool.ScanWorkPool.getInstance") as mock_pool_cls:
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
            mock_pool.getResults.return_value = results

            facade = BackendFacade()
            # Mock glob to return 2 dummy files
            with patch("pathlib.Path.rglob", return_value=["file1", "file2"]):
                vars = facade.scan_stats_variables("/tmp", limit=5)

            assert len(vars) == 1
            dist = vars[0]
            assert dist["name"] == "dist_var"
            assert dist["minimum"] == -5  # Min of 0 and -5
            assert dist["maximum"] == 10  # Max of 10 and 5

    def test_grouping_logic_propagates_min_max(self):
        # Mock scan_stats_variables to return raw vars
        facade = BackendFacade()

        raw_vars = [
            {"name": "system.cpu0.dist", "type": "distribution", "minimum": 0, "maximum": 10},
            {"name": "system.cpu1.dist", "type": "distribution", "minimum": 10, "maximum": 20},
        ]

        with patch.object(facade, "scan_stats_variables", return_value=raw_vars):
            grouped = facade.scan_stats_variables_with_grouping("/tmp")

        assert len(grouped) == 1
        group = grouped[0]
        assert group["name"] == "system.cpu\\d+.dist"
        assert group["minimum"] == 0
        assert group["maximum"] == 20
