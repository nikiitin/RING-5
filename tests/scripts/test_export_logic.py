import os
import shutil

# Mock streamlit to avoid runtime errors during generic imports if they happen
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.plotting import PlotFactory
from src.web.services.plot_service import PlotService

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


def test_export_plot_to_file(temp_dir):
    """Test that export_plot_to_file creates a file."""
    plot = PlotFactory.create_plot("bar", 1, "Test Plot")

    df = pd.DataFrame({"x": ["A", "B"], "y": [10, 20]})
    plot.processed_data = df
    plot.config["x"] = "x"
    plot.config["y"] = "y"
    plot.config["download_format"] = "pdf"
    plot.config["export_scale"] = 2
    plot.config["width"] = 400
    plot.config["height"] = 300
    plot.config["title"] = "Test Title"
    plot.config["xlabel"] = "X"
    plot.config["ylabel"] = "Y"

    path = PlotService.export_plot_to_file(plot, temp_dir)

    assert path is not None
    assert os.path.exists(path)
    assert path.endswith("Test_Plot.pdf")

    assert os.path.getsize(path) > 0

    print(f"Exported to {path}, size: {os.path.getsize(path)}")


def test_export_plot_format_override(temp_dir):
    """Test that format argument overrides config."""
    plot = PlotFactory.create_plot("bar", 2, "SVG Plot")
    df = pd.DataFrame({"x": ["A", "B"], "y": [1, 2]})
    plot.processed_data = df
    plot.config["x"] = "x"
    plot.config["y"] = "y"
    plot.config["download_format"] = "png"
    plot.config["title"] = "Test Title"
    plot.config["xlabel"] = "X"
    plot.config["ylabel"] = "Y"

    path = PlotService.export_plot_to_file(plot, temp_dir, format="svg")

    assert path.endswith("SVG_Plot.svg")
    assert os.path.exists(path)


@patch("plotly.graph_objects.Figure.write_image")
def test_export_scale_usage(mock_write_image, temp_dir):
    """Test that correct scale is passed to write_image."""
    plot = PlotFactory.create_plot("bar", 3, "Scale Plot")
    df = pd.DataFrame({"x": [1], "y": [1]})
    plot.processed_data = df
    plot.config["x"] = "x"
    plot.config["y"] = "y"
    plot.config["export_scale"] = 3
    plot.config["title"] = "Test Title"
    plot.config["xlabel"] = "X"
    plot.config["ylabel"] = "Y"

    PlotService.export_plot_to_file(plot, temp_dir, format="png")

    args, kwargs = mock_write_image.call_args
    assert kwargs.get("scale") == 3
    assert kwargs.get("format") == "png"
