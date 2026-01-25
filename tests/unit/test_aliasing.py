from unittest.mock import mock_open, patch

from src.web.facade import BackendFacade


class TestAliasing:
    @patch("src.web.facade.Path")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.parsers.parser.Gem5StatsParser.builder")
    def test_aliasing_config_generation(self, mock_builder, mock_file_open, mock_path):
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

        # Mocking mkdir
        mock_path.return_value.mkdir.return_value = None

        # Mock the builder chain
        mock_instance = mock_builder.return_value
        mock_instance.with_path.return_value = mock_instance
        mock_instance.with_pattern.return_value = mock_instance
        mock_instance.with_variables.return_value = mock_instance
        mock_instance.with_output.return_value = mock_instance
        mock_instance.build.return_value.parse.return_value = "/tmp/result.csv"

        facade.parse_gem5_stats(stats_path, stats_pattern, variables, "/tmp")

        # Verify variables passed to builder
        call_args = mock_instance.with_variables.call_args
        assert call_args is not None, "with_variables not called"

        passed_vars = call_args[0][0]
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
