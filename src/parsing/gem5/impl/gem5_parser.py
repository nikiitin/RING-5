"""
Module: src.parsing/parse_service.py

Purpose:
    Orchestrates gem5 stats file parsing workflow using persistent Perl worker pool.
    Coordinates parallel parsing across multiple stats files and aggregates results
    into a single consolidated CSV file.

Responsibilities:
    - Submit async parsing jobs to worker pool
    - Manage variable-to-file mapping for parallel processing
    - Aggregate parsed results into final CSV
    - Handle parse cancellation and cleanup
    - Maintain variable order consistency

Dependencies:
    - PerlWorkerPool: For persistent Perl process management (54x speedup)
    - ParseWorkPool: For parallel work distribution
    - TypeMapper: For variable type mapping and validation
    - Gem5ParseWork: For individual file parsing logic

Usage Example:
    >>> from src.parsing.parse_service import ParseService
    >>>
    >>> # Define variables to parse
    >>> variables = [
    ...     {"name": "system.cpu.ipc", "type": "scalar", "params": {}},
    ...     {"name": "system.cpu.numCycles", "type": "scalar", "params": {}}
    ... ]
    >>>
    >>> # Submit async parsing (returns futures)
    >>> futures = ParseService.submit_parse_async(
    ...     stats_path="/path/to/gem5/output",
    ...     stats_pattern="stats.txt",
    ...     variables=variables,
    ...     output_dir="/tmp/parsed"
    ... )
    >>>
    >>> # Wait for completion and get results
    >>> results = [f.result() for f in futures]
    >>>
    >>> # Aggregate into final CSV
    >>> csv_path = Gem5Parser.construct_final_csv("/tmp/parsed", results)

Design Patterns:
    - Service Layer Pattern: Coordinates parsing workflow
    - Async/Future Pattern: Non-blocking parallel execution
    - Worker Pool Pattern: Reuses persistent Perl processes
    - Facade Pattern: Simplifies complex parsing pipeline

Performance Characteristics:
    - Worker Pool: 54x speedup vs subprocess (30-50ms → <1ms per file)
    - Parallelism: Concurrent parsing across multiple stats files
    - Scalability: O(n/p) where n=files, p=pool_size
    - Typical: 20 files in ~0.01s (vs 0.5s with subprocess)

Error Handling:
    - Raises FileNotFoundError if stats_path doesn't exist
    - Raises RuntimeError for worker pool failures
    - Logs warnings for parse errors (continues with partial results)
    - Cancellation: Terminates pending work gracefully

Thread Safety:
    - Worker pool is thread-safe (uses locks internally)
    - Variable names are encapsulated in ParseBatchResult, no shared mutable
      class-level state. Multiple concurrent parse batches are fully isolated.

Testing:
    - Unit tests: tests/unit/test_parse_service.py
    - Integration tests: tests/integration/test_parser_integration.py
    - Performance tests: tests/performance/test_worker_pool_performance.py

Version: 2.0.0
Last Modified: 2026-01-27
"""

import csv
import logging
import os
import re
from dataclasses import replace
from typing import Any

from src.core.common.utils import normalize_user_path
from src.core.models import ParseBatchResult, ScannedVariable, StatConfig
from src.core.services.data_services.pattern_index_service import PatternIndexService
from src.parsing.gem5.impl.pool.pool import ParseWorkPool
from src.parsing.gem5.impl.strategies.factory import StrategyFactory

logger = logging.getLogger(__name__)


