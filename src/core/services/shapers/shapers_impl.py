"""
Default implementation of the ShapersAPI protocol.

Delegates to PipelineService and ShaperFactory.
"""

from pathlib import Path

import pandas as pd

from src.core.models.data_models import PipelineData, PipelineStep, ShaperStepConfig
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.pipeline_service import PipelineService
from src.core.services.shapers.shaper import Shaper


class DefaultShapersAPI:
    """Default implementation of ShapersAPI.

    Delegates to PipelineService and ShaperFactory.
    """

    def __init__(self, pipelines_dir: Path) -> None:
        """Initialize with the pipelines storage directory.

        Args:
            pipelines_dir: Path to directory where pipeline JSONs are stored.
        """
        self._pipeline_service = PipelineService(pipelines_dir)

    def list_pipelines(self) -> list[str]:
        """List all available saved pipelines."""
        return self._pipeline_service.list_pipelines()

    def save_pipeline(
        self,
        name: str,
        pipeline_config: list[PipelineStep],
        description: str = "",
    ) -> None:
        """Save a pipeline configuration to disk."""
        self._pipeline_service.save_pipeline(name, pipeline_config, description)

    def load_pipeline(self, name: str) -> PipelineData:
        """Load a pipeline configuration by name."""
        return self._pipeline_service.load_pipeline(name)

    def delete_pipeline(self, name: str) -> None:
        """Delete a pipeline configuration."""
        self._pipeline_service.delete_pipeline(name)

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
