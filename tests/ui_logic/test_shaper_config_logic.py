
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.web.ui.shaper_config import configure_shaper

# Mock streamlit
@pytest.fixture
def mock_streamlit():
    with patch("src.web.ui.shaper_config.st") as mock_st:
        # Mock session state as a dict
        mock_st.session_state = {}
        
        # Side effect for columns
        def columns_side_effect(spec, gap="small", vertical_alignment="top"):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]
            
        mock_st.columns.side_effect = columns_side_effect
        yield mock_st

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "dataset": ["A", "A", "B", "B"],
        "metric": [10, 20, 30, 40],
        "category": ["X", "Y", "X", "Y"]
    })

def test_configure_column_selector(mock_streamlit, sample_data):
    """Test Column Selector configuration UI."""
    # Setup mock return values
    mock_streamlit.multiselect.return_value = ["metric"]
    
    config = configure_shaper("columnSelector", sample_data, 1, {})
    
    assert config["type"] == "columnSelector"
    assert config["columns"] == ["metric"]
    
    # Verify existing config usage
    existing = {"columns": ["dataset"]}
    configure_shaper("columnSelector", sample_data, 1, existing)
    # Check default was passed correctly
    kwargs = mock_streamlit.multiselect.call_args[1]
    assert kwargs["default"] == ["dataset"]

def test_configure_sort(mock_streamlit, sample_data):
    """Test Sort configuration UI."""
    mock_streamlit.selectbox.return_value = "dataset"
    
    # Mock order list management
    # Session state key: pNone_sort_order_list_1
    
    config = configure_shaper("sort", sample_data, 1, {})
    
    # Sort config logic puts order into session_state first
    assert config["type"] == "sort"
    assert "dataset" in config["order_dict"]
    
    # Test adding missing values interaction
    # (Simulated by mock interactions if we want deeper logic, but basic config return is good for now)

def test_configure_filter_numeric(mock_streamlit, sample_data):
    """Test Numeric Filter configuration UI."""
    # Filter on 'metric'
    mock_streamlit.selectbox.side_effect = ["metric", "greater_than"]
    mock_streamlit.number_input.return_value = 15.0
    
    config = configure_shaper("conditionSelector", sample_data, 1, {})
    
    assert config["type"] == "conditionSelector"
    assert config["column"] == "metric"
    assert config["mode"] == "greater_than"
    assert config["threshold"] == 15.0

def test_configure_filter_categorical(mock_streamlit, sample_data):
    """Test Categorical Filter configuration UI."""
    # Filter on 'dataset'
    mock_streamlit.selectbox.side_effect = ["dataset"]
    # Selectbox is first call (Select Column)
    
    mock_streamlit.multiselect.return_value = ["A"]
    
    config = configure_shaper("conditionSelector", sample_data, 1, {})
    
    assert config["type"] == "conditionSelector"
    assert config["column"] == "dataset"
    assert config["values"] == ["A"]

def test_configure_mean(mock_streamlit, sample_data):
    """Test Mean Calculator configuration UI."""
    # col1: algo, col2: vars, col3: group
    # Calls: selectbox(algo), multiselect(vars), multiselect(group), selectbox(replace)
    
    mock_streamlit.selectbox.side_effect = [
        "arithmean", # Mean type
        "category"   # Replacing column
    ]
    mock_streamlit.multiselect.side_effect = [
        ["metric"],  # Variables
        ["dataset"]  # Group by
    ]
    
    config = configure_shaper("mean", sample_data, 1, {})
    
    assert config["type"] == "mean"
    assert config["meanAlgorithm"] == "arithmean"
    assert config["meanVars"] == ["metric"]
    assert config["groupingColumns"] == ["dataset"]
    assert config["replacingColumn"] == "category"
