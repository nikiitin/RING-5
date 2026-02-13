"""
Plot Interaction Service for RING-5.

Pure business logic for handling interactive plot state changes.
Extracts computation from UI layer to maintain architectural compliance.

Handles:
- Relayout event processing (zoom, pan, legend drag)
- Reorderable list synchronization
- Value conversion utilities

All functions are pure (no UI dependencies, no side effects beyond returned data).
"""

import math
from typing import Any, Dict, List, Optional, Tuple, Union


def try_float(value: str) -> Union[float, str]:
    """Try to convert a string value to float, return original string on failure.

    Useful for shape coordinate values that may be numeric or categorical.

    Args:
        value: String value to attempt float conversion on.

    Returns:
        Float value if conversion succeeds, original string otherwise.

    Examples:
        >>> try_float("3.14")
        3.14
        >>> try_float("category_a")
        'category_a'
        >>> try_float("")
        ''
    """
    try:
        return float(value)
    except ValueError:
        return value


def try_float_edit(value: Any) -> Union[float, str]:
    """Try to convert any value to float, fallback to string.

    Similar to try_float but handles non-string types (int, None, etc.).

    Args:
        value: Value to attempt float conversion on.

    Returns:
        Float value if conversion succeeds, string representation otherwise.

    Examples:
        >>> try_float_edit(42)
        42.0
        >>> try_float_edit("hello")
        'hello'
        >>> try_float_edit(None)
        'None'
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return str(value)


def _is_close(a: Any, b: Any) -> bool:
    """Check if two values are approximately equal.

    Uses math.isclose for numeric comparison, falls back to equality.

    Args:
        a: First value
        b: Second value

    Returns:
        True if values are close/equal.
    """
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-9)
    except (ValueError, TypeError):
        return bool(a == b)


def update_config_from_relayout(
    config: Dict[str, Any], relayout_data: Dict[str, Any]
) -> Tuple[Dict[str, Any], bool]:
    """
    Update plot config from Plotly client-side relayout data (zoom/pan, legend drag).

    This is a pure function that computes a new config dict from relayout events.
    It handles:
    - Zoom/pan: xaxis.range, yaxis.range → range_x, range_y
    - Reset zoom: xaxis.autorange → range_x = None
    - Legend drag: legend.x, legend.y → legend_x, legend_y + anchors
    - Legend title edit: legend.title.text → legend_title

    Args:
        config: Current plot configuration dictionary.
        relayout_data: Dictionary of relayout events from Plotly.

    Returns:
        Tuple of (updated_config, changed).
        updated_config is a new dict (config is not mutated).
        changed is True if any config value was modified.

    Examples:
        >>> config = {"range_x": None}
        >>> relayout = {"xaxis.range[0]": 0, "xaxis.range[1]": 10}
        >>> new_config, changed = update_config_from_relayout(config, relayout)
        >>> changed
        True
        >>> new_config["range_x"]
        [0, 10]
    """
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
            if all(_is_close(c, v) for c, v in zip(current, val)):
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
        new_range: List[Any] = [
            relayout_data["xaxis.range[0]"],
            relayout_data["xaxis.range[1]"],
        ]
        update_if_new("range_x", new_range)
    elif "xaxis.range" in relayout_data:
        update_if_new("range_x", relayout_data["xaxis.range"])

    # y-axis
    if "yaxis.range[0]" in relayout_data and "yaxis.range[1]" in relayout_data:
        new_range_y: List[Any] = [
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

        parts: List[str] = key.split(".")
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


def resolve_item_order(
    items: List[Any],
    default_order: Optional[List[Any]] = None,
    current_order: Optional[List[Any]] = None,
) -> List[Any]:
    """
    Resolve the display order for a list of items.

    Handles three scenarios:
    1. No existing order: use default_order if provided, else natural order
    2. Items changed (added/removed): preserve existing order for common items,
       append new items at end
    3. Items unchanged: return current order as-is

    Args:
        items: Current set of items to order.
        default_order: Optional default ordering preference.
        current_order: Optional current ordering from previous state.

    Returns:
        Ordered list of items.

    Examples:
        >>> resolve_item_order(["a", "b", "c"])
        ['a', 'b', 'c']
        >>> resolve_item_order(["a", "b", "c"], default_order=["c", "b", "a"])
        ['c', 'b', 'a']
        >>> resolve_item_order(["a", "b", "c", "d"], current_order=["c", "b", "a"])
        ['c', 'b', 'a', 'd']
        >>> resolve_item_order(["a", "c"], current_order=["c", "b", "a"])
        ['c', 'a']
    """
    if current_order is not None:
        # Sync: keep existing items in their order, append new ones
        if set(current_order) == set(items):
            return list(current_order)
        # Items changed: filter out removed, append new
        ordered: List[Any] = [x for x in current_order if x in items]
        ordered.extend([x for x in items if x not in current_order])
        return ordered

    if default_order:
        # Use default order, filtered to current items, with new items appended
        valid_defaults: List[Any] = [x for x in default_order if x in items]
        missing_items: List[Any] = [x for x in items if x not in valid_defaults]
        return valid_defaults + missing_items

    return list(items)
