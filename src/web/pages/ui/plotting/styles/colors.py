"""
Shared color utilities for consistent palette loading.
"""

import logging
import re
from typing import List

from src.core.visualization.palettes import resolve_palette


def get_palette_colors(palette_name: str) -> List[str]:
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
                return "#{:02x}{:02x}{:02x}".format(r, g, b)
        except Exception:
            logging.warning(f"Could not parse rgb color: {color_str}")

    # Handle named colors via Plotly utility
    # Streamlit dies on bad input, so fallback to black is safer for UI.
    try:
        import plotly.colors as pc

        result: List[tuple[str, ...]] = pc.convert_colors_to_same_type(color_str, "hex")
        return str(result[0][0])
    except Exception:
        logging.warning(f"Could not convert color {color_str} to hex. Fallback to black.")

    # Last resort fallback for Streamlit
    return "#000000"
