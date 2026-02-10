from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.base_plot import BasePlot


# Concrete implementation for testing abstract class
class ConcretePlot(BasePlot):
    def render_config_ui(self, data, saved_config):
        return {}

    def create_figure(self, data, config):
        return go.Figure()

    def get_legend_column(self, config):
        return "col"


@pytest.fixture
def concrete_plot():
    return ConcretePlot(plot_id=1, name="Test Plot", plot_type="test")


@pytest.fixture
def mock_streamlit():
    with patch("src.web.pages.ui.plotting.base_plot.st") as mock_st:
        mock_st.session_state = {}

        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]

        mock_st.columns.side_effect = columns_side_effect

        # Mock numeric inputs to return int for comparisons
        mock_st.number_input.return_value = 0
        mock_st.slider.return_value = 0

        # Mock selectbox to return first option or specific logic
        def selectbox_side_effect(label, options, index=0, **kwargs):
            if isinstance(options, list) and len(options) > index:
                return options[index]
            return MagicMock()

        mock_st.selectbox.side_effect = selectbox_side_effect

        yield mock_st


def test_serialization(concrete_plot):
    """Test to_dict and from_dict serialization."""
    concrete_plot.config = {"x": "col1"}
    concrete_plot.processed_data = pd.DataFrame({"col1": [1, 2, 3]})
    concrete_plot.pipeline = [{"type": "sort"}]

    data = concrete_plot.to_dict()

    assert data["id"] == 1
    assert data["name"] == "Test Plot"
    assert data["config"] == {"x": "col1"}
    assert "processed_data" in data

    # Test loading
    # Need to patch PlotFactory to avoiding circular imports or logic
    with patch("src.web.pages.ui.plotting.plot_factory.PlotFactory.create_plot") as mock_factory:
        mock_factory.return_value = ConcretePlot(1, "Test Plot", "test")

        loaded_plot = BasePlot.from_dict(data)

        assert loaded_plot.plot_id == 1
        assert loaded_plot.config == {"x": "col1"}
        assert len(loaded_plot.pipeline) == 1
        assert isinstance(loaded_plot.processed_data, pd.DataFrame)
        assert len(loaded_plot.processed_data) == 3


def test_render_common_config(concrete_plot, mock_streamlit):
    """Test common config UI rendering."""
    data = pd.DataFrame({"num": [1, 2], "cat": ["a", "b"]})
    saved_config = {"x": "num", "title": "My Title"}

    # Mock widget returns
    mock_streamlit.selectbox.side_effect = ["num", "num"]  # x, y
    mock_streamlit.text_input.side_effect = ["My Title", "X Label", "Y Label", "Leg Title"]

    config = concrete_plot.render_common_config(data, saved_config)

    assert config["x"] == "num"
    assert config["title"] == "My Title"


def test_apply_legend_labels(concrete_plot):
    """Test legend label application."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(name="trace1", x=[1], y=[1]))
    fig.add_trace(go.Scatter(name="trace2", x=[2], y=[2]))

    labels = {"trace1": "Renamed 1"}

    fig = concrete_plot.apply_legend_labels(fig, labels)

    assert fig.data[0].name == "Renamed 1"
    assert fig.data[1].name == "trace2"


def test_render_reorderable_list(concrete_plot, mock_streamlit):
    """Test reorderable list UI."""
    items = ["A", "B", "C"]

    # Initial render
    mock_streamlit.session_state = {}
    concrete_plot.render_reorderable_list("Label", items, "test_key")

    # Verify state initialization
    key = f"test_key_order_{concrete_plot.plot_id}"
    assert key in mock_streamlit.session_state
    assert mock_streamlit.session_state[key] == items

    # Simulate Swap A and B (Up button on B, index 1)
    # Mock button returns
    # We have loops. Up on index 1 should trigger swap.
    # Pattern: up_{i}
    def button_side_effect(label, key, **kwargs):
        if key == f"test_key_up_1_{concrete_plot.plot_id}":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    concrete_plot.render_reorderable_list("Label", items, "test_key")

    # State should be updated
    assert mock_streamlit.session_state[key] == ["B", "A", "C"]
    mock_streamlit.rerun.assert_called()


def test_render_advanced_options_shapes(concrete_plot, mock_streamlit):
    """Test advanced options with shape management."""
    config = {"shapes": []}

    # Mock adding a shape
    # Button "Add Shape" returns True
    # Inputs return minimal valid data
    def button_side_effect(label, key=None, **kwargs):
        if "add_shape" in str(key):
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    concrete_plot.render_advanced_options(config)

    # Should have appended a shape to config['shapes']
    # The code does shapes.append() which modifies the list in place if it came from config
    # `shapes = saved_config.get("shapes", [])`. If list exists in config, it updates config list.
    assert len(config["shapes"]) == 1
    assert config["shapes"][0]["type"] == "line"
    # Validate that the shape list length increased.
    mock_streamlit.rerun.assert_called()


def test_render_advanced_options_display(concrete_plot, mock_streamlit):
    """Test advanced options output dict."""
    config = {"download_format": "png"}

    res = concrete_plot.render_advanced_options(config)

    assert res["download_format"] == "png"  # Mock selectbox passes through or default
    # If mock selectbox returns MagicMock, this fails.
    # mock_streamlit fixture returns MagicMock for everything by default.
    # We should update side_effect strictly or use loose assertions.

    # Validate existence of expected configuration keys.
    assert "show_error_bars" in res
    assert "xaxis_tickangle" in res
