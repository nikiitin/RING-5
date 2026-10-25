"""Standard strategy for parsing gem5 statistics files."""

from __future__ import annotations

import copy
import logging
import os
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.parsing.gem5.types.base import StatContent, StatResult, StatType

from src.core.common.security_limits import (
    MAX_PARSE_FILES,
    MAX_PARSE_FILE_BYTES,
    MAX_PARSE_MATRIX_CELLS,
    MAX_PARSE_TOTAL_BYTES,
    MAX_PARSE_VARIABLES,
)
from src.core.common.utils import sanitize_log_value
from src.parsing.framework.file_discovery import find_stats_files
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.gem5.impl.strategies.file_parser_strategy import INTERNAL_SIM_PATH_KEY
from src.parsing.gem5.types.type_mapper import TypeMapper
from src.parsing.gem5.impl.source_bindings import AccumulatorSpec, SourcePlan

logger = logging.getLogger(__name__)


class SimpleStatsStrategy:
    """
    Standard parsing strategy for gem5 stats.txt files.

    This strategy iterates through all files matching the pattern,
    submits them to the parallel worker pool, and aggregates the results.
    """

    # [impl->req~ring5.ingestion.simple-strategy~1]

    def get_work_items(
        self,
        stats_path: str,
        stats_pattern: str,
        plan: SourcePlan,
        *,
        file_paths: list[str] | None = None,
    ) -> Sequence[Gem5ParseWork]:
        """Return a list of work items for parallel execution.

        Each work item receives its own independent copy of the variable
        map so that concurrent threads cannot corrupt shared mutable
        ``StatType`` objects.
        """
        t_start = time.perf_counter()
        if file_paths is None:
            files = self._get_files(stats_path, stats_pattern)
        else:
            files = file_paths
            self._validate_files(files, stats_path)
        t_files = time.perf_counter()
        logger.info(f"PERF: File discovery/selection took {t_files - t_start:.4f}s")

        # Build one template map, then deep-copy per file so that each
        # thread-based worker operates on its own mutable StatType set.
        t_map_start = time.perf_counter()
        template_map: dict[str, StatType[StatContent, StatResult]] = self._map_variables(
            plan.accumulators
        )
        if len(template_map) > MAX_PARSE_VARIABLES:
            raise RuntimeError(
                f"PARSER: {len(template_map)} logical variables and aliases exceed the "
                f"{MAX_PARSE_VARIABLES}-variable limit."
            )
        matrix_cells = len(files) * plan.workload_width
        if matrix_cells > MAX_PARSE_MATRIX_CELLS:
            raise RuntimeError(
                f"PARSER: workload requires {matrix_cells} file-variable cells; "
                f"the limit is {MAX_PARSE_MATRIX_CELLS}. Reduce the file set or variables."
            )
        t_map_end = time.perf_counter()
        logger.info(f"PERF: Variable map creation took {t_map_end - t_map_start:.4f}s")

        t_copy_start = time.perf_counter()
        works = [
            Gem5ParseWork(str(file_path), copy.deepcopy(template_map), plan) for file_path in files
        ]
        t_copy_end = time.perf_counter()
        logger.info(
            f"PERF: Total deepcopy cost for {len(files)} files: {t_copy_end - t_copy_start:.4f}s"
        )

        return works

    def post_process(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove worker-only provenance before writing the public CSV."""
        processed: list[dict[str, Any]] = []
        for result in results:
            public_result = dict(result)
            public_result.pop(INTERNAL_SIM_PATH_KEY, None)
            processed.append(public_result)
        return processed

    def _get_files(self, stats_path: str, stats_pattern: str) -> list[str]:
        """Find all stats files matching the pattern in the target path.

        Raises:
            FileNotFoundError: When no file matches — same contract as the
                scan path. Returning an empty work list instead would let a
                whole parse run "succeed" while producing nothing.
        """
        files = find_stats_files(stats_path, stats_pattern, raise_if_empty=True)
        self._validate_files(files, stats_path)
        return files

    @staticmethod
    def _validate_files(files: Sequence[str], stats_path: str) -> None:
        """Enforce parser byte and file-count limits for the selected work set."""
        if len(files) > MAX_PARSE_FILES:
            raise RuntimeError(
                f"PARSER: {len(files)} files exceed the {MAX_PARSE_FILES}-file parse limit."
            )

        total_bytes = 0
        for file_path in files:
            file_size = os.path.getsize(file_path)
            if file_size > MAX_PARSE_FILE_BYTES:
                raise RuntimeError(
                    f"PARSER: input exceeds the {MAX_PARSE_FILE_BYTES // (1024 * 1024)} MiB "
                    f"per-file limit: {file_path}"
                )
            total_bytes += file_size
            if total_bytes > MAX_PARSE_TOTAL_BYTES:
                raise RuntimeError(
                    f"PARSER: selected inputs exceed the "
                    f"{MAX_PARSE_TOTAL_BYTES // (1024 * 1024 * 1024)} GiB aggregate limit."
                )
        logger.info(
            "PARSER: Found %d candidate files in %s",
            len(files),
            sanitize_log_value(stats_path),
        )

    def _map_variables(
        self, specifications: Sequence[AccumulatorSpec]
    ) -> dict[str, StatType[StatContent, StatResult]]:
        """Create exactly one independent accumulator per resolved logical output."""
        # [impl->req~ring5.ingestion.output-aliases~1]
        var_map: dict[str, StatType[StatContent, StatResult]] = {}
        for spec in specifications:
            if spec.output_name in var_map:
                raise ValueError(f"Duplicate parser output name: {spec.output_name!r}.")
            if spec.output_name == INTERNAL_SIM_PATH_KEY:
                raise ValueError("The parser output name is reserved for provenance.")
            var_map[spec.output_name] = TypeMapper.create_stat(spec)
        return var_map
