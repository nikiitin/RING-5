"""
Default implementation of the ShapersAPI protocol.

Delegates to PipelineService and ShaperFactory.
"""

from collections.abc import Mapping, Sequence

import pandas as pd

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
        pipeline_config: Sequence[Mapping[str, object]],
        *,
        track_source_rows: bool = False,
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame."""
        return PipelineService.process_pipeline(
            data, pipeline_config, track_source_rows=track_source_rows
        )

    def create_shaper(
        self,
        shaper_type: str,
        params: Mapping[str, object],
    ) -> Shaper:
        """Create a shaper instance from type and parameters."""
        return ShaperFactory.create_shaper(shaper_type, params)

    def get_available_shaper_types(self) -> list[str]:
        """Return all registered shaper type identifiers."""
        return ShaperFactory.get_available_types()

    def get_shaper_display_names(self) -> dict[str, str]:
        """Return editor labels mapped to identifiers in display order."""
        return ShaperFactory.get_display_name_map()

    def validate_pipeline(
        self, pipeline: Sequence[Mapping[str, object]]
    ) -> tuple[dict[str, object], ...]:
        """Return owned current configurations after complete registry validation."""
        return ShaperFactory.validate_pipeline(pipeline)
