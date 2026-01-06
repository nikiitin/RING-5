"""
Comprehensive tests for StyleManager.
Tests theme options, layout, and style application.
"""

import pytest
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.plotting.style_manager import StyleManager


@pytest.fixture
def sample_dataframe():
    """Create sample data for style testing."""
    return pd.DataFrame({
        "x": ["A", "B", "C"],
        "y": [1, 2, 3],
        "group": ["G1", "G1", "G2"]
    })


@pytest.fixture
def bar_style_manager():
    """Create a StyleManager for bar plots."""
    return StyleManager(plot_id=1, plot_type="bar")


@pytest.fixture
def line_style_manager():
    """Create a StyleManager for line plots."""
    return StyleManager(plot_id=2, plot_type="line")


@pytest.fixture
def grouped_bar_style_manager():
    """Create a StyleManager for grouped bar plots."""
    return StyleManager(plot_id=3, plot_type="grouped_bar")


class TestStyleManagerInit:
    """Tests for StyleManager initialization."""

    def test_init_with_bar_type(self):
        """Test initialization with bar plot type."""
        manager = StyleManager(plot_id=1, plot_type="bar")
        assert manager.plot_id == 1
        assert manager.plot_type == "bar"

    def test_init_with_line_type(self):
        """Test initialization with line plot type."""
        manager = StyleManager(plot_id=2, plot_type="line")
        assert manager.plot_id == 2
        assert manager.plot_type == "line"

    def test_init_with_scatter_type(self):
        """Test initialization with scatter plot type."""
        manager = StyleManager(plot_id=3, plot_type="scatter")
        assert manager.plot_id == 3
        assert manager.plot_type == "scatter"


class TestGetLegendColumn:
    """Tests for get_legend_column method."""

    def test_get_color_column(self, bar_style_manager):
        """Test getting color column."""
        config = {"color": "group", "x": "x", "y": "y"}
        result = bar_style_manager.get_legend_column(config)
        assert result == "group"

    def test_get_group_column(self, bar_style_manager):
        """Test getting group column when color not present."""
        config = {"group": "category", "x": "x", "y": "y"}
        result = bar_style_manager.get_legend_column(config)
        assert result == "category"

    def test_no_legend_column(self, bar_style_manager):
        """Test when no legend column present."""
        config = {"x": "x", "y": "y"}
        result = bar_style_manager.get_legend_column(config)
        assert result is None


