"""
Scanner Service
Encapsulates logic for discovering and grouping variables from gem5 stats files.
Moves complex domain logic out of the Web Facade.
"""

import logging
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, cast

from src.parsers.workers.pool import ScanWorkPool

logger: logging.Logger = logging.getLogger(__name__)


class ScannedVariable(TypedDict, total=False):
    """Type definition for a scanned variable from gem5 stats."""

    name: str
    type: str  # "scalar", "vector", "distribution", "histogram", "configuration"
    entries: List[str]  # For vector/histogram types
    minimum: Optional[float]  # For distribution type
    maximum: Optional[float]  # For distribution type


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
    def aggregate_scan_results(results: List[List[Dict[str, Any]]]) -> List[ScannedVariable]:
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
        return sorted(list(merged_registry.values()), key=lambda x: x["name"])

    @staticmethod
    def _merge_variable(registry: Dict[str, ScannedVariable], var: Dict[str, Any]) -> None:
        """
        Merge a single variable into the registry.

        Handles deduplication and merging of:
        - Vector/histogram entries (union of all entries)
        - Distribution min/max ranges (expanded to include all values)

        Args:
            registry: Mutable registry dict to update
            var: Variable dict to merge in
        """
        name: str = var["name"]
        if name not in registry:
            registry[name] = var  # type: ignore[assignment]
        else:
            var_type: str = var.get("type", "")
            if var_type in ("vector", "histogram") and "entries" in var:
                existing_entries: set[str] = set(registry[name].get("entries", []))
                existing_entries.update(var["entries"])
                registry[name]["entries"] = sorted(list(existing_entries))

            if var_type == "distribution":
                _merge_distribution_ranges(cast(Dict[str, Any], registry[name]), var)


def _merge_distribution_ranges(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """
    Merge min/max ranges from source into target distribution.

    Args:
        target: Target distribution dict to update (mutated in place)
        source: Source distribution with min/max to merge
    """
    if "minimum" in source:
        cur_min: Optional[float] = target.get("minimum")
        source_min: float = source["minimum"]
        target["minimum"] = min(cur_min, source_min) if cur_min is not None else source_min
    if "maximum" in source:
        cur_max: Optional[float] = target.get("maximum")
        source_max: float = source["maximum"]
        target["maximum"] = max(cur_max, source_max) if cur_max is not None else source_max
