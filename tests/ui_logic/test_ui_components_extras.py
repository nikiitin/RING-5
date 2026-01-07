
import pytest
import pandas as pd
import datetime
from unittest.mock import MagicMock, patch, ANY
from src.web.components import UIComponents

@pytest.fixture
def mock_streamlit():
    with patch("src.web.components.st") as mock_st:
        # Mock columns to return list of mocks
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]
        mock_st.columns.side_effect = columns_side_effect
        
        # Mock expander
        mock_st.expander.return_value.__enter__.return_value = MagicMock()
        
        yield mock_st

def test_show_data_preview(mock_streamlit):
    df = pd.DataFrame({
        "A": [1, 2, 3],
        "B": ["x", "y", "z"]
    })
    
    UIComponents.show_data_preview(df, "Test Preview", rows=2)
    
    mock_streamlit.markdown.assert_called_with("### Test Preview")
    mock_streamlit.dataframe.assert_called()
    # Check if metrics were called (4 columns)
    assert mock_streamlit.metric.call_count == 4

def test_show_column_details(mock_streamlit):
    df = pd.DataFrame({
        "A": [1, 2],
        "B": ["x", None]
    })
    
    UIComponents.show_column_details(df)
    
    # Should create a dataframe for details
    mock_streamlit.dataframe.assert_called()
    # Expander used
    mock_streamlit.expander.assert_called_with("Column Details")

def test_file_info_card(mock_streamlit):
    # Setup
    info = {
        "name": "test.csv",
        "size": 1024,
        "modified": 1678886400.0
    }
    
    # Mock buttons to return True sequence
    mock_streamlit.button.side_effect = [True, False, False] # Load clicked
    
    load, preview, delete = UIComponents.file_info_card(info, 0)
    
    assert load is True
    assert preview is False
    assert delete is False
    
    mock_streamlit.expander.assert_called()
    assert "test.csv" in mock_streamlit.expander.call_args[0][0]

def test_config_info_card(mock_streamlit):
    info = {
        "name": "conf1",
        "description": "desc",
        "modified": 1678886400.0
    }
    
    # Mock buttons: Load, Delete
    mock_streamlit.button.side_effect = [False, True] # Delete clicked
    
    load, delete = UIComponents.config_info_card(info, 1)
    
    assert load is False
    assert delete is True
    
    mock_streamlit.expander.assert_called()

def test_download_buttons(mock_streamlit):
    df = pd.DataFrame({"A": [1, 2]})
    
    # Mock NamedTemporaryFile
    with patch("tempfile.NamedTemporaryFile") as mock_tmp:
        mock_tmp.return_value.name = "/tmp/test.xlsx"
        
        # Mock pandas to_excel to avoid openpyxl/fs logic
        with patch("pandas.DataFrame.to_excel") as mock_to_excel:
            
            # Mock open to return bytes
            from unittest.mock import mock_open
            with patch("builtins.open", mock_open(read_data=b"dummy_excel_data")) as mock_file:
                
                UIComponents.download_buttons(df, "test_prefix")
                
                # Check calls
                assert mock_to_excel.called
                assert mock_streamlit.download_button.call_count == 3
                
                # Verify Excel button specifically
                # args[1] is data, args[2] is file_name, args[3] is mime in download_button params...
                # Actually checking call_args is better. 
                # Last call should be Excel
                _, kwargs = mock_streamlit.download_button.call_args
                assert kwargs["file_name"] == "test_prefix.xlsx"
                assert kwargs["data"] == b"dummy_excel_data"
