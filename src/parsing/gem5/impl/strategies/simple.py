"""
Simple Stats Strategy - Standard Gem5 File Parser.

Implements traditional line-by-line parsing for standard gem5 stats.txt output.
Straightforward extraction without configuration awareness, suitable for
basic statistical analysis.

Responsibilities:
1. get_work_items(): discover matching stats files and build per-file
   ``Gem5ParseWork`` units (each with its own deep-copied variable map)
2. post_process(): aggregate the pool's results

The worker pool that runs the work units is owned by ``Gem5Parser``.
"""

from __future__ import annotations

import copy
import logging
import os
import time
from collections.abc import Sequence
from dataclasses import replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.parsing.gem5.types.base import StatType

from src.core.common.utils import (
    normalize_user_path,
    sanitize_glob_pattern,
    sanitize_log_value,
)
from src.core.models import StatConfig
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.gem5.types.type_mapper import TypeMapper

logger = logging.getLogger(__name__)


class SimpleStatsStrategy:
    """
    Standard parsing strategy for gem5 stats.txt files.

    This strategy iterates through all files matching the pattern,
    submits them to the parallel worker pool, and aggregates the results.
    It corresponds to the legacy behavior of Gem5StatsParser.
    """

    def get_work_items(
        self, stats_path: str, stats_pattern: str, variables: Sequence[StatConfig]
    ) -> Sequence[Gem5ParseWork]:
        """Return a list of work items for parallel execution.

        Each work item receives its own independent copy of the variable
        map so that concurrent threads cannot corrupt shared mutable
        ``StatType`` objects.
        """
        t_start = time.perf_counter()
        files = self._get_files(stats_path, stats_pattern)
        t_files = time.perf_counter()
        logger.info(f"PERF: File discovery (glob) took {t_files - t_start:.4f}s")

        if not files:
            logger.warning(
                "PARSER: No files found matching '%s' in %s",
                sanitize_log_value(stats_pattern),
                sanitize_log_value(stats_path),
            )
            return []

        # Build one template map, then deep-copy per file so that each
        # thread-based worker operates on its own mutable StatType set.
        t_map_start = time.perf_counter()
        template_map: dict[str, StatType] = self._map_variables(variables)
        t_map_end = time.perf_counter()
        logger.info(f"PERF: Variable map creation took {t_map_end - t_map_start:.4f}s")

        t_copy_start = time.perf_counter()
        works = [Gem5ParseWork(str(file_path), copy.deepcopy(template_map)) for file_path in files]
        t_copy_end = time.perf_counter()
        logger.info(
            f"PERF: Total deepcopy cost for {len(files)} files: {t_copy_end - t_copy_start:.4f}s"
        )

        return works

    def post_process(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Perform any post-processing on aggregated results."""
        return results

    def _get_files(self, stats_path: str, stats_pattern: str) -> list[str]:
        """Find all stats files matching the pattern in the target path."""
        # Path is already validated/resolved by Gem5Parser before reaching strategy
        safe_path: str = os.path.normpath(stats_path) if stats_path else "."
        base = normalize_user_path(safe_path)
        safe_pattern = sanitize_glob_pattern(stats_pattern)
        pattern = f"**/{safe_pattern}"
        files = [str(f) for f in base.glob(pattern)]
        logger.info(
            "PARSER: Found %d candidate files in %s",
            len(files),
            sanitize_log_value(stats_path),
        )
        return files

    def _map_variables(self, variables: Sequence[StatConfig]) -> dict[str, StatType]:
        """
        Convert configuration models into typed Stat objects.

        Handles multi-ID mapping (e.g., regex variables matching multiple controllers).
        """
        var_map: dict[str, StatType] = {}

        for var in variables:
            name = var.name
            # Validation logic kept from original parser
            if not name:
                raise ValueError("PARSER: Variable config missing 'name'.")

            if name in var_map:
                raise RuntimeError(f"PARSER: Duplicate variable definition: {name}")

            # Handle multi-ID mapping (Variables matched via regex scanning)
            parsed_ids_raw = var.params.get("parsed_ids", [])
            parsed_ids: list[str] = parsed_ids_raw if isinstance(parsed_ids_raw, list) else []

            if parsed_ids:
                # Update repeat count for the logical variable (Spatial aggregation)
                stat_obj = TypeMapper.create_stat(replace(var, repeat=len(parsed_ids)))
                if len(parsed_ids) > 50:
                    logger.warning(
                        "PARSER: Variable '%s' has repeat=%d (from %d parsed_ids) — "
                        "this may increase memory usage significantly.",
                        name,
                        len(parsed_ids),
                        len(parsed_ids),
                    )
            else:
                stat_obj = TypeMapper.create_stat(var)

            var_map[name] = stat_obj

            # Each alias gets a shallow copy to share _content with the parent
            # variable — this is intentional so that parsed values from aliases
            # flow to the parent for reduction. Deep copy happens at line 115
            # (per-file isolation), not here (intra-template sharing).
            for pid in parsed_ids:
                if pid != name:
                    var_map[pid] = copy.copy(stat_obj)

        return var_map
