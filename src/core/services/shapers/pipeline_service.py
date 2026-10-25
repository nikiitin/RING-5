"""Shaper pipeline execution.

Applies a sequence of shapers to a DataFrame. This is the single
canonical pipeline-execution engine, exposed to the UI through
``ApplicationAPI.shapers.process_pipeline``.
"""

import logging
from collections.abc import Mapping, Sequence
import time

import pandas as pd

from src.core.services.shapers.definition import ShaperValidationError
from src.core.services.shapers.factory import ShaperFactory

logger = logging.getLogger(__name__)


class PipelineStepError(ValueError):
    """A pipeline step failed — carries the step location as data.

    A ``ValueError`` subclass so existing callers keep working; consumers
    that need to point at the failing step (the public ring5 API, the UI)
    read ``step_index``/``shaper_type`` instead of parsing the message.
    """

    def __init__(self, message: str, *, step_index: int, shaper_type: str | None) -> None:
        self.step_index = step_index
        self.shaper_type = shaper_type
        super().__init__(message)


class PipelineService:
    """Executes shaper transformation chains."""

    @staticmethod
    def process_pipeline(
        data: pd.DataFrame, pipeline_config: Sequence[Mapping[str, object]]
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame.

        Each shaper copies its input internally, so no initial copy is made.
        Raises ``PipelineStepError`` (a ``ValueError`` carrying
        ``step_index``/``shaper_type``) if any step is malformed or fails.
        """
        # [impl->req~ring5.shaping.independent-pipelines~1]
        # [impl->req~ring5.quality.immutable-data~1]
        t_start = time.perf_counter()
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Pipeline input must be a pandas DataFrame.")
        current_data = data

        try:
            captured = ShaperFactory.validate_pipeline(pipeline_config)
        except ShaperValidationError as exc:
            raise PipelineStepError(
                str(exc), step_index=exc.step_index, shaper_type=exc.shaper_type
            ) from exc

        for i, shaper_config in enumerate(captured):
            shaper_type = ShaperFactory.get_definition(shaper_config["type"]).identifier
            try:
                t_shaper_start = time.perf_counter()
                shaper = ShaperFactory.create_shaper(shaper_type, shaper_config)
                current_data = current_data.pipe(shaper)
                t_shaper_end = time.perf_counter()
                logger.info(
                    f"PERF: Shaper {i} ({shaper_type}) took {t_shaper_end - t_shaper_start:.4f}s"
                )
            except Exception as e:
                raise PipelineStepError(
                    f"Failed to apply shaper {shaper_type} (step {i}): {e}",
                    step_index=i,
                    shaper_type=str(shaper_type),
                ) from e

        t_total = time.perf_counter() - t_start
        logger.info(f"PERF: process_pipeline total took {t_total:.4f}s for {len(data)} rows")
        return current_data