class TestApplyStyles:
    """Tests for apply_styles method."""

    def test_apply_basic_dimensions(self, bar_style_manager):
        """Test applying basic dimensions to figure."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        config = {"width": 1000, "height": 600}
        
        result = bar_style_manager.apply_styles(fig, config)
        
        assert result.layout.width == 1000
        assert result.layout.height == 600

    def test_apply_margins(self, bar_style_manager):
        """Test applying margins to figure."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        config = {
            "margin_l": 100,
            "margin_r": 50,
            "margin_t": 60,
            "margin_b": 80,
            "margin_pad": 10
        }
        
        result = bar_style_manager.apply_styles(fig, config)
        
        assert result.layout.margin.l == 100
        assert result.layout.margin.r == 50
        assert result.layout.margin.t == 60
        assert result.layout.margin.b == 80
        assert result.layout.margin.pad == 10

    def test_apply_bargap(self, bar_style_manager):
        """Test applying bar gap to bar chart."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        config = {"bargap": 0.3}
        
        result = bar_style_manager.apply_styles(fig, config)
        
        assert result.layout.bargap == 0.3

    def test_apply_bargroupgap(self, grouped_bar_style_manager):
        """Test applying bar group gap to grouped bar chart."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        config = {"bargroupgap": 0.1}
        
        result = grouped_bar_style_manager.apply_styles(fig, config)
        
        assert result.layout.bargroupgap == 0.1

    def test_apply_background_colors(self, bar_style_manager):
        """Test applying background colors."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        config = {
            "plot_bgcolor": "#f0f0f0",
            "paper_bgcolor": "#ffffff"
        }
        
        result = bar_style_manager.apply_styles(fig, config)
        
        assert result.layout.plot_bgcolor == "#f0f0f0"
        assert result.layout.paper_bgcolor == "#ffffff"

    def test_apply_transparent_background(self, bar_style_manager):
        """Test applying transparent background."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        config = {
            "plot_bgcolor": "rgba(0,0,0,0)",
            "paper_bgcolor": "rgba(0,0,0,0)"
        }
        
        result = bar_style_manager.apply_styles(fig, config)
        
        assert result.layout.plot_bgcolor == "rgba(0,0,0,0)"

    def test_apply_xaxis_ticket_angle(self, bar_style_manager):
        """Test applying x-axis tick angle."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        config = {"xaxis_tickangle": -60}
        
        result = bar_style_manager.apply_styles(fig, config)
        
        assert result.layout.xaxis.tickangle == -60

    def test_apply_legend_settings(self, bar_style_manager):
        """Test applying legend settings."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        config = {
            "legend_font_color": "#333333",
            "legend_font_size": 14,
            "legend_bgcolor": "#f5f5f5",
            "legend_border_width": 2,
            "legend_border_color": "#000000"
        }
        
        result = bar_style_manager.apply_styles(fig, config)
        
        assert result.layout.legend.font.color == "#333333"
        assert result.layout.legend.font.size == 14
        assert result.layout.legend.bgcolor == "#f5f5f5"
        assert result.layout.legend.borderwidth == 2
        assert result.layout.legend.bordercolor == "#000000"

    def test_apply_legend_title(self, bar_style_manager):
        """Test applying legend title."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2], name="Series 1")])
        config = {"legend_title": "My Legend"}
        
        result = bar_style_manager.apply_styles(fig, config)
        
        assert result.layout.legend.title.text == "My Legend"

    def test_apply_legend_title_styling(self, bar_style_manager):
        """Test applying legend title font size and color."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2], name="Series 1")])
        config = {
            "legend_title": "My Legend",
            "legend_title_font_color": "#ff0000",
            "legend_title_font_size": 20
        }
        
        result = bar_style_manager.apply_styles(fig, config)
        
        assert result.layout.legend.title.text == "My Legend"
        assert result.layout.legend.title.font.color == "#ff0000"
        assert result.layout.legend.title.font.size == 20


class TestApplySeriesStyling:
    """Tests for _apply_series_styling method."""

    def test_apply_custom_color(self, bar_style_manager):
        """Test applying custom color to series."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2], name="Series1")])
        config = {
            "series_styles": {
                "Series1": {"use_color": True, "color": "#ff0000"}
            }
        }
        
        bar_style_manager._apply_series_styling(fig, config)
        
        assert fig.data[0].marker.color == "#ff0000"

    def test_apply_palette(self, bar_style_manager):
        """Test applying color palette."""
        fig = go.Figure(data=[
            go.Bar(x=["A"], y=[1], name="S1"),
            go.Bar(x=["A"], y=[2], name="S2")
        ])
        config = {"color_palette": "Set1"}
        
        bar_style_manager._apply_series_styling(fig, config)
        
        # Both traces should have colors from Set1 palette
        assert fig.data[0].marker.color is not None
        assert fig.data[1].marker.color is not None

    def test_apply_symbol(self, line_style_manager):
        """Test applying marker symbol for line/scatter."""
        fig = go.Figure(data=[go.Scatter(x=[1, 2], y=[1, 2], name="Series1", mode='markers')])
        config = {
            "series_styles": {
                "Series1": {"symbol": "diamond"}
            }
        }
        
        line_style_manager._apply_series_styling(fig, config)
        
        assert fig.data[0].marker.symbol == "diamond"

    def test_apply_pattern(self, bar_style_manager):
        """Test applying bar pattern."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2], name="Series1")])
        config = {
            "series_styles": {
                "Series1": {"pattern": "/"}
            }
        }
        
        bar_style_manager._apply_series_styling(fig, config)
        
        assert fig.data[0].marker.pattern.shape == "/"

    def test_apply_stripes_global(self, bar_style_manager):
        """Test applying global stripes to bars."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2], name="Series1")])
        config = {"enable_stripes": True}
        
        bar_style_manager._apply_series_styling(fig, config)
        
        assert fig.data[0].marker.pattern.shape == "/"

    def test_custom_color_overrides_palette(self, bar_style_manager):
        """Test that custom color takes priority over palette."""
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="S1")])
        config = {
            "color_palette": "Set1",
            "series_styles": {
                "S1": {"use_color": True, "color": "#123456"}
            }
        }
        
        bar_style_manager._apply_series_styling(fig, config)
        
        assert fig.data[0].marker.color == "#123456"


class TestPaletteResolution:
    """Tests for color palette resolution."""

    def test_all_palettes_resolve(self, bar_style_manager):
        """Test that all available palettes can be resolved."""
        available_palettes = ["G10", "T10", "Alphabet", "Dark24", "Light24", 
                            "Pastel", "Set1", "Set2", "Set3", "Safe", "Vivid"]
        
        for palette in available_palettes:
            fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="S1")])
            config = {"color_palette": palette}
            
            # Should not raise
            bar_style_manager._apply_series_styling(fig, config)
            
            # Trace should have a color assigned
            assert fig.data[0].marker.color is not None

    def test_default_plotly_palette(self, bar_style_manager):
        """Test that Plotly default palette doesn't apply custom colors."""
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="S1")])
        original_color = fig.data[0].marker.color
        
        config = {"color_palette": "Plotly"}
        bar_style_manager._apply_series_styling(fig, config)
        
        # Color should remain unchanged (Plotly default handling)
        assert fig.data[0].marker.color == original_color


