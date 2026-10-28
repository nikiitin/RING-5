"""Configuration accumulator for explicit textual metadata."""

from typing import override

from src.parsing.gem5.types.base import Observation, StatType, register_type


@register_type("configuration")
class Configuration(StatType[list[str], str]):
    """Retain the first observed string, or the declared empty-input policy."""

    # [impl->req~ring5.ingestion.configuration-fallbacks~1]
    # [impl->req~ring5.ingestion.configuration~1]
    __slots__ = ("_values", "_on_empty")

    required_params = ["on_empty"]

    def __init__(self, repeat: int = 1, on_empty: str = "None") -> None:
        super().__init__(repeat)
        if not isinstance(on_empty, str):
            raise TypeError("Configuration on_empty must be text.")
        self._on_empty = on_empty
        self._values: list[str] = []

    @property
    def on_empty(self) -> str:
        """Return the declared value for absent configuration metadata."""
        return self._on_empty

    @property
    def content(self) -> list[str]:
        """Return a defensive snapshot of observed text."""
        return list(self._values)

    @override
    def _add_observation(self, value: Observation) -> None:
        if not isinstance(value, str):
            raise TypeError("CONFIGURATION: Observation must be text.")
        self._values.append(value)

    @override
    def _missing_count(self) -> int:
        return 0

    @override
    def _balance(self) -> int:
        return 0

    @override
    def _reduce(self) -> str:
        return self._values[0] if self._values else self.on_empty
