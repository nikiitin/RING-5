"""Scalar stat type for single numeric values."""

import math
from typing import Any, override

from src.parsing.gem5.types.base import StatType, register_type


@register_type("scalar")
class Scalar(StatType):
    """
    Represents a single scalar value (e.g., simTicks, IPC).

    Content is stored as a list for repeat support.
    Values must be convertible to int or float.

    Validation:
    - All values MUST be numeric (int or float)
    - Content length must match repeat count after balancing
    - Raises TypeError on non-numeric input
    """

    # [impl->req~ring5.ingestion.scalar~1]

    required_params = []

    @override
    def _validate_content(self, value: Any) -> None:
        """Ensure value can be converted to numeric (int or float)."""
        try:
            int(value)
            return  # Valid as int
        except (TypeError, ValueError):
            pass

        try:
            float(value)
            return  # Valid as float
        except (TypeError, ValueError) as e:
            raise TypeError(
                f"SCALAR: Variable non-convertible to float or int. "
                f"Value: {value}, Type: {type(value).__name__}"
            ) from e

    @override
    def _set_content(self, value: Any) -> None:
        """Convert to numeric and append to content list (preserve precision)."""
        # float() first so fractional values are NOT truncated; fall back to
        # int() only for inputs that float() rejects (same acceptance set).
        try:
            numeric_value: float = float(value)
        except (TypeError, ValueError):
            numeric_value = float(int(value))
        self._content.append(numeric_value)

    @override
    def reduce_duplicates(self) -> None:
        """Reduce content via arithmetic mean (sum / repeat)."""
        object.__setattr__(self, "_reduced", True)

        if not self._content:
            object.__setattr__(self, "_reduced_content", math.nan)
            return

        # Sum and divide using float to preserve decimal precision
        total = 0.0
        for i in range(self._repeat):
            total += float(self._content[i])
        object.__setattr__(self, "_reduced_content", total / self._repeat)
