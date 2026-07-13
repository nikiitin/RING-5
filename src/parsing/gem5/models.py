"""
Gem5-specific scanned variable model.

Extends the base ``ScannedVariable`` with gem5-specific metadata
(``minimum`` / ``maximum``) used by distribution and histogram types
for bucket range configuration.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.models.data_models import ScannedVariableDict
from src.core.models.parsing_models import ScannedVariable


@dataclass(frozen=True)
class Gem5ScannedVariable(ScannedVariable):
    """
    Gem5-specific scanned variable with distribution/histogram metadata.

    Adds ``minimum`` and ``maximum`` fields that are populated during
    deep scanning of distribution and histogram stats.  These values
    define the natural data range and are used by the UI to pre-fill
    bucket range inputs.
    """

    minimum: float | None = None
    maximum: float | None = None

    def to_dict(self) -> ScannedVariableDict:
        """Serialize to dictionary, including gem5-specific fields."""
        result = super().to_dict()
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        return result

    @classmethod
    def from_dict(cls, data: ScannedVariableDict) -> Gem5ScannedVariable:
        """Reconstruct Gem5ScannedVariable from dictionary."""
        return cls(
            name=data["name"],
            type=data["type"],
            entries=data.get("entries", []),
            minimum=data.get("minimum"),
            maximum=data.get("maximum"),
            pattern_indices=data.get("pattern_indices"),
        )
