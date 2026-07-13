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

from src.core.common.utils import sanitize_log_value
from src.core.models import StatConfig
from src.parsing.framework.file_discovery import find_stats_files
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.gem5.types.type_mapper import TypeMapper

logger = logging.getLogger(__name__)


def _max_var_repeat() -> int:
    """Per-variable cap on regex-expanded instances (``repeat``).

    A regex variable can match thousands of concrete instances (e.g. an NxN
    network traffic matrix → repeat in the thousands), which blows up memory when
    parsed across many files. Variables above this cap are skipped with a loud log
    rather than risking an OOM. Override with ``RING5_MAX_VAR_REPEAT``; ``0`` disables
    the cap (parse everything).
    """
    raw = os.environ.get("RING5_MAX_VAR_REPEAT")
    if raw is not None:
        try:
            n = int(raw)
            if n >= 0:
                return n
            logger.warning("RING5_MAX_VAR_REPEAT=%r is negative; using default", raw)
        except ValueError:
            logger.warning("RING5_MAX_VAR_REPEAT=%r is not an integer; using default", raw)
    return 1024


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
        """Find all stats files matching the pattern in the target path.

        Raises:
            FileNotFoundError: When no file matches — same contract as the
                scan path. Returning an empty work list instead would let a
                whole parse run "succeed" while producing nothing.
        """
        files = find_stats_files(stats_path, stats_pattern, raise_if_empty=True)
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
                n_ids = len(parsed_ids)
                cap = _max_var_repeat()
                if cap and n_ids > cap:
                    logger.error(
                        "PARSER: skipping variable '%s' — repeat=%d exceeds the cap of %d "
                        "(would risk excessive memory). Raise RING5_MAX_VAR_REPEAT (or set 0 "
                        "to disable) to include it.",
                        name,
                        n_ids,
                        cap,
                    )
                    continue
                # Update repeat count for the logical variable (Spatial aggregation)
                stat_obj = TypeMapper.create_stat(replace(var, repeat=n_ids))
                if n_ids > 50:
                    logger.warning(
                        "PARSER: Variable '%s' has repeat=%d (from %d parsed_ids) — "
                        "this may increase memory usage significantly.",
                        name,
                        n_ids,
                        n_ids,
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
