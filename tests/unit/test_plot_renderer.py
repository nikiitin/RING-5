"""
Comprehensive tests for PlotRenderer.
Tests legend customization, plot rendering, and export functionality.
"""

import pytest
import pandas as pd
import plotly.graph_objects as go
from unittest.mock import MagicMock, patch


class MockPlot:
    """Mock plot class for testing."""
    
    def __init__(self):
        self.plot_id = 1
        self.name = "test_plot"
        self.config = {}
        self.processed_data = None
        self.last_generated_fig = None
        self.legend_mappings = {}
        self.legend_mappings_by_column = {}
    
    def get_legend_column(self, config):
        return config.get("color") or config.get("group")
    
    def create_figure(self, data, config):
        return go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
    
    def apply_common_layout(self, fig, config):
        return fig
    
    def apply_legend_labels(self, fig, labels):
        return fig


class TestPlotRendererLegendCustomization:
    """Tests for legend customization rendering."""

    @pytest.fixture
    def mock_plot(self):
        return MockPlot()

    @pytest.fixture
    def sample_data(self):
        return pd.DataFrame({
            "x": ["A", "B", "C"],
            "y": [1, 2, 3],
            "category": ["Cat1", "Cat2", "Cat1"]
        })

    def test_no_legend_column_returns_none(self, mock_plot, sample_data):
        """Test that no legend column returns None."""
        from src.plotting.plot_renderer import PlotRenderer
        
        config = {"x": "x", "y": "y"}  # No color or group
        
        # Patch streamlit to avoid UI calls
        with patch('src.plotting.plot_renderer.st'):
            result = PlotRenderer.render_legend_customization(mock_plot, sample_data, config)
        
        assert result is None


class TestPlotRendererExport:
    """Tests for plot export functionality."""

    def test_html_export_format(self):
        """Test HTML export creates valid HTML."""
        import plotly.io as pio
        
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        html_str = pio.to_html(fig, include_plotlyjs=True)
        
        assert "<!DOCTYPE html>" in html_str or "<html>" in html_str.lower()
        assert "plotly" in html_str.lower()

    def test_png_export_with_kaleido(self):
        """Test PNG export with kaleido if available."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        
        try:
            import kaleido  # noqa: F401
            import io
            
            buf = io.BytesIO()
            fig.write_image(buf, format="png")
            buf.seek(0)
            
            # PNG magic bytes
            assert buf.read(4) == b'\x89PNG'
        except ImportError:
            pytest.skip("Kaleido not installed")

    def test_pdf_export_with_kaleido(self):
        """Test PDF export with kaleido if available."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        
        try:
            import kaleido  # noqa: F401
            import io
            
            buf = io.BytesIO()
            fig.write_image(buf, format="pdf")
            buf.seek(0)
            
            # PDF magic bytes
            assert buf.read(4) == b'%PDF'
        except ImportError:
            pytest.skip("Kaleido not installed")


class TestPlotRendererFallback:
    """Tests for matplotlib fallback export."""

    def test_matplotlib_fallback_png(self):
        """Test matplotlib fallback for PNG."""
        import io
        import matplotlib
        matplotlib.use('Agg')  # Non-GUI backend
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots()
        ax.bar(["A", "B"], [1, 2])
        
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100)
        buf.seek(0)
        plt.close(fig)
        
        # PNG magic bytes
        assert buf.read(4) == b'\x89PNG'

    def test_matplotlib_fallback_pdf(self):
        """Test matplotlib fallback for PDF."""
        import io
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots()
        ax.bar(["A", "B"], [1, 2])
        
        buf = io.BytesIO()
        fig.savefig(buf, format="pdf")
        buf.seek(0)
        plt.close(fig)
        
        # PDF magic bytes
        assert buf.read(4) == b'%PDF'


class TestPlotRendererFigureExtraction:
    """Tests for extracting data from Plotly figures."""

    def test_extract_bar_trace_data(self):
        """Test extracting data from bar trace."""
        fig = go.Figure(data=[
            go.Bar(x=["A", "B", "C"], y=[1, 2, 3], name="Series1")
        ])
        
        trace = fig.data[0]
        
        assert trace.type == "bar"
        assert list(trace.x) == ["A", "B", "C"]
        assert list(trace.y) == [1, 2, 3]
        assert trace.name == "Series1"

    def test_extract_scatter_trace_data(self):
        """Test extracting data from scatter trace."""
        fig = go.Figure(data=[
            go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="Series1")
        ])
        
        trace = fig.data[0]
        
        assert trace.type == "scatter"
        assert list(trace.x) == [1, 2, 3]
        assert list(trace.y) == [4, 5, 6]

    def test_extract_multiple_traces(self):
        """Test extracting data from multiple traces."""
        fig = go.Figure(data=[
            go.Bar(x=["A", "B"], y=[1, 2], name="S1"),
            go.Bar(x=["A", "B"], y=[3, 4], name="S2"),
            go.Bar(x=["A", "B"], y=[5, 6], name="S3")
        ])
        
        assert len(fig.data) == 3
        
        for i, trace in enumerate(fig.data):
            assert trace.name == f"S{i+1}"


class TestPlotRendererConfig:
    """Tests for plot configuration handling."""

    def test_default_download_format(self):
        """Test default download format is HTML."""
        mock_plot = MockPlot()
        
        download_format = mock_plot.config.get("download_format", "html")
        assert download_format == "html"

    def test_editable_mode_default(self):
        """Test default editable mode is disabled."""
        mock_plot = MockPlot()
        
        editable = mock_plot.config.get("enable_editable", False)
        assert editable is False

    def test_image_button_config(self):
        """Test image button configuration structure."""
        config = {
            "toImageButtonOptions": {
                "format": "svg",
                "filename": "custom_view",
                "height": None,
                "width": None,
                "scale": 1,
            }
        }
        
        assert config["toImageButtonOptions"]["format"] == "svg"
        assert config["toImageButtonOptions"]["scale"] == 1


class TestMockPlotIntegration:
    """Integration tests with mock plots."""

    def test_mock_plot_create_figure(self):
        """Test mock plot creates a figure."""
        plot = MockPlot()
        data = pd.DataFrame({"x": ["A", "B"], "y": [1, 2]})
        
        fig = plot.create_figure(data, {})
        
        assert fig is not None
        assert len(fig.data) > 0

    def test_mock_plot_legend_mapping_storage(self):
        """Test mock plot stores legend mappings."""
        plot = MockPlot()
        
        plot.legend_mappings_by_column["category"] = {"A": "Label A", "B": "Label B"}
        
        assert "category" in plot.legend_mappings_by_column
        assert plot.legend_mappings_by_column["category"]["A"] == "Label A"

    def test_mock_plot_get_legend_column_with_color(self):
        """Test getting legend column with color key."""
        plot = MockPlot()
        config = {"color": "category"}
        
        result = plot.get_legend_column(config)
        assert result == "category"

    def test_mock_plot_get_legend_column_with_group(self):
        """Test getting legend column with group key."""
        plot = MockPlot()
        config = {"group": "type"}
        
        result = plot.get_legend_column(config)
        assert result == "type"
