"""Distribution accumulator for fixed integer buckets and explicit boundaries."""

import math
from typing import override

from src.parsing.gem5.types.base import FrameStatType, entry_names, frequency_mean, register_type

SAFETY_MAX_BUCKETS = 100_000


@register_type("distribution")
class Distribution(FrameStatType):
    """Average complete frequency frames and retain missing observations as NaN."""

    # [impl->req~ring5.ingestion.distribution~1]
    __slots__ = ("_minimum", "_maximum", "_statistics", "_statistics_only", "_entries")

    required_params = ["minimum", "maximum"]

    def __init__(
        self,
        repeat: int = 1,
        minimum: int = 0,
        maximum: int = 100,
        statistics: list[str] | None = None,
        statistics_only: bool = False,
    ) -> None:
        super().__init__(repeat)
        if type(minimum) is not int or type(maximum) is not int:
            raise TypeError("Distribution bounds must be integers.")
        if minimum > maximum:
            raise ValueError("Distribution minimum must not exceed maximum.")
        if type(statistics_only) is not bool:
            raise TypeError("Distribution statistics_only must be a boolean.")
        self._statistics_only = statistics_only
        self._minimum = 0 if statistics_only else minimum
        self._maximum = 0 if statistics_only else maximum
        self._statistics = entry_names(statistics, "Distribution statistics")
        num_buckets = self._maximum - self._minimum + 1
        if num_buckets > SAFETY_MAX_BUCKETS:
            raise ValueError(
                f"DISTRIBUTION: Range {self._minimum}-{self._maximum} ({num_buckets} buckets) "
                f"exceeds safety limit of {SAFETY_MAX_BUCKETS}. Check your config."
            )
        buckets = (
            ()
            if statistics_only
            else (
                "underflows",
                *(str(i) for i in range(self._minimum, self._maximum + 1)),
                "overflows",
            )
        )
        self._entries = tuple(dict.fromkeys((*buckets, *self._statistics)))

    @property
    def minimum(self) -> int:
        """Return the configured lower bucket bound."""
        return self._minimum

    @property
    def maximum(self) -> int:
        """Return the configured upper bucket bound."""
        return self._maximum

    @property
    def statistics(self) -> list[str]:
        """Return selected summary names."""
        return list(self._statistics)

    @property
    def _content_entries(self) -> tuple[str, ...]:
        return self._entries

    @override
    def _prepare_frame(self, sample: dict[str, float]) -> dict[str, float]:
        if not self._statistics_only:
            if not {"underflows", "overflows"} <= sample.keys():
                raise TypeError("DISTRIBUTION: Missing mandatory keys 'underflows' or 'overflows'.")
            if not {str(self.minimum), str(self.maximum)} <= sample.keys():
                raise RuntimeError(
                    f"DISTRIBUTION: Boundary buckets {self.minimum} or {self.maximum} missing. "
                    "Check for format mismatch in stats file."
                )
            for key in sample.keys() - set(self._entries):
                try:
                    int(key)
                except ValueError:
                    continue
                raise RuntimeError(
                    f"DISTRIBUTION: Bucket {key} is out of configured range "
                    f"[{self.minimum}, {self.maximum}]."
                )
        return {
            key: sample.get(key, math.nan if key in self._statistics else 0.0)
            for key in self._entries
        }

    @override
    def _reduce_values(self, values: list[float]) -> float:
        return frequency_mean(values, self.repeat)

    def __str__(self) -> str:
        return f"Distribution(range=[{self.minimum}, {self.maximum}], repeat={self.repeat})"
