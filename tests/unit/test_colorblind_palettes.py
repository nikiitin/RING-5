"""Tests for colorblind-safe palette defaults and selector (Step 35)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.core.visualization.figure_spec import FigureSpec
from src.web.pages.ui.plotting.base_plot import BasePlot


class TestDefaultPalette:
    """Verify Wong palette is the default."""

    def test_figure_spec_default_is_wong(self) -> None:
        spec = FigureSpec()
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
        assert "wong" in BasePlot.BUILTIN_PALETTES
        assert "viridis_8" in BasePlot.BUILTIN_PALETTES
        assert "seaborn_cb" in BasePlot.BUILTIN_PALETTES
        assert "tol_bright" in BasePlot.BUILTIN_PALETTES
        assert "okabe_ito" in BasePlot.BUILTIN_PALETTES

    def test_all_palettes_have_at_least_7_colors(self) -> None:
        for name, colors in BasePlot.BUILTIN_PALETTES.items():
            assert len(colors) >= 7, f"Palette {name} has only {len(colors)} colors"

    def test_all_hex_colors_valid(self) -> None:
        import re

        pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for name, colors in BasePlot.BUILTIN_PALETTES.items():
            for c in colors:
                assert pattern.match(c), f"Invalid hex in {name}: {c}"


class TestPaletteSelector:
    """Verify palette selector widget in _section_colors."""

    def _make_plot(self) -> MagicMock:
        from src.web.pages.ui.plotting.base_plot import BasePlot

        plot = MagicMock()
        plot.plot_id = 1
        plot.BUILTIN_PALETTES = BasePlot.BUILTIN_PALETTES
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
