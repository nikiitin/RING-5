from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.pages.ui.components.plot_manager_components import PlotManagerComponents
from src.web.pages.ui.plotting.base_plot import BasePlot


class MockPlot(BasePlot):
    """Mock implementation of BasePlot for testing."""

    def render_config_ui(self, data, config):
        return {}

    def create_figure(self, data, config):
        return MagicMock()

    def get_legend_column(self, config):
        return None


@pytest.fixture
def mock_streamlit():
    with patch("src.web.pages.ui.components.plot_manager_components.st") as mock_st:
        mock_st.session_state = {}

        # Mock columns
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]

        mock_st.columns.side_effect = columns_side_effect

        yield mock_st


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.state_manager = MagicMock()
    api.backend = MagicMock()
    return api


@pytest.fixture
def mock_plot_service():
    with patch("src.web.pages.ui.components.plot_manager_components.PlotService") as mock_ps:
        yield mock_ps


@pytest.fixture
def mock_plot_factory():
    with patch("src.web.pages.ui.components.plot_manager_components.PlotFactory") as mock_pf:
        yield mock_pf


def test_render_create_plot_section(mock_streamlit, mock_api, mock_plot_service, mock_plot_factory):
    """Test creating a new plot."""
    mock_api.state_manager.get_plot_counter.return_value = 0
    mock_plot_factory.get_available_plot_types.return_value = ["Bar"]

    mock_streamlit.text_input.return_value = "New Plot"
    mock_streamlit.selectbox.return_value = "Bar"
    mock_streamlit.button.return_value = True

    PlotManagerComponents.render_create_plot_section(mock_api)

    mock_plot_service.create_plot.assert_called_with("New Plot", "Bar", mock_api.state_manager)
    mock_streamlit.rerun.assert_called()


def test_render_plot_selector(mock_streamlit, mock_api):
    """Test selecting a plot."""
    plot1 = MockPlot(1, "Plot 1", "Bar")
    plot2 = MockPlot(2, "Plot 2", "Line")
    mock_api.state_manager.get_plots.return_value = [plot1, plot2]
    mock_api.state_manager.get_current_plot_id.return_value = 1

    mock_streamlit.radio.return_value = "Plot 2"

    selected = PlotManagerComponents.render_plot_selector(mock_api)

    assert selected == plot2
    mock_api.state_manager.set_current_plot_id.assert_called_with(2)


def test_render_plot_controls(mock_streamlit, mock_api, mock_plot_service):
    """Test plot controls (rename, delete, duplicate)."""
    plot = MockPlot(1, "Original Name", "Bar")

    mock_streamlit.text_input.return_value = "New Name"

    def button_side_effect(label, key=None, **kwargs):
        if key == f"delete_plot_{plot.plot_id}":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    PlotManagerComponents.render_plot_controls(mock_api, plot)

    assert plot.name == "New Name"
    mock_plot_service.delete_plot.assert_called_with(1, mock_api.state_manager)
    mock_streamlit.rerun.assert_called()


def test_render_pipeline_editor_add_shaper(mock_streamlit, mock_api):
    """Test adding a shaper to the pipeline."""
    plot = MockPlot(1, "Test Plot", "Bar")
    plot.pipeline = []

    mock_api.state_manager.get_data.return_value = pd.DataFrame({"A": [1]})

    mock_streamlit.selectbox.return_value = "Sort"

    def button_side_effect(label, key=None, **kwargs):
        if key == f"add_shaper_btn_{plot.plot_id}":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    PlotManagerComponents.render_pipeline_editor(mock_api, plot)

    assert len(plot.pipeline) == 1
    assert plot.pipeline[0]["type"] == "sort"


def test_render_pipeline_editor_finalize(mock_streamlit, mock_api):
    """Test finalizing the pipeline."""
    plot = MockPlot(1, "Test Plot", "Bar")
    plot.pipeline = [{"type": "sort", "config": {"col": "A"}, "id": 0}]

    df = pd.DataFrame({"A": [2, 1]})
    mock_api.state_manager.get_data.return_value = df

    def button_side_effect(label, key=None, **kwargs):
        if key == f"finalize_{plot.plot_id}":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    with patch("src.web.pages.ui.components.plot_manager_components.apply_shapers") as mock_apply:
        mock_apply.return_value = pd.DataFrame({"A": [1, 2]})

        PlotManagerComponents.render_pipeline_editor(mock_api, plot)

        mock_apply.assert_called()
        assert plot.processed_data is not None
        mock_streamlit.success.assert_called()


def test_render_plot_display(mock_streamlit, mock_api, mock_plot_factory, mock_plot_service):
    """Test rendering the plot display section."""
    plot = MockPlot(1, "Test Plot", "Bar")
    plot.processed_data = pd.DataFrame({"A": [1]})
    plot.config = {}

    mock_plot_factory.get_available_plot_types.return_value = ["Bar", "Line"]

    mock_streamlit.selectbox.return_value = "Line"

    PlotManagerComponents.render_plot_display(mock_api, plot)

    mock_plot_service.change_plot_type.assert_called_with(plot, "Line", mock_api.state_manager)
