from unittest.mock import MagicMock, patch

import pytest

from src.web.pages.ui.components.layout_components import LayoutComponents


@pytest.fixture
def mock_streamlit():
    with patch("src.web.pages.ui.components.layout_components.st") as mock_st:
        # Mock columns to return list of mocks
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]

        mock_st.columns.side_effect = columns_side_effect
        yield mock_st


def test_sidebar_info(mock_streamlit):
    LayoutComponents.sidebar_info()
    mock_streamlit.markdown.assert_called_with("### About RING-5")
    mock_streamlit.info.assert_called()


def test_navigation_menu(mock_streamlit):
    mock_streamlit.radio.return_value = "Data Source"

    selected = LayoutComponents.navigation_menu()

    assert selected == "Data Source"
    mock_streamlit.radio.assert_called_with(
        "Navigation",
        [
            "Data Source",
            "Upload Data",
            "Data Managers",
            "Configure Pipeline",
            "Generate Plots",
            "Load Configuration",
        ],
        label_visibility="collapsed",
    )


def test_progress_display(mock_streamlit):
    LayoutComponents.progress_display(1, 5, "Processing...")

    # 1/5 = 0.2
    mock_streamlit.progress.assert_called_with(0.2)
    mock_streamlit.text.assert_called_with("Processing...")


def test_add_variable_button(mock_streamlit):
    # Case 1: Button clicked
    mock_streamlit.button.return_value = True
    assert LayoutComponents.add_variable_button() is True

    # Case 2: Button not clicked
    mock_streamlit.button.return_value = False
    assert LayoutComponents.add_variable_button() is False

    mock_streamlit.columns.assert_called_with([1, 4])


def test_clear_data_button(mock_streamlit):
    mock_streamlit.button.return_value = True
    assert LayoutComponents.clear_data_button() is True
    mock_streamlit.button.assert_called_with("Clear All Data", width="stretch")
