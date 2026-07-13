"""Unit tests for resolve_palette accepting an explicit hex list (not just a name)."""

from __future__ import annotations

from src.core.services.visualization.palette_service import resolve_palette


class TestResolvePaletteCustomList:
    """resolve_palette now accepts a sequence of colors, returned as a clean copy."""

    def test_list_passthrough(self) -> None:
        colors = ["#66c2a5", "#fc8d62", "#8da0cb"]
        assert resolve_palette(colors) == colors

    def test_tuple_passthrough(self) -> None:
        assert resolve_palette(("#111111", "#222222")) == ["#111111", "#222222"]

    def test_whitespace_stripped(self) -> None:
        assert resolve_palette([" #abcdef ", "#012345"]) == ["#abcdef", "#012345"]

    def test_non_string_entries_filtered(self) -> None:
        mixed: list[object] = ["#abcdef", None, 5, "#012345"]
        assert resolve_palette(mixed) == ["#abcdef", "#012345"]

    def test_empty_list_falls_back_to_wong(self) -> None:
        assert resolve_palette([]) == resolve_palette("wong")

    def test_returns_independent_copy(self) -> None:
        src = ["#66c2a5", "#fc8d62"]
        out = resolve_palette(src)
        out.append("#000000")
        assert src == ["#66c2a5", "#fc8d62"]  # original untouched

    def test_name_still_works(self) -> None:
        assert resolve_palette("Set2")[0] == "#66c2a5"
