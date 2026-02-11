import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _mock_streamlit_module():
    """Patch streamlit in sys.modules for isolation — undone after each test."""
    with patch.dict(sys.modules, {"streamlit": MagicMock()}):
        yield


@pytest.fixture
def temp_dir(tmp_path):
    """Use pytest's tmp_path for automatic cleanup."""
    return tmp_path


@pytest.fixture
def plot_factory():
    """Import PlotFactory lazily (after streamlit mock is in place)."""
    from src.web.pages.ui.plotting import PlotFactory

    return PlotFactory


@pytest.fixture
def plot_service():
    """Import PlotService lazily (after streamlit mock is in place)."""
    from src.web.pages.ui.plotting.plot_service import PlotService

    return PlotService


def test_export_plot_to_file(temp_dir, plot_factory, plot_service):
    """Test that export_plot_to_file creates a file."""
    plot = plot_factory.create_plot("bar", 1, "Test Plot")

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

    path = plot_service.export_plot_to_file(plot, temp_dir)

    assert path is not None
    assert os.path.exists(path)
    assert path.endswith("Test_Plot.pdf")

    assert os.path.getsize(path) > 0


def test_export_plot_format_override(temp_dir, plot_factory, plot_service):
    """Test that format argument overrides config."""
    plot = plot_factory.create_plot("bar", 2, "HTML Plot")
    df = pd.DataFrame({"x": ["A", "B"], "y": [1, 2]})
    plot.processed_data = df
    plot.config["x"] = "x"
    plot.config["y"] = "y"
    plot.config["download_format"] = "pdf"
    plot.config["title"] = "Test Title"
    plot.config["xlabel"] = "X"
    plot.config["ylabel"] = "Y"

    path = plot_service.export_plot_to_file(plot, temp_dir, format="html")

    assert path.endswith("HTML_Plot.html")
    assert os.path.exists(path)


def test_export_rejects_invalid_format(temp_dir, plot_factory, plot_service):
    """Test that invalid formats are rejected (security: prevent path traversal)."""
    plot = plot_factory.create_plot("bar", 3, "Security Test")
    df = pd.DataFrame({"x": ["A"], "y": [1]})
    plot.processed_data = df
    plot.config["x"] = "x"
    plot.config["y"] = "y"
    plot.config["title"] = "Test Title"
    plot.config["xlabel"] = "X"
    plot.config["ylabel"] = "Y"

    # Test path traversal attempt
    with pytest.raises(ValueError, match="Unsupported export format"):
        plot_service.export_plot_to_file(plot, temp_dir, format="../../../etc/passwd")

    # Test invalid extension
    with pytest.raises(ValueError, match="Unsupported export format"):
        plot_service.export_plot_to_file(plot, temp_dir, format="png")

    # Test empty format should use default (pdf) which is valid
    path = plot_service.export_plot_to_file(plot, temp_dir, format=None)
    assert path.endswith(".pdf")
