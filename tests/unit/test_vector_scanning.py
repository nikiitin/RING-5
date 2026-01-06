
import pytest
from unittest.mock import MagicMock, patch, mock_open
from src.web.facade import BackendFacade
from pathlib import Path

class TestVectorScanning:
    @patch("src.web.facade.Path")
    def test_scan_vector_entries_logic(self, mock_path):
        # Setup facade
        facade = BackendFacade()
        
        # Mock file system interactions
        mock_stats_dir = MagicMock()
        mock_path.return_value = mock_stats_dir
        mock_stats_dir.exists.return_value = True
        
        # Mock finding files
        # We need rglob to return valid path objects.
        # The facade iterates over them and calls open(file_path).
        # We need file_path to be something that builtins.open accepts.
        
        # Facade calls: files = list(search_path.rglob(file_pattern))
        # Then: for file_path in files[:100]:
        #           with open(file_path, ...)
        
        file_path_str = "/tmp/stats/stats.txt"
        mock_file_path = MagicMock(spec=Path)
        mock_file_path.__str__.return_value = file_path_str
        # When opened, it should trigger our mocked open. open(MagicMock) might fail if not str.
        # Facade iterates 'files'.
        
        mock_stats_dir.rglob.return_value = [file_path_str] # Return STRINGS directly to simplify open() mocking if Facade handles strings?
        # Facade: files = list(search_path.rglob(...)) -> rglob returns Paths usually.
        # Facade loop: for file_path in files... open(file_path)
        # open() accepts Path objects.
        
        # Let's verify what Facade does. It does: files = list(search_path.rglob(file_pattern))
        # So it expects Path objects.
        
        # To make patch("builtins.open") work with a specific file, we usually use side_effect or just return content for ANY file since we iterate 1 file.
        
        # The issue might be that open(mock_object) is not working as expected with mock_open.
        # Let's mock rglob to return a string, since open() works with strings.
        # rglob *should* return Paths, but python duck typing.
        
        # Wait, Facade line 762: files = list(search_path.rglob(file_pattern))
        # line 779: with open(file_path, ...)
        
        mock_stats_dir.rglob.return_value = ["/tmp/stats/stats.txt"]
        
        # Mock file content reading
        # Content with valid vector entries and some noise
        stats_content = """
        ---------- Begin Simulation Statistics ----------
        sim_seconds                                  0.000244                       # Number of seconds simulated
        system.cpu.op_class::IntAlu                     14501                       # Class of instruction: IntAlu
        system.cpu.op_class::IntMult                        0                       # Class of instruction: IntMult
        system.cpu.op_class::IntDiv                         0                       # Class of instruction: IntDiv
        system.cpu.op_class::FloatAdd                       0                       # Class of instruction: FloatAdd
        system.cpu.ipc                               0.500000                       # IPC
        """
        
        with patch("builtins.open", mock_open(read_data=stats_content)):
            entries = facade.scan_vector_entries("/tmp/stats", "system.cpu.op_class", "stats.txt")
            
        # Verify results
        assert isinstance(entries, list)
        assert "IntAlu" in entries
        assert "IntMult" in entries
        assert "IntDiv" in entries
        assert "FloatAdd" in entries
        assert "FloatAdd" in entries # Duplicates should be handled by set logic inside, but list returned
        
        # standard gem5 stats often have multiple dumps, so we might see simulated seconds again etc.
        # But for vector entries, they are usually static per dump or identical set.
        
        # Check that we retrieved exactly the expected entries
        expected = ["FloatAdd", "IntAlu", "IntDiv", "IntMult"]
        assert sorted(entries) == sorted(expected)

    @patch("src.web.facade.Path")
    def test_scan_vector_entries_no_match(self, mock_path):
        facade = BackendFacade()
        mock_stats_dir = MagicMock()
        mock_path.return_value = mock_stats_dir
        mock_stats_dir.exists.return_value = True
        mock_stats_dir.rglob.return_value = [MagicMock()] # 1 file
        
        stats_content = """
        system.cpu.ipc 1.0
        """
        
        with patch("builtins.open", mock_open(read_data=stats_content)):
             entries = facade.scan_vector_entries("/tmp/stats", "system.cpu.op_class")
             
        assert entries == []

