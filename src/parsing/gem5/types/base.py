"""Registered statistic accumulators with explicit observation and lifecycle stages."""

from __future__ import annotations

import copy
import math
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from typing import ClassVar, Generic, TypeVar, final

from src.core.models.parsing_models import StatParamValue

Observation = float | str | Mapping[str, float]
StatContent = list[float] | list[str] | dict[str, list[float]]
StatResult = float | str | dict[str, float]
ContentT = TypeVar("ContentT", bound=StatContent, covariant=True)
ResultT = TypeVar("ResultT", bound=StatResult, covariant=True)


class StatType(ABC, Generic[ContentT, ResultT]):
    """Collect observations, balance missing samples, then reduce exactly once.

    Subclasses implement storage and the three protected hooks. Public lifecycle
    methods own phase transitions, so a failed operation never publishes a result.
    """

    __slots__ = ("_repeat", "_balanced", "_reduced", "_padded", "_reduced_content")
    _type_name: ClassVar[str] = "base"
    # OFT discovery binds requirements to these defining constructor options.
    required_params: ClassVar[list[str]] = []

    def __init__(self, repeat: int = 1, **kwargs: StatParamValue) -> None:
        if kwargs:
            raise TypeError(f"Unsupported {self._type_name} options: {sorted(kwargs)}")
        if type(repeat) is not int:
            raise TypeError("Statistic repeat must be an integer.")
        if repeat < 1:
            raise ValueError("Statistic repeat must be positive.")
        self._repeat = repeat
        self._balanced = False
        self._reduced = False
        self._padded = 0
        self._reduced_content: ResultT | None = None

    @property
    def repeat(self) -> int:
        """Return the expected number of source/dump observations."""
        return self._repeat

    @property
    def is_balanced(self) -> bool:
        """Whether collection has ended successfully."""
        return self._balanced

    @property
    def is_reduced(self) -> bool:
        """Whether reduction has completed successfully."""
        return self._reduced

    @property
    def padded_count(self) -> int:
        """Return the number of missing measurements filled with NaN."""
        return self._padded

    @property
    @abstractmethod
    def content(self) -> ContentT:
        """Return a defensive snapshot of collected, unreduced measurements."""

    @property
    def reduced_content(self) -> ResultT:
        """Return a defensive result after balancing and duplicate reduction.

        Raises:
            AttributeError: Either required lifecycle stage has not completed.
        """
        if not self._balanced or not self._reduced or self._reduced_content is None:
            raise AttributeError(
                f"{self._type_name.upper()}: Cannot access reduced_content before calling "
                "balance_content() AND reduce_duplicates()"
            )
        return copy.deepcopy(self._reduced_content)

    @property
    def entries(self) -> list[str] | None:
        """Return ordered output fields, or None for a point/text statistic."""
        return None

    @final
    def add_observation(self, value: Observation) -> None:
        """Append one numeric point, configuration string or numeric entry frame.

        Args:
            value: One complete source/dump observation of the concrete kind.

        Raises:
            RuntimeError: Collection has already ended.
            TypeError: The observation does not match the concrete statistic kind.
        """
        if self._balanced:
            raise RuntimeError(
                f"{self._type_name.upper()}: Cannot add observations after balancing."
            )
        self._add_observation(value)

    @abstractmethod
    def _add_observation(self, value: Observation) -> None:
        """Validate one observation completely before changing owned storage."""

    @final
    def balance_content(self) -> None:
        """End collection, padding missing measurements with NaN.

        Repeated calls are idempotent. Excess observations raise without advancing
        the lifecycle, so reduced content remains inaccessible.

        Raises:
            RuntimeError: More numeric observations were collected than expected.
        """
        if not self._balanced:
            self._padded = self._balance()
            self._balanced = True

    @abstractmethod
    def _balance(self) -> int:
        """Validate sample counts, fill missing values and return padding count."""

    @final
    def reduce_duplicates(self) -> None:
        """Reduce balanced observations, preserving missing measurements as NaN.

        Raises:
            RuntimeError: Balancing has not completed.
        """
        # [impl->req~ring5.ingestion.pattern-aggregation~1]
        if not self._balanced:
            raise RuntimeError(
                f"{self._type_name.upper()}: Call balance_content() before reduction."
            )
        if not self._reduced:
            self._reduced_content = self._reduce()
            self._reduced = True

    @abstractmethod
    def _reduce(self) -> ResultT:
        """Compute a result without changing observation storage."""

    def __str__(self) -> str:
        return f"{self._type_name}({self.content})"

    def __repr__(self) -> str:
        return str(self)


