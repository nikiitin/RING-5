from unittest.mock import MagicMock, patch

import pytest

from src.plotting.base_plot import BasePlot


# Concrete implementation for testing abstract class
class ConcretePlot(BasePlot):
    def render_config_ui(self, data, saved_config):
        return {}

    def create_figure(self, data, config):
        pass

    def get_legend_column(self, config):
        return None


@pytest.fixture
def mock_streamlit():
    with patch("src.plotting.base_plot.st") as mock_st:
        # Mock columns
        mock_st.columns.side_effect = lambda n: (
            [MagicMock() for _ in range(n)] if isinstance(n, int) else [MagicMock() for _ in n]
        )
        # Mock session_state
        mock_st.session_state = {}
        # Mock expander
        mock_st.expander.return_value.__enter__.return_value = MagicMock()
        yield mock_st


def test_render_advanced_options_shapes_add(mock_streamlit):
    plot = ConcretePlot(1, "Test Plot", "scatter")
    config = {"shapes": []}

    # Mock inputs for adding shape
    # selectbox (Type): "line"
    # text_input (x0, y0, x1, y1): "0", "0", "1", "1"
    # color_picker (Color): "#000000"
    # number_input (Width): 2
    # button (Add Shape): True

    # 1. Add Shape Inputs (4 text_inputs)
    # 2. Existing Shape Inputs (4 text_inputs per shape) - After addition, there is 1 shape.
    # Total needed: 4 + 4 = 8

    mock_streamlit.selectbox.return_value = "line"
    mock_streamlit.text_input.side_effect = ["0", "0", "1", "1", "0", "0", "1", "1"]
    mock_streamlit.color_picker.return_value = "#000000"
    mock_streamlit.number_input.return_value = 2

    # Mock specific button return for "Add Shape".
    def button_side_effect(label, key=None, **kwargs):
        if key == "add_shape_1":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    # Render
    plot.render_advanced_options(config, None)

    # Check config update
    assert len(config["shapes"]) == 1
    shape_cfg = config["shapes"][0]
    assert shape_cfg["type"] == "line"
    assert shape_cfg["x0"] == 0.0
    assert shape_cfg["y0"] == 0.0


def test_render_advanced_options_shapes_edit_delete(mock_streamlit):
    plot = ConcretePlot(1, "Test Plot", "scatter")
    config = {
        "shapes": [{"type": "line", "x0": 0, "y0": 0, "x1": 1, "y1": 1, "line": {"color": "red"}}]
    }

    # Mock inputs for editing
    # We want to delete the shape.
    # key=f"del_shape_{i}_{self.plot_id}" -> "del_shape_0_1"

    def button_side_effect(label, key=None, **kwargs):
        if key == "del_shape_0_1":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect
    mock_streamlit.number_input.return_value = 0.0  # yaxis_dtick etc

    # Inputs for text_input (x0..y1).
    # 'Add New Shape' inputs are rendered first (4), then existing shapes (4 * N).
    # Provide 4 dummy values for "Add New", then 4 for the shape about to be deleted.

    mock_streamlit.text_input.side_effect = [
        "new_x0",
        "new_y0",
        "new_x1",
        "new_y1",
        "0",
        "0",
        "1",
        "1",
    ]

    plot.render_advanced_options(config, None)

    # Shape should be popped
    assert len(config["shapes"]) == 0


def test_render_reorderable_list(mock_streamlit):
    plot = ConcretePlot(1, "Test Plot", "bar")
    items = ["A", "B", "C"]

    # First render: Init session state
    result = plot.render_reorderable_list("List", items, "test")
    assert result == items
    assert mock_streamlit.session_state["test_order_1"] == items

    # Second render: Trigger Move Down on A (index 0)
    # key=f"{key_prefix}_down_{i}_{self.plot_id}" -> "test_down_0_1"

    def button_side_effect(label, key=None, **kwargs):
        if key == "test_down_0_1":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    # We need to simulate the loop.
    # Logic: It iterates `current_items` from session state.
    # So if we want to test interaction, we run it again with the mocked click.

    plot.render_reorderable_list("List", items, "test")

    # A should swap with B -> [B, A, C]
    # Logic modifies `current_items` in place then writes back to session state.

    expected = ["B", "A", "C"]
    assert mock_streamlit.session_state["test_order_1"] == expected
