"""gem5 parser backend for parallel scanning, parsing, and CSV assembly."""

import csv
import logging
import math
import os
import re
import time
from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path
from typing import Any

from src.core.common.utils import normalize_user_path
from src.core.models import (
    ParseBatchResult,
    ScanFileResult,
    ScannedVariable,
    ScanResult,
    StatConfig,
)
from src.core.models.csv_contract import MISSING_VALUE, validate_parser_csv
from src.core.models.pattern_index_service import PatternIndexService
from src.parsing.framework.file_discovery import find_stats_files
from src.parsing.gem5.impl.pool.pool import ParseWorkPool, ScanWorkPool
from src.parsing.gem5.impl.scanning.gem5_scan_work import Gem5ScanWork
from src.parsing.gem5.impl.scanning.pattern_aggregator import PatternAggregator
from src.parsing.gem5.impl.strategies.factory import StrategyFactory
from src.parsing.gem5.models import Gem5ScannedVariable
from src.parsing.parser_protocol import SimulationParser

logger = logging.getLogger(__name__)


def _render_value(val: Any) -> str:
    """Render a reduced stat value for the CSV, mapping missing → MISSING_VALUE.

    A missing/unmeasured numeric value (None, NaN, or the legacy ``"NA"``
    sentinel) is written as the canonical ``MISSING_VALUE`` so it is never
    confused with a measured 0 (hard rule 6).
    """
    if val is None or val == "NA":
        return MISSING_VALUE
    if isinstance(val, float) and math.isnan(val):
        return MISSING_VALUE
    return str(val)


