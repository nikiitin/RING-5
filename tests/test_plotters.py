"""Unit tests for plotting functionality."""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import os
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from plotting.plot_engine import PlotGenerator, PlotManager, DataProcessor


@pytest.fixture
def sample_data():
    """Create sample DataFrame for testing."""
    return pd.DataFrame({
        'benchmark': ['bzip2', 'gcc', 'mcf', 'hmmer', 'sjeng'],
        'config': ['baseline'] * 5,
        'simTicks': [1000, 1500, 1200, 1100, 1300],
        'ipc': [1.5, 2.0, 1.8, 1.6, 1.9]
    })


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / 'plots'
    output_dir.mkdir()
    return str(output_dir)


@pytest.fixture
def temp_csv_file(tmp_path, sample_data):
    """Create temporary CSV file."""
    csv_file = tmp_path / 'test_data.csv'
    sample_data.to_csv(csv_file, index=False)
    return str(csv_file)


class TestPlotGenerator:
    """Test cases for PlotGenerator class."""
    
    def test_bar_plot_generation(self, sample_data, temp_output_dir):
        """Test basic bar plot generation."""
        plot_config = {
            'type': 'bar',
            'output': {'filename': str(Path(temp_output_dir) / 'test_bar')},
            'data': {'x': 'benchmark', 'y': 'simTicks'},
            'style': {'title': 'Test Bar Plot'}
        }
        
        generator = PlotGenerator(sample_data, plot_config)
        generator.generate()
        
        # Check that plot file was created
        output_file = Path(temp_output_dir) / 'test_bar.png'
        assert output_file.exists()
    
    def test_line_plot_generation(self, sample_data, temp_output_dir):
        """Test line plot generation."""
        plot_config = {
            'type': 'line',
            'output': {'filename': str(Path(temp_output_dir) / 'test_line')},
            'data': {'x': 'benchmark', 'y': 'ipc'},
            'style': {'title': 'Test Line Plot'}
        }
        
        generator = PlotGenerator(sample_data, plot_config)
        generator.generate()
        
        output_file = Path(temp_output_dir) / 'test_line.png'
        assert output_file.exists()
    
    def test_scatter_plot_generation(self, sample_data, temp_output_dir):
        """Test scatter plot generation."""
        plot_config = {
            'type': 'scatter',
            'output': {'filename': str(Path(temp_output_dir) / 'test_scatter')},
            'data': {'x': 'simTicks', 'y': 'ipc'},
            'style': {'title': 'Test Scatter Plot'}
        }
        
        generator = PlotGenerator(sample_data, plot_config)
        generator.generate()
        
        output_file = Path(temp_output_dir) / 'test_scatter.png'
        assert output_file.exists()
    
    def test_box_plot_generation(self, temp_output_dir):
        """Test box plot generation."""
        # Create data with multiple values per category
        data = pd.DataFrame({
            'config': ['A', 'A', 'A', 'B', 'B', 'B'],
            'value': [1, 2, 3, 4, 5, 6]
        })
        
        plot_config = {
            'type': 'box',
            'output': {'filename': str(Path(temp_output_dir) / 'test_box')},
            'data': {'x': 'config', 'y': 'value'},
            'style': {'title': 'Test Box Plot'}
        }
        
        generator = PlotGenerator(data, plot_config)
        generator.generate()
        
        output_file = Path(temp_output_dir) / 'test_box.png'
        assert output_file.exists()
    
    def test_heatmap_generation(self, temp_output_dir):
        """Test heatmap generation."""
        # Create matrix-like data
        data = pd.DataFrame({
            'benchmark': ['A', 'A', 'B', 'B'],
            'config': ['C1', 'C2', 'C1', 'C2'],
            'value': [1, 2, 3, 4]
        })
        
        plot_config = {
            'type': 'heatmap',
            'output': {'filename': str(Path(temp_output_dir) / 'test_heatmap')},
            'data': {'x': 'config', 'y': 'benchmark', 'value': 'value'},
            'style': {'title': 'Test Heatmap'}
        }
        
        generator = PlotGenerator(data, plot_config)
        generator.generate()
        
        output_file = Path(temp_output_dir) / 'test_heatmap.png'
        assert output_file.exists()
    
    def test_output_format_pdf(self, sample_data, temp_output_dir):
        """Test PDF output format."""
        plot_config = {
            'type': 'bar',
            'output': {'filename': str(Path(temp_output_dir) / 'test_pdf'), 'format': 'pdf'},
            'data': {'x': 'benchmark', 'y': 'simTicks'}
        }
        
        generator = PlotGenerator(sample_data, plot_config)
        generator.generate()
        
        output_file = Path(temp_output_dir) / 'test_pdf.pdf'
        assert output_file.exists()
    
    def test_output_format_svg(self, sample_data, temp_output_dir):
        """Test SVG output format."""
        plot_config = {
            'type': 'bar',
            'output': {'filename': str(Path(temp_output_dir) / 'test_svg'), 'format': 'svg'},
            'data': {'x': 'benchmark', 'y': 'simTicks'}
        }
        
        generator = PlotGenerator(sample_data, plot_config)
        generator.generate()
        
        output_file = Path(temp_output_dir) / 'test_svg.svg'
        assert output_file.exists()
    
    def test_plot_with_hue(self, temp_output_dir):
        """Test plot with hue parameter."""
        data = pd.DataFrame({
            'benchmark': ['A', 'A', 'B', 'B'],
            'config': ['C1', 'C2', 'C1', 'C2'],
            'value': [1, 2, 3, 4]
        })
        
        plot_config = {
            'type': 'bar',
            'output': {'filename': str(Path(temp_output_dir) / 'test_hue')},
            'data': {'x': 'benchmark', 'y': 'value', 'hue': 'config'}
        }
        
        generator = PlotGenerator(data, plot_config)
        generator.generate()
        
        output_file = Path(temp_output_dir) / 'test_hue.png'
        assert output_file.exists()
    
    def test_plot_with_filters(self, sample_data, temp_output_dir):
        """Test plot with data filters."""
        plot_config = {
            'type': 'bar',
            'output': {'filename': str(Path(temp_output_dir) / 'test_filter')},
            'data': {
                'x': 'benchmark',
                'y': 'simTicks',
                'filters': {'benchmark': ['bzip2', 'gcc']}
            }
        }
        
        generator = PlotGenerator(sample_data, plot_config)
        generator.generate()
        
        # Verify file created
        output_file = Path(temp_output_dir) / 'test_filter.png'
        assert output_file.exists()
        
        # Verify data was filtered
        assert len(generator.data) == 2
    
    def test_invalid_plot_type_raises_error(self, sample_data, temp_output_dir):
        """Test that invalid plot type raises error."""
        plot_config = {
            'type': 'invalid_type',
            'output': {'filename': str(Path(temp_output_dir) / 'test')},
            'data': {'x': 'benchmark', 'y': 'simTicks'}
        }
        
        generator = PlotGenerator(sample_data, plot_config)
        with pytest.raises(ValueError, match="Unknown plot type"):
            generator.generate()


