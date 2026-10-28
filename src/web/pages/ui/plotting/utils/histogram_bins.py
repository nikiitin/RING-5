"""Histogram interval parsing and count-conserving view preparation."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import cast

_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_RANGE = re.compile(r"^([+-]?\d+)-([+-]?\d+)$")
_INTERVAL = re.compile(rf"^\[({_NUMBER}),\s*({_NUMBER})\)$")


@dataclass(frozen=True)
class HistogramBin:
    """A half-open finite interval, or a labelled unbounded tail."""

    lower: float | None
    upper: float | None
    label: str

    @property
    def width(self) -> float | None:
        """Return interval width when both bounds are known."""
        if self.lower is None or self.upper is None:
            return None
        return self.upper - self.lower


def parse_histogram_bins(labels: list[str]) -> tuple[list[HistogramBin], list[int]]:
    """Parse one observation's explicit, nonoverlapping bucket geometry.

    Explicit ``[a,b)`` intervals are half-open. Integer ``a-b`` intervals
    include both endpoints and occupy ``[a,b+1)`` for rendering.
    ``a+`` and ``<b`` retain overflow and underflow observations.

    Raises:
        ValueError: If buckets are malformed, unrepresentable, empty, or overlap.
    """
    # [impl->req~ring5.plot.histogram~2]
    if not labels:
        raise ValueError("A histogram observation requires at least one bucket.")
    parsed: list[tuple[int, HistogramBin]] = []
    for index, label in enumerate(labels):
        explicit = _INTERVAL.fullmatch(label)
        ranged = _RANGE.fullmatch(label)
        if explicit:
            lower, upper = map(float, explicit.groups())
        elif ranged:
            first, last = map(int, ranged.groups())
            if first > last:
                raise ValueError(f"Reversed histogram bucket: {label!r}.")
            try:
                lower, upper = float(first), float(last + 1)
            except OverflowError as exc:
                raise ValueError(f"Unrepresentable histogram bucket: {label!r}.") from exc
            if lower != first or upper != last + 1:
                raise ValueError(f"Unrepresentable histogram bucket: {label!r}.")
        elif label.endswith("+"):
            lower, upper = float(label[:-1]), None
        elif label.startswith("<"):
            lower, upper = None, float(label[1:])
        else:
            raise ValueError(f"Unsupported histogram bucket: {label!r}.")
        if any(bound is not None and not math.isfinite(bound) for bound in (lower, upper)):
            raise ValueError(f"Nonfinite histogram bucket: {label!r}.")
        if lower is not None and upper is not None and lower > upper:
            raise ValueError(f"Reversed histogram bucket: {label!r}.")
        bucket = HistogramBin(lower, upper, label)
        if bucket.width is not None and (not math.isfinite(bucket.width) or bucket.width <= 0):
            raise ValueError(f"Empty or unrepresentable histogram bucket: {label!r}.")
        parsed.append((index, bucket))
    parsed.sort(key=lambda item: -math.inf if item[1].lower is None else item[1].lower)
    for (_, left), (_, right) in zip(parsed, parsed[1:]):
        if left.upper is None or right.lower is None or left.upper > right.lower:
            raise ValueError(
                f"Overlapping histogram buckets in one observation: {left.label!r}, "
                f"{right.label!r}. Use explicit [a,b) labels for continuous intervals."
            )
    return [bucket for _, bucket in parsed], [index for index, _ in parsed]


def sum_histogram_counts(values: Iterable[float]) -> float:
    """Sum admitted counts, rejecting native floating-point overflow.

    Raises:
        ValueError: The combined count cannot be represented as a finite float.
    """
    try:
        total = math.fsum(values)
    except OverflowError as exc:
        if type(exc) is not OverflowError:
            raise
        raise ValueError("Combined Histogram counts exceed the finite numeric range.") from exc
    if not math.isfinite(total):
        raise ValueError("Combined Histogram counts must remain finite.")
    return total


def cumulative_histogram_counts(values: Sequence[float]) -> list[float]:
    """Round each nonnegative binary64 prefix once with linear bounded work.

    Every binary64 denominator divides 2**1074. Its scaled numerator needs at
    most 2098 bits; 100000 displayed cells add at most 17 carry bits.

    Raises:
        ValueError: An accumulated count cannot be represented as a finite float.
    """
    scale = 1 << 1074
    total = 0
    result = []
    for value in values:
        numerator, denominator = value.as_integer_ratio()
        total += numerator * (scale // denominator)
        try:
            count = total / scale
        except OverflowError as exc:
            if type(exc) is not OverflowError:
                raise
            raise ValueError("Cumulative Histogram counts must remain finite.") from exc
        if not math.isfinite(count):
            raise ValueError("Cumulative Histogram counts must remain finite.")
        result.append(count)
    return result


def aggregate_histogram_observations(
    labels: list[str],
    rows: Iterable[Sequence[float | None]],
) -> tuple[list[HistogramBin], list[float]]:
    """Normalize each observed row's geometry before combining interval mass.

    NaN fields represent intervals absent from that observation's bucket schema.
    Each measured row must contain nonoverlapping buckets. Different rows can
    have different schemas, whose overlapping intervals retain their own mass.

    Raises:
        ValueError: If an observation is missing or contains invalid counts.
    """
    mass: dict[tuple[float | None, float | None], tuple[HistogramBin, list[float]]] = {}
    for row in rows:
        measured = [
            (label, float(value))
            for label, value in zip(labels, row, strict=True)
            if value is not None and not math.isnan(float(value))
        ]
        if not measured:
            raise ValueError(
                "Every histogram observation must contain at least one measured bucket."
            )
        if any(not math.isfinite(value) or value < 0 for _, value in measured):
            raise ValueError("Histogram counts must be finite and nonnegative.")
        bins, order = parse_histogram_bins([label for label, _ in measured])
        for bucket, index in zip(bins, order, strict=True):
            key = (bucket.lower, bucket.upper)
            if key not in mass:
                mass[key] = (bucket, [])
            mass[key][1].append(measured[index][1])
    if not mass:
        raise ValueError("A histogram requires at least one measured observation.")
    ordered = sorted(
        mass.values(),
        key=lambda item: (
            -math.inf if item[0].lower is None else item[0].lower,
            math.inf if item[0].upper is None else item[0].upper,
        ),
    )
    return [bucket for bucket, _ in ordered], [
        sum_histogram_counts(values) for _, values in ordered
    ]


def histogram_mass_ratio(
    value: float, multiplier: float, divisor: float, second_divisor: float = 1.0
) -> float:
    """Round admitted finite mass times a scale over one or two positive divisors.

    All callers supply binary64 counts, overlap/width or normalization operands.
    Four binary64 integer ratios bound the integer work to a few thousand bits.
    One final division preserves subnormals without a staged arithmetic fallback.

    Raises:
        ValueError: Positive final mass is outside the finite nonzero float range.
    """
    # [impl->req~ring5.plot.histogram~2]
    if value == 0 or multiplier == 0:
        return 0.0
    value_numerator, value_denominator = value.as_integer_ratio()
    scale_numerator, scale_denominator = multiplier.as_integer_ratio()
    divisor_numerator, divisor_denominator = divisor.as_integer_ratio()
    second_numerator, second_denominator = second_divisor.as_integer_ratio()
    numerator = value_numerator * scale_numerator * divisor_denominator * second_denominator
    denominator = value_denominator * scale_denominator * divisor_numerator * second_numerator
    try:
        contribution = numerator / denominator
    except OverflowError as exc:
        if type(exc) is not OverflowError:
            raise
        raise ValueError("Histogram mass exceeds the finite numeric range.") from exc
    if not math.isfinite(contribution) or contribution <= 0:
        raise ValueError("Positive Histogram mass is outside the finite nonzero range.")
    return contribution


def rebin_histogram(
    bins: list[HistogramBin],
    values: list[float],
    bucket_size: float | None,
) -> tuple[list[HistogramBin], list[float]]:
    """Rebin finite counts by interval overlap, preserving both unbounded tails.

    Splitting a source bin assumes uniform mass within that interval.
    """
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("Histogram counts must be finite and nonnegative.")
    finite = [bucket for bucket in bins if bucket.width is not None]
    if not finite:
        return bins, values
    if bucket_size is None:
        overlapping = any(
            cast(float, left.upper) > cast(float, right.lower)
            for left, right in zip(finite, finite[1:])
        )
        if not overlapping:
            return bins, values
        edges = sorted(
            {cast(float, bound) for bucket in finite for bound in (bucket.lower, bucket.upper)}
        )
        targets = [HistogramBin(lower, upper, "") for lower, upper in zip(edges, edges[1:])]
    else:
        if not math.isfinite(bucket_size) or bucket_size <= 0:
            raise ValueError("Histogram bucket size must be finite and positive.")
        lower = min(bucket.lower for bucket in finite if bucket.lower is not None)
        upper = max(bucket.upper for bucket in finite if bucket.upper is not None)
        span = upper - lower
        quotient = span / bucket_size
        if not math.isfinite(span) or not math.isfinite(quotient):
            raise ValueError("Histogram rebin geometry exceeds the finite numeric range.")
        count = max(1, math.ceil(quotient))
        if count > 100_000:
            raise ValueError("Histogram bucket size produces more than 100000 bins.")
        targets = []
        for index in range(count):
            start = lower + index * bucket_size
            stop = min(upper, lower + (index + 1) * bucket_size)
            if not math.isfinite(start) or not math.isfinite(stop) or stop <= start:
                raise ValueError("Histogram rebin cells must have finite positive widths.")
            targets.append(HistogramBin(start, stop, ""))
    rebinned: list[float] = []
    for target in targets:
        assert target.lower is not None and target.upper is not None
        target_lower: float = target.lower
        target_upper: float = target.upper

        def contributions() -> Iterable[float]:
            for source, value in zip(bins, values, strict=True):
                width = source.width
                if width is None:
                    continue
                assert source.lower is not None and source.upper is not None
                overlap = max(
                    0.0, min(source.upper, target_upper) - max(source.lower, target_lower)
                )
                yield histogram_mass_ratio(value, overlap, width)

        rebinned.append(sum_histogram_counts(contributions()))
    underflow = [
        (bucket, value) for bucket, value in zip(bins, values, strict=True) if bucket.lower is None
    ]
    overflow = [
        (bucket, value) for bucket, value in zip(bins, values, strict=True) if bucket.upper is None
    ]
    return (
        [bucket for bucket, _ in underflow] + targets + [bucket for bucket, _ in overflow],
        [value for _, value in underflow] + rebinned + [value for _, value in overflow],
    )
