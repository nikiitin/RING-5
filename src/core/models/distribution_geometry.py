"""Explicit native Distribution geometry, independent of printed entry labels."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import cast

MAX_DISTRIBUTION_BUCKETS = 100_000


def _native_double(value: object, field_name: str) -> float:
    """Own a finite native-double value without coercing text or truncating integers."""
    if type(value) not in (int, float):
        raise TypeError(f"Distribution {field_name} must be an actual finite number.")
    try:
        owned = float(cast(int | float, value))
    except OverflowError as exc:
        raise ValueError(f"Distribution {field_name} is outside the native-double range.") from exc
    if not math.isfinite(owned):
        raise ValueError(f"Distribution {field_name} must be finite.")
    if type(value) is int and owned != value:
        raise ValueError(f"Distribution {field_name} cannot be represented exactly as a double.")
    return owned


@dataclass(frozen=True, slots=True)
class DistributionGeometry:
    """Declared gem5 grid origin, inclusive tracked maximum and bucket width.

    Native storage allocates ``ceil((maximum - minimum + 1) / bucket_size)``
    cells. This is not a continuous partition inferred from printed ranges;
    narrow buckets can allocate cells above the inclusive tracked maximum.

    Attributes:
        minimum: Finite origin of the native grid.
        maximum: Finite inclusive tracked limit, at or above the origin.
        bucket_size: Finite positive native bucket width.
        bucket_count: Bounded native storage cell count, computed before allocation.

    Raises:
        TypeError: A field is not an actual int or float.
        ValueError: Geometry is nonfinite, reversed, lossy or exceeds its budget.
    """

    minimum: float
    maximum: float
    bucket_size: float
    bucket_count: int = field(init=False)

    def __post_init__(self) -> None:
        minimum = _native_double(self.minimum, "minimum")
        maximum = _native_double(self.maximum, "maximum")
        bucket_size = _native_double(self.bucket_size, "bucket_size")
        if minimum > maximum:
            raise ValueError("Distribution minimum must not exceed maximum.")
        if bucket_size <= 0:
            raise ValueError("Distribution bucket_size must be positive.")
        span = maximum - minimum + 1.0
        cells = span / bucket_size
        if not math.isfinite(span) or not math.isfinite(cells):
            raise ValueError("Distribution geometry arithmetic must remain finite.")
        bucket_count = math.ceil(cells)
        if not 1 <= bucket_count <= MAX_DISTRIBUTION_BUCKETS:
            raise ValueError(
                f"Distribution geometry requires between 1 and {MAX_DISTRIBUTION_BUCKETS} buckets."
            )
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)
        object.__setattr__(self, "bucket_size", bucket_size)
        object.__setattr__(self, "bucket_count", bucket_count)


def encode_distribution_geometry(geometry: DistributionGeometry) -> dict[str, float]:
    """Encode the three authoritative fields without derived labels or cell counts.

    Args:
        geometry: Exact current immutable geometry model.

    Returns:
        An independently owned current JSON object.

    Raises:
        TypeError: Geometry is not the current model.
    """
    if type(geometry) is not DistributionGeometry:
        raise TypeError("Distribution geometry requires its current typed model.")
    return {
        "minimum": geometry.minimum,
        "maximum": geometry.maximum,
        "bucket_size": geometry.bucket_size,
    }


def decode_distribution_geometry(value: object) -> DistributionGeometry:
    """Decode exactly the current minimum, maximum and bucket_size fields.

    Args:
        value: A current JSON object containing actual numeric values.

    Returns:
        Validated, independently owned native geometry.

    Raises:
        TypeError: Input is not an object or a field is not numeric.
        ValueError: Fields are missing, unsupported or invalid.
    """
    if type(value) is not dict:
        raise TypeError("Distribution geometry must be an object.")
    if set(value) != {"minimum", "maximum", "bucket_size"}:
        raise ValueError("Distribution geometry requires exactly minimum, maximum and bucket_size.")
    return DistributionGeometry(
        minimum=cast(float, value["minimum"]),
        maximum=cast(float, value["maximum"]),
        bucket_size=cast(float, value["bucket_size"]),
    )
