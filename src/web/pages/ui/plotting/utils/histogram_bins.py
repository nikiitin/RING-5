"""Histogram interval parsing and count-conserving view preparation."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import cast

_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_RANGE = re.compile(rf"^({_NUMBER})-({_NUMBER})$")
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
    """Parse gem5 inclusive ranges and legacy shared-edge continuous ranges.

    Explicit ``[a,b)`` intervals are half-open. Integer ``a-b`` intervals
    are inclusive, except adjacent legacy ranges sharing an endpoint.
    ``a+`` and ``<b`` retain overflow and underflow observations.

    Raises:
        ValueError: If a label is malformed, nonfinite, or empty.
    """
    # [impl->req~ring5.plot.histogram~1]
    parsed: list[tuple[int, HistogramBin, bool]] = []
    for index, label in enumerate(labels):
        explicit = _INTERVAL.fullmatch(label)
        ranged = _RANGE.fullmatch(label)
        inclusive = False
        if explicit or ranged:
            match = explicit or ranged
            assert match is not None
            lower, upper = map(float, match.groups())
            inclusive = explicit is None and lower.is_integer() and upper.is_integer()
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
        parsed.append((index, HistogramBin(lower, upper, label), inclusive))
    parsed.sort(key=lambda item: -math.inf if item[1].lower is None else item[1].lower)
    # CSVs produced by older releases use continuous shared endpoints.
    shared_edges = any(
        left.upper is not None and left.upper == right.lower
        for (_, left, left_inclusive), (_, right, right_inclusive) in zip(parsed, parsed[1:])
        if left_inclusive and right_inclusive
    )
    result: list[HistogramBin] = []
    for _, bucket, inclusive in parsed:
        upper = bucket.upper
        if inclusive and not shared_edges and upper is not None:
            upper += 1
        normalized = HistogramBin(bucket.lower, upper, bucket.label)
        if normalized.width is not None and normalized.width <= 0:
            raise ValueError(f"Empty histogram bucket: {bucket.label!r}.")
        result.append(normalized)
    return result, [index for index, _, _ in parsed]


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
        count = math.ceil((upper - lower) / bucket_size)
        if count > 100_000:
            raise ValueError("Histogram bucket size produces more than 100000 bins.")
        targets = [
            HistogramBin(
                lower + index * bucket_size, min(upper, lower + (index + 1) * bucket_size), ""
            )
            for index in range(count)
        ]
    rebinned: list[float] = []
    for target in targets:
        assert target.lower is not None and target.upper is not None
        mass = 0.0
        for source, value in zip(bins, values, strict=True):
            if source.width is None:
                continue
            assert source.lower is not None and source.upper is not None
            overlap = max(0.0, min(source.upper, target.upper) - max(source.lower, target.lower))
            mass += value * overlap / source.width
        rebinned.append(mass)
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
