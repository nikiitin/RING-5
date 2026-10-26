"""Histogram stat type for range-based frequency distributions."""

import logging
import math
import re
from typing import override

from src.core.common.parse_failure import bounded_parse_text
from src.core.common.security_limits import MAX_INCREMENTAL_CACHE_COLUMNS
from src.core.models.parse_failure_models import ParseDataValueError
from src.parsing.gem5.types.base import FrameStatType, entry_names, population_mean, register_type

logger = logging.getLogger(__name__)


@register_type("histogram")
class Histogram(FrameStatType):
    """
    Represents histogram statistics with range-based buckets.
    Example: system.mem::0-1023 5

    One numeric entry frame is stored per concrete source/dump. Entry views are
    derived from those frames, preserving missing observations and summaries.

    Rebinning:
    If `bins` and `max_range` are provided, raw histogram data is proportionally
    redistributed into uniform buckets using linear interpolation. This assumes
    a uniform distribution of values within each raw bucket.

    Validation:
    - Keys should generally be range strings (e.g., "0-10") or specific markers.
    - Each observation records one complete source/dump frame.
    - Missing observations and summaries remain NaN.
    - Raw integer endpoints and integer output labels are inclusive; fractional
      output labels are explicitly half-open. Negative mass is retained in `<0`.
    """

    # [impl->req~ring5.ingestion.histogram~1]

    __slots__ = ("_bins", "_max_range", "_entries", "_statistics", "_statistics_only")

    required_params = []

    def __init__(
        self,
        repeat: int = 1,
        entries: list[str] | None = None,
        bins: int = 0,
        max_range: float = 0.0,
        statistics: list[str] | None = None,
        statistics_only: bool = False,
    ) -> None:
        """Configure selected buckets, optional uniform rebinning and summaries.

        Args:
            repeat: Expected number of source/dump frames.
            entries: Explicit bucket selection, taking precedence over rebinning.
            bins: Number of output buckets, including the overflow bucket.
            max_range: Nonnegative upper edge of the uniform range.
            statistics: Exact summary names to retain.
            statistics_only: Retain summaries without discovering raw buckets.

        Raises:
            ValueError: Active rebin geometry exceeds the physical-column budget.
        """
        super().__init__(repeat)
        if type(bins) is not int:
            raise TypeError("Histogram bins must be an integer.")
        if bins < 0:
            raise ValueError("Histogram bins must be nonnegative.")
        if type(max_range) not in (int, float):
            raise TypeError("Histogram max_range must be numeric.")
        if not math.isfinite(max_range) or max_range < 0:
            raise ValueError("Histogram max_range must be finite and nonnegative.")
        if type(statistics_only) is not bool:
            raise TypeError("Histogram statistics_only must be a boolean.")
        self._statistics_only = statistics_only
        self._bins = bins
        self._max_range = float(max_range)
        self._entries = tuple(
            self._canonical_bucket_key(entry) for entry in entry_names(entries, "Histogram entries")
        )
        self._statistics = entry_names(statistics, "Histogram statistics")
        if self._is_rebinning and self._bins > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ParseDataValueError("HISTOGRAM: output exceeds the physical column limit.")

    @property
    def _is_rebinning(self) -> bool:
        """Whether uniform output geometry owns the bucket schema."""
        return (
            not self._statistics_only
            and not self._entries
            and self._bins > 0
            and self._max_range > 0
        )

    @property
    def _content_entries(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                (
                    *self._entries,
                    *self._statistics,
                    *(key for sample in self._frames for key in sample),
                )
            )
        )

    @staticmethod
    def _canonical_bucket_key(key: str) -> str:
        """Represent a gem5 singleton bucket with explicit inclusive endpoints."""
        return f"{key}-{key}" if re.fullmatch(r"-?\d+", key) else key

    @staticmethod
    def _bin_label(start: float, end: float) -> str:
        """Label integer buckets inclusively and fractional buckets explicitly."""
        if float(start).is_integer() and float(end).is_integer():
            return f"{int(start)}-{int(end) - 1}"
        return f"[{start:.12g},{end:.12g})"

    @classmethod
    def declared_entries(
        cls,
        entries: tuple[str, ...],
        statistics: tuple[str, ...],
        bins: int,
        max_range: float,
        statistics_only: bool,
    ) -> tuple[str, ...]:
        """Return known physical labels without allocating a mutable accumulator.

        Summary-only and explicit-entry selection bypass unused rebin geometry.
        Dynamic raw cells and an observed negative tail are admitted when known.
        """
        if statistics_only:
            return statistics
        if entries:
            result = [cls._canonical_bucket_key(entry) for entry in entries]
        elif bins > 0 and max_range > 0:
            if bins > MAX_INCREMENTAL_CACHE_COLUMNS:
                raise ParseDataValueError("HISTOGRAM: output exceeds the physical column limit.")
            if bins > 1:
                width = max_range / (bins - 1)
                result = [
                    cls._bin_label(index * width, (index + 1) * width) for index in range(bins - 1)
                ]
                result.append(f"{max_range:.12g}+")
            else:
                result = ["0+"]
        else:
            result = []
        return tuple(dict.fromkeys([*result, *statistics]))

    @property
    def entries(self) -> list[str]:
        """Return exact selected/rebinned labels and actually discovered raw cells.

        Raises:
            ValueError: Active rebin output exceeds the physical-column budget.
        """
        if not self._statistics_only and not self._entries and not self._is_rebinning:
            result = sorted(self._content_entries)
            result.extend(stat for stat in self._statistics if stat not in result)
        else:
            result = list(
                self.declared_entries(
                    self._entries,
                    self._statistics,
                    self._bins,
                    self._max_range,
                    self._statistics_only,
                )
            )
        if self._is_rebinning and any(
            (bounds := self._parse_range_key(key)) and bounds[0] < 0
            for key in self._content_entries
        ):
            result.insert(0, "<0")
        if self._is_rebinning and len(result) > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ParseDataValueError("HISTOGRAM: output exceeds the physical column limit.")
        return result

    @override
    def _prepare_frame(self, sample: dict[str, float]) -> dict[str, float]:
        return {
            self._canonical_bucket_key(key): value
            for key, value in sample.items()
            if not self._statistics_only or key in self._statistics
        }

    @override
    def _reduce(self) -> dict[str, float]:
        """Average raw frames or proportionally rebin each observed frame."""
        if self._is_rebinning:
            return self._reduce_with_rebinning()
        return super()._reduce()

    def _reduce_with_rebinning(self) -> dict[str, float]:
        """Perform reduction by rebinning each simulation's data into target uniform buckets."""
        # [impl->req~ring5.ingestion.histogram-rebinning~1]
        target_keys = set(self.entries)
        bin_mapping = self._compute_bin_mapping(self._bins, self._max_range)
        raw_keys = set(self._content_entries)
        target_keys.update(
            key
            for mappings in bin_mapping.values()
            if mappings is not None
            for key, _proportion in mappings
        )
        target_keys.update(key for key, mappings in bin_mapping.items() if mappings is None)
        if len(self._frames) < self.repeat:
            return dict.fromkeys(target_keys, math.nan)
        target_values: dict[str, list[float]] = {key: [] for key in target_keys}

        for sample in self._frames:
            has_buckets = any(bin_mapping.get(key) is not None for key in sample)
            # Zeros are justified only within an observed histogram dump.
            rebinned = {key: 0.0 if has_buckets else float("nan") for key in target_keys}
            for raw_key, value in sample.items():
                mappings = bin_mapping.get(raw_key)
                if mappings is None:
                    continue
                for target_key, proportion in mappings:
                    rebinned[target_key] += value * proportion
            for key in target_keys:
                if bin_mapping.get(key) is None and key in raw_keys:
                    rebinned[key] = sample.get(key, float("nan"))
                target_values[key].append(rebinned[key])

        return {key: population_mean(values) for key, values in target_values.items()}

    def _compute_bin_mapping(
        self, num_bins: int, max_val: float
    ) -> dict[str, list[tuple[str, float]] | None]:
        """Pre-compute the mapping from raw buckets to target bins.

        Returns a dict mapping each raw_key to a list of (target_key, proportion)
        tuples, or None for non-range keys (summary stats preserved as-is).
        Computed once and reused across actual observed frames.
        """
        if num_bins > 1:
            num_std_bins = num_bins - 1
            bin_width = max_val / num_std_bins
            overflow_key = f"{max_val:.12g}+"
        else:
            num_std_bins = num_bins
            bin_width = max_val / num_bins
            overflow_key = None

        mapping: dict[str, list[tuple[str, float]] | None] = {}

        for raw_key in self._content_entries:
            bounds = self._parse_range_key(raw_key)
            if not bounds:
                mapping[raw_key] = None
                continue

            raw_start, inclusive_end = bounds
            if inclusive_end < raw_start:
                raise ParseDataValueError(f"HISTOGRAM: Reversed bucket range: {raw_key}")
            raw_end = inclusive_end + 1
            raw_span = raw_end - raw_start

            targets: list[tuple[str, float]] = []

            underflow_length = max(0.0, min(raw_end, 0.0) - raw_start)
            if underflow_length:
                targets.append(("<0", underflow_length / raw_span))

            # Standard bins portion
            effective_end = min(raw_end, max_val)
            if effective_end > raw_start:
                for b in range(num_std_bins):
                    b_start = b * bin_width
                    b_end = (b + 1) * bin_width
                    overlap_start = max(raw_start, b_start)
                    overlap_end = min(effective_end, b_end)
                    if overlap_end > overlap_start:
                        proportion = (overlap_end - overlap_start) / raw_span
                        target_key = "0+" if num_bins == 1 else self._bin_label(b_start, b_end)
                        targets.append((target_key, proportion))

            # Overflow portion
            overflow_length = max(0.0, raw_end - max(raw_start, max_val))
            if overflow_length > 0:
                proportion = overflow_length / raw_span
                if overflow_key:
                    targets.append((overflow_key, proportion))
                else:
                    last_b_idx = num_std_bins - 1
                    last_start = last_b_idx * bin_width
                    last_end = (last_b_idx + 1) * bin_width
                    last_key = "0+" if num_bins == 1 else self._bin_label(last_start, last_end)
                    targets.append((last_key, proportion))

            mapping[raw_key] = targets

        return mapping

    def _parse_range_key(self, key: str) -> list[float]:
        """Extract numeric bounds from a range string (e.g., '0-1023')."""
        match = re.fullmatch(r"(-?\d+)-(-?\d+)", key)
        if match:
            return [float(match.group(1)), float(match.group(2))]
        if any(c.isdigit() for c in key):
            logger.debug("HISTOGRAM: Could not parse range from key '%s'", bounded_parse_text(key))
        return []

    def __str__(self) -> str:
        return f"Histogram(buckets={len(self._content_entries)}, repeat={self._repeat})"
