"""Histogram stat type for range-based frequency distributions."""

from typing import Any, Dict, List

from src.common.types.base import StatType, register_type


@register_type("histogram")
class Histogram(StatType):
    """
    Represents histogram statistics with range-based buckets.
    Example: system.mem::0-1023 5

    Content is stored as dict mapping range strings to values.

    Validation:
    - Keys should generally be range strings (e.g., "0-10") or specific markers.
    - Values must be convertible to int/float.
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
        }
    )

    def __init__(self, repeat: int = 1, entries: List[str] = None, bins: int = 0, max_range: float = 0, **kwargs):
        super().__init__(repeat, **kwargs)
        # Content is a dict of {range_key: [value1, value2...]}
        object.__setattr__(self, "_content", {})
        object.__setattr__(self, "_bins", int(bins))
        object.__setattr__(self, "_max_range", float(max_range))
        object.__setattr__(self, "_entries", list(entries) if entries else None)

    @property
    def entries(self) -> List[str]:
        # Priority 1: User-selected entries (Summary stats or specific buckets)
        if self._entries:
            return self._entries

        # Priority 2: Rebinned buckets
        if self._bins > 0 and self._max_range > 0:
            num_bins = self._bins
            max_val = self._max_range
            bin_width = max_val / num_bins
            return [f"{int(b * bin_width)}-{int((b + 1) * bin_width)}" for b in range(num_bins)]

        # Priority 3: Discovered raw buckets
        return sorted(list(object.__getattribute__(self, "_content").keys()))

    @property
    def content(self) -> Dict[str, List[Any]]:
        return object.__getattribute__(self, "_content")

    @content.setter
    def content(self, value: Dict[str, List[Any]]) -> None:
        """Set content from dict."""
        if not isinstance(value, dict):
            raise TypeError(f"HISTOGRAM: Content must be dict, got {type(value).__name__}")

        # Validate values are numeric
        for key, vals in value.items():
            # Check key format (optional, but good for validation)
            # gem5 range format: number-number
            # But we allow 'overflows'/'underflows' if they appear in histograms too?
            # Typically Histograms in gem5 use ranges.

            if isinstance(vals, list):
                val_list = vals
            else:
                val_list = [vals]

            # Aggregate multiple matches from a single file (e.g. regex across CPUs)
            # We sum them so that one file adds exactly one aggregated value.
            aggregated_val = 0.0
            for v in val_list:
                try:
                    aggregated_val += float(v)
                except (TypeError, ValueError) as e:
                    raise TypeError(
                        f"HISTOGRAM: Value non-convertible to number. " f"Key: {key}, Value: {v}"
                    ) from e

            # Update content
            str_key = str(key)
            if str_key not in self._content:
                self._content[str_key] = []

            self._content[str_key].append(aggregated_val)

    def balance_content(self) -> None:
        """Balance each bucket to have exactly `repeat` values."""
        object.__setattr__(self, "_balanced", True)

        for bucket in self._content:
            current_len = len(self._content[bucket])
            if current_len < self._repeat:
                padding = self._repeat - current_len
                self._content[bucket].extend([0] * padding)
            elif current_len > self._repeat:
                # If we have too many, it might be due to multiple dumps?
                # For now raise error as per other types logic
                raise RuntimeError(
                    f"HISTOGRAM: Bucket '{bucket}' has more values than expected. "
                    f"Values: {self._content[bucket]}, "
                    f"Length: {current_len}, Repeat: {self._repeat}"
                )

    def reduce_duplicates(self) -> None:
        """Reduce each bucket via arithmetic mean, applying rebinning if configured."""
        object.__setattr__(self, "_reduced", True)

        # If rebinning is configured, we transform the data first
        if self._bins > 0 and self._max_range > 0:
            self._reduce_with_rebinning()
            return

        reduced = {}
        for bucket in self._content:
            values = self._content.get(bucket, [])
            if not values:
                reduced[bucket] = 0
            else:
                total = 0
                for i in range(self._repeat):
                    total += float(values[i])
                reduced[bucket] = total / self._repeat

        object.__setattr__(self, "_reduced_content", reduced)

    def _reduce_with_rebinning(self) -> None:
        """Perform reduction by rebinning each simulation's data into target uniform buckets."""
        num_bins = self._bins
        max_val = self._max_range
        bin_width = max_val / num_bins

        # Initialize target result
        target_reduced = {}
        # Pre-fill standard buckets to ensure order and existence
        for b in range(num_bins):
            key = f"{int(b * bin_width)}-{int((b + 1) * bin_width)}"
            target_reduced[key] = 0.0

        # Process each simulation
        for i in range(self._repeat):
            sim_data = {}
            for bucket, values in self._content.items():
                if i < len(values):
                    sim_data[bucket] = float(values[i])
                else:
                    sim_data[bucket] = 0.0

            # Rebin this simulation's data
            rebinned = self._rebin_simulation_data(sim_data, num_bins, max_val)

            # Accumulate into target (includes both buckets and preserved stats)
            for key, val in rebinned.items():
                if key not in target_reduced:
                    target_reduced[key] = 0.0
                target_reduced[key] += val

        # Calculate mean across simulations
        for key in target_reduced:
            target_reduced[key] /= self._repeat

        object.__setattr__(self, "_reduced_content", target_reduced)

    def _rebin_simulation_data(self, data: Dict[str, float], num_bins: int, max_val: float) -> Dict[str, float]:
        """Proportionally redistribute raw histogram data into uniform target bins."""
        bin_width = max_val / num_bins
        rebinned = {}
        for b in range(num_bins):
            key = f"{int(b * bin_width)}-{int((b + 1) * bin_width)}"
            rebinned[key] = 0.0

        for raw_key, value in data.items():
            if value == 0:
                continue

            # Parse range from key (e.g. "0-1023")
            bounds = self._parse_range_key(raw_key)
            if not bounds:
                # If it's not a range (e.g. "mean", "total"), we preserve it as is
                # It will be averaged across simulations in _reduce_with_rebinning
                rebinned[raw_key] = value
                continue

            raw_start, raw_end = bounds

            # Clip to max_val
            if raw_start >= max_val:
                continue
            actual_end = min(raw_end, max_val)
            if actual_end <= raw_start:
                continue

            # Distribute 'value' across target bins [b_start, b_end]
            # that overlap with [raw_start, actual_end]
            raw_span = raw_end - raw_start
            if raw_span <= 0:
                continue

            for b in range(num_bins):
                b_start = b * bin_width
                b_end = (b + 1) * bin_width

                # Calculate overlap
                overlap_start = max(raw_start, b_start)
                overlap_end = min(actual_end, b_end)

                if overlap_end > overlap_start:
                    overlap_width = overlap_end - overlap_start
                    # Linear redistribution assumption
                    proportion = overlap_width / raw_span
                    target_key = f"{int(b_start)}-{int(b_end)}"
                    rebinned[target_key] += value * proportion

        return rebinned

    def _parse_range_key(self, key: str) -> List[float]:
        """Extract numeric bounds from a range string (e.g., '0-1023' or '1024-2047')."""
        import re
        match = re.search(r"(\d+)-(\d+)", key)
        if match:
            return [float(match.group(1)), float(match.group(2))]
        return []

    @property
    def reduced_content(self) -> Dict[str, float]:
        balanced = object.__getattribute__(self, "_balanced")
        reduced = object.__getattribute__(self, "_reduced")
        if not balanced or not reduced:
            raise AttributeError(
                "HISTOGRAM: Cannot access reducedContent before calling "
                "balance_content() AND reduce_duplicates()"
            )
        return object.__getattribute__(self, "_reduced_content")

    # Backward compatibility
    @property
    def reducedContent(self) -> Dict[str, float]:
        return self.reduced_content

    def __str__(self) -> str:
        return f"Histogram(buckets={len(self._content)})"
