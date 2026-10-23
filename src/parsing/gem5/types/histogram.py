"""Histogram stat type for range-based frequency distributions."""

import logging
import math
import re
from typing import override

from src.core.models.parsing_models import StatParamValue
from src.parsing.gem5.types.base import StatType, register_type

logger = logging.getLogger(__name__)


@register_type("histogram")
class Histogram(StatType):
    """
    Represents histogram statistics with range-based buckets.
    Example: system.mem::0-1023 5

    Content is stored as a dictionary mapping range strings to a list of numeric values
    (one value per simulation/repeat).

    Rebinning:
    If `bins` and `max_range` are provided, raw histogram data is proportionally
    redistributed into uniform buckets using linear interpolation. This assumes
    a uniform distribution of values within each raw bucket.

    Validation:
    - Keys should generally be range strings (e.g., "0-10") or specific markers.
    - Each assignment records one instance/dump; lists within it are summed.
    - Missing observations and summaries remain NaN.
    - Raw integer endpoints and integer output labels are inclusive; fractional
      output labels are explicitly half-open. Negative mass is retained in `<0`.
    """

    # [impl->req~ring5.ingestion.histogram~1]

    required_params = []  # Histogram buckets are usually dynamic in gem5 stats
    _allowed_attributes = frozenset(
        {
            "_repeat",
            "_content",
            "_reduced_content",
            "_balanced",
            "_reduced",
            "_bins",
            "_max_range",
            "_entries",
            "_statistics",
        }
    )

    def __init__(
        self,
        repeat: int = 1,
        entries: list[str] | None = None,
        bins: int = 0,
        max_range: float = 0.0,
        statistics: str | list[str] | None = None,
        **kwargs: StatParamValue,
    ) -> None:
        """
        Initialize Histogram type.

        Args:
            repeat: Number of simulations/dumps expected.
            entries: Explicit list of buckets to extract (overrides rebinning).
            bins: Number of target buckets for rebinning.
            max_range: Maximum value for rebinning range.
            statistics: Additional aggregate fields to retain.
            **kwargs: Additional attributes passed to parent.
        """
        super().__init__(repeat, **kwargs)
        # Content is a dict of {range_key: [value1, value2...]}
        if isinstance(statistics, str):
            statistics = [s.strip() for s in statistics.split(",")]

        object.__setattr__(self, "_bins", int(bins))
        object.__setattr__(self, "_max_range", float(max_range))
        object.__setattr__(
            self,
            "_entries",
            [self._canonical_bucket_key(entry) for entry in entries] if entries else None,
        )
        object.__setattr__(self, "_statistics", list(statistics) if statistics else [])

        # Pre-initialize content with statistics to ensure column presence
        content: dict[str, list[float]] = {
            entry: [] for entry in [*(self._entries or []), *self._statistics]
        }
        object.__setattr__(self, "_content", content)
        # Shared by shallow source aliases, just like the content dictionary.
        object.__setattr__(self, "_observations", [])

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

    @property
    def entries(self) -> list[str]:
        """Get the expected output entry keys for this histogram."""
        result = []
        # Priority 1: User-selected specific buckets
        if self._entries:
            result.extend(self._entries)
        # Priority 2: Rebinned buckets
        elif self._bins > 0 and self._max_range > 0:
            if self._bins > 1:
                num_std = self._bins - 1
                bin_width = self._max_range / num_std
                result.extend(
                    [self._bin_label(b * bin_width, (b + 1) * bin_width) for b in range(num_std)]
                )
                result.append(f"{self._max_range:.12g}+")
            else:
                result.append("0+")
        # Priority 3: Discovered raw buckets
        else:
            raw_content = object.__getattribute__(self, "_content")
            result.extend(sorted(list(raw_content.keys())))

        if (
            not self._entries
            and self._bins > 0
            and self._max_range > 0
            and any(
                (bounds := self._parse_range_key(key)) and bounds[0] < 0 for key in self._content
            )
        ):
            result.insert(0, "<0")

        # Always include extra statistics if they were discovered or configured
        for stat in self._statistics:
            if stat not in result:
                result.append(stat)

        return result

    @property
    def content(self) -> dict[str, list[float]]:
        """Get the raw accumulated content mapping."""
        content_dict: dict[str, list[float]] = object.__getattribute__(self, "_content")
        return content_dict

    @content.setter
    def content(self, value: dict[str, list[str | int | float] | str | int | float]) -> None:
        """
        Set and aggregate content from a dictionary.

        Multiple occurrences in one file are summed, such as a regex spanning CPU cores.
        """
        if not isinstance(value, dict):
            raise TypeError(f"HISTOGRAM: Content must be dict, got {type(value).__name__}")

        sample: dict[str, float] = {}
        for key, vals in value.items():
            val_list = vals if isinstance(vals, list) else [vals]
            try:
                sample[self._canonical_bucket_key(str(key))] = math.fsum(float(v) for v in val_list)
            except (TypeError, ValueError) as error:
                raise TypeError(
                    f"HISTOGRAM: Value non-convertible to number. Key: {key}, Value: {vals}"
                ) from error

        count = len(self._observations)
        for key in sample:
            if key not in self._content:
                self._content[key] = [float("nan")] * count
        for key in self._content:
            self._content[key].append(sample.get(key, float("nan")))
        self._observations.append(sample)

    @override
    def balance_content(self) -> None:
        """
        Ensure each bucket has exactly `repeat` values, preserving missingness.

        Fails loudly if more values than expected are found, preventing data corruption.
        """
        object.__setattr__(self, "_balanced", True)

        # Include missing configured statistics before balancing each bucket.
        target_keys = set(self._content.keys())
        if self._statistics:
            target_keys.update(self._statistics)

        for bucket in target_keys:
            if bucket not in self._content:
                self._content[bucket] = []

            current_len = len(self._content[bucket])
            if current_len < self._repeat:
                padding = self._repeat - current_len
                self._content[bucket].extend([float("nan")] * padding)
                object.__setattr__(self, "_padded", self._padded + padding)
            elif current_len > self._repeat:
                raise RuntimeError(
                    f"HISTOGRAM: Bucket '{bucket}' has more values than expected. "
                    f"Length: {current_len}, Repeat: {self._repeat}"
                )

    @override
    def reduce_duplicates(self) -> None:
        """Reduce collected data via mean, applying rebinning if requested."""
        object.__setattr__(self, "_reduced", True)

        # Explicit entry selection has the same precedence as the entries property.
        if not self._entries and self._bins > 0 and self._max_range > 0:
            self._reduce_with_rebinning()
            return

        reduced = {}
        for bucket, values in self._content.items():
            if not values:
                reduced[bucket] = float("nan")
            else:
                reduced[bucket] = sum(values[: self._repeat]) / self._repeat

        object.__setattr__(self, "_reduced_content", reduced)

    def _reduce_with_rebinning(self) -> None:
        """Perform reduction by rebinning each simulation's data into target uniform buckets."""
        # [impl->req~ring5.ingestion.histogram-rebinning~1]
        bin_mapping = self._compute_bin_mapping(self._bins, self._max_range)
        target_keys = set(self.entries)
        target_keys.update(
            key
            for mappings in bin_mapping.values()
            if mappings is not None
            for key, _proportion in mappings
        )
        target_keys.update(key for key, mappings in bin_mapping.items() if mappings is None)
        target_values: dict[str, list[float]] = {key: [] for key in target_keys}

        for index in range(self._repeat):
            sample = self._observations[index] if index < len(self._observations) else {}
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
                if bin_mapping.get(key) is None and key in self._content:
                    rebinned[key] = sample.get(key, float("nan"))
                target_values[key].append(rebinned[key])

        object.__setattr__(
            self,
            "_reduced_content",
            {key: math.fsum(values) / self._repeat for key, values in target_values.items()},
        )

    def _compute_bin_mapping(
        self, num_bins: int, max_val: float
    ) -> dict[str, list[tuple[str, float]] | None]:
        """Pre-compute the mapping from raw buckets to target bins.

        Returns a dict mapping each raw_key to a list of (target_key, proportion)
        tuples, or None for non-range keys (summary stats preserved as-is).
        Computed once and reused across all repeat iterations.
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

        for raw_key in self._content:
            bounds = self._parse_range_key(raw_key)
            if not bounds:
                mapping[raw_key] = None
                continue

            raw_start, inclusive_end = bounds
            if inclusive_end < raw_start:
                raise ValueError(f"HISTOGRAM: Reversed bucket range: {raw_key}")
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
            logger.debug("HISTOGRAM: Could not parse range from key '%s'", key)
        return []

    def __str__(self) -> str:
        return f"Histogram(buckets={len(self._content)}, repeat={self._repeat})"
