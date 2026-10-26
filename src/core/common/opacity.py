"""Exact finite opacity admission shared by typed models and editable values."""

import math
from typing import cast


def require_opacity(value: object, *, field: str = "opacity") -> float:
    """Return a supported real scalar from zero through one.

    Args:
        value: A native integer/float or immutable NumPy real scalar.
        field: Field name included in the validation error.

    Returns:
        Finite native opacity without interpreting text or conversion hooks.

    Raises:
        ValueError: The value is boolean, nonnumeric, nonfinite or outside [0, 1].
    """
    numeric = type(value) in (int, float)
    if not numeric:
        import numpy as np

        if isinstance(value, np.generic):
            dtype = np.dtype(type(value))
            numeric = dtype.type is type(value) and dtype.kind in "iuf"
    if not numeric:
        raise ValueError(f"{field} must be a finite real number from zero through one.")
    scalar = cast(int | float, value)
    if scalar < 0 or scalar > 1:
        raise ValueError(f"{field} must be a finite real number from zero through one.")
    try:
        opacity = float(scalar)
    except OverflowError as exc:
        raise ValueError(f"{field} must be a finite real number from zero through one.") from exc
    if not math.isfinite(opacity) or not 0.0 <= opacity <= 1.0:
        raise ValueError(f"{field} must be a finite real number from zero through one.")
    return opacity
