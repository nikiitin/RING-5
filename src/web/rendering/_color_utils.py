"""Shared CSS color normalization without native figure construction."""

import math
import re

_CSS_RGB_RE = re.compile(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", re.IGNORECASE)
_CSS_RGBA_RE = re.compile(
    r"^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9]*\.?[0-9]+)\s*\)$", re.IGNORECASE
)


def css_rgb_to_hex(color: str) -> str:
    """Convert a CSS ``rgb(r,g,b)`` string to ``#rrggbb`` hex.

    If *color* is already a hex string or any other format, return it
    unchanged so that Matplotlib's own validator handles it.
    """
    m = _CSS_RGB_RE.match(color.strip())
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"#{r:02x}{g:02x}{b:02x}"
    return color


def css_color_to_matplotlib(color: str) -> str | tuple[float, float, float, float]:
    """Normalize CSS RGBA/RGB while retaining other native color formats."""
    m = _CSS_RGBA_RE.match(color.strip())
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return (r / 255.0, g / 255.0, b / 255.0, float(m.group(4)))
    return css_rgb_to_hex(color)


def color_with_alpha(color: str, alpha: float) -> str:
    """Apply explicit background opacity, replacing any embedded color opacity.

    Args:
        color: A named, hexadecimal, RGB or RGBA color.
        alpha: Finite opacity from zero through one.

    Returns:
        A CSS RGBA color with the requested opacity.

    Raises:
        ValueError: The color or opacity is invalid.
    """
    from matplotlib.colors import to_rgba

    if not math.isfinite(alpha) or not 0.0 <= alpha <= 1.0:
        raise ValueError("Background alpha must be finite and from zero through one.")
    red, green, blue, _ = to_rgba(css_color_to_matplotlib(color))
    channels = [round(value * 255) for value in (red, green, blue)]
    return f"rgba({channels[0]},{channels[1]},{channels[2]},{alpha})"
