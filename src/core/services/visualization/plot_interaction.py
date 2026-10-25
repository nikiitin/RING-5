"""Pure item ordering for plot categories and reorderable controls."""


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
