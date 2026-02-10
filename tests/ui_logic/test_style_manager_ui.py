from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.pages.ui.plotting.styles import StyleManager


@pytest.fixture
def mock_streamlit():
    with patch("src.web.pages.ui.plotting.styles.base_ui.st") as mock_st:
        # Mock columns
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]

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
def style_manager():
    return StyleManager("plot1", "bar")


def test_render_layout_options(mock_streamlit, style_manager):
    config = {"width": 100}
    # Mock return values for sliders/inputs
    # Layout order: Width, Height, then Margin Inputs

    result = style_manager.render_layout_options(config)

    # Assert keys present
    assert "width" in result
    assert "height" in result
    assert "margin_l" in result
    mock_streamlit.slider.assert_called()


def test_render_style_ui_basic(style_manager, mock_streamlit):
    config = {}

    # Just verify it runs and collects basics
    result = style_manager.render_style_ui(config)

    assert "color_palette" in result
    assert "plot_bgcolor" in result
    assert "legend_orientation" in result


def test_render_series_styling_ui_no_data(mock_streamlit, style_manager):
    config = {}
    result = style_manager.render_series_renaming_ui(config, None)
    assert result == {}


def test_render_series_styling_ui_with_data(mock_streamlit, style_manager):
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


def test_render_xaxis_labels_ui(mock_streamlit, style_manager):
    config = {"x": "XCol"}
    data = pd.DataFrame({"XCol": [1, 2]})

    # Mock text_input for renaming
    # Renaming 1 -> "One", 2 -> "" (no change)
    def text_input_side_effect(label, value, key, **k):
        # Validate key matching via placeholder argument.
        placeholder = k.get("placeholder", "")
        if str(placeholder) == "1":
            return "One"
        return ""

    mock_streamlit.text_input.side_effect = text_input_side_effect

    result = style_manager.render_xaxis_labels_ui(config, data)

    assert result["1"] == "One"
    assert "2" not in result
