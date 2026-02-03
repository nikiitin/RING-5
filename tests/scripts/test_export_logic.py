import os
import shutil

# Mock streamlit to avoid runtime errors during generic imports if they happen
import sys
import tempfile
from unittest.mock import MagicMock

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
    plot = PlotFactory.create_plot("bar", 2, "HTML Plot")
    df = pd.DataFrame({"x": ["A", "B"], "y": [1, 2]})
    plot.processed_data = df
    plot.config["x"] = "x"
    plot.config["y"] = "y"
    plot.config["download_format"] = "pdf"
    plot.config["title"] = "Test Title"
    plot.config["xlabel"] = "X"
    plot.config["ylabel"] = "Y"

    path = PlotService.export_plot_to_file(plot, temp_dir, format="html")

    assert path.endswith("HTML_Plot.html")
    assert os.path.exists(path)


def test_export_rejects_invalid_format(temp_dir):
    """Test that invalid formats are rejected (security: prevent path traversal)."""
    plot = PlotFactory.create_plot("bar", 3, "Security Test")
    df = pd.DataFrame({"x": ["A"], "y": [1]})
    plot.processed_data = df
    plot.config["x"] = "x"
    plot.config["y"] = "y"
    plot.config["title"] = "Test Title"
    plot.config["xlabel"] = "X"
    plot.config["ylabel"] = "Y"

    # Test path traversal attempt
    with pytest.raises(ValueError, match="Unsupported export format"):
        PlotService.export_plot_to_file(plot, temp_dir, format="../../../etc/passwd")

    # Test invalid extension
    with pytest.raises(ValueError, match="Unsupported export format"):
        PlotService.export_plot_to_file(plot, temp_dir, format="png")

    # Test empty format should use default (pdf) which is valid
    path = PlotService.export_plot_to_file(plot, temp_dir, format=None)
    assert path.endswith(".pdf")
