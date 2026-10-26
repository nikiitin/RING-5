"""Declared native storage-cell frequencies with explicit omission semantics."""

import re
from typing import cast, override

from src.core.common.security_limits import MAX_INCREMENTAL_CACHE_COLUMNS
from src.core.models.distribution_geometry import DistributionGeometry, native_bucket_label
from src.core.models.native_distribution_layout import ZeroPolicy
from src.core.models.parse_failure_models import ParseDataRuntimeError, ParseDataValueError
from src.parsing.gem5.types.base import FrameStatType, entry_names, register_type

_NUMBER = r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
_COORDINATE_LABEL = re.compile(rf"{_NUMBER}(?:-{_NUMBER})?\Z")


@register_type("distribution")
class Distribution(FrameStatType):
    """Reduce actual native observations without inventing missing cells or frames."""

    # [impl->req~ring5.ingestion.distribution~1]
    __slots__ = ("_statistics", "_statistics_only", "_entries", "_zero_policy")
    required_params = ["minimum", "maximum", "bucket_size", "zero_policy"]

    def __init__(
        self,
        repeat: int = 1,
        minimum: float | None = None,
        maximum: float | None = None,
        bucket_size: float | None = None,
        zero_policy: ZeroPolicy | None = None,
        statistics: list[str] | None = None,
        statistics_only: bool = False,
    ) -> None:
        """Configure the declared grid or a summary-only extraction.

        Args:
            repeat: Expected source/dump observations, without allocating padding.
            minimum: Full-precision native grid origin; required for frequency output.
            maximum: Inclusive tracked maximum; required for frequency output.
            bucket_size: Positive native storage width; required for frequency output.
            zero_policy: Explicit missing/nozero omission declaration for frequency output.
            statistics: Literal selected summary labels, which are never zero-filled.
            statistics_only: Extract summaries without allocating or certifying a grid.

        Raises:
            TypeError: Fields have invalid types.
            ValueError: Geometry, omission policy or physical output width is invalid.
        """
        super().__init__(repeat)
        if type(statistics_only) is not bool:
            raise TypeError("Distribution statistics_only must be a boolean.")
        self._statistics_only = statistics_only
        self._statistics = entry_names(statistics, "Distribution statistics")
        self._zero_policy = None if statistics_only else zero_policy
        if len(self._statistics) > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ParseDataValueError("Distribution summaries exceed the physical column limit.")
        if statistics_only:
            self._entries = self._statistics
            return
        geometry = DistributionGeometry(
            cast(float, minimum), cast(float, maximum), cast(float, bucket_size)
        )
        if type(zero_policy) is not str or zero_policy not in {"missing", "nozero"}:
            raise ValueError("Distribution requires explicit missing or nozero policy.")
        if geometry.bucket_count + 2 + len(self._statistics) > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ParseDataValueError("Distribution exceeds the physical column limit.")
        frequencies = (
            "underflows",
            *(native_bucket_label(geometry, index) for index in range(geometry.bucket_count)),
            "overflows",
        )
        self._entries = (*frequencies, *self._statistics)
        if len(set(self._entries)) != len(self._entries):
            raise ParseDataValueError("Distribution source labels collide after native formatting.")

    @property
    def _content_entries(self) -> tuple[str, ...]:
        return self._entries

    @override
    def _prepare_frame(self, sample: dict[str, float]) -> dict[str, float]:
        if self._statistics_only:
            return {key: sample[key] for key in self._statistics if key in sample}
        for key in sample.keys() - set(self._entries):
            if _COORDINATE_LABEL.fullmatch(key):
                raise ParseDataRuntimeError(
                    f"DISTRIBUTION: Source bucket {key!r} contradicts the declared native grid."
                )
        if self._zero_policy == "nozero":
            return {
                key: sample.get(key, 0.0)
                for key in self._entries
                if key in sample or key not in self._statistics
            }
        return {key: sample[key] for key in self._entries if key in sample}

    def __str__(self) -> str:
        return f"Distribution(entries={len(self._entries)}, repeat={self.repeat})"
