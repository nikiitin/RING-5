
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.web.ui.components.data_manager_components import DataManagerComponents

@pytest.fixture
def mock_streamlit():
    with patch("src.web.ui.components.data_manager_components.st") as mock_st:
        # Mock session_state to support both attribute (state.x) and item (state['x']) access
        class MockState(dict):
            def __getattr__(self, key):
                return self.get(key)
            def __setattr__(self, key, value):
                self[key] = value
        
        mock_st.session_state = MockState()
        
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]
        mock_st.columns.side_effect = columns_side_effect
        
        mock_st.button.return_value = False
        
        yield mock_st

def test_render_summary_tab_stats(mock_streamlit):
    df = pd.DataFrame({
        "num": [1, 2, 3],
        "cat": ["a", "b", "a"],
        "mixed": [1.1, None, 3.3]
    })
    
    DataManagerComponents.render_summary_tab(df)
    
    mock_streamlit.dataframe.assert_called()
    # Check if describe() was called (by checking dataframe calls)
    # The code calls st.dataframe(numeric_data.describe()...)
    # It's hard to verify exact DataFrame content in mock call args easily without complex unpacking.
    # But we can verify execution flow.
    mock_streamlit.metric.assert_called()

def test_render_summary_tab_empty(mock_streamlit):
    df = pd.DataFrame()
    DataManagerComponents.render_summary_tab(df)
    mock_streamlit.info.assert_called() # "No numeric columns" or "No categorical columns"

def test_render_visualization_tab_search_all(mock_streamlit):
    df = pd.DataFrame({
        "A": ["foo", "bar"],
        "B": ["baz", "qux"]
    })
    
    # Search "foo" in "All Columns"
    mock_streamlit.selectbox.return_value = "All Columns"
    mock_streamlit.text_input.return_value = "foo"
    
    # Rows per page "All" to skip pagination logic complexity for now
    mock_streamlit.selectbox.side_effect = ["All Columns", "All"] 
    # Actually selectbox 2 is "Rows per page"
    # Wait, side_effect needs to match order of calls.
    # 1. Search column
    # 2. Rows per page
    
    mock_streamlit.selectbox.side_effect = ["All Columns", "All"]
    
    DataManagerComponents.render_visualization_tab(df)
    
    # Should show info with "Found 1 matching rows"
    mock_streamlit.info.assert_any_call("Found 1 matching rows (out of 2 total)")

def test_render_visualization_tab_search_specific(mock_streamlit):
    df = pd.DataFrame({
        "A": ["foo", "bar"],
        "B": ["foo", "qux"]
    })
    
    # Search "foo" in column "B" -> Should find 1 row (row 0: A=foo, B=foo. row 1: A=bar, B=qux. Wait.
    # Row 0: B=foo. Row 1: B=qux. 
    # Find "foo" in "B": 1 match.
    
    mock_streamlit.selectbox.side_effect = ["B", "All"]
    mock_streamlit.text_input.return_value = "foo"
    
    DataManagerComponents.render_visualization_tab(df)
    
    mock_streamlit.info.assert_any_call("Found 1 matching rows (out of 2 total)")

def test_render_visualization_tab_pagination(mock_streamlit):
    df = pd.DataFrame({"A": range(100)})
    
    # Search: None
    mock_streamlit.text_input.return_value = ""
    
    # Rows per page: 20
    mock_streamlit.selectbox.side_effect = ["All Columns", "20"]
    
    # Page input: 2
    mock_streamlit.number_input.return_value = 2
    
    DataManagerComponents.render_visualization_tab(df)
    
    # Should show rows 21-40 (indices 20-40)
    mock_streamlit.info.assert_any_call("Showing rows 21 to 40 of 100 (Page 2/5)")

def test_render_visualization_tab_download(mock_streamlit):
    df = pd.DataFrame({"A": [1]})
    
    mock_streamlit.text_input.return_value = ""
    mock_streamlit.selectbox.side_effect = ["All Columns", "All"]
    
    # Button click
    mock_streamlit.button.return_value = True
    
    DataManagerComponents.render_visualization_tab(df)
    
    mock_streamlit.download_button.assert_called()
