"""Ordering helpers shared by plot trace builders."""

from collections.abc import Iterable
from typing import Any

import pandas as pd


def observed_order(series: pd.Series, configured: object = None) -> list[Any]:
    """Keep distinct source values in encounter order after preferred labels.

    Preferred labels select observed values by their string representation.
    Unlisted values retain their source order and scalar types, including missing
    categories. An absent or empty preference preserves the encounter order.
    """
    available = list(series.drop_duplicates())
    if not isinstance(configured, list):
        return available
    by_label = {str(value): value for value in available}
    labels = [str(label) for label in configured]
    ordered = [by_label[label] for label in labels if label in by_label]
    return ordered + [value for value in available if str(value) not in labels]


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
