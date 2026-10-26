"""Scalar accumulator for numeric point measurements."""

import math
from typing import cast, override

from src.core.models.parse_failure_models import ParseDataRuntimeError
from src.parsing.gem5.types.base import Observation, StatType, population_mean, register_type


@register_type("scalar")
class Scalar(StatType[list[float], float]):
    """Average expected point observations while preserving missing values."""

    # [impl->req~ring5.ingestion.scalar~1]
    __slots__ = ("_values",)

    def __init__(self, repeat: int = 1) -> None:
        super().__init__(repeat)
        self._values: list[float] = []

    @property
    def content(self) -> list[float]:
        """Return a defensive snapshot of numeric observations."""
        return list(self._values)

    @override
    def _add_observation(self, value: Observation) -> None:
        if type(value) not in (int, float):
            raise TypeError("SCALAR: Observation must be one numeric measurement.")
        self._values.append(float(cast(float, value)))

    @override
    def _missing_count(self) -> int:
        return max(self.repeat - len(self._values), 0)

    @override
    def _balance(self) -> int:
        if len(self._values) > self.repeat:
            raise ParseDataRuntimeError(
                f"SCALAR: More values ({len(self._values)}) than expected ({self.repeat})."
            )
        return self.missing_measurement_count

    @override
    def _reduce(self) -> float:
        if len(self._values) < self.repeat:
            return math.nan
        return population_mean(self._values)
