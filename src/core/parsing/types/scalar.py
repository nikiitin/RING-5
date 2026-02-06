"""Scalar stat type for single numeric values."""

from typing import Any

from src.core.parsing.types.base import StatType, register_type


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

    required_params = []

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

    def _set_content(self, value: Any) -> None:
        """Convert to numeric and append to content list."""
        try:
            numeric_value: float = float(int(value))
        except (TypeError, ValueError):
            numeric_value = float(value)
        self._content.append(numeric_value)

    def reduce_duplicates(self) -> None:
        """Reduce content via arithmetic mean (sum / repeat)."""
        object.__setattr__(self, "_reduced", True)

        if not self._content:
            object.__setattr__(self, "_reduced_content", "NA")
            return

        # Sum and divide - matching original implementation
        total = 0
        for i in range(self._repeat):
            total += int(self._content[i])
        object.__setattr__(self, "_reduced_content", total / self._repeat)
