
import pytest
import sys
import tempfile
import pandas as pd
from pathlib import Path

# Add project root to path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.parsing.params import DataParserParams
from src.parsing.impl.data_parser_perl.dataParserPerl import DataParserPerl
from src.web.facade import BackendFacade

class TestParserFunctional:
    
    @pytest.fixture
    def test_data_path(self):
        """Path to the test data provided by the user (subset for speed)."""
        # Using the first subdirectory found to speed up test execution
        base_path = Path("/home/vnicolas/workspace/micro26-sens/results-micro26-sens")
        if not base_path.exists():
            pytest.skip(f"Test data not found at {base_path}")
        
        # Pick first subdirectory
        subdirs = [d for d in base_path.iterdir() if d.is_dir()]
        if not subdirs:
             pytest.skip(f"No subdirectories found in {base_path}")
             
        return str(subdirs[0])

    def test_parse_real_stats(self, test_data_path):
        """
        Test parsing actual gem5 stats files from the provided directory.
        Verifies that simTicks and IPC are correctly extracted.
        """
        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as output_dir:
            
            # Configuration for the parser
            # We want to extract simTicks and IPC
            variables = [
                {"name": "simTicks", "type": "scalar"},
                {"name": "system.cpu0.ipc", "type": "scalar"}
            ]
            
            # Use BackendFacade logic to create the params structure
            # mimicking how the web app does it, or construct manually to test Parser directly
            
            # Let's construct manually to test DataParserPerl directly as requested
            # but using the Facade helper to ensure we match app logic is smart.
            # However, for a unit test, explicit construction is better.
            
            parser_vars = [
                {"id": "simTicks", "type": "scalar"},
                {"id": "system.cpu0.ipc", "type": "scalar"},
                {"id": "benchmark_name", "type": "configuration", "onEmpty": "Unknown"}
            ]
            
            # Match strict directory structure expected by parser
            # The files are at test_data_path/**/stats.txt
            
            # Mock ConfigurationManager to avoid file system dependency for config files
            from unittest.mock import patch
            
            # The configuration expected by DataParserInterface/Perl
            parsings_config = [{
                "path": test_data_path,
                "files": "stats.txt",
                "vars": parser_vars
            }]
            
            # DataParserPerl calls:
            # 1. ConfigurationManager.getParser(params.get_json()) -> returns parsings list
            # 2. ConfigurationManager.getCompress(params.get_json()) -> returns string "True"/"False"
            
            with patch('src.parsing.config_manager.ConfigurationManager.getParser') as mock_get_parser, \
                 patch('src.parsing.config_manager.ConfigurationManager.getCompress') as mock_get_compress:
                
                mock_get_parser.return_value = parsings_config
                mock_get_compress.return_value = "False"
                
                # We can pass empty/dummy json to params since we mock the reader
                params = DataParserParams(config_json={"outputPath": output_dir})
                parser = DataParserPerl(params)
                
                # Execute parsing
                parser()
            
            # Verify results
            expected_csv = Path(output_dir) / "results.csv"
            assert expected_csv.exists(), "results.csv was not created"
            
            # Check content
            df = pd.read_csv(expected_csv)
            
            # Verify headers (Note: parser might rename headers or keep as is)
            # The parser typically writes columns with the variable ID
            assert "simTicks" in df.columns
            assert "system.cpu0.ipc" in df.columns
            
            # Verify we got rows
            assert len(df) > 0, "No data rows were parsed"
            
            # Verify no NA values in these columns (should be well-formed stats)
            assert not df["simTicks"].isnull().any()
            assert not df["system.cpu0.ipc"].isnull().any()
            
            # Check values are numeric and at least some are non-zero (assuming simulations ran)
            sim_ticks = pd.to_numeric(df["simTicks"])
            ipc = pd.to_numeric(df["system.cpu0.ipc"])
            
            if not (sim_ticks > 0).any():
                print("DEBUG: simTicks head:", df["simTicks"].head())
                pytest.fail("All simTicks are 0 or negative")
                
            if not (ipc > 0).any():
                print("DEBUG: IPC head:", df["system.cpu0.ipc"].head())
                pytest.fail("All IPC values are 0 or negative")



