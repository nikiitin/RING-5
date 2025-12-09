"""Tests for the new plot class hierarchy."""
import pytest
import pandas as pd
from src.plotting import (
    PlotFactory,
    BasePlot,
    BarPlot,
    GroupedBarPlot,
    GroupedStackedBarPlot,
    LinePlot,
    ScatterPlot
)


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    return pd.DataFrame({
        'category': ['A', 'B', 'C', 'A', 'B', 'C'],
        'value': [10, 20, 15, 12, 18, 16],
        'group': ['G1', 'G1', 'G1', 'G2', 'G2', 'G2'],
        'stack': ['S1', 'S1', 'S2', 'S1', 'S2', 'S2']
    })


class TestPlotFactory:
    """Test the PlotFactory."""
    
    def test_create_bar_plot(self):
        """Test creating a bar plot."""
        plot = PlotFactory.create_plot('bar', 1, 'Test Bar')
        assert isinstance(plot, BarPlot)
        assert plot.plot_id == 1
        assert plot.name == 'Test Bar'
        assert plot.plot_type == 'bar'
    
    def test_create_grouped_bar_plot(self):
        """Test creating a grouped bar plot."""
        plot = PlotFactory.create_plot('grouped_bar', 2, 'Test Grouped')
        assert isinstance(plot, GroupedBarPlot)
        assert plot.plot_type == 'grouped_bar'
    
    def test_create_grouped_stacked_bar_plot(self):
        """Test creating a grouped stacked bar plot."""
        plot = PlotFactory.create_plot('grouped_stacked_bar', 3, 'Test Stacked')
        assert isinstance(plot, GroupedStackedBarPlot)
        assert plot.plot_type == 'grouped_stacked_bar'
    
    def test_create_line_plot(self):
        """Test creating a line plot."""
        plot = PlotFactory.create_plot('line', 4, 'Test Line')
        assert isinstance(plot, LinePlot)
        assert plot.plot_type == 'line'
    
    def test_create_scatter_plot(self):
        """Test creating a scatter plot."""
        plot = PlotFactory.create_plot('scatter', 5, 'Test Scatter')
        assert isinstance(plot, ScatterPlot)
        assert plot.plot_type == 'scatter'
    
    def test_invalid_plot_type(self):
        """Test that invalid plot type raises error."""
        with pytest.raises(ValueError, match="Unknown plot type"):
            PlotFactory.create_plot('invalid', 1, 'Test')
    
    def test_get_available_plot_types(self):
        """Test getting available plot types."""
        types = PlotFactory.get_available_plot_types()
        assert 'bar' in types
        assert 'grouped_bar' in types
        assert 'grouped_stacked_bar' in types
        assert 'line' in types
        assert 'scatter' in types


class TestBarPlot:
    """Test BarPlot functionality."""
    
    def test_initialization(self):
        """Test bar plot initialization."""
        plot = BarPlot(1, 'My Plot')
        assert plot.plot_id == 1
        assert plot.name == 'My Plot'
        assert plot.plot_type == 'bar'
        assert plot.config == {}
        assert plot.processed_data is None
    
    def test_create_figure(self, sample_data):
        """Test creating a figure."""
        plot = BarPlot(1, 'Test')
        config = {
            'x': 'category',
            'y': 'value',
            'color': None,
            'title': 'Test Plot',
            'xlabel': 'Category',
            'ylabel': 'Value',
            'show_error_bars': False
        }
        fig = plot.create_figure(sample_data, config)
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_get_legend_column(self):
        """Test getting legend column."""
        plot = BarPlot(1, 'Test')
        config = {'color': 'category'}
        assert plot.get_legend_column(config) == 'category'
        
        config = {'color': None}
        assert plot.get_legend_column(config) is None
    
    def test_to_dict(self, sample_data):
        """Test serialization to dictionary."""
        plot = BarPlot(1, 'Test')
        plot.processed_data = sample_data
        plot.config = {'x': 'category', 'y': 'value'}
        plot.pipeline = [{'type': 'columnSelector', 'config': {}}]
        
        data_dict = plot.to_dict()
        assert data_dict['id'] == 1
        assert data_dict['name'] == 'Test'
        assert data_dict['plot_type'] == 'bar'
        assert data_dict['config'] == {'x': 'category', 'y': 'value'}
        assert isinstance(data_dict['processed_data'], str)  # CSV string
        assert data_dict['pipeline'] == [{'type': 'columnSelector', 'config': {}}]


