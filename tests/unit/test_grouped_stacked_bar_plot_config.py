
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.plotting.types.grouped_stacked_bar_plot import GroupedStackedBarPlot

@pytest.fixture
def mock_streamlit():
    with patch("src.plotting.types.grouped_stacked_bar_plot.st") as mock_st:
        mock_st.session_state = {}
        
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            return [MagicMock()]
        mock_st.columns.side_effect = columns_side_effect
        
        yield mock_st

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "Benchmark": ["A", "B"],
        "Config": ["Low", "High"],
        "Value": [10, 20],
        "Value2": [5, 15]
    })

def test_render_config_ui_basic(mock_streamlit, sample_data):
    """Test basic configuration UI rendering."""
    plot = GroupedStackedBarPlot(1, "Test Plot")
    saved_config = {"x": "Benchmark", "y_columns": ["Value"]}
    
    # Mocks for widgets
    # Col 1: X, Group
    # Text inputs: Title, XLabel, YLabel (3)
    # Then Renaming:
    #   Legend renames loops over y_columns (1 call: Value)
    #   X-axis renames loops over unique Benchmark (2 calls: A, B)
    #   Group renames (None, group is None)
    # Total Text Inputs: 3 + 1 + 2 = 6
    mock_streamlit.selectbox.side_effect = ["Benchmark", None]
    mock_streamlit.multiselect.return_value = ["Value"]
    mock_streamlit.text_input.side_effect = ["Title", "X Label", "Y Label", "Value", "A", "B"]
    
    config = plot.render_config_ui(sample_data, saved_config)
    
    assert config["x"] == "Benchmark"
    assert config["y_columns"] == ["Value"]
    assert config["group"] is None

def test_render_config_ui_grouped(mock_streamlit, sample_data):
    """Test configuration UI with grouping."""
    plot = GroupedStackedBarPlot(1, "Test Plot")
    saved_config = {"x": "Benchmark", "group": "Config", "y_columns": ["Value", "Value2"]}
    
    mock_streamlit.selectbox.side_effect = ["Benchmark", "Config"]
    mock_streamlit.multiselect.return_value = ["Value", "Value2"]
    
    # Text inputs: Title, XLabel, YLabel (3)
    # Then Renaming expander: 
    #   Legend renames loops over y_columns (2 calls)
    #   X-axis renames loops over unique Benchmark (2 calls: A, B)
    #   Group renames loops over unique Config (2 calls: Low, High)
    # Total Text Inputs: 3 + 2 + 2 + 2 = 9
    
    # We simplify by using a broad side effect or simpler expectations
    # Let's just mock returns to be "New Value" if needed, or pass through
    mock_streamlit.text_input.return_value = "Test Input"
    
    config = plot.render_config_ui(sample_data, saved_config)
    
    assert config["x"] == "Benchmark"
    assert config["group"] == "Config"
    assert len(config["y_columns"]) == 2

def test_render_config_filter_options(mock_streamlit, sample_data):
    """Test filter options rendering."""
    plot = GroupedStackedBarPlot(1, "Test Plot")
    saved_config = {"x": "Benchmark", "group": "Config", "y_columns": ["Value"]}
    
    # Mocking selectboxes is crucial for control flow
    mock_streamlit.selectbox.side_effect = ["Benchmark", "Config"]
    
    # Multiselects:
    # 1. Y-axis
    # 2. X Filter
    # 3. Group Filter
    
    def multiselect_side_effect(label, options, default=None, key=None, **kwargs):
        if "Statistics" in label:
            return ["Value"]
        if "Filter Benchmark" in label:
            return ["A"]
        if "Filter Config" in label:
             return ["Low"]
        return []
    
    mock_streamlit.multiselect.side_effect = multiselect_side_effect
    
    config = plot.render_config_ui(sample_data, saved_config)
    
    assert config["x_filter"] == ["A"]
    assert config["group_filter"] == ["Low"]

def test_create_figure_grouped_calculated(sample_data):
    """Test figure creation with calculated logic for grouping."""
    plot = GroupedStackedBarPlot(1, "Test")
    config = {
        "x": "Benchmark",
        "group": "Config",
        "y_columns": ["Value"],
        "bargap": 0.2,
        "bargroupgap": 0.1
    }
    
    fig = plot.create_figure(sample_data, config)
    
    # Check trace count (1 Y column => 1 trace per series?)
    # Implementation loops over y_columns and adds trace.
    # Color/Legend mapping is usually handled by BasePlot's style manager 
    # or implicit grouping?
    # Actually GSB adds one trace per Y column.
    
    assert len(fig.data) == 1
    trace = fig.data[0]
    
    # Check x coordinates
    # 2 Benchmarks * 2 configs = 4 bars total?
    # Data has 2 rows (A, Low) and (B, High).
    # So 2 bars.
    assert len(trace.x) == 2
    
    # Check customdata (totals)
    assert trace.customdata is not None
