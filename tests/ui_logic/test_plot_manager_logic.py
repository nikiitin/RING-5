from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.plotting.base_plot import BasePlot
from src.web.ui.components.plot_manager_components import PlotManagerComponents


# Mock streamlit
@pytest.fixture
def mock_streamlit():
    with patch("src.web.ui.components.plot_manager_components.st") as mock_st:
        # Mock session state as a dict
        mock_st.session_state = {}

        # Side effect for columns to return correct number of items
        def columns_side_effect(spec, gap="small", vertical_alignment="top"):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]

        mock_st.columns.side_effect = columns_side_effect
        yield mock_st


@pytest.fixture
def mock_plot_service():
    with patch("src.web.ui.components.plot_manager_components.PlotService") as mock_ps:
        yield mock_ps


@pytest.fixture
def mock_state_manager():
    with patch("src.web.ui.components.plot_manager_components.StateManager") as mock_sm:
        yield mock_sm


@pytest.fixture
def mock_plot_factory():
    with patch("src.web.ui.components.plot_manager_components.PlotFactory") as mock_pf:
        yield mock_pf


class DummyPlot(BasePlot):
    def render_config_ui(self, data, saved_config):
        return {}

    def create_figure(self, data, config):
        return None

    def get_legend_column(self, config):
        return None


def test_render_create_plot_section(
    mock_streamlit, mock_plot_service, mock_state_manager, mock_plot_factory
):
    """Test creating a new plot via UI."""

    # Setup Mocks
    mock_state_manager.get_plot_counter.return_value = 0
    mock_plot_factory.get_available_plot_types.return_value = ["bar", "line"]

    # Mock UI Interactions
    mock_streamlit.text_input.return_value = "My New Plot"  # Plot Name
    mock_streamlit.selectbox.return_value = "bar"  # Plot Type
    mock_streamlit.button.return_value = True  # Click Create

    # Run SUT
    PlotManagerComponents.render_create_plot_section()

    # Assertions
    mock_plot_service.create_plot.assert_called_once_with("My New Plot", "bar")
    mock_streamlit.rerun.assert_called_once()


def test_render_plot_controls_rename(mock_streamlit, mock_plot_service):
    """Test renaming a plot."""
    plot = DummyPlot(1, "Old Name", "bar")

    # Mock UI
    mock_streamlit.columns.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_streamlit.text_input.return_value = "New Name"
    mock_streamlit.button.return_value = False

    PlotManagerComponents.render_plot_controls(plot)

    assert plot.name == "New Name"


def test_render_plot_controls_delete(mock_streamlit, mock_plot_service):
    """Test deleting a plot."""
    plot = DummyPlot(1, "To Delete", "bar")

    # Mock UI
    cols = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_streamlit.columns.return_value = cols
    mock_streamlit.text_input.return_value = "To Delete"

    # Logic:
    # col1: rename
    # col2: save/load
    # col3: delete -> We want this button to be True
    # col4: duplicate

    # Mock button calls. Since button is called multiple times, we need side_effect
    # Calls: Save Pipe, Load Pipe, Delete, Duplicate
    # Keys used: save_plot_1, load_plot_1, delete_plot_1, dup_plot_1

    def button_side_effect(label, key=None, **kwargs):
        if key == f"delete_plot_{plot.plot_id}":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    PlotManagerComponents.render_plot_controls(plot)

    mock_plot_service.delete_plot.assert_called_once_with(1)
    mock_streamlit.rerun.assert_called_once()


def test_pipeline_editor_add_shaper(mock_streamlit, mock_state_manager):
    """Test adding a shaper to the pipeline."""
    plot = DummyPlot(1, "Pipe Plot", "bar")

    # Mock Data
    mock_state_manager.get_data.return_value = pd.DataFrame()

    # Mock UI
    mock_streamlit.columns.return_value = [MagicMock(), MagicMock()]
    mock_streamlit.selectbox.return_value = "Sort"  # Selected Shaper

    def button_side_effect(label=None, key=None, **kwargs):
        if key == f"add_shaper_btn_{plot.plot_id}":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    PlotManagerComponents.render_pipeline_editor(plot)

    assert len(plot.pipeline) == 1
    assert plot.pipeline[0]["type"] == "sort"
    assert plot.pipeline[0]["id"] == 0
    mock_streamlit.rerun.assert_called_once()
