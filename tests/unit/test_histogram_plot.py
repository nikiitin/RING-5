"""Unit tests for Histogram plot type."""

from ring5 import Session
from ring5.errors import RenderError
from typing import cast
import plotly.graph_objects as go

from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot


class TestHistogramPlotInitialization:
    """Test histogram plot initialization."""

    def test_initialization(self) -> None:
        """Test histogram plot can be initialized."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        assert plot.plot_id == 1
        assert plot.name == "Test Histogram"
        assert plot.plot_type == "histogram"


_HIST_CFG = "src.web.components.plotting.config.histogram_config"


class TestHistogramPlotConfiguration:
    """Test histogram plot configuration UI."""

    @patch(f"{_HIST_CFG}.render_common_config")
    @patch(f"{_HIST_CFG}.detect_column_types")
    @patch(f"{_HIST_CFG}.st")
    def test_render_config_ui_basic(self, mock_st: Any, mock_detect: Any, mock_common: Any) -> None:
        """Test basic configuration rendering."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        # Sample data with histogram-style columns
        data = pd.DataFrame(
            {
                "benchmark": ["A", "B", "C"],
                "latency..0-9": [5, 8, 3],
                "latency..10-19": [10, 12, 9],
                "latency..20-29": [3, 5, 2],
            }
        )

        mock_common.return_value = {
            "x": "benchmark",
            "y": "latency..0-9",
            "title": "Test Histogram",
            "xlabel": "X Label",
            "ylabel": "Y Label",
        }
        mock_detect.return_value = (
            ["latency..0-9", "latency..10-19", "latency..20-29"],
            ["benchmark"],
        )

        # histogram-specific widgets:
        # selectbox: histogram_variable, group_by, normalization
        mock_st.selectbox.side_effect = ["latency", None, "count"]
        mock_st.number_input.return_value = 10
        mock_st.checkbox.return_value = False

        config = plot.render_config_ui(data, {})

        assert "histogram_variable" in config
        assert config["histogram_variable"] == "latency"

    @patch(f"{_HIST_CFG}.render_common_config")
    @patch(f"{_HIST_CFG}.detect_column_types")
    @patch(f"{_HIST_CFG}.st")
    def test_render_config_with_grouping(
        self, mock_st: Any, mock_detect: Any, mock_common: Any
    ) -> None:
        """Test configuration with categorical grouping variable."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        data = pd.DataFrame(
            {
                "benchmark": ["A", "A", "B", "B"],
                "config": ["X", "Y", "X", "Y"],
                "latency..0-9": [5, 8, 3, 6],
                "latency..10-19": [10, 12, 9, 11],
            }
        )

        mock_common.return_value = {
            "x": "benchmark",
            "y": "latency..0-9",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
        }
        mock_detect.return_value = (
            ["latency..0-9", "latency..10-19"],
            ["benchmark", "config"],
        )

        # selectbox: histogram_variable, group_by, normalization
        mock_st.selectbox.side_effect = ["latency", "benchmark", "count"]
        mock_st.number_input.return_value = 5
        mock_st.checkbox.return_value = False

        config = plot.render_config_ui(data, {"group_by": "benchmark"})

        assert config.get("group_by") == "benchmark"


class TestHistogramPlotFigureCreation:
    """Test histogram plot figure generation."""

    # [test->req~ring5.plot.histogram~1]

    def test_create_figure_single_histogram(self, plot_session: Session) -> None:
        """Test creating figure with single histogram."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        # Data with histogram buckets
        data = pd.DataFrame(
            {
                "latency..0-9": [5],
                "latency..10-19": [10],
                "latency..20-29": [3],
                "latency..30-39": [1],
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

        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        assert fig is not None
        assert len(list(fig.data)) > 0

    def test_create_figure_grouped_histograms(self, plot_session: Session) -> None:
        """Test creating figure with multiple grouped histograms."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        # Data with grouping variable
        data = pd.DataFrame(
            {
                "benchmark": ["A", "B", None],
                "latency..0-9": [5, 8, 100],
                "latency..10-19": [10, 12, 100],
                "latency..20-29": [3, 5, 100],
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
            "legend_order": ["B", "A"],
            "legend_labels": {"B": "Optimized"},
        }

        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        assert fig is not None
        # Missing group values do not create a bogus empty trace.
        assert len(list(fig.data)) == 2
        assert [trace.name for trace in fig.data] == ["Optimized", "A"]

    def test_create_figure_with_rebinning(self, plot_session: Session) -> None:
        """Test histogram with custom bucket size (rebinning)."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        # Data with fine-grained buckets
        data = pd.DataFrame(
            {
                "latency..0-4": [3],
                "latency..5-9": [5],
                "latency..10-14": [7],
                "latency..15-19": [4],
                "latency..20-24": [2],
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

        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        assert fig is not None
        # Should have rebinned the data
        assert len(list(fig.data)) > 0

    def test_create_figure_normalized(self, plot_session: Session) -> None:
        """Test histogram with probability normalization."""
        plot = HistogramPlot(plot_id=1, name="Test Histogram")

        data = pd.DataFrame(
            {
                "latency..0-9": [10],
                "latency..10-19": [20],
                "latency..20-29": [30],
                "latency..30-39": [40],
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

        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        assert fig is not None
        assert len(list(fig.data)) > 0


class TestHistogramPlotValidation:
    """Test histogram plot validation."""

    def test_validates_histogram_variable_exists(self, plot_session: Session) -> None:
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
        with pytest.raises(RenderError, match="No histogram bucket columns"):
            plot.processed_data = data
            plot.config = config
            cast(go.Figure, plot_session.render(plot))
