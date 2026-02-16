"""
Conftest for UI AppTest tests.

Monkey-patches a bug in Streamlit 1.53.1's testing framework where
ButtonGroup.indices iterates over string characters in single-selection mode
instead of treating the value as a single item.
"""

from __future__ import annotations

from typing import Any, Sequence

from streamlit.testing.v1.element_tree import ButtonGroup


def _patched_indices(self: Any) -> Sequence[int]:
    """Fix: wrap single string value in list before iterating."""
    vals = self.value
    if isinstance(vals, str):
        vals = [vals]
    return [self.options.index(self.format_func(v)) for v in vals]


# Apply monkey-patch at import time
ButtonGroup.indices = property(_patched_indices)  # type: ignore[assignment]
