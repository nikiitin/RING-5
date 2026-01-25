"""Distribution stat type for fixed-bucket frequency distributions."""

from typing import Any, Dict, List, Optional, Set

from src.common.types.base import StatType, register_type

# Scientific Safety: Prevent memory explosion for incorrectly configured large ranges.
SAFETY_MAX_BUCKETS = 100_000


@register_type("distribution")
class Distribution(StatType):
    """
    Represents distribution statistics with defined min/max integer buckets.

    Content is stored as a dictionary mapping bucket names (underflows, overflows,
    min..max as strings) to frequency lists.

    Aggregation:
    Similar to Histograms, multiple matches within a single file (e.g., matching across
    CPU cores) are summed. This assumes the variable represents a countable frequency.

    Validation:
    - minimum and maximum must be specified and reasonable (< SAFETY_MAX_BUCKETS).
    - Keys within stats must match "underflows", "overflows", or integers in [min, max].
    - Underflows and overflows are mandatory entries in the input data.
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
            "_statistics",
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
        statistics: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Initialize Distribution type.

        Args:
            repeat: Number of simulations/dumps expected.
            minimum: The lowest expected value for standard buckets.
            maximum: The highest expected value for standard buckets.
            statistics: List of additional statistics to extract (mean, samples, etc.)
            **kwargs: Additional attributes passed to parent.

        Raises:
            ValueError: If the range exceeds SAFETY_MAX_BUCKETS.
        """
        super().__init__(repeat, **kwargs)
        object.__setattr__(self, "_minimum", int(minimum))
        object.__setattr__(self, "_maximum", int(maximum))
        object.__setattr__(self, "_statistics", statistics or [])

        num_buckets = self._maximum - self._minimum + 1
        if num_buckets > SAFETY_MAX_BUCKETS:
            raise ValueError(
                f"DISTRIBUTION: Range {self._minimum}-{self._maximum} ({num_buckets} buckets) "
                f"exceeds safety limit of {SAFETY_MAX_BUCKETS}. Check your config."
            )

        # Pre-initialize buckets for deterministic output ordering
        content = {"underflows": []}
        for i in range(self._minimum, self._maximum + 1):
            content[str(i)] = []
        content["overflows"] = []

        # Initialize configured additional statistics
        for stat in self._statistics:
            content[stat] = []

        object.__setattr__(self, "_content", content)

    @property
    def minimum(self) -> int:
        """Get the configured minimum bucket value."""
        return object.__getattribute__(self, "_minimum")

    @property
    def maximum(self) -> int:
        """Get the configured maximum bucket value."""
        return object.__getattribute__(self, "_maximum")

    @property
    def statistics(self) -> List[str]:
        """Get the list of extra statistics being extracted."""
        return object.__getattribute__(self, "_statistics")

    @property
    def entries(self) -> List[str]:
        """Return all bucket names in order for layout reconstruction."""
        return list(object.__getattribute__(self, "_content").keys())

    @property
    def content(self) -> Dict[str, List[float]]:
        """Get the raw accumulated frequency lists."""
        return object.__getattribute__(self, "_content")

    @content.setter
    def content(self, value: Dict[str, Any]) -> None:
        """
        Set and aggregate content from a dictionary.

        Handles aggregation of multiple matches from the same file.
        Fails loudly if critical buckets (under/overflows) are missing.
        """
        if not isinstance(value, dict):
            raise TypeError(f"DISTRIBUTION: Content must be dict, got {type(value).__name__}")

        keys = set(value.keys())
        stats_keys = set(self._statistics)

        # Mandatory Presence Check (Zero Hallucination)
        if "underflows" not in keys or "overflows" not in keys:
            raise TypeError(
                f"DISTRIBUTION: Missing mandatory keys 'underflows' or 'overflows'. "
                f"Found: {keys}"
            )

        if str(self._minimum) not in keys or str(self._maximum) not in keys:
            raise RuntimeError(
                f"DISTRIBUTION: Boundary buckets {self._minimum} or {self._maximum} missing. "
                "Check for format mismatch in stats file."
            )

        # Logical Set of expected buckets
        expected: Set[str] = {"underflows", "overflows"}
        expected.update(str(i) for i in range(self._minimum, self._maximum + 1))
        expected.update(stats_keys)

        for key, vals in value.items():
            str_key = str(key)

            # Strict Range Validation
            if str_key not in expected:
                try:
                    int(str_key)
                    # It's a number but out of our configured [min, max] range
                    raise RuntimeError(
                        f"DISTRIBUTION: Bucket {str_key} is out of configured range "
                        f"[{self._minimum}, {self._maximum}]."
                    )
                except ValueError:
                    # It's a non-numeric extra stat we're not tracking, skip it
                    continue

            # Accumulate values with strict numerical validation
            if isinstance(vals, list):
                val_list = vals
            else:
                val_list = [vals]

            try:
                # Scientific Integrity: Ensure all items are numeric before summing
                float_vals = [float(v) for v in val_list]
                aggregated_val = sum(float_vals)
            except (TypeError, ValueError) as e:
                raise TypeError(
                    f"DISTRIBUTION: Value error at key {str_key}. Expected numbers, got: {val_list}"
                ) from e

            self._content[str_key].append(aggregated_val)

    def balance_content(self) -> None:
        """Ensure all buckets have consistent length across repeats."""
        object.__setattr__(self, "_balanced", True)

        for bucket in self._content:
            current_len = len(self._content[bucket])
            if current_len < self._repeat:
                padding = self._repeat - current_len
                self._content[bucket].extend([0.0] * padding)
            elif current_len > self._repeat:
                raise RuntimeError(
                    f"DISTRIBUTION: Bucket '{bucket}' has more values than expected ({current_len}). "
                    f"Repeat count: {self._repeat}"
                )

    def reduce_duplicates(self) -> None:
        """Flatten repeats into a single distribution via population mean."""
        object.__setattr__(self, "_reduced", True)
        reduced = {}

        for bucket in self._content:
            values = self._content.get(bucket, [])
            if not values:
                reduced[bucket] = 0.0
            else:
                total = sum(float(v) for v in values[: self._repeat])
                reduced[bucket] = total / self._repeat

        object.__setattr__(self, "_reduced_content", reduced)

    @property
    def reduced_content(self) -> Dict[str, float]:
        """Get the final processed distribution data."""
        balanced = object.__getattribute__(self, "_balanced")
        reduced = object.__getattribute__(self, "_reduced")
        if not balanced or not reduced:
            raise AttributeError(
                "DISTRIBUTION: Process incomplete. Call balance_content() and reduce_duplicates()."
            )
        return object.__getattribute__(self, "_reduced_content")

    @property
    def reducedContent(self) -> Dict[str, float]:
        """Backward compatibility alias."""
        return self.reduced_content

    def __str__(self) -> str:
        return f"Distribution(range=[{self._minimum}, {self._maximum}], repeat={self._repeat})"
