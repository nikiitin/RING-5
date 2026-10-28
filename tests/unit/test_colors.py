"""Tests for color utilities."""

from typing import cast

import pytest

from src.web.rendering._color_utils import css_color_to_matplotlib, picker_hex_color


class TestPickerHexColor:
    """A derived RGB preview never invents a repair color."""

    def test_hex_color_unchanged(self) -> None:
        """Long hexadecimal colors keep their RGB measurements."""
        assert picker_hex_color("#FF0000") == "#ff0000"
        assert picker_hex_color("#00FF00") == "#00ff00"

    def test_short_hex(self) -> None:
        """Test short hex format."""
        assert picker_hex_color("#F00") == "#ff0000"

    def test_hex_with_alpha_stripped(self) -> None:
        """Test hex with alpha gets stripped."""
        result = picker_hex_color("#FF0000FF")
        assert result == "#ff0000"

    def test_rgb_picker_hex_color(self) -> None:
        """Test rgb() string conversion."""
        result = picker_hex_color("rgb(255, 0, 0)")
        assert result.lower() == "#ff0000"

    def test_rgb_no_spaces(self) -> None:
        """Test rgb without spaces."""
        result = picker_hex_color("rgb(0,255,0)")
        assert result.lower() == "#00ff00"

    def test_non_string_rejects_without_replacement(self) -> None:
        for value in (None, 123):
            with pytest.raises(ValueError, match="CSS text"):
                picker_hex_color(cast(str, value))

    def test_named_color_projects_to_rgb(self) -> None:
        assert picker_hex_color("red") == "#ff0000"

    def test_invalid_format_rejects_without_replacement(self) -> None:
        with pytest.raises(ValueError):
            picker_hex_color("not-a-color")


@pytest.mark.parametrize("color", ["none", "C0", (0.1, 0.2, 0.3), (0.1, 0.2, 0.3, 0.4)])
def test_native_static_color_values_retain_their_native_contract(
    color: str | tuple[float, float, float] | tuple[float, float, float, float],
) -> None:
    assert css_color_to_matplotlib(color) is color