def numeric_frame(value: Observation, kind: str) -> dict[str, float]:
    """Validate and copy a numeric observation without coercing entry names/text."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{kind}: Observation must be a numeric entry mapping.")
    result: dict[str, float] = {}
    for key, measurement in value.items():
        if not isinstance(key, str):
            raise TypeError(f"{kind}: Entry names must be text.")
        if type(measurement) not in (int, float):
            raise TypeError(f"{kind}: Entry {key!r} must contain one numeric measurement.")
        result[key] = float(measurement)
    return result


def entry_names(value: list[str] | None, option: str) -> tuple[str, ...]:
    """Validate exact list options and retain an immutable owned entry schema."""
    if value is None:
        return ()
    if type(value) is not list or any(not isinstance(item, str) for item in value):
        raise TypeError(f"{option} must be a list of text entry names.")
    if len(set(value)) != len(value):
        raise ValueError(f"{option} must not contain duplicate entry names.")
    return tuple(value)


def frequency_mean(values: list[float], repeat: int) -> float:
    """Retain accurate finite sums and IEEE missing/nonfinite frequency values."""
    total = math.fsum(values) if all(math.isfinite(value) for value in values) else sum(values)
    return total / repeat


class FrameStatType(StatType[dict[str, list[float]], dict[str, float]], ABC):
    """Own one numeric mapping per source/dump and derive entry-oriented views."""

    __slots__ = ("_frames",)

    def __init__(self, repeat: int = 1) -> None:
        super().__init__(repeat)
        self._frames: list[dict[str, float]] = []

    @property
    @abstractmethod
    def _content_entries(self) -> tuple[str, ...]:
        """Return raw fields represented by the current observation store."""

    @property
    def entries(self) -> list[str]:
        """Return ordered output fields."""
        return list(self._content_entries)

    @property
    def content(self) -> dict[str, list[float]]:
        """Return raw measurements by entry, preserving per-frame missingness."""
        return {
            entry: [sample.get(entry, math.nan) for sample in self._frames]
            for entry in self._content_entries
        }

    def _add_observation(self, value: Observation) -> None:
        sample = numeric_frame(value, self._type_name.upper())
        prepared = self._prepare_frame(sample)
        # Unrequested fields do not constitute an observation of this output.
        if prepared or not sample:
            self._frames.append(prepared)

    @abstractmethod
    def _prepare_frame(self, sample: dict[str, float]) -> dict[str, float]:
        """Apply concrete entry schema rules to an already validated frame."""

    def _balance(self) -> int:
        if len(self._frames) > self.repeat:
            raise RuntimeError(
                f"{self._type_name.upper()}: More observations ({len(self._frames)}) "
                f"than expected ({self.repeat})."
            )
        padding = sum(
            self.repeat - sum(entry in sample for sample in self._frames)
            for entry in self._content_entries
        )
        self._frames.extend({} for _ in range(self.repeat - len(self._frames)))
        return padding

    def _reduce(self) -> dict[str, float]:
        return {
            entry: self._reduce_values([sample.get(entry, math.nan) for sample in self._frames])
            for entry in self._content_entries
        }

    def _reduce_values(self, values: list[float]) -> float:
        """Average one entry while retaining its concrete summation policy."""
        return sum(values) / self.repeat


class StatTypeRegistry:
    """Dispatch registered statistic constructors without alternate type routes."""

    _types: dict[str, type[StatType[StatContent, StatResult]]] = {}

    @classmethod
    def register(
        cls, type_name: str
    ) -> Callable[
        [type[StatType[StatContent, StatResult]]], type[StatType[StatContent, StatResult]]
    ]:
        """Register a class implementing the typed observation lifecycle."""

        def decorator(
            klass: type[StatType[StatContent, StatResult]],
        ) -> type[StatType[StatContent, StatResult]]:
            cls._types[type_name] = klass
            klass._type_name = type_name
            return klass

        return decorator

    @classmethod
    def create(
        cls, type_name: str, repeat: int = 1, **kwargs: StatParamValue
    ) -> StatType[StatContent, StatResult]:
        """Create a registered accumulator with its exact constructor options."""
        if type_name not in cls._types:
            raise ValueError(
                f"Unknown stat type: '{type_name}'. Available: {', '.join(cls._types)}"
            )
        return cls._types[type_name](repeat=repeat, **kwargs)

    @classmethod
    def get_types(cls) -> list[str]:
        """Return registered type names in registration order."""
        return list(cls._types)


register_type = StatTypeRegistry.register
