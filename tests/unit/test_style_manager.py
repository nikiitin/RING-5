
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import plotly.graph_objects as go
from src.plotting.style_manager import StyleManager

@pytest.fixture
def style_manager():
    return StyleManager(plot_id=1, plot_type="bar")

@pytest.fixture
def mock_streamlit():
    with patch("src.plotting.style_manager.st") as mock_st:
        mock_st.session_state = {}
        # Mock columns
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]
        mock_st.columns.side_effect = columns_side_effect
        yield mock_st

def test_apply_styles_basic(style_manager):
    """Test applying basic layout styles."""
    fig = go.Figure()
    config = {
        "width": 1000,
        "height": 600,
        "title": "Test Plot",
        "plot_bgcolor": "#fafafa"
    }
    
    fig = style_manager.apply_styles(fig, config)
    
    assert fig.layout.width == 1000
    assert fig.layout.height == 600
    assert fig.layout.title.text == "Test Plot"
    assert fig.layout.plot_bgcolor == "#fafafa"

def test_apply_styles_legend(style_manager):
    """Test applying legend styles."""
    fig = go.Figure()
    config = {
        "legend_orientation": "h",
        "legend_x": 0.5,
        "legend_y": -0.2,
        "legend_font_size": 14,
        "legend_font_color": "black"
    }
    
    fig = style_manager.apply_styles(fig, config)
    
    assert fig.layout.legend.orientation == "h"
    assert fig.layout.legend.x == 0.5
    assert fig.layout.legend.font.size == 14

def test_apply_styles_axis(style_manager):
    """Test applying axis styles."""
    fig = go.Figure()
    config = {
        "xaxis_title": "X Axis",
        "xaxis_tickangle": -90,
        "grid_color": "#cccccc"
    }
    
    fig = style_manager.apply_styles(fig, config)
    
    assert fig.layout.xaxis.title.text == "X Axis"
    assert fig.layout.xaxis.tickangle == -90
    assert fig.layout.yaxis.gridcolor == "#cccccc"

def test_render_theme_options(style_manager, mock_streamlit):
    """Test rendering theme options UI."""
    saved_config = {"color_palette": "G10", "transparent_bg": False}
    
    # Mock return values for widgets
    mock_streamlit.selectbox.return_value = "G10"
    mock_streamlit.checkbox.return_value = False
    mock_streamlit.color_picker.return_value = "#ffffff"
    mock_streamlit.number_input.return_value = 12
    
    result = style_manager.render_theme_options(saved_config)
    
    assert result["color_palette"] == "G10"
    assert result["transparent_bg"] is False
    assert "plot_bgcolor" in result

def test_render_xaxis_labels_ui(style_manager, mock_streamlit):
    """Test X-axis renaming UI."""
    saved_config = {"x": "col1", "xaxis_labels": {"A": "Label A"}}
    data = pd.DataFrame({"col1": ["A", "B", "C"]})
    
    # Mock text input interaction
    # For A: return "Label A" (existing)
    # For B: return "New Label B"
    # For C: return ""
    mock_streamlit.text_input.side_effect = ["Label A", "New Label B", ""]
    
    result = style_manager.render_xaxis_labels_ui(saved_config, data)
    
    assert result["A"] == "Label A"
    assert result["B"] == "New Label B"
    assert "C" not in result

def test_render_layout_options(style_manager, mock_streamlit):
    """Test layout options rendering."""
    saved_config = {"width": 900}
    mock_streamlit.slider.return_value = 900
    mock_streamlit.number_input.return_value = 50
    mock_streamlit.checkbox.return_value = True
    
    result = style_manager.render_layout_options(saved_config)
    
    assert result["width"] == 900
    assert result["automargin"] is True
