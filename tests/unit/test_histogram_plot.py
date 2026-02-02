"""Unit tests for Histogram plot type."""

from typing import Any, Dict
from unittest.mock import patch

import pandas as pd
import pytest

from src.plotting.types.histogram_plot import HistogramPlot


class TestHistogramPlotInitialization:
    """Test histogram plot initialization."""

    def test_initialization(self) -> None:
        """Test histogram plot can be initialized."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        assert plot.plot_id == 1
        assert plot.name == "Test Histogram"
        assert plot.plot_type == "histogram"


class TestHistogramPlotConfiguration:
    """Test histogram plot configuration UI."""

    def test_render_config_ui_basic(self) -> None:
        """Test basic configuration rendering."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        # Sample data with histogram-style columns
        data = pd.DataFrame(
            {
                "benchmark": ["A", "B", "C"],
                "latency..0-10": [5, 8, 3],
                "latency..10-20": [10, 12, 9],
                "latency..20-30": [3, 5, 2],
            }
        )

        saved_config: Dict[str, Any] = {}

        with patch("src.plotting.types.histogram_plot.st") as mock_st:
            # Mock selectbox returns
            mock_st.selectbox.side_effect = ["latency", None, 20, "count"]
            mock_st.number_input.return_value = 10
            mock_st.checkbox.return_value = False
            mock_st.text_input.side_effect = ["Test Histogram", "X Label", "Y Label"]

            config = plot.render_config_ui(data, saved_config)

            assert "histogram_variable" in config
            assert config["histogram_variable"] == "latency"

    def test_render_config_with_grouping(self) -> None:
        """Test configuration with categorical grouping variable."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        data = pd.DataFrame(
            {
                "benchmark": ["A", "A", "B", "B"],
                "config": ["X", "Y", "X", "Y"],
                "latency..0-10": [5, 8, 3, 6],
                "latency..10-20": [10, 12, 9, 11],
            }
        )

        saved_config: Dict[str, Any] = {"group_by": "benchmark"}

        with patch("src.plotting.types.histogram_plot.st") as mock_st:
            mock_st.selectbox.side_effect = ["latency", "benchmark", 20, "count"]
            mock_st.number_input.return_value = 5
            mock_st.checkbox.return_value = False
            mock_st.text_input.side_effect = ["Test", "X", "Y"]

            config = plot.render_config_ui(data, saved_config)

            assert config.get("group_by") == "benchmark"


class TestHistogramPlotFigureCreation:
    """Test histogram plot figure generation."""

    def test_create_figure_single_histogram(self) -> None:
        """Test creating figure with single histogram."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        # Data with histogram buckets
        data = pd.DataFrame(
            {
                "latency..0-10": [5],
                "latency..10-20": [10],
                "latency..20-30": [3],
                "latency..30-40": [1],
            }
        )

        config = {
            "histogram_variable": "latency",
            "title": "Latency Distribution",
            "xlabel": "Latency (cycles)",
            "ylabel": "Count",
            "bucket_size": 10,
            "normalization": "count",
            "group_by": None,
        }

        fig = plot.create_figure(data, config)

        assert fig is not None
        assert len(fig.data) > 0
        assert fig.layout.title.text == "Latency Distribution"

    def test_create_figure_grouped_histograms(self) -> None:
        """Test creating figure with multiple grouped histograms."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        # Data with grouping variable
        data = pd.DataFrame(
            {
                "benchmark": ["A", "B"],
                "latency..0-10": [5, 8],
                "latency..10-20": [10, 12],
                "latency..20-30": [3, 5],
            }
        )

        config = {
            "histogram_variable": "latency",
            "title": "Latency by Benchmark",
            "xlabel": "Latency (cycles)",
            "ylabel": "Count",
            "bucket_size": 10,
            "normalization": "count",
            "group_by": "benchmark",
        }

        fig = plot.create_figure(data, config)

        assert fig is not None
        # Should have 2 traces (one per benchmark)
        assert len(fig.data) == 2

    def test_create_figure_with_rebinning(self) -> None:
        """Test histogram with custom bucket size (rebinning)."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        # Data with fine-grained buckets
        data = pd.DataFrame(
            {
                "latency..0-5": [3],
                "latency..5-10": [5],
                "latency..10-15": [7],
                "latency..15-20": [4],
                "latency..20-25": [2],
            }
        )

        config = {
            "histogram_variable": "latency",
            "title": "Latency Distribution",
            "xlabel": "Latency",
            "ylabel": "Count",
            "bucket_size": 10,  # Rebin to 10-unit buckets
            "normalization": "count",
            "group_by": None,
        }

        fig = plot.create_figure(data, config)

        assert fig is not None
        # Should have rebinned the data
        assert len(fig.data) > 0

    def test_create_figure_normalized(self) -> None:
        """Test histogram with probability normalization."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        data = pd.DataFrame(
            {
                "latency..0-10": [10],
                "latency..10-20": [20],
                "latency..20-30": [30],
                "latency..30-40": [40],
            }
        )

        config = {
            "histogram_variable": "latency",
            "title": "Latency Distribution",
            "xlabel": "Latency",
            "ylabel": "Probability",
            "bucket_size": 10,
            "normalization": "probability",
            "group_by": None,
        }

        fig = plot.create_figure(data, config)

        assert fig is not None
        assert len(fig.data) > 0


class TestHistogramPlotLegend:
    """Test histogram plot legend handling."""

    def test_get_legend_column_no_grouping(self) -> None:
        """Test legend column when no grouping."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        config = {"group_by": None}
        legend_col = plot.get_legend_column(config)

        assert legend_col is None

    def test_get_legend_column_with_grouping(self) -> None:
        """Test legend column with grouping variable."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        config = {"group_by": "benchmark"}
        legend_col = plot.get_legend_column(config)

        assert legend_col == "benchmark"


class TestHistogramPlotValidation:
    """Test histogram plot validation."""

    def test_validates_histogram_variable_exists(self) -> None:
        """Test validation when histogram variable doesn't exist."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        # Data without histogram columns
        data = pd.DataFrame({"benchmark": ["A", "B"], "value": [1, 2]})

        config = {
            "histogram_variable": "nonexistent",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "bucket_size": 10,
            "normalization": "count",
            "group_by": None,
        }

        # Should handle gracefully (return empty figure or raise)
        with pytest.raises((ValueError, KeyError)):
            plot.create_figure(data, config)
