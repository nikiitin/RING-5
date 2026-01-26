from unittest.mock import MagicMock, mock_open, patch

from src.web.facade import BackendFacade


class TestAliasing:
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.parsers.parser.Gem5StatsParser.builder")
    def test_aliasing_config_generation(self, mock_builder, mock_file_open):
        # Setup
        facade = BackendFacade()
        stats_path = "/tmp/stats"
        stats_pattern = "stats.txt"

        # Define variables with Alias
        variables = [
            {"name": "system.cpu.ipc", "type": "scalar", "alias": "IPC"},  # ALIAS!
            {
                "name": "system.cpu.cpi",
                "type": "scalar",
                # No alias
            },
        ]

        # Mock the builder chain
        mock_instance = mock_builder.return_value
        mock_instance.with_path.return_value = mock_instance
        mock_instance.with_pattern.return_value = mock_instance
        mock_instance.with_variables.return_value = mock_instance
        mock_instance.with_output.return_value = mock_instance
        mock_instance.build.return_value.parse.return_value = "/tmp/result.csv"

        # Mock parser execution
        with patch("src.parsers.parse_service.ParseService.submit_parse_async") as mock_submit, \
             patch("src.parsers.parse_service.ParseService.construct_final_csv") as mock_construct:
            
            # Mock futures properly
            mock_future = MagicMock()
            mock_future.result = MagicMock(return_value={"data": "test"})
            mock_submit.return_value = [mock_future]
            mock_construct.return_value = "/tmp/result.csv"
            
            # Execute async parse
            parse_futures = facade.submit_parse_async(stats_path, stats_pattern, variables, "/tmp")
            results = [f.result() for f in parse_futures]
            csv_path = facade.finalize_parsing("/tmp", results)
            
            # Verify variables passed to parse service
            call_args = mock_submit.call_args
            assert call_args is not None, "submit_parse_async not called"

            passed_vars = call_args[0][2]  # Third argument is variables
        assert len(passed_vars) == 2

        # Check Aliased Variable
        ipc_var = next((v for v in passed_vars if v["name"] == "IPC"), None)
        assert ipc_var is not None, "Aliased variable IPC not found in config"
        assert ipc_var["parsed_ids"] == [
            "system.cpu.ipc"
        ], "Aliased variable does not map original name"

        # Check Non-Aliased Variable
        cpi_var = next((v for v in passed_vars if v["name"] == "system.cpu.cpi"), None)
        assert cpi_var is not None, "Non-aliased variable not found"
        assert "parsed_ids" not in cpi_var, "Non-aliased variable should not have parsed_ids"
        # Check Aliased Variable
        ipc_var = next((v for v in passed_vars if v["name"] == "IPC"), None)
        assert ipc_var is not None, "Aliased variable IPC not found in config"
        assert ipc_var["parsed_ids"] == [
            "system.cpu.ipc"
        ], "Aliased variable does not map original name"

        # Check Non-Aliased Variable
        cpi_var = next((v for v in passed_vars if v["name"] == "system.cpu.cpi"), None)
        assert cpi_var is not None, "Non-aliased variable not found"
        assert "parsed_ids" not in cpi_var, "Non-aliased variable should not have parsed_ids"
