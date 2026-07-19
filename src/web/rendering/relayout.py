"""Plotly relayout decoding — presentation-layer event handling.

Translates a Plotly client-side ``relayout`` event payload into updates on the
engine-agnostic plot config (zoom/pan ranges, legend drag, legend-title edit).

This understands one rendering engine's wire format (Plotly's ``xaxis.range[0]``,
``legend.x``, ``legend.title.text`` …), so it lives in the web rendering layer,
not in ``core`` — core stays engine-agnostic.
"""

from __future__ import annotations

import math
from typing import Any


def _is_close(a: Any, b: Any) -> bool:
    """Check if two values are approximately equal (numeric isclose, else ==)."""
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-9)
    except (ValueError, TypeError):
        return bool(a == b)


def update_config_from_relayout(
    config: dict[str, Any], relayout_data: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Update plot config from a Plotly client-side relayout payload.

    Handles:
    - Zoom/pan: xaxis.range, yaxis.range -> range_x, range_y
    - Reset zoom: xaxis.autorange -> range_x = None
    - Legend drag: legend.x, legend.y -> legend_x, legend_y + anchors
    - Legend title edit: legend.title.text -> legend_title

    Returns ``(updated_config, changed)``; the input config is not mutated.
    """
    # [impl->req~ring5.figure.interactive-editing~1]
    if not relayout_data:
        return config, False

    updated = config.copy()
    changed: bool = False

    def update_if_new(key: str, val: Any) -> bool:
        """Update config key if value is meaningfully different."""
        nonlocal changed
        current: Any = updated.get(key)

        # Check for float equality if both are lists of numbers (ranges)
        if isinstance(current, list) and isinstance(val, list) and len(current) == len(val):
            if all(_is_close(c, v) for c, v in zip(current, val, strict=True)):
                return False

        # Simple equality check for non-lists or different lengths
        if current != val:
            if _is_close(current, val):
                return False
            updated[key] = val
            changed = True
            return True
        return False

    # 1. Custom Range (Zoom)
    # x-axis
    if "xaxis.range[0]" in relayout_data and "xaxis.range[1]" in relayout_data:
        new_range: list[float] = [
            relayout_data["xaxis.range[0]"],
            relayout_data["xaxis.range[1]"],
        ]
        update_if_new("range_x", new_range)
    elif "xaxis.range" in relayout_data:
        update_if_new("range_x", relayout_data["xaxis.range"])

    # y-axis
    if "yaxis.range[0]" in relayout_data and "yaxis.range[1]" in relayout_data:
        new_range_y: list[float] = [
            relayout_data["yaxis.range[0]"],
            relayout_data["yaxis.range[1]"],
        ]
        update_if_new("range_y", new_range_y)
    elif "yaxis.range" in relayout_data:
        update_if_new("range_y", relayout_data["yaxis.range"])

    # Autosize / Reset Zoom
    if "xaxis.autorange" in relayout_data and relayout_data["xaxis.autorange"]:
        if updated.get("range_x") is not None:
            updated["range_x"] = None
            changed = True

    if "yaxis.autorange" in relayout_data and relayout_data["yaxis.autorange"]:
        if updated.get("range_y") is not None:
            updated["range_y"] = None
            changed = True

    # 2. Legend Position (Drag)
    for key, val in relayout_data.items():
        if not key.startswith("legend"):
            continue

        parts: list[str] = key.split(".")
        if len(parts) != 2:
            continue

        legend_name: str = parts[0]  # "legend" or "legend2", etc.
        prop: str = parts[1]  # "x", "y", "xanchor", etc.

        # Build config key: legend.x -> legend_x, legend2.x -> legend2_x
        config_key: str
        if legend_name == "legend":
            config_key = f"legend_{prop}"
        else:
            config_key = f"{legend_name}_{prop}"

        if prop in ("x", "y"):
            if update_if_new(config_key, val):
                # Also set anchor when position changes
                if prop == "x":
                    anchor_key = config_key.replace("_x", "_xanchor")
                    updated[anchor_key] = "left"
                elif prop == "y":
                    anchor_key = config_key.replace("_y", "_yanchor")
                    updated[anchor_key] = "top"
        elif prop in ("xanchor", "yanchor"):
            update_if_new(config_key, val)

    # 3. Legend Title (Edit)
    if "legend.title.text" in relayout_data:
        update_if_new("legend_title", relayout_data["legend.title.text"])

    return updated, changed