class TestLineStyleManager:
    """Specific tests for line plot styling."""

    def test_line_with_markers(self, line_style_manager):
        """Test styling line plot with markers."""
        fig = go.Figure(data=[
            go.Scatter(x=[1, 2, 3], y=[1, 2, 3], name="Line1", mode='lines+markers')
        ])
        config = {
            "series_styles": {
                "Line1": {"symbol": "square", "use_color": True, "color": "#00ff00"}
            }
        }
        
        result = line_style_manager.apply_styles(fig, config)
        
        assert result.data[0].marker.symbol == "square"
        assert result.data[0].marker.color == "#00ff00"


class TestComplexConfig:
    """Tests with complex configurations."""

    def test_full_config_application(self, grouped_bar_style_manager):
        """Test applying a full configuration."""
        fig = go.Figure(data=[
            go.Bar(x=["A", "B"], y=[1, 2], name="Group1"),
            go.Bar(x=["A", "B"], y=[3, 4], name="Group2")
        ])
        
        config = {
            "width": 1200,
            "height": 700,
            "margin_l": 120,
            "margin_r": 100,
            "margin_t": 80,
            "margin_b": 90,
            "margin_pad": 5,
            "plot_bgcolor": "#fafafa",
            "paper_bgcolor": "#ffffff",
            "grid_color": "#dddddd",
            "axis_color": "#333333",
            "bargap": 0.25,
            "bargroupgap": 0.15,
            "xaxis_tickangle": -45,
            "legend_font_color": "#222222",
            "legend_font_size": 11,
            "legend_bgcolor": "#f0f0f0",
            "legend_border_width": 1,
            "legend_border_color": "#cccccc",
            "color_palette": "Set2",
            "series_styles": {
                "Group2": {"use_color": True, "color": "#ff6600"}
            }
        }
        
        result = grouped_bar_style_manager.apply_styles(fig, config)
        
        # Verify dimensions
        assert result.layout.width == 1200
        assert result.layout.height == 700
        
        # Verify margins
        assert result.layout.margin.l == 120
        
        # Verify backgrounds
        assert result.layout.plot_bgcolor == "#fafafa"
        
        # Verify bar settings
        assert result.layout.bargap == 0.25
        assert result.layout.bargroupgap == 0.15
        
        # Verify legend
        assert result.layout.legend.font.size == 11
        
        # Verify custom color for Group2
        assert result.data[1].marker.color == "#ff6600"
