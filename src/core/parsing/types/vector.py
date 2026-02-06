"""
Vector Type - Named Array Statistics Parser.

Handles vector statistics from gem5, which contain named entries with
associated values. Examples: per-CPU statistics, per-core metrics, regional data.

Parses vector output format and validates entries against configured schema.
Implements type registry pattern for stat type dispatch.
"""

import logging
from typing import Any, Dict, List, Optional

from src.core.parsing.types.base import StatType, register_type

logger = logging.getLogger(__name__)


@register_type("vector")
class Vector(StatType):
    """
    Represents vector statistics with named entries (e.g., cycles per region).

    Content is stored as dict mapping entry names to lists of values.

    Validation:
    - Entries must be specified at construction
    - Keys in content must be convertible to strings
    - Values must be convertible to int/float
    - Warns if content has entries not in configured entries (skips them)
    - Raises RuntimeError if more values than expected after balancing
    """

    required_params = ["entries"]
    _allowed_attributes = frozenset(
        {
            "_repeat",
            "_content",
            "_reduced_content",
            "_balanced",
            "_reduced",
            "_entries",
            "balancedContent",
            "reducedDuplicates",
            "reducedContent",
        }
    )

    def __init__(self, repeat: int = 1, entries: Optional[List[str]] = None, **kwargs: Any) -> None:
        super().__init__(repeat, **kwargs)
        if entries is None:
            raise ValueError("VECTOR: entries parameter is required")

        # Handle comma-separated string format
        if isinstance(entries, str):
            entries = [e.strip() for e in entries.split(",")]

        object.__setattr__(self, "_entries", list(entries))
        object.__setattr__(self, "_content", {e: [] for e in self._entries})

    @property
    def entries(self) -> List[str]:
        entries_list: List[str] = object.__getattribute__(self, "_entries")
        return entries_list

    @property
    def content(self) -> Dict[str, List[Any]]:
        content_dict: Dict[str, List[Any]] = object.__getattribute__(self, "_content")
        return content_dict

    @content.setter
    def content(self, value: Dict[str, List[Any]]) -> None:
        """
        Set content from dict, extending existing entries.

        Validates:
        - Keys can be converted to strings
        - Values can be converted to int/float
        - Warns and skips entries not in configured list
        """
        if not isinstance(value, dict):
            raise TypeError(f"VECTOR: Content must be dict, got {type(value).__name__}")

        # Validate keys can be strings
        try:
            list(map(str, value.keys()))
        except Exception as e:
            raise TypeError(
                f"VECTOR: Unable to convert keys to strings. "
                f"Value: {value}, Type: {type(value).__name__}"
            ) from e

        # Validate values are numeric
        for key, vals in value.items():
            if isinstance(vals, list):
                for v in vals:
                    try:
                        int(v)
                    except (TypeError, ValueError):
                        try:
                            float(v)
                        except (TypeError, ValueError) as e:
                            raise TypeError(
                                f"VECTOR: Value non-convertible to int or float. "
                                f"Key: {key}, Value: {v}"
                            ) from e

        # Check for unknown entries - warn but continue
        found_keys = set(str(k) for k in value.keys())
        expected_keys = set(self._entries)
        unknown_keys = found_keys - expected_keys

        # Silent skip for standard statistics which might be present but not requested
        standard_stats = {"total", "mean", "samples", "stdev", "gmean"}
        unknown_keys_to_warn = unknown_keys - standard_stats

        if unknown_keys_to_warn:
            logger.warning(
                "VECTOR: Entries in file are not the same as configured entries: "
                "Expected: %s, Found: %s. Skipping unknown entries: %s",
                self._entries,
                list(value.keys()),
                unknown_keys_to_warn,
            )

        # Only keep entries that are in our configured list
        for key, vals in value.items():
            str_key = str(key)
            if str_key in self._entries:
                if isinstance(vals, list):
                    # Sum multiple matches from a single file (aggregation)
                    try:
                        aggregated_val = sum(float(v) for v in vals)
                    except (TypeError, ValueError) as e:
                        raise TypeError(
                            f"VECTOR: Value non-convertible to number. "
                            f"Key: {key}, Values: {vals}"
                        ) from e
                    self._content[str_key].append(aggregated_val)
                else:
                    self._content[str_key].append(vals)

    def balance_content(self) -> None:
        """Balance each entry to have exactly `repeat` values."""
        object.__setattr__(self, "_balanced", True)

        for entry in self._entries:
            current_len = len(self._content.get(entry, []))
            if current_len < self._repeat:
                padding = self._repeat - current_len
                self._content[entry].extend([0] * padding)
            elif current_len > self._repeat:
                raise RuntimeError(
                    f"VECTOR: Entry '{entry}' has more values than expected. "
                    f"Values: {self._content[entry]}, "
                    f"Length: {current_len}, Repeat: {self._repeat}"
                )

    def reduce_duplicates(self) -> None:
        """Reduce each entry via arithmetic mean."""
        object.__setattr__(self, "_reduced", True)
        reduced = {}

        for entry in self._entries:
            values = self._content.get(entry, [])
            if not values:
                reduced[entry] = 0
            else:
                total = 0
                for i in range(self._repeat):
                    total += int(values[i])
                reduced[entry] = total / self._repeat

        object.__setattr__(self, "_reduced_content", reduced)

    @property
    def reduced_content(self) -> Dict[str, float]:
        balanced = object.__getattribute__(self, "_balanced")
        reduced = object.__getattribute__(self, "_reduced")
        if not balanced or not reduced:
            raise AttributeError(
                "VECTOR: Cannot access reducedContent before calling "
                "balance_content() AND reduce_duplicates()"
            )
        reduced_dict: Dict[str, float] = object.__getattribute__(self, "_reduced_content")
        return reduced_dict

    # Backward compatibility
    @property
    def reducedContent(self) -> Dict[str, float]:
        return self.reduced_content

    def __str__(self) -> str:
        return f"Vector({self._content})"
