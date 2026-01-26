"""
Scanner Service
Encapsulates logic for discovering and grouping variables from gem5 stats files.
Moves complex domain logic out of the Web Facade.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from src.parsers.workers.pool import ScanWorkPool

logger = logging.getLogger(__name__)


class ScannerService:
    """Service for scanning and discovering statistics from files."""



    @staticmethod
    def submit_scan_async(
        stats_path: str, stats_pattern: str = "stats.txt", limit: int = 5
    ) -> None:
        """Submit async scan job."""
        
        search_path = Path(stats_path)
        if not search_path.exists():
            raise FileNotFoundError(f"Stats path does not exist: {stats_path}")

        files = list(search_path.rglob(stats_pattern))
        if not files:
            raise FileNotFoundError("No stats files found.")

        if limit > 0:
            files_to_sample = files[:limit]
        else:
            files_to_sample = files
            
        pool = ScanWorkPool.get_instance()
        from src.parsers.workers.gem5_scan_work import Gem5ScanWork
        batch_work = [Gem5ScanWork(str(file_path)) for file_path in files_to_sample]
        pool.submit_batch_async(batch_work)

    @staticmethod
    def cancel_scan() -> None:
        """Cancel current scan."""
        ScanWorkPool.get_instance().cancel_current_job()

    @staticmethod
    def get_scan_status() -> Dict[str, Any]:
        """Get scan status."""
        return ScanWorkPool.get_instance().get_status()

    @staticmethod
    def get_scan_results_snapshot() -> List[Dict[str, Any]]:
        """Get processed results from async scan."""
        pool = ScanWorkPool.get_instance()
        results = pool.get_results_async_snapshot()
        
        merged_registry: Dict[str, Dict[str, Any]] = {}
        for file_vars in results:
             for var in file_vars:
                 ScannerService._merge_variable(merged_registry, var)
        return sorted(list(merged_registry.values()), key=lambda x: x["name"])

    @staticmethod
    def _merge_variable(registry: Dict[str, Any], var: Dict[str, Any]):
        """Helper to merge a single variable into registry."""
        name = var["name"]
        if name not in registry:
            registry[name] = var
        else:
            if var["type"] in ("vector", "histogram") and "entries" in var:
                existing = set(registry[name].get("entries", []))
                existing.update(var["entries"])
                registry[name]["entries"] = sorted(list(existing))

            if var["type"] == "distribution":
                _merge_distribution_ranges(registry[name], var)


def _merge_distribution_ranges(target: Dict[str, Any], source: Dict[str, Any]):
    """Helper to merge min/max ranges."""
    if "minimum" in source:
        cur_min = target.get("minimum")
        target["minimum"] = (
            min(cur_min, source["minimum"]) if cur_min is not None else source["minimum"]
        )
    if "maximum" in source:
        cur_max = target.get("maximum")
        target["maximum"] = (
            max(cur_max, source["maximum"]) if cur_max is not None else source["maximum"]
        )
