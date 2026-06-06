"""
Scanner Service
Encapsulates logic for discovering and grouping variables from gem5 stats files.
Moves complex domain logic out of the Web Facade.
"""

import os
from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path

from src.core.common.utils import normalize_user_path, sanitize_glob_pattern
from src.core.models import ScanFileResult, ScannedVariable, ScanResult
from src.parsing.gem5.impl.pool.pool import ScanWorkPool
from src.parsing.gem5.impl.scanning.gem5_scan_work import Gem5ScanWork
from src.parsing.gem5.impl.scanning.pattern_aggregator import PatternAggregator
from src.parsing.gem5.models import Gem5ScannedVariable


class Gem5Scanner:
    """
    Service for scanning and discovering statistics from files.

    This service handles the async scanning workflow:
    1. submit_scan_async() - submits scan jobs to worker pool
    2. aggregate_scan_results() - merges results from multiple files
    """

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
        search_path: Path = normalize_user_path(os.path.normpath(stats_path) if stats_path else ".")
        if not search_path.exists():
            raise FileNotFoundError(f"Stats path does not exist: {stats_path}")

        safe_pattern: str = sanitize_glob_pattern(stats_pattern)

        # Early-stop iteration: when limit > 0, stop collecting files from the
        # generator as soon as we have enough, avoiding a full tree traversal.
        if limit > 0:
            files_unsorted: list[Path] = []
            for f in search_path.rglob(safe_pattern):
                files_unsorted.append(f)
                if len(files_unsorted) >= limit:
                    break
            files: list[Path] = sorted(files_unsorted)
        else:
            files = sorted(search_path.rglob(safe_pattern))

        if not files:
            raise FileNotFoundError("No stats files found.")

        pool: ScanWorkPool = ScanWorkPool.get_instance()
        batch_work: list[Gem5ScanWork] = [Gem5ScanWork(str(file_path)) for file_path in files]
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
                Gem5Scanner._merge_variable(merged_registry, var)

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

                new_min = (
                    min(cur_min, var_min)
                    if cur_min is not None and var_min is not None
                    else (var_min or cur_min)
                )
                new_max = (
                    max(cur_max, var_max)
                    if cur_max is not None and var_max is not None
                    else (var_max or cur_max)
                )

                registry[name] = Gem5ScannedVariable(
                    name=existing.name,
                    type=existing.type,
                    entries=existing.entries,
                    pattern_indices=existing.pattern_indices,
                    minimum=new_min,
                    maximum=new_max,
                )
