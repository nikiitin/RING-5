"""Tests for color utilities."""

from typing import cast

from src.web.pages.ui.plotting.styles.colors import to_hex


class TestToHex:
    """Tests for to_hex function."""

    def test_hex_color_unchanged(self) -> None:
        """Test that hex colors are returned unchanged."""
        assert to_hex("#FF0000") == "#FF0000"
        assert to_hex("#00FF00") == "#00FF00"

    def test_short_hex(self) -> None:
        """Test short hex format."""
        assert to_hex("#F00") == "#F00"

    def test_hex_with_alpha_stripped(self) -> None:
        """Test hex with alpha gets stripped."""
        result = to_hex("#FF0000FF")
        assert result == "#FF0000"

    def test_rgb_to_hex(self) -> None:
        """Test rgb() string conversion."""
        result = to_hex("rgb(255, 0, 0)")
        assert result.lower() == "#ff0000"

    def test_rgb_no_spaces(self) -> None:
        """Test rgb without spaces."""
        result = to_hex("rgb(0,255,0)")
        assert result.lower() == "#00ff00"

    def test_non_string_returns_black(self) -> None:
        """Test non-string returns black."""
        assert to_hex(cast(str, None)) == "#000000"
        assert to_hex(cast(str, 123)) == "#000000"

    def test_named_color_fallback(self) -> None:
        """Test that named colors get handled."""
        # This may convert or fallback to black
        result = to_hex("red")
        assert result.startswith("#")

    def test_invalid_format_returns_black(self) -> None:
        """Test invalid format returns black."""
        result = to_hex("not-a-color")
        assert result == "#000000"
