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

    def __init__(self, repeat: int = 1, **kwargs):
        super().__init__(repeat, **kwargs)
        # Content is a dict of {range_key: [value1, value2...]}
        object.__setattr__(self, "_content", {})

    @property
    def entries(self) -> List[str]:
        return list(object.__getattribute__(self, "_content").keys())

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

            for v in val_list:
                try:
                    float(v)
                except (TypeError, ValueError) as e:
                    raise TypeError(
                        f"HISTOGRAM: Value non-convertible to number. " f"Key: {key}, Value: {v}"
                    ) from e

            # Update content
            str_key = str(key)
            if str_key not in self._content:
                self._content[str_key] = []

            self._content[str_key].extend(val_list)

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
        """Reduce each bucket via arithmetic mean."""
        object.__setattr__(self, "_reduced", True)
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
