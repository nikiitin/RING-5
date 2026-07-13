"""Tests for colorblind-safe palette defaults and selection."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.palettes import PALETTE_REGISTRY
from tests.conftest import columns_side_effect


class TestDefaultPalette:
    """Verify Wong palette is the default."""

    def test_figure_spec_default_is_wong(self) -> None:
        spec = FigureConfig()
        expected_wong = [
            "#000000",
            "#E69F00",
            "#56B4E9",
            "#009E73",
            "#F0E442",
            "#0072B2",
            "#D55E00",
            "#CC79A7",
        ]
        assert spec.color_palette == expected_wong

    def test_builtin_palettes_exist(self) -> None:
        assert "wong" in PALETTE_REGISTRY
        assert "viridis_8" in PALETTE_REGISTRY
        assert "seaborn_cb" in PALETTE_REGISTRY
        assert "tol_bright" in PALETTE_REGISTRY
        assert "okabe_ito" in PALETTE_REGISTRY

    def test_all_palettes_have_at_least_7_colors(self) -> None:
        for name in ("wong", "viridis_8", "seaborn_cb", "tol_bright", "okabe_ito"):
            colors = PALETTE_REGISTRY[name]
            assert len(colors) >= 7, f"Palette {name} has only {len(colors)} colors"

    def test_all_hex_colors_valid(self) -> None:
        import re

        pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for name in ("wong", "viridis_8", "seaborn_cb", "tol_bright", "okabe_ito"):
            for c in PALETTE_REGISTRY[name]:
                assert pattern.match(c), f"Invalid hex in {name}: {c}"


class TestPaletteSelector:
    """Verify palette selector widget in ColorsSettingsComponent."""

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings import (
            ColorsSettingsComponent,
        )

        return ColorsSettingsComponent(plot_id=1, plot_type="bar")

    @patch("src.web.components.plotting.settings.colors_settings.st")
    def test_selecting_wong_sets_palette_key(self, mock_st: MagicMock) -> None:
        mock_st.selectbox.return_value = "wong"
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#000000"
        comp = self._make_component()
        result = comp.render({}, data=None)
        assert result["color_palette"] == "wong"

    @patch("src.web.components.plotting.settings.colors_settings.st")
    def test_selecting_viridis_sets_palette_key(self, mock_st: MagicMock) -> None:
        mock_st.selectbox.return_value = "viridis_8"
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#000000"
        comp = self._make_component()
        with patch("src.web.components.plotting.settings.widget_factory.st", mock_st):
            result = comp.render({}, data=None)
        assert result["color_palette"] == "viridis_8"

    @patch("src.web.components.plotting.settings.colors_settings.st")
    def test_swatch_html_is_rendered(self, mock_st: MagicMock) -> None:
        """Verify markdown is called with swatch HTML."""
        mock_st.selectbox.return_value = "wong"
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#000000"
        comp = self._make_component()
        comp.render({}, data=None)
        # Find the markdown call with color swatches
        html_calls = [
            c for c in mock_st.markdown.call_args_list if c.kwargs.get("unsafe_allow_html")
        ]
        assert len(html_calls) >= 1
        html = html_calls[0].args[0]
        assert "background:#000000" in html or "background: #000000" in html


class TestCssRgbToHex:
    """Verify CSS rgb() → hex conversion for Matplotlib compatibility."""

    def test_basic_rgb_conversion(self) -> None:
        from src.web.rendering.matplotlib_connector import _css_rgb_to_hex

        assert _css_rgb_to_hex("rgb(102,194,165)") == "#66c2a5"

    def test_rgb_with_spaces(self) -> None:
        from src.web.rendering.matplotlib_connector import _css_rgb_to_hex

        assert _css_rgb_to_hex("rgb( 255 , 0 , 128 )") == "#ff0080"

    def test_hex_passthrough(self) -> None:
        from src.web.rendering.matplotlib_connector import _css_rgb_to_hex

        assert _css_rgb_to_hex("#E69F00") == "#E69F00"

    def test_named_color_passthrough(self) -> None:
        from src.web.rendering.matplotlib_connector import _css_rgb_to_hex

        assert _css_rgb_to_hex("red") == "red"
