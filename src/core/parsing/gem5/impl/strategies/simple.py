"""
Simple Stats Strategy - Standard Gem5 File Parser.

Implements traditional line-by-line parsing for standard gem5 stats.txt output.
Straightforward extraction without configuration awareness, suitable for
basic statistical analysis.

Workflow:
1. discovers all matching stats files
2. Submits parallel parse jobs to worker pool
3. Aggregates results into unified DataFrame
4. Handles type conversion and validation
"""

import logging
import os
from dataclasses import replace
from typing import Any, Dict, List, Sequence

from src.core.common.utils import normalize_user_path, sanitize_glob_pattern, sanitize_log_value
from src.core.models import StatConfig
from src.core.parsing.gem5.impl.pool import ParseWorkPool
from src.core.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.core.parsing.gem5.types.type_mapper import TypeMapper

logger = logging.getLogger(__name__)


class SimpleStatsStrategy:
    """
    Standard parsing strategy for gem5 stats.txt files.

    This strategy iterates through all files matching the pattern,
    submits them to the parallel worker pool, and aggregates the results.
    It corresponds to the legacy behavior of Gem5StatsParser.
    """

    def execute(
        self, stats_path: str, stats_pattern: str, variables: Sequence[StatConfig]
    ) -> List[Dict[str, Any]]:
        """
        Execute the simple parsing workflow.
        """
        batch_work = self.get_work_items(stats_path, stats_pattern, variables)
        if not batch_work:
            return []

        # We process using the global ParseWorkPool
        pool = ParseWorkPool.get_instance()

        logger.info("PARSER: Queueing simulation data for digestion...")
        futures = pool.submit_batch_async(list(batch_work))

        logger.info("PARSER: Waiting for parallel worker completion...")
        results = [f.result() for f in futures]

        return self.post_process(results)

    def get_work_items(
        self, stats_path: str, stats_pattern: str, variables: Sequence[StatConfig]
    ) -> Sequence[Gem5ParseWork]:
        """Return a list of work items for parallel execution."""
        files = self._get_files(stats_path, stats_pattern)
        if not files:
            logger.warning(
                "PARSER: No files found matching '%s' in %s",
                sanitize_log_value(stats_pattern),
                sanitize_log_value(stats_path),
            )
            return []

        variable_map = self._map_variables(variables)

        return [Gem5ParseWork(str(file_path), variable_map) for file_path in files]

    def post_process(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform any post-processing on aggregated results."""
        return results

    def _get_files(self, stats_path: str, stats_pattern: str) -> List[str]:
        """Find all stats files matching the pattern in the target path."""
        # Path is already validated/resolved by ParseService before reaching strategy
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

    def _map_variables(self, variables: Sequence[StatConfig]) -> Dict[str, Any]:
        """
        Convert configuration models into typed Stat objects.

        Handles multi-ID mapping (e.g., regex variables matching multiple controllers).
        """
        var_map: Dict[str, Any] = {}

        for var in variables:
            name = var.name
            # Validation logic kept from original parser
            if not name:
                raise ValueError("PARSER: Variable config missing 'name'.")

            if name in var_map:
                raise RuntimeError(f"PARSER: Duplicate variable definition: {name}")

            # Handle multi-ID mapping (Variables matched via regex scanning)
            parsed_ids = var.params.get("parsed_ids", [])

            if parsed_ids:
                # Update repeat count for the logical variable (Spatial aggregation)
                stat_obj = TypeMapper.create_stat(replace(var, repeat=len(parsed_ids)))
            else:
                stat_obj = TypeMapper.create_stat(var)

            var_map[name] = stat_obj

            for pid in parsed_ids:
                if pid != name:
                    var_map[pid] = stat_obj

        return var_map
