"""Regression tests for ShapesSettingsComponent (audit finding M1).

The component must NEVER mutate the caller's (live) ``saved_config`` in
place; all edits are returned as a new list and committed through the
controller's change-detection path.
"""

from __future__ import annotations

from collections.abc import Generator
from copy import deepcopy
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.web.components.plotting.settings.shapes_settings import ShapesSettingsComponent
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_st() -> Generator[MagicMock]:
    """Mock Streamlit for shapes_settings."""
    with patch("src.web.components.plotting.settings.shapes_settings.st") as m_st:
        m_st.columns.side_effect = columns_side_effect
        m_st.button.return_value = False
        m_st.session_state.get.return_value = False  # edit mode off
        m_st.selectbox.return_value = "line"
        m_st.text_input.return_value = "1.0"
        m_st.color_picker.return_value = "#000000"
        m_st.number_input.return_value = 2
        yield m_st


def _config_with_shapes() -> dict[str, Any]:
    return {
        "shapes": [
            {
                "type": "line",
                "x0": 0.0,
                "y0": 0.5,
                "x1": 1.0,
                "y1": 0.5,
                "line": {"color": "#FF0000", "width": 2},
            }
        ]
    }


def test_render_does_not_mutate_saved_config(mock_st: MagicMock) -> None:
    """render() returns an independent copy; the input config is untouched."""
    saved_config = _config_with_shapes()
    snapshot = deepcopy(saved_config)

    result = ShapesSettingsComponent(plot_id=1, plot_type="bar").render(saved_config)

    # Input is byte-for-byte unchanged (no in-place mutation).
    assert saved_config == snapshot
    # Returned content equals the input shapes but is a distinct object graph.
    assert result == saved_config["shapes"]
    assert result is not saved_config["shapes"]
    assert result[0] is not saved_config["shapes"][0]
    assert result[0]["line"] is not saved_config["shapes"][0]["line"]


def test_add_shape_returns_new_list_without_mutating(mock_st: MagicMock) -> None:
    """Clicking 'Add Shape' yields a longer list, leaving saved_config intact."""
    mock_st.button.return_value = True  # 'Add Shape' clicked
    saved_config = _config_with_shapes()
    snapshot = deepcopy(saved_config)

    result = ShapesSettingsComponent(plot_id=1, plot_type="bar").render(saved_config)

    assert len(result) == 2  # original + appended
    assert saved_config == snapshot  # live config not mutated
