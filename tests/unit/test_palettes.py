"""Unit tests for the unified palette registry."""

from __future__ import annotations

import re

from src.core.models.visualization.palettes import PALETTE_REGISTRY
from src.core.services.visualization.palette_service import (
    get_palette_names,
    is_colorblind_safe,
    resolve_palette,
)

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class TestPaletteRegistry:
    """Tests for PALETTE_REGISTRY contents."""

    def test_registry_has_colorblind_palettes(self) -> None:
        for name in ("wong", "okabe_ito", "tol_bright", "viridis_8", "seaborn_cb"):
            assert name in PALETTE_REGISTRY, f"Missing colorblind palette: {name}"

    def test_registry_has_plotly_qualitative(self) -> None:
        expected = [
            "Plotly",
            "D3",
            "G10",
            "T10",
            "Alphabet",
            "Dark24",
            "Light24",
            "Set1",
            "Set2",
            "Set3",
            "Pastel",
            "Safe",
            "Vivid",
            "Bold",
        ]
        for name in expected:
            assert name in PALETTE_REGISTRY, f"Missing Plotly palette: {name}"

    def test_all_colors_are_hex(self) -> None:
        for name, colors in PALETTE_REGISTRY.items():
            assert len(colors) > 0, f"Palette {name} is empty"
            for c in colors:
                assert _HEX_RE.match(c), f"Non-hex color '{c}' in palette {name}"

    def test_registry_total_count(self) -> None:
        assert len(PALETTE_REGISTRY) == 19  # 5 colorblind + 14 plotly


class TestResolvePalette:
    """Tests for resolve_palette()."""

    def test_resolve_known_name(self) -> None:
        colors = resolve_palette("wong")
        assert len(colors) == 8
        assert colors[0] == "#000000"

    def test_resolve_plotly_name(self) -> None:
        colors = resolve_palette("D3")
        assert len(colors) == 10
        assert colors[0] == "#1F77B4"

    def test_resolve_case_insensitive(self) -> None:
        colors_lower = resolve_palette("d3")
        colors_upper = resolve_palette("D3")
        assert colors_lower == colors_upper

    def test_resolve_unknown_falls_back_to_wong(self) -> None:
        colors = resolve_palette("nonexistent_palette")
        wong = resolve_palette("wong")
        assert colors == wong

    def test_resolve_none_falls_back_to_wong(self) -> None:
        colors = resolve_palette(None)
        wong = resolve_palette("wong")
        assert colors == wong

    def test_resolve_empty_string_falls_back_to_wong(self) -> None:
        colors = resolve_palette("")
        wong = resolve_palette("wong")
        assert colors == wong

    def test_resolve_returns_copy(self) -> None:
        """Mutating the returned list must not affect the registry."""
        colors = resolve_palette("wong")
        original = resolve_palette("wong")
        colors.pop()
        assert len(resolve_palette("wong")) == len(original)

    def test_resolve_viridis_8_returns_correct(self) -> None:
        """viridis_8 previously fell back to Wong due to disconnected registry."""
        colors = resolve_palette("viridis_8")
        assert colors[0] == "#440154"  # not #000000 (Wong)
        assert len(colors) == 8


class TestGetPaletteNames:
    """Tests for get_palette_names()."""

    def test_returns_all_names(self) -> None:
        names = get_palette_names()
        assert len(names) == len(PALETTE_REGISTRY)

    def test_colorblind_safe_first(self) -> None:
        names = get_palette_names()
        cb_names = {"wong", "okabe_ito", "tol_bright", "viridis_8", "seaborn_cb"}
        first_five = set(names[:5])
        assert first_five == cb_names

    def test_no_duplicates(self) -> None:
        names = get_palette_names()
        assert len(names) == len(set(names))


class TestIsColorblindSafe:
    """Tests for is_colorblind_safe()."""

    def test_wong_is_colorblind_safe(self) -> None:
        assert is_colorblind_safe("wong") is True

    def test_plotly_is_not_colorblind_safe(self) -> None:
        assert is_colorblind_safe("Plotly") is False

    def test_unknown_is_not_colorblind_safe(self) -> None:
        assert is_colorblind_safe("foo") is False
