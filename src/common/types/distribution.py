"""Distribution stat type for bucketed frequency distributions."""

from typing import Any, Dict, List

from src.common.types.base import StatType, register_type


@register_type("distribution")
class Distribution(StatType):
    """
    Represents distribution statistics with min/max buckets.

    Content is stored as dict mapping bucket names to frequency lists.
    Buckets: underflows, min..max (as strings), overflows

    Validation:
    - minimum and maximum must be specified
    - Keys must be "underflows", "overflows", or integers in [min, max]
    - Values must be convertible to integers
    - Underflows and overflows MUST be present in content
    - Keys outside expected buckets are rejected (RuntimeError)
    """

    required_params = ["minimum", "maximum"]
    _allowed_attributes = frozenset(
        {
            "_repeat",
            "_content",
            "_reduced_content",
            "_balanced",
            "_reduced",
            "_minimum",
            "_maximum",
            "balancedContent",
            "reducedDuplicates",
            "reducedContent",
        }
    )

    def __init__(
        self,
        repeat: int = 1,
        minimum: int = 0,
        maximum: int = 100,
        statistics: List[str] = None,
        **kwargs,
    ):
        super().__init__(repeat, **kwargs)
        object.__setattr__(self, "_minimum", int(minimum))
        object.__setattr__(self, "_maximum", int(maximum))
        object.__setattr__(self, "_statistics", statistics or [])

        # Create buckets: underflows, min..max, overflows
        content = {"underflows": []}
        for i in range(self._minimum, self._maximum + 1):
            content[str(i)] = []
        content["overflows"] = []

        # Initialize configured statistics
        for stat in self._statistics:
            content[stat] = []

        object.__setattr__(self, "_content", content)

    @property
    def minimum(self) -> int:
        return object.__getattribute__(self, "_minimum")

    @property
    def maximum(self) -> int:
        return object.__getattribute__(self, "_maximum")

    @property
    def statistics(self) -> List[str]:
        return object.__getattribute__(self, "_statistics")

    @property
    def entries(self) -> List[str]:
        """Return bucket names for compatibility."""
        return list(object.__getattribute__(self, "_content").keys())

    @property
    def content(self) -> Dict[str, List[int]]:
        return object.__getattribute__(self, "_content")

    @content.setter
    def content(self, value: Dict[str, List[Any]]) -> None:
        """
        Set content from dict, extending existing buckets.

        Validates:
        - Keys are "underflows", "overflows", or integers
        - Values are integers
        - underflows and overflows MUST be present
        - All keys must be in expected bucket range
        """
        if not isinstance(value, dict):
            raise TypeError(f"DISTRIBUTION: Content must be dict, got {type(value).__name__}")

        keys = list(value.keys())

        # Stats keys allowed (Configured only)
        stats_keys = set(self._statistics)

        # Validate values are integers (or floats for stats)
        # Stats are often floats (mean, stdev). Buckets are ints.
        # We should allow floats generally if we want to support stats.
        for key, vals in value.items():
            if isinstance(vals, list):
                for v in vals:
                    try:
                        float(v)
                    except (TypeError, ValueError) as e:
                        raise TypeError(
                            f"DISTRIBUTION: Value non-convertible to number. "
                            f"Key: {key}, Value: {v}"
                        ) from e
            else:
                try:
                    float(vals)
                except (TypeError, ValueError) as e:
                     raise TypeError(
                        f"DISTRIBUTION: Value non-convertible to number. " f"Key: {key}, Value: {vals}"
                    ) from e

        if "underflows" not in keys or "overflows" not in keys:
             raise TypeError(
                f"DISTRIBUTION: Content must contain 'underflows' and 'overflows'. "
                f"Found keys: {keys}"
            )

        if str(self._minimum) not in keys or str(self._maximum) not in keys:
            raise RuntimeError(
                f"DISTRIBUTION: Minimum or maximum not in keys.\n"
                f"Expected min: {self._minimum}, max: {self._maximum}\n"
                f"Found keys: {keys}\n"
                f"Check configuration file."
            )

        expected = {"underflows", "overflows"}
        expected.update(str(i) for i in range(self._minimum, self._maximum + 1))
        expected.update(stats_keys)

        for key, vals in value.items():
            str_key = str(key)

            is_static_bucket = str_key in expected

            if not is_static_bucket:
                try:
                    int(str_key)
                    raise RuntimeError(f"DISTRIBUTION: Bucket {str_key} out of range [{self._minimum}, {self._maximum}]")
                except ValueError:
                    continue

            if str_key not in self._content:
                self._content[str_key] = []

            if isinstance(vals, list):
                # Aggregate multiple matches from a single file
                try:
                    aggregated_val = sum(float(v) for v in vals)
                except (TypeError, ValueError) as e:
                    raise TypeError(
                        f"DISTRIBUTION: Value non-convertible to number. "
                        f"Key: {str_key}, Values: {vals}"
                    ) from e
                self._content[str_key].append(aggregated_val)
            else:
                self._content[str_key].append(vals)

    def balance_content(self) -> None:
        """Balance each bucket to have exactly `repeat` values."""
        object.__setattr__(self, "_balanced", True)

        for bucket in self._content:
            current_len = len(self._content[bucket])
            if current_len < self._repeat:
                padding = self._repeat - current_len
                self._content[bucket].extend([0] * padding)
            elif current_len > self._repeat:
                raise RuntimeError(
                    f"DISTRIBUTION: Bucket '{bucket}' has more values than expected. "
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
                total = 0.0
                for i in range(self._repeat):
                     # Use float because we might have floating point stats (mean, stdev)
                     # or integer counts.
                    total += float(values[i])
                reduced[bucket] = total / self._repeat

        object.__setattr__(self, "_reduced_content", reduced)

    @property
    def reduced_content(self) -> Dict[str, float]:
        balanced = object.__getattribute__(self, "_balanced")
        reduced = object.__getattribute__(self, "_reduced")
        if not balanced or not reduced:
            raise AttributeError(
                "DISTRIBUTION: Cannot access reducedContent before calling "
                "balance_content() AND reduce_duplicates()"
            )
        return object.__getattribute__(self, "_reduced_content")

    # Backward compatibility
    @property
    def reducedContent(self) -> Dict[str, float]:
        return self.reduced_content

    def __str__(self) -> str:
        return (
            f"Distribution(min={self._minimum}, max={self._maximum}, buckets={len(self._content)})"
        )