class Gem5Parser(SimulationParser):
    """The gem5 simulation backend — parsing, scanning, and CSV assembly.

    The single class the registry instantiates for ``"gem5"``; implements the
    ``SimulationParser`` protocol. Methods are static (no instance state — the
    pools are singletons), so they are callable both on the class and on the
    instance the registry hands to ``ApplicationAPI``.
    """

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
        t_start = time.perf_counter()
        safe_path: str = os.path.normpath(stats_path) if stats_path else "."
        search_path = normalize_user_path(safe_path)
        if not search_path.exists():
            raise FileNotFoundError(f"Stats path does not exist: {stats_path}")

        # 1. Regex Expansion (Centralized Logic)
        t_regex_start = time.perf_counter()
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
                            user_ids_raw = config.params.get("parsed_ids", [])
                            user_ids: list[str] = (
                                user_ids_raw if isinstance(user_ids_raw, list) else []
                            )
                            ids_to_expand = user_ids if user_ids else matched_ids
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

                            if len(concrete_names) > 50:
                                logger.warning(
                                    "PARSER: Regex '%s' expanded to %d concrete variables — "
                                    "this may increase memory usage and processing time.",
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
                            continue
                        else:
                            params = config.params.copy()
                            params["parsed_ids"] = matched_ids
                            expanded_config = replace(config, params=params)
                    else:
                        logger.warning(f"PARSER: No matches found for regex '{config.name}'")
                except re.error:
                    logger.warning(f"PARSER: Invalid regex in variable: {config.name}")

            processed_configs.append(expanded_config)

        t_regex_end = time.perf_counter()
        logger.info(f"PERF: Regex expansion took {t_regex_end - t_regex_start:.4f}s")

        # 2. Resolve strategy via factory
        strategy = StrategyFactory.create(strategy_type)

        # 3. Get work items from strategy
        t_work_start = time.perf_counter()
        batch_work = strategy.get_work_items(stats_path, stats_pattern, processed_configs)
        t_work_end = time.perf_counter()
        logger.info(f"PERF: Work item generation took {t_work_end - t_work_start:.4f}s")

        if not batch_work:
            # Strategies raise on zero matching files; an empty work list here
            # means a custom strategy produced nothing — fail loudly rather
            # than letting the parse "succeed" while producing no CSV.
            raise FileNotFoundError(
                f"No parse work generated for pattern '{stats_pattern}' under: {stats_path}"
            )

        var_names: list[str] = [v.name for v in processed_configs]

        pool = ParseWorkPool.get_instance()
        futures = pool.submit_batch_async(batch_work)

        t_total = time.perf_counter() - t_start
        logger.info(f"PERF: submit_parse_async total (pre-pool) took {t_total:.4f}s")
        return ParseBatchResult(futures=futures, var_names=var_names)

    # ------------------------------------------------------------------ scanning

    @staticmethod
    def submit_scan_async(
        stats_path: str, stats_pattern: str = "stats.txt", limit: int = 5
    ) -> list[Future[ScanFileResult]]:
        """
        Submit async scan job and return futures.

        Args:
            stats_path: Base directory to search for stats files
            stats_pattern: Filename pattern to match (default: "stats.txt")
            limit: Maximum number of files to scan (0 for unlimited)

        Returns:
            List of Future objects that each resolve to a ``ScanFileResult``

        Raises:
            FileNotFoundError: If stats_path doesn't exist or no files found
        """
        files = find_stats_files(
            stats_path, stats_pattern, limit=limit, sort=True, raise_if_empty=True
        )
        pool: ScanWorkPool = ScanWorkPool.get_instance()
        batch_work: list[Gem5ScanWork] = [Gem5ScanWork(f) for f in files]
        return pool.submit_batch_async(batch_work)

    @staticmethod
    def aggregate_scan_results(results: list[ScanFileResult]) -> ScanResult:
        """
        Aggregate per-file scan results into a unified outcome.

        Successful files are merged and deduplicated into one variable list;
        failed files are collected separately so the caller can surface them
        instead of silently treating a failed scan as "no variables".

        Args:
            results: Per-file ``ScanFileResult`` objects from the workers.

        Returns:
            ``ScanResult`` with the merged variables and the list of failures.
        """
        failures: list[ScanFileResult] = [r for r in results if not r.ok]

        merged_registry: dict[str, ScannedVariable] = {}
        for file_result in results:
            for var in file_result.variables:
                Gem5Parser._merge_variable(merged_registry, var)

        merged_vars = sorted(list(merged_registry.values()), key=lambda x: x.name)

        # Apply pattern aggregation to consolidate repeated numeric patterns
        aggregated_vars = PatternAggregator.aggregate_patterns(merged_vars)

        return ScanResult(variables=aggregated_vars, failures=failures)

    @staticmethod
    def _merge_variable(registry: dict[str, ScannedVariable], var: ScannedVariable) -> None:
        """
        Merge a single variable into the registry.

        Handles deduplication and merging of:
        - Vector/histogram entries (union of all entries)
        - Distribution min/max ranges (expanded to include all values)

        Args:
            registry: Mutable registry dict to update
            var: ScannedVariable to merge in
        """

        name: str = var.name
        if name not in registry:
            registry[name] = var
        else:
            existing = registry[name]
            if var.type in ("vector", "histogram"):
                new_entries = sorted(list(set(existing.entries) | set(var.entries)))
                # Preserve other fields (like pattern_indices) while updating entries
                registry[name] = replace(existing, entries=new_entries)

            elif var.type == "distribution":
                # Handle distribution range merging (gem5-specific min/max)
                gem5_existing = existing if isinstance(existing, Gem5ScannedVariable) else None
                gem5_var = var if isinstance(var, Gem5ScannedVariable) else None

                cur_min = gem5_existing.minimum if gem5_existing else None
                cur_max = gem5_existing.maximum if gem5_existing else None
                var_min = gem5_var.minimum if gem5_var else None
                var_max = gem5_var.maximum if gem5_var else None

                # Explicit None guards — `var_min or cur_min` would discard a
                # legitimate scanned minimum of 0.0 (falsy), losing the range.
                new_min: float | None
                new_max: float | None
                if cur_min is not None and var_min is not None:
                    new_min = min(cur_min, var_min)
                else:
                    new_min = var_min if var_min is not None else cur_min
                if cur_max is not None and var_max is not None:
                    new_max = max(cur_max, var_max)
                else:
                    new_max = var_max if var_max is not None else cur_max

                registry[name] = Gem5ScannedVariable(
                    name=existing.name,
                    type=existing.type,
                    entries=existing.entries,
                    pattern_indices=existing.pattern_indices,
                    minimum=new_min,
                    maximum=new_max,
                )

    # ----------------------------------------------------------------- finalize

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
        t_start = time.perf_counter()
        if not results:
            logger.warning("PARSER: No results to persist.")
            return None

        # Resolve strategy via factory for post-processing
        strategy = StrategyFactory.create(strategy_type)

        t_post_start = time.perf_counter()
        processed_results = strategy.post_process(results)
        t_post_end = time.perf_counter()
        logger.info(f"PERF: Strategy post-processing took {t_post_end - t_post_start:.4f}s")

        csv_path = Gem5Parser.construct_final_csv(
            output_dir, processed_results, var_names=var_names
        )

        # Enforce the inter-layer CSV contract (logged, non-fatal).
        if csv_path and Path(csv_path).exists():
            for warning in validate_parser_csv(Path(csv_path)):
                logger.warning("CSV contract: %s", warning)

        t_total = time.perf_counter() - t_start
        logger.info(f"PERF: finalize_parsing total took {t_total:.4f}s")
        return csv_path

    @staticmethod
    def construct_final_csv(
        output_dir: str,
        results: list[dict[str, Any]],
        var_names: list[str] | None = None,
    ) -> str | None:
        """
        Aggregate provided results and save to CSV.
        """
        t_start = time.perf_counter()
        if not results:
            return None
        logger.info(f"PERF: Starting construct_final_csv for {len(results)} files")

        # Include variables that are absent from the first result in the CSV header.
        header_parts: list[str] = []
        column_map: dict[str, list[str] | None] = {}

        # Use provided var_names to ensure consistent order
        ordered_names: list[str] = var_names if var_names else list(results[0].keys())

        for var_name in ordered_names:
            # Search all results for the first occurrence of this variable
            # to determine its entries (union approach for header completeness)
            found_var = None
            for res in results:
                if var_name in res:
                    found_var = res[var_name]
                    break

            if found_var is None:
                column_map[var_name] = None
                header_parts.append(var_name)
                continue

            entries = getattr(found_var, "entries", None)
            if entries:
                column_map[var_name] = entries
                header_parts.extend(f"{var_name}..{e}" for e in entries)
            else:
                column_map[var_name] = None
                header_parts.append(var_name)

        os.makedirs(str(normalize_user_path(output_dir)), exist_ok=True)
        output_path = os.path.join(str(normalize_user_path(output_dir)), "results.csv")

        t_write_start = time.perf_counter()
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(header_parts)

            for file_stats in results:
                row_parts: list[str] = []
                for var_name in ordered_names:
                    if var_name not in file_stats:
                        row_parts.append(MISSING_VALUE)
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
                                row_parts.append(_render_value(reduced.get(e)))
                        else:
                            row_parts.append(_render_value(var.reduced_content))
                    else:
                        # Raw data (string/int/etc.)
                        row_parts.append(str(var))

                writer.writerow(row_parts)
        t_write_end = time.perf_counter()
        logger.info(f"PERF: CSV writing loop took {t_write_end - t_write_start:.4f}s")

        t_total = time.perf_counter() - t_start
        logger.info(f"PERF: construct_final_csv total took {t_total:.4f}s")
        return output_path
