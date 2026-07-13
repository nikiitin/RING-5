from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.pages.ui.plotting.base_plot import BasePlot


class ConcretePlot(BasePlot):
    """Minimal BasePlot implementation for control tests."""

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
        mock_st.columns.side_effect = lambda n: (
            [MagicMock() for _ in range(n)] if isinstance(n, int) else [MagicMock() for _ in n]
        )
        mock_st.session_state = {}
        mock_st.expander.return_value.__enter__.return_value = MagicMock()
        yield mock_st


def test_render_advanced_options_shapes_add(mock_streamlit: Any) -> None:

    plot = ConcretePlot(1, "Test Plot", "scatter")
    config = {"shapes": []}

    # Four fields configure the new shape and four configure its editor.
    mock_streamlit.selectbox.return_value = "line"
    mock_streamlit.text_input.side_effect = ["0", "0", "1", "1", "0", "0", "1", "1"]
    mock_streamlit.color_picker.return_value = "#000000"
    mock_streamlit.number_input.return_value = 2

    def button_side_effect(label: Any, key: Any = None, **kwargs: Any) -> int:

        if key == "add_shape_1":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    result = plot.render_advanced_options(config, None)

    # Rendering leaves the input configuration unchanged.
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

    mock_streamlit.session_state["edit_shapes_1"] = True

    def button_side_effect(label: Any, key: Any = None, **kwargs: Any) -> int:

        if key == "del_shape_0_1":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect
    mock_streamlit.number_input.return_value = 0.0
    # New-shape fields precede the fields for the existing shape.
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

    mock_streamlit.rerun = MagicMock()

    result = plot.render_advanced_options(config, None)

    # Deletion leaves the input configuration unchanged.
    assert len(config["shapes"]) == 1
    assert len(result["shapes"]) == 0


def test_render_reorderable_list(mock_streamlit: Any) -> None:

    plot = ConcretePlot(1, "Test Plot", "bar")
    items = ["A", "B", "C"]

    result = plot.render_reorderable_list("List", items, "test")
    assert result == items
    assert mock_streamlit.session_state["test_order_1"] == items

    def button_side_effect(label: Any, key: Any = None, **kwargs: Any) -> int:

        if key == "test_down_0_1":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    # The second render moves the first item down once.
    plot.render_reorderable_list("List", items, "test")
    expected = ["B", "A", "C"]
    assert mock_streamlit.session_state["test_order_1"] == expected
