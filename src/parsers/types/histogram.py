"""Histogram stat type for range-based frequency distributions."""

import re
from typing import Any, Dict, List, Optional

from src.parsers.types.base import StatType, register_type


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
    - Values are automatically aggregated (summed) if multiple matches occur in one file.
    """

    required_params = []  # Histogram buckets are usually dynamic in gem5 stats
    _allowed_attributes = frozenset(
        {
            "_repeat",
            "_content",
            "_reduced_content",
            "_balanced",
            "_reduced",
            "balancedContent",
            "reducedDuplicates",
            "reducedContent",
            "_bins",
            "_max_range",
            "_entries",
            "_statistics",
        }
    )

    def __init__(
        self,
        repeat: int = 1,
        entries: Optional[List[str]] = None,
        bins: int = 0,
        max_range: float = 0.0,
        statistics: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize Histogram type.

        Args:
            repeat: Number of simulations/dumps expected.
            entries: Explicit list of buckets to extract (overrides rebinning).
            bins: Number of target buckets for rebinning.
            max_range: Maximum value for rebinning range.
            **kwargs: Additional attributes passed to parent.
        """
        super().__init__(repeat, **kwargs)
        # Content is a dict of {range_key: [value1, value2...]}
        if isinstance(statistics, str):
            statistics = [s.strip() for s in statistics.split(",")]

        object.__setattr__(self, "_bins", int(bins))
        object.__setattr__(self, "_max_range", float(max_range))
        object.__setattr__(self, "_entries", list(entries) if entries else None)
        object.__setattr__(self, "_statistics", list(statistics) if statistics else [])

        # Pre-initialize content with statistics to ensure column presence
        content: Dict[str, List[Any]] = {stat: [] for stat in self._statistics}
        object.__setattr__(self, "_content", content)

    @property
    def entries(self) -> List[str]:
        """Get the expected output entry keys for this histogram."""
        result = []
        # Priority 1: User-selected specific buckets
        if self._entries:
            result.extend(self._entries)
        # Priority 2: Rebinned buckets
        # Priority 2: Rebinned buckets
        elif self._bins > 0 and self._max_range > 0:
            if self._bins > 1:
                num_std = self._bins - 1
                bin_width = self._max_range / num_std
                result.extend(
                    [f"{int(b * bin_width)}-{int((b + 1) * bin_width)}" for b in range(num_std)]
                )
                result.append(f"{int(self._max_range)}+")
            else:
                bin_width = self._max_range / self._bins
                result.extend(
                    [f"{int(b * bin_width)}-{int((b + 1) * bin_width)}" for b in range(self._bins)]
                )
        # Priority 3: Discovered raw buckets
        else:
            raw_content = object.__getattribute__(self, "_content")
            result.extend(sorted(list(raw_content.keys())))

        # Always include extra statistics if they were discovered or configured
        for stat in self._statistics:
            if stat not in result:
                result.append(stat)

        return result

    @property
    def content(self) -> Dict[str, List[float]]:
        """Get the raw accumulated content mapping."""
        content_dict: Dict[str, List[float]] = object.__getattribute__(self, "_content")
        return content_dict

    @content.setter
    def content(self, value: Dict[str, Any]) -> None:
        """
        Set and aggregate content from a dictionary.

        This setter handles the 'Sacred Scanning' requirement by automatically
        summing multiple occurrences per file (e.g., aggregating across CPU cores).
        """
        if not isinstance(value, dict):
            raise TypeError(f"HISTOGRAM: Content must be dict, got {type(value).__name__}")

        # Validate values are numeric and aggregate matches
        for key, vals in value.items():
            if isinstance(vals, list):
                val_list = vals
            else:
                val_list = [vals]

            # Aggregate multiple matches from a single file (e.g. regex across CPUs)
            # Sum for aggregated value per repeat.
            aggregated_val = 0.0
            for v in val_list:
                try:
                    aggregated_val += float(v)
                except (TypeError, ValueError) as e:
                    raise TypeError(
                        f"HISTOGRAM: Value non-convertible to number. Key: {key}, Value: {v}"
                    ) from e

            # Update content
            str_key = str(key)
            if str_key not in self._content:
                self._content[str_key] = []

            self._content[str_key].append(aggregated_val)

    def balance_content(self) -> None:
        """
        Ensure each bucket has exactly `repeat` values by padding with 0.

        Fails loudly if more values than expected are found, preventing data corruption.
        """
        object.__setattr__(self, "_balanced", True)

        # Scientific Integrity: Ensure all configured/discovered buckets are balanced
        # This includes re-initializing missing statistical buckets for this dump factor.
        target_keys = set(self._content.keys())
        if self._statistics:
            target_keys.update(self._statistics)

        for bucket in target_keys:
            if bucket not in self._content:
                self._content[bucket] = []

            current_len = len(self._content[bucket])
            if current_len < self._repeat:
                padding = self._repeat - current_len
                self._content[bucket].extend([0.0] * padding)
            elif current_len > self._repeat:
                # This could happen if simpoint aware dumps are incorrectly aggregated
                raise RuntimeError(
                    f"HISTOGRAM: Bucket '{bucket}' has more values than expected. "
                    f"Length: {current_len}, Repeat: {self._repeat}"
                )

    def reduce_duplicates(self) -> None:
        """Reduce collected data via mean, applying rebinning if requested."""
        object.__setattr__(self, "_reduced", True)

        # Rebinning takes precedence if configured
        if self._bins > 0 and self._max_range > 0:
            self._reduce_with_rebinning()
            return

        reduced = {}
        for bucket in self._content:
            values = self._content.get(bucket, [])
            if not values:
                reduced[bucket] = 0.0
            else:
                total = sum(float(v) for v in values[: self._repeat])
                reduced[bucket] = total / self._repeat

        object.__setattr__(self, "_reduced_content", reduced)

    def _reduce_with_rebinning(self) -> None:
        """Perform reduction by rebinning each simulation's data into target uniform buckets."""
        num_bins = self._bins
        max_val = self._max_range

        # Initialize target result set from expected entries
        target_reduced = {key: 0.0 for key in self.entries}

        # Process each simulation independently
        for i in range(self._repeat):
            sim_data = {}
            for bucket, values in self._content.items():
                sim_data[bucket] = float(values[i]) if i < len(values) else 0.0

            # Rebin this simulation's data (deterministic transformation)
            rebinned = self._rebin_simulation_data(sim_data, num_bins, max_val)

            # Accumulate (includes rebinned buckets and preserved summary stats)
            for key, val in rebinned.items():
                if key not in target_reduced:
                    target_reduced[key] = 0.0
                target_reduced[key] += val

        # Calculate population mean across simulations
        for key in target_reduced:
            target_reduced[key] /= self._repeat

        object.__setattr__(self, "_reduced_content", target_reduced)

    def _rebin_simulation_data(
        self, data: Dict[str, float], num_bins: int, max_val: float
    ) -> Dict[str, float]:
        """
        Proportionally redistribute raw histogram data into uniform target bins.

        Uses linear interpolation to map raw mass to target bins.
        """
        if num_bins > 1:
            num_std_bins = num_bins - 1
            bin_width = max_val / num_std_bins
            overflow_key = f"{int(max_val)}+"
        else:
            num_std_bins = num_bins
            bin_width = max_val / num_bins
            overflow_key = None

        rebinned = {
            f"{int(b * bin_width)}-{int((b + 1) * bin_width)}": 0.0 for b in range(num_std_bins)
        }
        if overflow_key:
            rebinned[overflow_key] = 0.0

        for raw_key, value in data.items():
            if value == 0:
                continue

            bounds = self._parse_range_key(raw_key)
            if not bounds:
                # Preserve summary stats (mean, total, etc.) as-is
                rebinned[raw_key] = value
                continue

            raw_start, raw_end = bounds
            raw_span = raw_end - raw_start
            if raw_span <= 0:
                continue

            # Determine effective range to process for distribution
            # We treat max_val as a soft limit: anything above it goes to the overflow buckets.

            # 1. Calculate and distribute the portion strictly within the [0, max_val] range
            effective_end = min(raw_end, max_val)
            if effective_end > raw_start:
                # Redistribute 'value' across target bins based on overlap
                for b in range(num_std_bins):
                    b_start = b * bin_width
                    b_end = (b + 1) * bin_width

                    overlap_start = max(raw_start, b_start)
                    overlap_end = min(effective_end, b_end)

                    if overlap_end > overlap_start:
                        overlap_width = overlap_end - overlap_start
                        proportion = overlap_width / raw_span
                        target_key = f"{int(b_start)}-{int(b_end)}"
                        rebinned[target_key] += value * proportion

            # 2. Handle Overflow: Add any mass above max_val to the overflow bucket (or last bin)
            overflow_length = max(0.0, raw_end - max(raw_start, max_val))
            if overflow_length > 0:
                proportion = overflow_length / raw_span

                if overflow_key:
                    rebinned[overflow_key] += value * proportion
                else:
                    # Fallback to last regular bin if no dedicated overflow
                    last_b_idx = num_std_bins - 1
                    last_start = last_b_idx * bin_width
                    last_end = (last_b_idx + 1) * bin_width
                    last_key = f"{int(last_start)}-{int(last_end)}"
                    rebinned[last_key] += value * proportion

        return rebinned

    def _parse_range_key(self, key: str) -> List[float]:
        """Extract numeric bounds from a range string (e.g., '0-1023')."""
        match = re.search(r"(\d+)-(\d+)", key)
        if match:
            return [float(match.group(1)), float(match.group(2))]
        return []

    @property
    def reduced_content(self) -> Dict[str, float]:
        """Get the final reduced (averaged) data."""
        balanced = object.__getattribute__(self, "_balanced")
        reduced = object.__getattribute__(self, "_reduced")
        if not balanced or not reduced:
            raise AttributeError(
                "HISTOGRAM: Cannot access reduced_content before calling "
                "balance_content() AND reduce_duplicates()"
            )
        reduced_dict: Dict[str, float] = object.__getattribute__(self, "_reduced_content")
        return reduced_dict

    @property
    def reducedContent(self) -> Dict[str, float]:
        """Backward compatibility alias."""
        return self.reduced_content

    def __str__(self) -> str:
        return f"Histogram(buckets={len(self._content)}, repeat={self._repeat})"
