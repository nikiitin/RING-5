"""Ordering helpers shared by plot trace builders."""

from collections.abc import Iterable
from typing import Any


def order_with_overrides(present: Iterable[Any], explicit_order: list[Any] | None) -> list[str]:
    """Place explicit values first, then append remaining present values sorted.

    Args:
        present: Category-like values available in the current data.
        explicit_order: Preferred leading order, or ``None`` for lexical order.

    Returns:
        Present values ordered without introducing absent categories.
    """
    present_list = list(present)
    if not explicit_order:
        return sorted(present_list)
    ordered = [str(value) for value in explicit_order if str(value) in present_list]
    ordered.extend(value for value in sorted(present_list) if value not in ordered)
    return ordered
