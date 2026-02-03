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
        # Ensure to_json returns a string to avoid serialization errors
        # if the real interactive_plotly_chart is accidentally hit
        fig.to_json.return_value = "{}"
        return fig

    def render_config_ui(self, data, config):
        return config

    def get_legend_column(self, config):
        return config.get("legend_col")


@pytest.fixture
def mock_streamlit():
    with patch("src.plotting.plot_renderer.st") as mock_st, patch(
        "src.plotting.base_plot.StyleManager"
    ) as MockStyleManager:

        # Configure StyleManager mock
        style_manager_instance = MockStyleManager.return_value
        style_manager_instance.apply_styles.side_effect = lambda fig, config: fig

        # Configure session_state
        mock_st.session_state = {}

        # Configure st.columns to return the correct number of MagicMocks
        def mock_columns(num_cols):
            return tuple(MagicMock() for _ in range(num_cols))

        mock_st.columns.side_effect = mock_columns

        yield mock_st


@pytest.fixture
def mock_plot(mock_streamlit):
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


@patch("src.plotting.plot_renderer.LaTeXExportService")
@patch("src.plotting.plot_renderer.interactive_plotly_chart")
def test_render_plot_regenerate(
    mock_interactive_chart, mock_export_service, mock_streamlit, mock_plot
):
    # Configure the LaTeXExportService mock
    mock_service_instance = mock_export_service.return_value
    mock_service_instance.list_presets.return_value = ["single_column", "double_column"]
    mock_service_instance.get_preset_info.return_value = {
        "width_inches": 3.5,
        "height_inches": 2.5,
        "dpi": 300,
        "legend_columnspacing": 1.0,
        "legend_labelspacing": 0.3,
        "legend_handlelength": 1.5,
        "legend_handleheight": 0.7,
        "legend_handletextpad": 0.5,
        "legend_borderpad": 0.3,
        "legend_borderaxespad": 0.3,
        "font_size_title": 10,
        "font_size_xlabel": 9,
        "font_size_ylabel": 9,
        "font_size_legend": 8,
        "font_size_ticks": 7,
        "font_size_annotations": 6,
        "bold_title": False,
        "bold_xlabel": False,
        "bold_ylabel": False,
        "bold_ticks": False,
        "bold_legend": False,
        "bold_annotations": True,
        "ylabel_pad": 10.0,
        "ylabel_y_position": 0.5,
        "xtick_pad": 5.0,
        "ytick_pad": 5.0,
        "xtick_rotation": 0.0,
        "xtick_ha": "center",
    }

    mock_plot.processed_data = pd.DataFrame({"x": [1]})

    PlotRenderer.render_plot(mock_plot, should_generate=True)

    # Check that st.error wasn't called (which would indicate an exception)
    if mock_streamlit.error.called:
        pytest.fail(f"st.error called with: {mock_streamlit.error.call_args}")

    assert mock_plot.last_generated_fig is not None
    mock_interactive_chart.assert_called()


@patch("src.plotting.plot_renderer.LaTeXExportService")
@patch("src.plotting.plot_renderer.interactive_plotly_chart")
def test_render_plot_cached(mock_interactive_chart, mock_export_service, mock_streamlit, mock_plot):
    # Configure the LaTeXExportService mock
    mock_service_instance = mock_export_service.return_value
    mock_service_instance.list_presets.return_value = ["single_column", "double_column"]
    mock_service_instance.get_preset_info.return_value = {
        "width_inches": 3.5,
        "height_inches": 2.5,
        "legend_columnspacing": 1.0,
        "legend_labelspacing": 0.3,
        "legend_handlelength": 1.5,
        "legend_handleheight": 0.7,
        "legend_handletextpad": 0.5,
        "legend_borderpad": 0.3,
        "legend_borderaxespad": 0.3,
        "font_size_title": 10,
        "font_size_xlabel": 9,
        "font_size_ylabel": 9,
        "font_size_legend": 8,
        "dpi": 300,
        "font_size_ticks": 7,
        "font_size_annotations": 6,
        "bold_title": False,
        "bold_xlabel": False,
        "bold_ylabel": False,
        "bold_ticks": False,
        "bold_legend": False,
        "bold_annotations": True,
        "ylabel_pad": 10.0,
        "ylabel_y_position": 0.5,
        "xtick_pad": 5.0,
        "ytick_pad": 5.0,
        "xtick_rotation": 0.0,
        "xtick_ha": "center",
    }

    fig = MagicMock()
    # Safely mock to_json in case real code is hit
    fig.to_json.return_value = "{}"
    mock_plot.last_generated_fig = fig
    mock_plot.processed_data = pd.DataFrame({"x": [1]})  # Add required data

    PlotRenderer.render_plot(mock_plot, should_generate=False)

    # create_figure should NOT be called
    with patch.object(mock_plot, "create_figure") as mock_create:
        PlotRenderer.render_plot(mock_plot, should_generate=False)
        mock_create.assert_not_called()

    # Verify interactive chart called instead of st.plotly_chart
    # Check that st.error wasn't called
    if mock_streamlit.error.called:
        pytest.fail(f"st.error called with: {mock_streamlit.error.call_args}")

    mock_interactive_chart.assert_called()
    args, kwargs = mock_interactive_chart.call_args
    assert args[0] == fig
    assert "config" in kwargs


@patch("src.plotting.plot_renderer.LaTeXExportService")
def test_export_delegation(mock_export_service, mock_streamlit, mock_plot):
    # Configure the LaTeXExportService mock
    mock_service_instance = mock_export_service.return_value
    mock_service_instance.list_presets.return_value = ["single_column", "double_column"]
    mock_service_instance.get_preset_info.return_value = {
        "width_inches": 3.5,
        "height_inches": 2.5,
        "legend_columnspacing": 1.0,
        "legend_labelspacing": 0.3,
        "legend_handlelength": 1.5,
        "legend_handleheight": 0.7,
        "legend_handletextpad": 0.5,
        "legend_borderpad": 0.3,
        "legend_borderaxespad": 0.3,
        "font_size_title": 10,
        "font_size_xlabel": 9,
        "dpi": 300,
        "font_size_ylabel": 9,
        "font_size_legend": 8,
        "font_size_ticks": 7,
        "font_size_annotations": 6,
        "bold_title": False,
        "bold_xlabel": False,
        "bold_ylabel": False,
        "bold_ticks": False,
        "bold_legend": False,
        "bold_annotations": True,
        "ylabel_pad": 10.0,
        "ylabel_y_position": 0.5,
        "xtick_pad": 5.0,
        "ytick_pad": 5.0,
        "xtick_rotation": 0.0,
        "xtick_ha": "center",
    }

    fig = MagicMock()

    # Test HTML delegation
    mock_plot.config = {"download_format": "html"}
    PlotRenderer._render_download_button(mock_plot, fig)

    # Note: LaTeXExportService doesn't have render_download_button method
    # The button is rendered directly by PlotRenderer
    # This test verifies the method runs without error
    assert mock_streamlit.columns.called
