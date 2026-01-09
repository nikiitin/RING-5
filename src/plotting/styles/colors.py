"""
Shared color utilities for consistent palette loading.
"""

from typing import List

import plotly.colors as pc


def get_palette_colors(palette_name: str) -> List[str]:
    """
    Get a list of colors for a given palette name.
    Attempts to match case-insensitively against Plotly's qualitative palettes.
    Defaults to Plotly's default qualitative palette if not found.
    """
    # Default fallback
    default_palette = pc.qualitative.Plotly

    if not palette_name:
        return default_palette

    # 1. Try direct attribute access (exact match)
    if hasattr(pc.qualitative, palette_name):
        return getattr(pc.qualitative, palette_name)

    # 2. Try case-insensitive match
    for p_attr in dir(pc.qualitative):
        if p_attr.lower() == palette_name.lower():
            return getattr(pc.qualitative, p_attr)

    return default_palette


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
        # Handle alpha hex (strip alpha for streamlit picker)?
        return color_str[:7]

    # Handle rgb(r, g, b)
    if color_str.startswith("rgb"):
        try:
            # Extract numbers
            import re

            nums = re.findall(r"\d+", color_str)
            if len(nums) >= 3:
                r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
                return "#{:02x}{:02x}{:02x}".format(r, g, b)
        except Exception:
            import logging

            logging.warning(f"Could not parse rgb color: {color_str}")

    # Handle named colors via Plotly/Matplotlib?
    # For now, if we can't convert, return black or input.
    # Streamlit dies on bad input, so fallback to black is safer for UI.
    # Last resort fallback for Streamlit
    import logging

    try:
        return pc.convert_colors_to_same_type(color_str, "hex")[0][0]
    except Exception:
        logging.warning(f"Could not convert color {color_str} to hex. Fallback to black.")

    # Last resort fallback for Streamlit
    return "#000000"
