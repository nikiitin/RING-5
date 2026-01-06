
import pytest
from unittest.mock import MagicMock, patch, mock_open
from src.web.facade import BackendFacade
import json
from pathlib import Path

class TestAliasing:
    @patch("src.web.facade.Path")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    @patch("src.data_parser.src.dataParserFactory.DataParserFactory")
    def test_aliasing_config_generation(self, mock_factory, mock_json_dump, mock_file_open, mock_path):
        # Setup
        facade = BackendFacade()
        stats_path = "/tmp/stats"
        stats_pattern = "stats.txt"
        
        # Define variables with Alias
        variables = [
            {
                "name": "system.cpu.ipc",
                "type": "scalar",
                "alias": "IPC" # ALIAS!
            },
            {
                "name": "system.cpu.cpi",
                "type": "scalar"
                # No alias
            }
        ]
        
        # Calling the private method or checking the output file content?
        # parse_gem5_stats writes to a file. We mocked open and json.dump.
        # We need to mock pathlib Path to avoid actual file creation issues and to satisfy the method.
        
        # Mocking mkdir
        mock_path.return_value.mkdir.return_value = None
        
        facade.parse_gem5_stats(stats_path, stats_pattern, False, variables, "/tmp")
        
        # Verify JSON content passed to dump
        # The method writes TWO json files: parser_config and config_desc.
        # usually 1st call is parser_config.
        
        # Extract arguments from json.dump calls
        call_args_list = mock_json_dump.call_args_list
        assert len(call_args_list) >= 1
        
        # Find the call that looks like parser configuration
        parser_config = None
        for args, kwargs in call_args_list:
            data = args[0]
            if isinstance(data, list) and "parsings" in data[0]:
                parser_config = data
                break
                
        assert parser_config is not None, "Parser config not found in json.dump calls"
        
        parsing_vars = parser_config[0]["parsings"][0]["vars"]
        
        # Check Aliased Variable
        ipc_var = next((v for v in parsing_vars if v["id"] == "IPC"), None)
        assert ipc_var is not None, "Aliased variable IPC not found in config"
        assert ipc_var["parsed_ids"] == ["system.cpu.ipc"], "Aliased variable does not map original name"
        
        # Check Non-Aliased Variable
        cpi_var = next((v for v in parsing_vars if v["id"] == "system.cpu.cpi"), None)
        assert cpi_var is not None, "Non-aliased variable not found"
        assert "parsed_ids" not in cpi_var, "Non-aliased variable should not have parsed_ids"

