"""Behavioral tests for figure layout controls."""

from contextlib import nullcontext
from unittest.mock import MagicMock, patch


@patch("src.web.components.plotting.settings.layout_settings.st")
def test_custom_dimensions_are_converted_to_preview_pixels(mock_st: MagicMock) -> None:
    """Custom physical dimensions produce deterministic Plotly preview dimensions."""
    # [test->req~ring5.figure.layout~1]
    from src.web.components.plotting.settings.layout_settings import (
        LayoutSettingsComponent,
    )

    mock_st.selectbox.return_value = "Custom"
    mock_st.columns.return_value = [nullcontext(), nullcontext()]

    def number_input(label: str, *args: object, **kwargs: object) -> float:
        return 4.5 if label == "Width (inches)" else 3.0

    mock_st.number_input.side_effect = number_input

    result = LayoutSettingsComponent(plot_id=7, plot_type="bar").render({})

    assert result["document_width_preset"] == "Custom"
    assert result["width_inches"] == 4.5
    assert result["height_inches"] == 3.0
    assert result["width"] == 450
    assert result["height"] == 300
    assert result["automargin"] is True


@patch("src.web.components.plotting.settings.layout_settings.st")
def test_single_column_preset_fixes_width(mock_st: MagicMock) -> None:
    """The single-column publication preset resolves to 3.5 inches."""
    # [test->req~ring5.figure.layout~1]
    from src.web.components.plotting.settings.layout_settings import (
        LayoutSettingsComponent,
    )

    mock_st.selectbox.return_value = "Single Column (~3.5in)"
    mock_st.columns.return_value = [nullcontext(), nullcontext()]
    mock_st.number_input.side_effect = [3.5, 2.5]

    result = LayoutSettingsComponent(plot_id=2, plot_type="line").render({})

    assert result["width_inches"] == 3.5
    assert result["height_inches"] == 2.5
    assert result["width"] == 350