class TestGroupedBarPlot:
    """Test GroupedBarPlot functionality."""
    
    def test_create_figure(self, sample_data):
        """Test creating a grouped bar figure."""
        plot = GroupedBarPlot(1, 'Test')
        config = {
            'x': 'category',
            'y': 'value',
            'group': 'group',
            'title': 'Test Plot',
            'xlabel': 'Category',
            'ylabel': 'Value',
            'show_error_bars': False
        }
        fig = plot.create_figure(sample_data, config)
        assert fig is not None
        assert len(fig.data) >= 2  # Multiple groups
    
    def test_get_legend_column(self):
        """Test getting legend column for grouped bar."""
        plot = GroupedBarPlot(1, 'Test')
        config = {'group': 'group_column'}
        assert plot.get_legend_column(config) == 'group_column'


class TestGroupedStackedBarPlot:
    """Test GroupedStackedBarPlot functionality."""
    
    def test_create_figure(self, sample_data):
        """Test creating a grouped stacked bar figure."""
        plot = GroupedStackedBarPlot(1, 'Test')
        config = {
            'x': 'category',
            'y': 'value',
            'group': 'group',
            'stack': 'stack',
            'title': 'Test Plot',
            'xlabel': 'Category',
            'ylabel': 'Value',
            'show_error_bars': False
        }
        fig = plot.create_figure(sample_data, config)
        assert fig is not None
    
    def test_get_legend_column(self):
        """Test getting legend column for grouped stacked bar."""
        plot = GroupedStackedBarPlot(1, 'Test')
        config = {'stack': 'stack_column'}
        assert plot.get_legend_column(config) == 'stack_column'


class TestLinePlot:
    """Test LinePlot functionality."""
    
    def test_create_figure(self, sample_data):
        """Test creating a line figure."""
        plot = LinePlot(1, 'Test')
        config = {
            'x': 'category',
            'y': 'value',
            'color': 'group',
            'title': 'Test Plot',
            'xlabel': 'Category',
            'ylabel': 'Value',
            'show_error_bars': False
        }
        fig = plot.create_figure(sample_data, config)
        assert fig is not None


class TestScatterPlot:
    """Test ScatterPlot functionality."""
    
    def test_create_figure(self, sample_data):
        """Test creating a scatter figure."""
        plot = ScatterPlot(1, 'Test')
        config = {
            'x': 'category',
            'y': 'value',
            'color': 'group',
            'title': 'Test Plot',
            'xlabel': 'Category',
            'ylabel': 'Value',
            'show_error_bars': False
        }
        fig = plot.create_figure(sample_data, config)
        assert fig is not None


class TestPlotSerialization:
    """Test plot serialization and deserialization."""
    
    def test_to_dict_and_from_dict(self, sample_data):
        """Test round-trip serialization."""
        # Create and configure plot
        plot = BarPlot(1, 'Test Plot')
        plot.processed_data = sample_data
        plot.config = {'x': 'category', 'y': 'value'}
        plot.pipeline = [{'type': 'columnSelector', 'config': {'columns': ['category', 'value']}}]
        plot.legend_mappings = {'A': 'Label A', 'B': 'Label B'}
        
        # Serialize
        data_dict = plot.to_dict()
        
        # Deserialize
        restored_plot = BasePlot.from_dict(data_dict)
        
        assert restored_plot.plot_id == plot.plot_id
        assert restored_plot.name == plot.name
        assert restored_plot.plot_type == plot.plot_type
        assert restored_plot.config == plot.config
        assert restored_plot.pipeline == plot.pipeline
        assert restored_plot.legend_mappings == plot.legend_mappings
        assert restored_plot.processed_data.equals(plot.processed_data)


class TestPlotCommonLayout:
    """Test common layout application."""
    
    def test_apply_common_layout(self, sample_data):
        """Test applying common layout settings."""
        plot = BarPlot(1, 'Test')
        config = {
            'x': 'category',
            'y': 'value',
            'title': 'Test',
            'xlabel': 'X',
            'ylabel': 'Y',
            'width': 1000,
            'height': 600,
            'legend_title': 'My Legend',
            'show_error_bars': False
        }
        
        fig = plot.create_figure(sample_data, config)
        fig = plot.apply_common_layout(fig, config)
        
        assert fig.layout.width == 1000
        assert fig.layout.height == 600
        assert fig.layout.legend.title.text == 'My Legend'


class TestPlotLegendLabels:
    """Test legend label customization."""
    
    def test_apply_legend_labels(self, sample_data):
        """Test applying custom legend labels."""
        plot = BarPlot(1, 'Test')
        config = {
            'x': 'category',
            'y': 'value',
            'color': 'group',
            'title': 'Test',
            'xlabel': 'X',
            'ylabel': 'Y',
            'show_error_bars': False
        }
        
        fig = plot.create_figure(sample_data, config)
        
        # Apply custom labels
        legend_labels = {'G1': 'Group One', 'G2': 'Group Two'}
        fig = plot.apply_legend_labels(fig, legend_labels)
        
        # Check that labels were applied
        trace_names = [trace.name for trace in fig.data]
        assert 'Group One' in trace_names or 'Group Two' in trace_names
