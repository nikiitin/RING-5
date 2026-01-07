
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, ANY
from src.plotting.style_manager import StyleManager
import plotly.graph_objects as go

@pytest.fixture
def mock_streamlit():
    with patch("src.plotting.style_manager.st") as mock_st:
        # Mock columns
        mock_st.columns.side_effect = lambda n: [MagicMock() for _ in range(n)] if isinstance(n, int) else [MagicMock() for _ in n]
        # Mock session_state
        mock_st.session_state = {}
        # Mock expander
        mock_st.expander.return_value.__enter__.return_value = MagicMock()
        yield mock_st

def test_render_series_styling_ui_full(mock_streamlit):
    # Setup data and config
    df = pd.DataFrame({"group": ["A", "B"], "val": [1, 2]})
    config = {"color": "group", "series_styles": {}}
    sm = StyleManager(1, "line")
    
    # Mock inputs
    # Loop over A and B
    # A: name, color, use_color, symbol, marker_size, line_width
    # B: name, color, use_color, symbol, marker_size, line_width
    
    # We need to ensure we return enough values for the loop
    # text_input (name): "A_new", "B_new"
    mock_streamlit.text_input.side_effect = ["A_new", "B_new"]
    # color_picker (color): "#ff0000", "#00ff00"
    mock_streamlit.color_picker.side_effect = ["#ff0000", "#00ff00"]
    # checkbox (use_color): True, False
    mock_streamlit.checkbox.side_effect = [True, False]
    # selectbox (symbol): "circle", "square"
    mock_streamlit.selectbox.side_effect = ["circle", "square"]
    # number_input (marker_size): 10, 12
    # number_input (line_width): 3, 4
    mock_streamlit.number_input.side_effect = [10, 3, 12, 4]
    
    styles = sm.render_series_styling_ui(config, df)
    
    assert styles["A"]["name"] == "A_new"
    assert styles["A"]["use_color"] is True
    assert styles["A"]["color"] == "#ff0000"
    assert styles["A"]["symbol"] == "circle"
    assert styles["A"]["marker_size"] == 10
    
    assert styles["B"]["name"] == "B_new"
    assert styles["B"]["use_color"] is False
    assert "color" not in styles["B"] # Popped
    
def test_render_xaxis_labels_ui_filtering(mock_streamlit):
    df = pd.DataFrame({"x": ["a", "b"]})
    config = {"x": "x", "xaxis_labels": {"a": "A_lbl"}}
    sm = StyleManager(1, "bar")
    
    # text_input calls: 'a' -> 'A_new', 'b' -> ''
    mock_streamlit.text_input.side_effect = ["A_new", ""]
    
    labels = sm.render_xaxis_labels_ui(config, df)
    
    assert labels["a"] == "A_new"
    assert "b" not in labels # Not added because empty string input

def test_apply_styles_palette_and_series(mock_streamlit):
    sm = StyleManager(1, "scatter")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1], y=[1], name="A"))
    fig.add_trace(go.Scatter(x=[2], y=[2], name="B"))
    
    config = {
        "color_palette": "Set1", # Non-Plotly palette
        "series_styles": {
            "A": {
                "use_color": True,
                "color": "#123456",
                "symbol": "square",
                "marker_size": 15,
                "line_width": 5
            }
        },
        "enable_stripes": True # Should be ignored for scatter
    }
    
    sm.apply_styles(fig, config)
    
    # Trace A (Custom)
    trace_a = fig.data[0]
    assert trace_a.marker.color == "#123456"
    assert trace_a.marker.symbol == "square"
    assert trace_a.marker.size == 15
    assert trace_a.line.width == 5
    
    # Trace B (Palette)
    trace_b = fig.data[1]
    # Set1 palette first color is usually red-ish, checking it's applied (not default)
    assert trace_b.marker.color is not None 
    assert trace_b.marker.color != "#123456"
    
def test_apply_styles_axis_labels_sorting(mock_streamlit):
    sm = StyleManager(1, "bar")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["b", "a"], y=[1, 2]))
    
    config = {
        "xaxis_labels": {"a": "Alpha", "b": "Beta"},
        # No xaxis_order, reliant on sorting
    }
    
    sm.apply_styles(fig, config)
    
    # Check layoutxaxis tickvals/ticktext
    layout = fig.layout
    assert layout.xaxis.tickmode == "array"
    # Should be sorted 'a', 'b'
    assert list(layout.xaxis.tickvals) == ["a", "b"]
    assert list(layout.xaxis.ticktext) == ["Alpha", "Beta"]

def test_apply_styles_axis_order(mock_streamlit):
    sm = StyleManager(1, "bar")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["b", "a", "c"], y=[1, 2, 3]))
    
    config = {
        "xaxis_labels": {"a": "Alpha"},
        "xaxis_order": ["c", "a", "b"]
    }
    
    sm.apply_styles(fig, config)
    
    layout = fig.layout
    # Should follow order
    assert list(layout.xaxis.categoryarray) == ["c", "a", "b"]
    # tickvals/text should also honor order if applied
    assert list(layout.xaxis.tickvals) == ["c", "a", "b"]
    # 'a' mapped, others default
    assert list(layout.xaxis.ticktext) == ["c", "Alpha", "b"]