class Gem5Parser:
    """Service for orchestrating the parsing workflow."""

    @staticmethod
    def submit_parse_async(
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | None = None,
    ) -> ParseBatchResult:
        """Submit async parsing job and return a ParseBatchResult."""
        safe_path: str = os.path.normpath(stats_path) if stats_path else "."
        search_path = normalize_user_path(safe_path)
        if not search_path.exists():
            raise FileNotFoundError(f"Stats path does not exist: {stats_path}")

        # 1. Regex Expansion (Centralized Logic)
        # If scanned_vars are provided, we expand patterns (e.g., cpu\d+)
        # before passing to the strategies.
        processed_configs: list[StatConfig] = []
        for config in variables:
            expanded_config = config
            if scanned_vars and config.is_regex:
                try:
                    logger.info(
                        f"PARSER: Matching regex '{config.name}' "
                        f"against {len(scanned_vars)} scanned variables"
                    )
                    pattern = re.compile(config.name)
                    matched_ids: list[str] = []
                    for sv in scanned_vars:
                        sv_name = sv.name
                        if config.name == sv_name or pattern.fullmatch(sv_name):
                            # If sv is already an aggregated pattern, use its constituents
                            if sv.pattern_indices:
                                matched_ids.extend(sv.pattern_indices)
                            else:
                                matched_ids.append(sv_name)

                    if matched_ids:
                        if config.keep_indices:
                            # keep_indices: Expand each concrete variable
                            # as a separate config to avoid spatial reduction.
                            # Respect user-filtered parsed_ids from the UI
                            # (PatternIndexSelector), falling back to all
                            # matched_ids when no filter was applied.
                            user_ids_raw = config.params.get("parsed_ids", [])
                            user_ids: list[str] = (
                                user_ids_raw if isinstance(user_ids_raw, list) else []
                            )
                            ids_to_expand = user_ids if user_ids else matched_ids

                            # Determine if IDs are full variable names
                            # (scalar patterns) or numeric IDs (vector/etc.).
                            # Full names contain '.' — numeric IDs don't.
                            ids_are_full_names = any("." in pid for pid in ids_to_expand)

                            concrete_names: list[str] = []
                            if ids_are_full_names:
                                concrete_names = list(ids_to_expand)
                            else:
                                for nid in ids_to_expand:
                                    try:
                                        cname = PatternIndexService.reconstruct_concrete_name(
                                            config.name, nid
                                        )
                                        concrete_names.append(cname)
                                    except ValueError:
                                        logger.warning(
                                            "PARSER: Could not reconstruct "
                                            "name for id '%s' in '%s'",
                                            nid,
                                            config.name,
                                        )

                            logger.info(
                                "PARSER: keep_indices — expanding '%s' "
                                "into %d individual variables",
                                config.name,
                                len(concrete_names),
                            )
                            for cname in concrete_names:
                                individual = replace(
                                    config,
                                    name=cname,
                                    is_regex=False,
                                    keep_indices=False,
                                    params={
                                        k: v for k, v in config.params.items() if k != "parsed_ids"
                                    },
                                )
                                processed_configs.append(individual)
                            continue  # skip appending the original config
                        else:
                            # Default: Inject identified leaf variables for
                            # spatial aggregation (mean across instances).
                            params = config.params.copy()
                            params["parsed_ids"] = matched_ids
                            expanded_config = replace(config, params=params)
                            logger.info(
                                f"PARSER: Expanded '{config.name}' to "
                                f"{len(matched_ids)} instances: {matched_ids}"
                            )
                    else:
                        logger.warning(f"PARSER: No matches found for regex '{config.name}'")
                except re.error:
                    logger.warning(f"PARSER: Invalid regex in variable: {config.name}")

            processed_configs.append(expanded_config)

        # 2. Resolve strategy via factory
        strategy = StrategyFactory.create(strategy_type)

        # 3. Get work items from strategy
        batch_work = strategy.get_work_items(stats_path, stats_pattern, processed_configs)
        if not batch_work:
            return ParseBatchResult(futures=[], var_names=[])

        var_names: list[str] = [v.name for v in processed_configs]

        pool = ParseWorkPool.get_instance()
        futures = pool.submit_batch_async(batch_work)
        return ParseBatchResult(futures=futures, var_names=var_names)

    @staticmethod
    def finalize_parsing(
        output_dir: str,
        results: list[dict[str, Any]],
        strategy_type: str = "simple",
        var_names: list[str] | None = None,
    ) -> str | None:
        """
        Post-process and aggregate provided results into final CSV.
        """
        if not results:
            logger.warning("PARSER: No results to persist.")
            return None

        # Resolve strategy via factory for post-processing
        strategy = StrategyFactory.create(strategy_type)

        processed_results = strategy.post_process(results)
        return Gem5Parser.construct_final_csv(output_dir, processed_results, var_names=var_names)

    @staticmethod
    def construct_final_csv(
        output_dir: str,
        results: list[dict[str, Any]],
        var_names: list[str] | None = None,
    ) -> str | None:
        """
        Aggregate provided results and save to CSV.

        Args:
            output_dir: Directory for output CSV file.
            results: Parsed results to aggregate.
            var_names: Ordered variable names for column consistency.
                       If None, falls back to keys from the first result.
        """
        if not results:
            return None

        # Logic adapted from Gem5StatsParser._persist_results
        header_parts: list[str] = []
        sample = results[0]
        column_map: dict[str, list[str] | None] = {}

        # Use provided var_names to ensure consistent order
        ordered_names: list[str] = var_names if var_names else list(sample.keys())

        for var_name in ordered_names:
            if var_name not in sample:
                # Variable absent from first result (e.g., a file with
                # fewer CPUs).  Include as scalar column; rows for files
                # that lack this variable will get "NaN".
                column_map[var_name] = None
                header_parts.append(var_name)
                continue

            var = sample[var_name]
            entries = getattr(var, "entries", None)
            if entries:
                column_map[var_name] = entries
                header_parts.extend(f"{var_name}..{e}" for e in entries)
            else:
                column_map[var_name] = None
                header_parts.append(var_name)

        os.makedirs(str(normalize_user_path(output_dir)), exist_ok=True)
        output_path = os.path.join(str(normalize_user_path(output_dir)), "results.csv")

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(header_parts)

            for file_stats in results:
                row_parts: list[str] = []
                for var_name in ordered_names:
                    if var_name not in file_stats:
                        row_parts.append("NaN")
                        continue

                    var = file_stats[var_name]

                    # Handle Stat objects vs Raw Data (from ConfigAwareStrategy)
                    if hasattr(var, "balance_content"):
                        var.balance_content()
                        var.reduce_duplicates()

                        entries = column_map[var_name]
                        if entries is not None:
                            reduced = var.reduced_content
                            for e in entries:
                                val = reduced.get(e, "NaN")
                                row_parts.append(str(val))
                        else:
                            row_parts.append(str(var.reduced_content))
                    else:
                        # Raw data (string/int/etc.)
                        row_parts.append(str(var))

                writer.writerow(row_parts)

        return output_path
