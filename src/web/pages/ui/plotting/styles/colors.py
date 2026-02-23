"""
Shared color utilities for consistent palette loading.
"""

import logging
import re

from src.core.models.visualization.palettes import resolve_palette


def get_palette_colors(palette_name: str) -> list[str]:
    """
    Get a list of colors for a given palette name.

    Delegates to the unified ``resolve_palette()`` in the core
    visualization layer.  Returns hex color strings.
    """
    return resolve_palette(palette_name)


def to_hex(color_str: str) -> str:
    """
    Ensure the color string is a hex code.
    Converts 'rgb(r, g, b)' and named colors to hex.
    Returns None or raises if invalid (but we try to return input if fallback).
    """
    if not isinstance(color_str, str):
        return "#000000"

    color_str = color_str.strip()

    # Already hex
    if color_str.startswith("#"):
        if len(color_str) in (4, 7):
            return color_str
        # Strip alpha for streamlit picker compatibility
        return color_str[:7]

    # Handle rgb(r, g, b)
    if color_str.startswith("rgb"):
        try:
            # Extract numbers
            nums = re.findall(r"\d+", color_str)
            if len(nums) >= 3:
                r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
                return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            logging.warning(f"Could not parse rgb color: {color_str}")

    # Handle named colors via Plotly utility
    # Streamlit dies on bad input, so fallback to black is safer for UI.
    try:
        import plotly.colors as pc

        converted = pc.convert_colors_to_same_type(color_str, "hex")  # type: ignore[attr-defined]
        color_list: list[str] = [str(c) for c in converted[0]]
        if color_list:
            return str(color_list[0])
    except Exception:
        logging.warning(f"Could not convert color {color_str} to hex. Fallback to black.")

    # Last resort fallback for Streamlit
    return "#000000"
