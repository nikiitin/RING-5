"""Vector accumulator for exact named numeric entries."""

import logging
from typing import override

from src.parsing.gem5.types.base import FrameStatType, entry_names, register_type

logger = logging.getLogger(__name__)


@register_type("vector")
class Vector(FrameStatType):
    """Average entry frames without conflating absent values and measured zero."""

    # [impl->req~ring5.ingestion.vector~1]
    __slots__ = ("_entries",)

    required_params = ["entries"]

    def __init__(self, repeat: int = 1, entries: list[str] | None = None) -> None:
        super().__init__(repeat)
        if entries is None:
            raise ValueError("VECTOR: entries parameter is required")
        self._entries = entry_names(entries, "Vector entries")

    @property
    def _content_entries(self) -> tuple[str, ...]:
        return self._entries

    @override
    def _prepare_frame(self, sample: dict[str, float]) -> dict[str, float]:
        unknown = sample.keys() - set(self._entries)
        unrequested = unknown - {"total", "mean", "samples", "stdev", "gmean"}
        if unrequested:
            logger.warning(
                "VECTOR: Skipping unknown entries %s; configured entries are %s.",
                sorted(unrequested),
                self._entries,
            )
        return {key: value for key, value in sample.items() if key in self._entries}
