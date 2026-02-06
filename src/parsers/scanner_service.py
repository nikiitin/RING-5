"""
Scanner Service
Encapsulates logic for discovering and grouping variables from gem5 stats files.
Moves complex domain logic out of the Web Facade.
"""

import logging
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Dict, List

from src.parsers.models import ScannedVariable
from src.parsers.pattern_aggregator import PatternAggregator
from src.parsers.workers.pool import ScanWorkPool

logger: logging.Logger = logging.getLogger(__name__)


class ScannerService:
    """
    Service for scanning and discovering statistics from files.

    This service handles the async scanning workflow:
    1. submit_scan_async() - submits scan jobs to worker pool
    2. aggregate_scan_results() - merges results from multiple files
    """

    @staticmethod
    def submit_scan_async(
        stats_path: str, stats_pattern: str = "stats.txt", limit: int = 5
    ) -> List[Future[List[ScannedVariable]]]:
        """
        Submit async scan job and return futures.

        Args:
            stats_path: Base directory to search for stats files
            stats_pattern: Filename pattern to match (default: "stats.txt")
            limit: Maximum number of files to scan (0 for unlimited)

        Returns:
            List of Future objects that will resolve to scan results

        Raises:
            FileNotFoundError: If stats_path doesn't exist or no files found
        """
        search_path: Path = Path(stats_path)
        if not search_path.exists():
            raise FileNotFoundError(f"Stats path does not exist: {stats_path}")

        files: List[Path] = list(search_path.rglob(stats_pattern))
        if not files:
            raise FileNotFoundError("No stats files found.")

        files_to_sample: List[Path] = files[:limit] if limit > 0 else files

        pool: ScanWorkPool = ScanWorkPool.get_instance()
        from src.parsers.workers.gem5_scan_work import Gem5ScanWork

        batch_work: List[Any] = [Gem5ScanWork(str(file_path)) for file_path in files_to_sample]
        return pool.submit_batch_async(batch_work)

    @staticmethod
    def cancel_scan() -> None:
        """Cancel current scan by cancelling all pending futures."""
        ScanWorkPool.get_instance().cancel_all()

    @staticmethod
    def aggregate_scan_results(results: List[List[ScannedVariable]]) -> List[ScannedVariable]:
        """
        Aggregate results from async scan into unified variable list.

        Args:
            results: List of scan results from each file (each is a list of variables)

        Returns:
            Sorted list of merged variables with deduplicated entries
        """
        merged_registry: Dict[str, ScannedVariable] = {}
        for file_vars in results:
            for var in file_vars:
                ScannerService._merge_variable(merged_registry, var)

        merged_vars = sorted(list(merged_registry.values()), key=lambda x: x.name)

        # Apply pattern aggregation to consolidate repeated numeric patterns
        # Use models for aggregation
        aggregated_vars = PatternAggregator.aggregate_patterns(merged_vars)

        return aggregated_vars

    @staticmethod
    def _merge_variable(registry: Dict[str, ScannedVariable], var: Any) -> None:
        """
        Merge a single variable into the registry.

        Handles deduplication and merging of:
        - Vector/histogram entries (union of all entries)
        - Distribution min/max ranges (expanded to include all values)

        Args:
            registry: Mutable registry dict to update
            var: Variable model (or dict) to merge in
        """
        from dataclasses import replace

        # Handle raw dicts (from legacy or testing code)
        if isinstance(var, dict):
            var = ScannedVariable.from_dict(var)

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
                # Handle distribution range merging
                cur_min = existing.minimum
                cur_max = existing.maximum

                new_min = (
                    min(cur_min, var.minimum)
                    if cur_min is not None and var.minimum is not None
                    else (var.minimum or cur_min)
                )
                new_max = (
                    max(cur_max, var.maximum)
                    if cur_max is not None and var.maximum is not None
                    else (var.maximum or cur_max)
                )

                registry[name] = replace(existing, minimum=new_min, maximum=new_max)
