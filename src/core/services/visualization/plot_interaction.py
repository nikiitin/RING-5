"""Plot interaction service — value conversion and item ordering.

Pure, engine-agnostic business logic for interactive plot state.

Handles:
    - Reorderable list / item-order synchronization
    - Value conversion utilities

Engine-specific event decoding (e.g. Plotly relayout payloads) lives in the
web rendering layer (``src.web.rendering.relayout``), not here.

All functions are pure (no UI dependencies, no side effects beyond returned data).
"""

from typing import Any


def try_float(value: str) -> float | str:
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


def try_float_edit(value: Any) -> float | str:
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


def resolve_item_order(
    items: list[str],
    default_order: list[str] | None = None,
    current_order: list[str] | None = None,
) -> list[str]:
    """Resolve the display order for a list of items.

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
        ordered: list[str] = [x for x in current_order if x in items]
        ordered.extend([x for x in items if x not in current_order])
        return ordered

    if default_order:
        # Use default order, filtered to current items, with new items appended
        valid_defaults: list[str] = [x for x in default_order if x in items]
        missing_items: list[str] = [x for x in items if x not in valid_defaults]
        return valid_defaults + missing_items

    return list(items)
