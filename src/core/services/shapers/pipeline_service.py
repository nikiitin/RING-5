"""Shaper pipeline execution.

Applies a sequence of shapers to a DataFrame. This is the single
canonical pipeline-execution engine, exposed to the UI through
``ApplicationAPI.apply_shapers`` / ``ShapersAPI.process_pipeline``.
"""

import logging
import time

import pandas as pd

from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.shapers.factory import ShaperFactory

logger = logging.getLogger(__name__)


class PipelineService:
    """Executes shaper transformation chains."""

    @staticmethod
    def process_pipeline(
        data: pd.DataFrame, pipeline_config: list[ShaperStepConfig]
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame.

        Each shaper copies its input internally, so no initial copy is made.
        Raises ``ValueError`` (wrapping the original error) if any shaper fails.
        """
        t_start = time.perf_counter()
        current_data = data

        for i, shaper_config in enumerate(pipeline_config):
            shaper_type = shaper_config.get("type")
            if not shaper_type:
                continue

            try:
                t_shaper_start = time.perf_counter()
                shaper = ShaperFactory.create_shaper(shaper_type, shaper_config)
                current_data = current_data.pipe(shaper)
                t_shaper_end = time.perf_counter()
                logger.info(
                    f"PERF: Shaper {i} ({shaper_type}) took {t_shaper_end - t_shaper_start:.4f}s"
                )
            except Exception as e:
                raise ValueError(f"Failed to apply shaper {shaper_type}: {e}") from e

        t_total = time.perf_counter() - t_start
        logger.info(f"PERF: process_pipeline total took {t_total:.4f}s for {len(data)} rows")
        return current_data
