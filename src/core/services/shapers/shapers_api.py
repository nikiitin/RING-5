"""
Shapers API Protocol -- Interface for shaper pipeline operations.

Defines the contract for executing shaper transformation chains.
"""

from typing import Protocol, runtime_checkable

from collections.abc import Mapping, Sequence

import pandas as pd

from src.core.services.shapers.shaper import Shaper


@runtime_checkable
class ShapersAPI(Protocol):
    """Protocol for shaper transformation operations."""

    def process_pipeline(
        self,
        data: pd.DataFrame,
        pipeline_config: Sequence[Mapping[str, object]],
        *,
        track_source_rows: bool = False,
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame."""
        raise NotImplementedError

    def create_shaper(
        self,
        shaper_type: str,
        params: Mapping[str, object],
    ) -> Shaper:
        """Create a shaper instance from type and parameters."""
        raise NotImplementedError

    def get_available_shaper_types(self) -> list[str]:
        """Return all registered shaper type identifiers."""
        raise NotImplementedError

    def get_shaper_display_names(self) -> dict[str, str]:
        """Return editor labels mapped to identifiers in display order."""
        raise NotImplementedError

    def validate_pipeline(
        self, pipeline: Sequence[Mapping[str, object]]
    ) -> tuple[dict[str, object], ...]:
        """Return owned current configurations after complete registry validation."""
        raise NotImplementedError
