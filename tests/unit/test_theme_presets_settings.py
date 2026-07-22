"""Human-facing theme preset settings component tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.core.services.visualization.figure_theme_service import FigureThemeService
from src.web.components.plotting.settings.theme_presets_settings import (
    ThemePresetsSettingsComponent,
)


@patch("src.web.components.plotting.settings.theme_presets_settings.st")
def test_apply_dark_theme_refreshes_and_clears_only_stale_appearance_widgets(
    mock_st: MagicMock,
) -> None:
    # [test->req~ring5.figure.theme-presets~1]
    mock_st.selectbox.return_value = "dark"
    mock_st.button.return_value = True
    mock_st.file_uploader.return_value = None
    mock_st.text_input.return_value = "Dark review"
    mock_st.session_state = {
        "theme_title_sz_7": 8,
        "palette_select_7": "wong",
        "theme_title_sz_8": 99,
        "x_7": "phase",
    }

    result = ThemePresetsSettingsComponent(7, "bar").render({"x": "phase", "y": "ipc"})

    assert result["figure_theme_id"] == "dark"
    assert result["plot_bgcolor"] == "#202633"
    assert result["x"] == "phase"
    assert result["_ring5_request_refresh"] is True
    assert "theme_title_sz_7" not in mock_st.session_state
    assert "palette_select_7" not in mock_st.session_state
    assert mock_st.session_state["theme_title_sz_8"] == 99
    assert mock_st.session_state["x_7"] == "phase"
    mock_st.download_button.assert_called_once()


@patch("src.web.components.plotting.settings.theme_presets_settings.st")
def test_imported_theme_can_be_reviewed_and_applied(mock_st: MagicMock) -> None:
    # [test->req~ring5.figure.theme-presets~1]
    uploaded = MagicMock()
    uploaded.getvalue.return_value = FigureThemeService.dumps(FigureThemeService.get("paper"))
    mock_st.selectbox.return_value = "dashboard"
    mock_st.button.side_effect = [False, True]
    mock_st.file_uploader.return_value = uploaded
    mock_st.text_input.return_value = "Imported review"
    mock_st.session_state = {}

    result = ThemePresetsSettingsComponent(2, "line").render({"x": "phase", "y": "ipc"})

    assert result["figure_theme_id"] == "paper"
    assert result["x"] == "phase"
    assert result["_ring5_request_refresh"] is True
    assert any(
        "Imported Publication paper" in call.args[0] for call in mock_st.success.call_args_list
    )


@patch("src.web.components.plotting.settings.theme_presets_settings.st")
def test_invalid_import_is_explained_without_changing_the_plot(mock_st: MagicMock) -> None:
    # [test->req~ring5.figure.theme-presets~1]
    uploaded = MagicMock()
    uploaded.getvalue.return_value = b"not-json"
    mock_st.selectbox.return_value = "paper"
    mock_st.button.return_value = False
    mock_st.file_uploader.return_value = uploaded
    mock_st.text_input.return_value = "Current theme"
    mock_st.session_state = {}

    result = ThemePresetsSettingsComponent(3, "scatter").render({"x": "phase"})

    assert result == {}
    assert "valid UTF-8 JSON" in mock_st.error.call_args.args[0]
