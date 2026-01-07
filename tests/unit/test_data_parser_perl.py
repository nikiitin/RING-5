
import pytest
from unittest.mock import MagicMock, patch, mock_open
import os
from src.parsing.impl.data_parser_perl.dataParserPerl import DataParserPerl
from src.parsing.params import DataParserParams

@pytest.fixture
def mock_params():
    params = MagicMock(spec=DataParserParams)
    params.get_json.return_value = {}
    params.getOutputDir.return_value = "/tmp/output"
    return params

@pytest.fixture
def mock_config_manager():
    with patch("src.parsing.interface.ConfigurationManager") as mock_cm:
        mock_cm.getParser.return_value = []
        mock_cm.getCompress.return_value = "False"
        yield mock_cm

@pytest.fixture
def mock_work_pool():
    with patch("src.parsing.interface.ParseWorkPool") as mock_pool:
        instance = MagicMock()
        mock_pool.getInstance.return_value = instance
        yield instance

@pytest.fixture
def data_parser(mock_params, mock_config_manager, mock_work_pool):
    # Initialize with mocked dependencies
    parser = DataParserPerl(mock_params)
    return parser

def test_map_parsing_vars_valid(data_parser):
    """Test mapping of valid parsing variables."""
    vars_config = [
        {"id": "var1", "type": "scalar"},
        {"id": "var2", "type": "vector", "vectorEntries": "total,mean"},
        {"id": "var3", "type": "distribution", "minimum": 0, "maximum": 10},
        {"id": "var4", "type": "configuration"}
    ]
    
    with patch("src.utils.utils.checkElementExists"):
        with patch("src.utils.utils.getElementValue", side_effect=lambda obj, key: obj.get(key)):
            mapped = data_parser._mapParsingVars(vars_config)
    
    assert "var1" in mapped
    assert "var2" in mapped
    assert "var3" in mapped
    assert "var4" in mapped

def test_map_parsing_vars_duplicate_error(data_parser):
    """Test that duplicate variable IDs raise RuntimeError."""
    vars_config = [
        {"id": "var1", "type": "scalar"},
        {"id": "var1", "type": "scalar"}
    ]
    
    with patch("src.utils.utils.checkElementExists"), \
         patch("src.utils.utils.getElementValue", side_effect=lambda obj, key: obj.get(key)):
        
        with pytest.raises(RuntimeError, match="Variable already defined"):
            data_parser._mapParsingVars(vars_config)

def test_parse_stats_no_files(data_parser):
    """Test _parseStats with no files found."""
    # Setup config
    data_parser._parseConfig = [{"path": "/path", "files": "*.txt", "vars": []}]
    data_parser._shouldCompress = "False"
    
    with patch("glob.glob", return_value=[]), \
         patch("src.utils.utils.getElementValue", side_effect=lambda obj, key: obj.get(key)):
        
        # Should invoke Warning or log, but not crash
        # The code uses Warning("msg"), which constructs a Warning but doesn't raise or print unless caught?
        # Actually Warning("...") just creates an object. It might not do anything visible.
        # We just verify it runs through.
        data_parser._parseStats()
        
        # Verify no work added
        data_parser._parseWorkPool.addWork.assert_not_called()

def test_parse_stats_with_files(data_parser):
    """Test _parseStats with files found."""
    data_parser._parseConfig = [{
        "path": "/path", 
        "files": "*.txt", 
        "vars": [{"id": "v1", "type": "scalar"}]
    }]
    data_parser._shouldCompress = "False"
    
    with patch("glob.glob", return_value=["file1.txt"]), \
         patch("src.utils.utils.getElementValue", side_effect=lambda obj, key: obj.get(key)), \
         patch("src.utils.utils.checkElementExists"), \
         patch.object(data_parser, "_mapParsingVars", return_value={"v1": MagicMock()}):
            
            data_parser._parseStats()
            
            data_parser._parseWorkPool.startPool.assert_called_once()
            assert len(data_parser._parseWorkPool.addWork.call_args_list) == 1
            data_parser._parseWorkPool.getResults.assert_called_once()

def test_turn_into_csv_empty(data_parser):
    """Test _turnIntoCsv with no results."""
    data_parser._results = []
    
    # Should just return
    with patch("builtins.open", mock_open()) as m_open:
        data_parser._turnIntoCsv()
        m_open.assert_not_called()

def test_turn_into_csv_content(data_parser):
    """Test _turnIntoCsv with results containing scalar and vector."""
    data_parser._varsToParse = ["scalar_var", "vector_var"]
    
    # Mock result objects
    mock_scalar = MagicMock()
    mock_scalar.reducedContent = 10
    
    mock_vector = MagicMock()
    mock_vector.entries = ["0", "1"]
    mock_vector.reducedContent = {"0": 100, "1": 200}
    
    # Mock result dict
    result = {
        "scalar_var": mock_scalar,
        "vector_var": mock_vector
    }
    data_parser._results = [result]
    
    # Ensure types match for logic check
    # The code does: type(var).__name__. 
    # We need to mock the type name on the mock object?
    # Or wrap basic classes.
    
    class MockVar:
        def __init__(self, content, entries=None, name="Scalar"):
            self.reducedContent = content
            self.entries = entries
            self.name = name
        def balanceContent(self): pass
        def reduceDuplicates(self): pass
    
    # We patch tyoe(var).__name__ logic or use objects that result in correct names.
    # The code uses `type(var).__name__`.
    # Let's simple classes.
    class Scalar:
        def __init__(self): self.reducedContent = 10
        def balanceContent(self): pass
        def reduceDuplicates(self): pass
    
    class Vector:
        def __init__(self): 
            self.entries = ["0"]
            self.reducedContent = {"0": 20}
        def balanceContent(self): pass
        def reduceDuplicates(self): pass
        
    data_parser._results = [{
        "scalar_var": Scalar(),
        "vector_var": Vector()
    }]
    
    m_open = mock_open()
    with patch("builtins.open", m_open), \
         patch("os.makedirs"):
        
        data_parser._turnIntoCsv()
        
        m_open.assert_called_once()
        handle = m_open()
        
        # Check Header write
        # Header: scalar_var,vector_var..0
        # Check Data write
        # Line: 10,20
        
        writes = handle.write.call_args_list
        header = writes[0][0][0]
        assert "scalar_var" in header
        assert "vector_var..0" in header
        
        line = writes[1][0][0]
        assert "10,20" in line
