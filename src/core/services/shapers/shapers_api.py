"""
Shapers API Protocol -- Interface for shaper pipeline operations.

Defines the contract for executing shaper transformation chains.
"""

from typing import Protocol, runtime_checkable

import pandas as pd

from src.core.models.data_models import ShaperStepConfig
from src.core.services.shapers.shaper import Shaper


@runtime_checkable
class ShapersAPI(Protocol):
    """Protocol for shaper transformation operations."""

    def process_pipeline(
        self,
        data: pd.DataFrame,
        pipeline_config: list[ShaperStepConfig],
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame."""
        ...

    def create_shaper(
        self,
        shaper_type: str,
        params: ShaperStepConfig,
    ) -> Shaper:
        """Create a shaper instance from type and parameters."""
        ...

    def get_available_shaper_types(self) -> list[str]:
        """Return all registered shaper type identifiers."""
        ...
