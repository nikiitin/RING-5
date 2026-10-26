"""Shaper pipeline execution.

Applies a sequence of shapers to a DataFrame. This is the single
canonical pipeline-execution engine, exposed to the UI through
``ApplicationAPI.shapers.process_pipeline``.
"""

import logging
from collections.abc import Mapping, Sequence
import time

import pandas as pd

from src.core.common.distribution_metadata import (
    inspect_distribution_layouts,
    preserve_distribution_layouts,
    with_distribution_layouts,
)
from src.core.services.shapers.definition import ShaperValidationError
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.impl.derive_column import DeriveColumn
from src.core.services.shapers.impl.mean import Mean
from src.core.services.shapers.impl.normalize import Normalize
from src.core.services.shapers.impl.selector_algorithms.column_selector import ColumnSelector
from src.core.services.shapers.impl.selector_algorithms.condition_selector import ConditionSelector
from src.core.services.shapers.impl.selector_algorithms.group_cardinality_selector import (
    GroupCardinalitySelector,
)
from src.core.services.shapers.impl.selector_algorithms.group_predicate_selector import (
    GroupPredicateSelector,
)
from src.core.services.shapers.impl.selector_algorithms.item_selector import ItemSelector
from src.core.services.shapers.impl.sort import Sort
from src.core.services.shapers.impl.transformer import Transformer
from src.core.services.shapers.shaper import Shaper

logger = logging.getLogger(__name__)


_COORDINATE_PRESERVING_SHAPERS = frozenset(
    {
        ColumnSelector,
        ConditionSelector,
        GroupCardinalitySelector,
        GroupPredicateSelector,
        ItemSelector,
        Sort,
        Mean,
        Normalize,
    }
)


def _distribution_policy(
    shaper: Shaper, source: pd.DataFrame, result: pd.DataFrame
) -> pd.DataFrame:
    """Apply only reviewed built-in semantics; subclasses and plugins drop layouts."""
    if type(shaper) in _COORDINATE_PRESERVING_SHAPERS:
        return preserve_distribution_layouts(source, result)
    if type(shaper) is DeriveColumn:
        same_coordinate = (
            shaper.op == "scalar"
            and shaper.sources == [shaper.dest]
            and type(shaper.scalar) in (int, float)
            and shaper.scalar_op in {"+", "-", "*", "/"}
        )
        invalidated = () if same_coordinate else (shaper.dest,)
        return preserve_distribution_layouts(source, result, invalidated_columns=invalidated)
    if type(shaper) is Transformer:
        return preserve_distribution_layouts(source, result, invalidated_columns=(shaper.column,))
    return with_distribution_layouts(result, {})


class PipelineStepError(ValueError):
    """Report pipeline admission or execution failure with optional location.

    Attributes:
        step_index: Zero-based failing step, or None before step admission.
        shaper_type: Registered identifier when the failure belongs to a known step.
    """

    def __init__(self, message: str, *, step_index: int | None, shaper_type: str | None) -> None:
        self.step_index = step_index
        self.shaper_type = shaper_type
        super().__init__(message)


class PipelineService:
    """Executes shaper transformation chains."""

    @staticmethod
    def process_pipeline(
        data: pd.DataFrame, pipeline_config: Sequence[Mapping[str, object]]
    ) -> pd.DataFrame:
        """Apply admitted shapers with explicit Distribution metadata policies.

        Args:
            data: Input frame with optional valid current Distribution declarations.
            pipeline_config: Ordered registered shaper configurations.

        Returns:
            The final independent step output, or the admitted input for an empty pipeline.

        Raises:
            PipelineStepError: Input admission, step validation or execution fails.
                Location fields are None when no individual step is implicated.
        """
        # [impl->req~ring5.shaping.independent-pipelines~1]
        # [impl->req~ring5.quality.immutable-data~1]
        t_start = time.perf_counter()
        try:
            if not isinstance(data, pd.DataFrame):
                raise ValueError("Pipeline input must be a pandas DataFrame.")
            inspect_distribution_layouts(data)
            captured = ShaperFactory.validate_pipeline(pipeline_config)
        except ShaperValidationError as exc:
            raise PipelineStepError(
                str(exc), step_index=exc.step_index, shaper_type=exc.shaper_type
            ) from exc
        except (TypeError, ValueError) as exc:
            raise PipelineStepError(str(exc), step_index=None, shaper_type=None) from exc

        current_data = data
        for i, shaper_config in enumerate(captured):
            shaper_type = ShaperFactory.get_definition(shaper_config["type"]).identifier
            try:
                t_shaper_start = time.perf_counter()
                shaper = ShaperFactory.create_shaper(shaper_type, shaper_config)
                source = current_data
                # Reconstruction can slice before invoking nested pipelines. Clear its
                # inherited declarations before those strict admission boundaries.
                coordinate_input = type(shaper) in _COORDINATE_PRESERVING_SHAPERS or type(
                    shaper
                ) in (DeriveColumn, Transformer)
                operation_input = (
                    source if coordinate_input else with_distribution_layouts(source, {})
                )
                result = operation_input.pipe(shaper)
                if not isinstance(result, pd.DataFrame):
                    raise TypeError(
                        f"Shaper output must be a pandas DataFrame; got {type(result).__name__}."
                    )
                current_data = _distribution_policy(shaper, source, result)
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
