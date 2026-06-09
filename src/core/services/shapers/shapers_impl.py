"""
Default implementation of the ShapersAPI protocol.

Delegates to PipelineService and ShaperFactory.
"""

import pandas as pd

from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.pipeline_service import PipelineService
from src.core.services.shapers.shaper import Shaper


class DefaultShapersAPI:
    """Default implementation of ShapersAPI.

    Delegates to PipelineService and ShaperFactory.
    """

    def process_pipeline(
        self,
        data: pd.DataFrame,
        pipeline_config: list[ShaperStepConfig],
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame."""
        return PipelineService.process_pipeline(data, pipeline_config)

    def create_shaper(
        self,
        shaper_type: str,
        params: ShaperStepConfig,
    ) -> Shaper:
        """Create a shaper instance from type and parameters."""
        return ShaperFactory.create_shaper(shaper_type, params)

    def get_available_shaper_types(self) -> list[str]:
        """Return all registered shaper type identifiers."""
        return ShaperFactory.get_available_types()
