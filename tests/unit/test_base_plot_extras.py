from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.pages.ui.plotting.base_plot import BasePlot


# Concrete implementation for testing abstract class
class ConcretePlot(BasePlot):
    def render_config_ui(self, data: Any, saved_config: Any) -> dict:

        return {}

    def create_traces(self, data: Any, config: Any) -> TraceBuildResult:

        from src.core.models.visualization.trace_build_result import TraceBuildResult

        return TraceBuildResult(traces=[])

    def get_legend_column(self, config: Any) -> None:

        return None


@pytest.fixture
def mock_streamlit() -> Generator[None, None, None]:
    with (
        patch("src.web.pages.ui.plotting.plot_config_ui.st") as mock_st,
        patch("src.web.components.common.reorderable_list.st", mock_st),
        patch("src.web.components.plotting.settings.shapes_settings.st", mock_st),
        patch("src.web.components.plotting.settings.reference_line_settings.st", mock_st),
        patch("src.web.components.plotting.settings.ordering_settings.st", mock_st),
    ):
        # Mock columns
        mock_st.columns.side_effect = lambda n: (
            [MagicMock() for _ in range(n)] if isinstance(n, int) else [MagicMock() for _ in n]
        )
        # Mock session_state
        mock_st.session_state = {}
        # Mock expander
        mock_st.expander.return_value.__enter__.return_value = MagicMock()
        yield mock_st


def test_render_advanced_options_shapes_add(mock_streamlit: Any) -> None:

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
    def button_side_effect(label: Any, key: Any = None, **kwargs: Any) -> int:

        if key == "add_shape_1":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    # Render
    result = plot.render_advanced_options(config, None)

    # New contract (audit M1): returned config holds the added shape; the
    # input saved_config is never mutated in place.
    assert config["shapes"] == []
    assert len(result["shapes"]) == 1
    shape_cfg = result["shapes"][0]
    assert shape_cfg["type"] == "line"
    assert shape_cfg["x0"] == 0.0
    assert shape_cfg["y0"] == 0.0


def test_render_advanced_options_shapes_edit_delete(mock_streamlit: Any) -> None:

    plot = ConcretePlot(1, "Test Plot", "scatter")
    config = {
        "shapes": [{"type": "line", "x0": 0, "y0": 0, "x1": 1, "y1": 1, "line": {"color": "red"}}]
    }

    # Enable edit mode in session state
    mock_streamlit.session_state["edit_shapes_1"] = True

    # Mock inputs for editing
    # We want to delete the shape.
    # key=f"del_shape_{i}_{self.plot_id}" -> "del_shape_0_1"

    def button_side_effect(label: Any, key: Any = None, **kwargs: Any) -> int:

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

    # Mock st.rerun to prevent actual rerun
    mock_streamlit.rerun = MagicMock()

    result = plot.render_advanced_options(config, None)

    # New contract (audit M1): deletion is reflected in the RETURNED config;
    # the input saved_config is never mutated in place.
    assert len(config["shapes"]) == 1
    assert len(result["shapes"]) == 0


def test_render_reorderable_list(mock_streamlit: Any) -> None:

    plot = ConcretePlot(1, "Test Plot", "bar")
    items = ["A", "B", "C"]

    # First render: Init session state
    result = plot.render_reorderable_list("List", items, "test")
    assert result == items
    assert mock_streamlit.session_state["test_order_1"] == items

    # Second render: Trigger Move Down on A (index 0)
    # key=f"{key_prefix}_down_{i}_{self.plot_id}" -> "test_down_0_1"

    def button_side_effect(label: Any, key: Any = None, **kwargs: Any) -> int:

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
