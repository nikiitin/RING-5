"""Standard strategy for parsing gem5 statistics files."""

from __future__ import annotations

import copy
import logging
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.parsing.gem5.types.base import StatContent, StatResult, StatType

from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.parser_protocol import ParseWorkItem
from src.parsing.gem5.types.type_mapper import TypeMapper
from src.parsing.gem5.impl.source_bindings import AccumulatorSpec, SourcePlan
from src.core.models.parsed_output_models import ParsedColumn

logger = logging.getLogger(__name__)


class SimpleStatsStrategy:
    """
    Standard parsing strategy for gem5 stats.txt files.

    This strategy iterates through all files matching the pattern,
    submits them to the parallel worker pool, and aggregates the results.
    """

    metadata_columns: tuple[ParsedColumn, ...] = ()

    # [impl->req~ring5.ingestion.simple-strategy~1]

    def get_work_items(
        self,
        files: tuple[str, ...],
        plan: SourcePlan,
    ) -> Sequence[ParseWorkItem]:
        """Compose independent work from the admitted exact selected source tuple."""
        t_map_start = time.perf_counter()
        template_map = self._map_variables(plan.accumulators)
        logger.info("PERF: Variable map creation took %.4fs", time.perf_counter() - t_map_start)
        t_copy_start = time.perf_counter()
        works = tuple(
            Gem5ParseWork(file_path, copy.deepcopy(template_map), plan) for file_path in files
        )
        logger.info(
            "PERF: Total deepcopy cost for %d files: %.4fs",
            len(files),
            time.perf_counter() - t_copy_start,
        )
        return works

    def _map_variables(
        self, specifications: Sequence[AccumulatorSpec]
    ) -> dict[str, StatType[StatContent, StatResult]]:
        """Create exactly one independent accumulator per resolved logical output."""
        # [impl->req~ring5.ingestion.output-aliases~1]
        var_map: dict[str, StatType[StatContent, StatResult]] = {}
        for spec in specifications:
            if spec.output_name in var_map:
                raise ValueError(f"Duplicate parser output name: {spec.output_name!r}.")
            var_map[spec.output_name] = TypeMapper.create_stat(spec)
        return var_map