class TestDataProcessor:
    """Test cases for DataProcessor class."""
    
    def test_filter_data(self, sample_data):
        """Test data filtering."""
        filters = {'benchmark': ['bzip2', 'gcc']}
        filtered = DataProcessor.filter_data(sample_data, filters)
        
        assert len(filtered) == 2
        assert set(filtered['benchmark'].values) == {'bzip2', 'gcc'}
    
    def test_aggregate_data(self, sample_data):
        """Test data aggregation."""
        # Add multiple rows for same benchmark
        data = pd.concat([sample_data, sample_data], ignore_index=True)
        
        aggregated = DataProcessor.aggregate_data(
            data, 'mean', ['benchmark'], ['simTicks']
        )
        
        assert len(aggregated) == 5  # 5 unique benchmarks
        assert 'simTicks' in aggregated.columns


class TestPlotManager:
    """Test cases for PlotManager class."""
    
    def test_plot_manager_loads_data(self, temp_csv_file):
        """Test that PlotManager loads data correctly."""
        manager = PlotManager(temp_csv_file, '/tmp')
        assert manager.data is not None
        assert len(manager.data) > 0
    
    def test_plot_manager_generates_single_plot(self, temp_csv_file, temp_output_dir):
        """Test generating a single plot."""
        plot_configs = [{
            'type': 'bar',
            'output': {'filename': str(Path(temp_output_dir) / 'test')},
            'data': {'x': 'benchmark', 'y': 'simTicks'}
        }]
        
        manager = PlotManager(temp_csv_file, temp_output_dir)
        manager.generate_plots(plot_configs)
        
        # Check plot was created
        output_file = Path(temp_output_dir) / 'test.png'
        assert output_file.exists()
