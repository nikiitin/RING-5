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


@patch("src.plotting.export.ExportService")
def test_export_delegation(mock_export_service, mock_plot):
    fig = MagicMock()

    # Test HTML delegation
    mock_plot.config = {"download_format": "html"}
    PlotRenderer._render_download_button(mock_plot, fig)

    mock_export_service.render_download_button.assert_called_with(
        plot_name=mock_plot.name,
        plot_id=mock_plot.plot_id,
        fig=fig,
        config=mock_plot.config,
        key_prefix="dl_btn",
    )

    # Test PNG delegation
    mock_plot.config = {"download_format": "png"}
    PlotRenderer._render_download_button(mock_plot, fig)
    assert mock_export_service.render_download_button.call_count == 2
