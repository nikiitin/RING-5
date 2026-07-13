"""Tests for advanced_settings component."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tests.conftest import columns_side_effect


@pytest.fixture
def mock_st() -> Generator[MagicMock]:
    """Mock Streamlit for advanced_settings."""
    with patch("src.web.components.plotting.settings.advanced_settings.st") as m_st:
        m_st.columns.side_effect = columns_side_effect
        m_st.checkbox.return_value = False
        m_st.selectbox.return_value = "html"
        m_st.caption.return_value = None
        yield m_st


class TestAdvancedSettingsComponent:
    """Tests for ``AdvancedSettingsComponent``."""

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings.advanced_settings import (
            AdvancedSettingsComponent,
        )

        return AdvancedSettingsComponent(plot_id=1, plot_type="bar")

    def test_render_returns_config_dict(self, mock_st: MagicMock) -> None:
        """render() should return a dict with expected keys."""
        comp = self._make_component()
        result = comp.render(saved_config={})
        assert isinstance(result, dict)
        assert "show_error_bars" in result
        assert "download_format" in result
        assert "export_scale" in result
        assert "enable_editable" in result

    def test_default_values(self, mock_st: MagicMock) -> None:
        """Default config should have sensible defaults."""
        mock_st.checkbox.return_value = False
        mock_st.selectbox.side_effect = ["html", 1]
        comp = self._make_component()
        result = comp.render(saved_config={})
        assert result["show_error_bars"] is False
        assert result["enable_editable"] is False

    def test_preserves_series_styles(self, mock_st: MagicMock) -> None:
        """Existing series_styles should be preserved."""
        mock_st.selectbox.side_effect = ["html", 1]
        comp = self._make_component()
        saved = {"series_styles": {"s1": {"color": "red"}}}
        result = comp.render(saved_config=saved)
        assert result["series_styles"] == {"s1": {"color": "red"}}

    def test_reference_line_callback_called(self, mock_st: MagicMock) -> None:
        """When render_reference_line_fn is provided, it should be called."""
        mock_st.selectbox.side_effect = ["html", 1]
        comp = self._make_component()
        ref_fn = MagicMock()

        saved: dict[str, Any] = {}
        df = pd.DataFrame({"x": [1]})
        comp.render(
            saved_config=saved,
            data=df,
            render_reference_line_fn=ref_fn,
        )
        ref_fn.assert_called_once()

    def test_shapes_callback_called(self, mock_st: MagicMock) -> None:
        """When render_shapes_fn is provided, it should be called."""
        mock_st.selectbox.side_effect = ["html", 1]
        comp = self._make_component()
        shapes_fn = MagicMock(return_value=[])

        saved: dict[str, Any] = {}
        result = comp.render(
            saved_config=saved,
            render_shapes_fn=shapes_fn,
        )
        shapes_fn.assert_called_once()
        assert result["shapes"] == []

    def test_engine_callback_called(self, mock_st: MagicMock) -> None:
        """When render_engine_fn is provided, it should be called."""
        mock_st.selectbox.side_effect = ["html", 1]
        comp = self._make_component()
        engine_fn = MagicMock()

        comp.render(
            saved_config={},
            render_engine_fn=engine_fn,
        )
        engine_fn.assert_called_once()

    def test_saved_download_format_used(self, mock_st: MagicMock) -> None:
        """Saved download format should set the selectbox index correctly."""
        # We mock selectbox to return the saved value
        mock_st.selectbox.side_effect = ["pdf", 1]
        comp = self._make_component()
        result = comp.render(saved_config={"download_format": "pdf"})
        assert result["download_format"] == "pdf"

    def test_export_scale_caption(self, mock_st: MagicMock) -> None:
        """Should show download size caption."""
        mock_st.selectbox.side_effect = ["html", 2]
        comp = self._make_component()
        comp.render(saved_config={"width": 800, "height": 500})
        mock_st.caption.assert_called_once()
        caption_text = mock_st.caption.call_args[0][0]
        assert "1600" in caption_text  # 800 * 2
        assert "1000" in caption_text  # 500 * 2

    def test_no_callbacks_renders_without_error(self, mock_st: MagicMock) -> None:
        """Rendering with no callbacks should not raise."""
        mock_st.selectbox.side_effect = ["html", 1]
        comp = self._make_component()
        result = comp.render(saved_config={})
        assert isinstance(result, dict)
