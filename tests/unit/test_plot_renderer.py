from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.plotting.base_plot import BasePlot
from src.plotting.plot_renderer import PlotRenderer


class MockPlot(BasePlot):
    def __init__(self):
        super().__init__("TestPlot", "test_id", "bar")
        self.config = {}
        self.processed_data = None
        self.last_generated_fig = None
        self.legend_mappings_by_column = {}

    def create_figure(self, data, config):
        fig = MagicMock()
        fig.data = []
        return fig

    def render_config_ui(self, data, config):
        return config

    def get_legend_column(self, config):
        return config.get("legend_col")


@pytest.fixture
def mock_streamlit():
    with patch("src.plotting.plot_renderer.st") as mock_st:
        yield mock_st


@pytest.fixture
def mock_plot():
    return MockPlot()


def test_render_legend_customization_no_col(mock_plot):
    mock_plot.config = {}  # No legend_col
    data = pd.DataFrame()

    result = PlotRenderer.render_legend_customization(mock_plot, data, mock_plot.config)

    assert result is None


def test_render_legend_customization_with_col(mock_streamlit, mock_plot):
    mock_plot.config = {"legend_col": "C"}
    data = pd.DataFrame({"C": ["A", "B", "A"]})

    # Mock text_input to provide custom label for 'A' but not 'B'
    def text_input_side_effect(label, value, key, **kwargs):
        if "A" in label:
            return "Custom A"
        return value  # Default

    mock_streamlit.text_input.side_effect = text_input_side_effect

    result = PlotRenderer.render_legend_customization(mock_plot, data, mock_plot.config)

    assert result["A"] == "Custom A"
    assert result["B"] == "B"
    assert mock_plot.legend_mappings_by_column["C"] == result


@patch("src.web.ui.components.interactive_plot.interactive_plotly_chart")
def test_render_plot_regenerate(mock_interactive_chart, mock_streamlit, mock_plot):
    mock_plot.processed_data = pd.DataFrame({"x": [1]})

    PlotRenderer.render_plot(mock_plot, should_generate=True)

    assert mock_plot.last_generated_fig is not None
    mock_interactive_chart.assert_called()


@patch("src.web.ui.components.interactive_plot.interactive_plotly_chart")
def test_render_plot_cached(mock_interactive_chart, mock_streamlit, mock_plot):
    fig = MagicMock()
    mock_plot.last_generated_fig = fig

    PlotRenderer.render_plot(mock_plot, should_generate=False)

    # create_figure should NOT be called
    with patch.object(mock_plot, "create_figure") as mock_create:
        PlotRenderer.render_plot(mock_plot, should_generate=False)
        mock_create.assert_not_called()

    # Verify interactive chart called instead of st.plotly_chart
    args, kwargs = mock_interactive_chart.call_args
    assert args[0] == fig
    assert "config" in kwargs


def test_export_html(mock_streamlit, mock_plot):
    mock_plot.config = {"download_format": "html"}
    fig = MagicMock()

    with patch("plotly.io.to_html", return_value="<html></html>"):
        PlotRenderer._render_download_button(mock_plot, fig)

    mock_streamlit.download_button.assert_called()
    args = mock_streamlit.download_button.call_args[1]
    assert args["mime"] == "text/html"


def test_export_png_kaleido_success(mock_streamlit, mock_plot):
    mock_plot.config = {"download_format": "png"}
    fig = MagicMock()

    # Mock kaleido write_image success
    fig.write_image = MagicMock()

    # We need to mock import kaleido.
    # Since it's inside the function, we can patch sys.modules or just let it fail/pass depending on env.
    # To ensure success path, we need to mock fig.write_image AND ensure import works or is mocked.
    # The code does `import kaleido`.

    with patch.dict("sys.modules", {"kaleido": MagicMock()}):
        PlotRenderer._render_download_button(mock_plot, fig)

    fig.write_image.assert_called()
    mock_streamlit.download_button.assert_called()
    args = mock_streamlit.download_button.call_args[1]
    assert args["mime"] == "image/png"


def test_export_png_fallback(mock_streamlit, mock_plot):
    mock_plot.config = {"download_format": "png"}
    fig = MagicMock()
    # Ensure write_image fails
    fig.write_image.side_effect = ImportError("No kaleido")

    # Mock matplotlib
    with patch("matplotlib.pyplot.figure") as mock_plt_fig:
        PlotRenderer._render_download_button(mock_plot, fig)

    mock_plt_fig.assert_called()  # Fallback triggered
    mock_streamlit.download_button.assert_called()
