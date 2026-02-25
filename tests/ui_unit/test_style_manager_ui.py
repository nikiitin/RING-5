from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.pages.ui.plotting.styles import StyleManager
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_streamlit() -> Generator[None, None, None]:
    with (
        patch("src.web.pages.ui.plotting.styles.base_ui.st") as mock_st,
        patch(
            "src.web.components.plotting.settings.layout_settings.st",
            mock_st,
        ),
        patch(
            "src.web.components.plotting.settings.typography_settings.st",
            mock_st,
        ),
        patch(
            "src.web.components.plotting.settings.legend_settings.st",
            mock_st,
        ),
        patch(
            "src.web.components.plotting.settings.data_labels_settings.st",
            mock_st,
        ),
        patch(
            "src.web.components.plotting.settings.colors_settings.st",
            mock_st,
        ),
    ):
        mock_st.columns.side_effect = columns_side_effect

        # Mock number_input/slider to return int not Mock to match > logic
        mock_st.number_input.return_value = 0
        mock_st.slider.return_value = 0

        # Mock expander
        mock_st.expander.return_value.__enter__.return_value = MagicMock()

        # Mock selectbox to return a valid string for palette
        mock_st.selectbox.return_value = "Plotly"

        yield mock_st


@pytest.fixture
def style_manager() -> StyleManager:
    return StyleManager(1, "bar")


def test_render_layout_options(mock_streamlit: Any, style_manager: Any) -> None:

    config = {"width": 100}
    # render_layout_options now uses st.selectbox for preset + st.number_input
    mock_streamlit.selectbox.return_value = "Double Column (~7.0in)"

    result = style_manager.render_layout_options(config)

    # Assert keys present
    assert "width" in result
    assert "height" in result
    assert "margin_l" in result
    mock_streamlit.selectbox.assert_called()


def test_render_style_ui_basic(style_manager: Any, mock_streamlit: Any) -> None:

    config = {}

    # Just verify it runs and collects basics
    result = style_manager.render_style_ui(config)

    # Palette selection moved to _section_colors; render_style_ui handles
    # series styles, backgrounds, legends, and typography only.
    assert "series_styles" in result
    assert "plot_bgcolor" in result


def test_render_series_styling_ui_no_data(mock_streamlit: Any, style_manager: Any) -> None:

    config = {}
    result = style_manager.render_series_renaming_ui(config, None)
    assert result == {}


def test_render_series_styling_ui_with_data(mock_streamlit: Any, style_manager: Any) -> None:

    config = {"color": "C"}
    data = pd.DataFrame({"C": ["G1", "G2"]})

    # Mock styling inputs
    # For G1: Name="G1", CustomColor=True, Color="Red"
    # For G2: Name="G2 New", CustomColor=False

    # Mock unique values iteration by checking calls to markdown("**val**").

    style_manager.render_series_renaming_ui(config, data)

    # Should see markdown calls for group names
    # Note: unittest mock matching args in list
    calls = [c[0][0] for c in mock_streamlit.markdown.call_args_list]
    assert "**G1**" in calls
    assert "**G2**" in calls


def test_render_xaxis_labels_ui(mock_streamlit: Any, style_manager: Any) -> None:

    config = {"x": "XCol"}
    data = pd.DataFrame({"XCol": [1, 2]})

    # Mock text_input for renaming
    # Renaming 1 -> "One", 2 -> "" (no change)
    def text_input_side_effect(label: Any, value: Any, key: Any, **k: Any) -> str:

        # Validate key matching via placeholder argument.
        placeholder = k.get("placeholder", "")
        if str(placeholder) == "1":
            return "One"
        return ""

    mock_streamlit.text_input.side_effect = text_input_side_effect

    result = style_manager.render_xaxis_labels_ui(config, data)

    assert result["1"] == "One"
    assert "2" not in result
