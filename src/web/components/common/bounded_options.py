"""Bound option lists before sending untrusted data to Streamlit widgets."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from src.core.common.security_limits import (
    MAX_FILTER_OPTIONS,
    MAX_FILTER_ROWS,
    MAX_FILTER_VALUE_LENGTH,
)


def bounded_unique_strings(values: Iterable[object]) -> tuple[list[str], bool]:
    """Collect a sorted, bounded set of short display values.

    Returns the options and whether rows, cardinality, or value length caused
    truncation. Iteration stops once the row or unique-value budget is reached.
    """
    unique: set[str] = set()
    truncated = False
    for row_index, value in enumerate(values):
        if row_index >= MAX_FILTER_ROWS:
            truncated = True
            break
        text = str(value)
        if len(text) > MAX_FILTER_VALUE_LENGTH:
            truncated = True
            continue
        if text in unique:
            continue
        if len(unique) >= MAX_FILTER_OPTIONS:
            truncated = True
            break
        unique.add(text)
    return sorted(unique), truncated


def stable_widget_suffix(index: int, value: object) -> str:
    """Return a collision-resistant, index-qualified Streamlit key suffix."""
    digest = hashlib.sha256(str(value).encode()).hexdigest()
    return f"{index}_{digest}"
