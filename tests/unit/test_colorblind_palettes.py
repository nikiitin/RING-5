"""Tests for colorblind-safe palette defaults and selector (Step 35)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.palettes import PALETTE_REGISTRY


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
    """Verify palette selector widget in _section_colors."""

    def _make_plot(self) -> MagicMock:
        from src.web.pages.ui.plotting.base_plot import BasePlot

        plot = MagicMock()
        plot.plot_id = 1
        plot.style_manager = MagicMock()
        plot.style_manager.ui_manager._render_series_section.return_value = {}
        plot.style_manager.ui_manager._render_backgrounds_section.return_value = {}
        plot._section_colors = BasePlot._section_colors.__get__(plot, type(plot))
        return plot

    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_selecting_wong_sets_palette_key(self, mock_st: MagicMock) -> None:
        mock_st.selectbox.return_value = "wong"
        plot = self._make_plot()
        result = plot._section_colors({}, None)
        assert result["color_palette"] == "wong"

    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_selecting_viridis_sets_palette_key(self, mock_st: MagicMock) -> None:
        mock_st.selectbox.return_value = "viridis_8"
        plot = self._make_plot()
        result = plot._section_colors({}, None)
        assert result["color_palette"] == "viridis_8"

    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_swatch_html_is_rendered(self, mock_st: MagicMock) -> None:
        """Verify markdown is called with swatch HTML."""
        mock_st.selectbox.return_value = "wong"
        plot = self._make_plot()
        plot._section_colors({}, None)
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
        from src.web.rendering.matplotlib_connector import (
            _css_rgb_to_hex,
        )

        assert _css_rgb_to_hex("rgb(102,194,165)") == "#66c2a5"

    def test_rgb_with_spaces(self) -> None:
        from src.web.rendering.matplotlib_connector import (
            _css_rgb_to_hex,
        )

        assert _css_rgb_to_hex("rgb( 255 , 0 , 128 )") == "#ff0080"

    def test_hex_passthrough(self) -> None:
        from src.web.rendering.matplotlib_connector import (
            _css_rgb_to_hex,
        )

        assert _css_rgb_to_hex("#E69F00") == "#E69F00"

    def test_named_color_passthrough(self) -> None:
        from src.web.rendering.matplotlib_connector import (
            _css_rgb_to_hex,
        )

        assert _css_rgb_to_hex("red") == "red"
