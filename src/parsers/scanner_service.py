"""
Scanner Service
Encapsulates logic for discovering and grouping variables from gem5 stats files.
Moves complex domain logic out of the Web Facade.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.parsers.workers.pool import ParseWorkPool as ScanWorkPool

logger = logging.getLogger(__name__)


class ScannerService:
    """Service for scanning and discovering statistics from files."""

    @staticmethod
    def scan_stats_variables(
        stats_path: str, stats_pattern: str = "stats.txt", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Parallel scan of stats files to discover available metrics.
        """
        search_path = Path(stats_path)
        if not search_path.exists():
            logger.error(f"SCANNER: Stats path does not exist: {stats_path}")
            return []

        files = list(search_path.rglob(stats_pattern))
        if not files:
            return []

        # Optimization: Scan few samples to build the schema quickly
        files_to_sample = files[:limit]

        pool = ScanWorkPool.get_instance()
        
        # Correctly import the worker class
        from src.parsers.workers.gem5_scan_work import Gem5ScanWork
        
        for file_path in files_to_sample:
            # Reusing the existing worker architecture
            pool.add_work(Gem5ScanWork(str(file_path)))

        results = pool.get_results()

        # Scientific Merging: Combine discovered keys across all sampled files
        merged_registry: Dict[str, Dict[str, Any]] = {}

        for file_vars in results:
            for var in file_vars:
                name = var["name"]
                if name not in merged_registry:
                    merged_registry[name] = var
                else:
                    # Union of discovered keys for vectors/histograms
                    if var["type"] in ("vector", "histogram") and "entries" in var:
                        existing = set(merged_registry[name].get("entries", []))
                        existing.update(var["entries"])
                        merged_registry[name]["entries"] = sorted(list(existing))

                    # Global range detection for distributions
                    if var["type"] == "distribution":
                        _merge_distribution_ranges(merged_registry[name], var)

        return sorted(list(merged_registry.values()), key=lambda x: x["name"])

    @staticmethod
    def scan_stats_variables_with_grouping(
        stats_path: str, file_pattern: str = "stats.txt", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Scan and group variables using Regex (heuristic for reduction).
        """
        raw_vars = ScannerService.scan_stats_variables(stats_path, file_pattern, limit)
        if not raw_vars:
            return []

        grouped_vars: Dict[str, Dict[str, Any]] = {}

        for var in raw_vars:
            name = var["name"]
            if re.search(r"\d+", name):
                pattern = re.sub(r"\d+", r"\\d+", name)

                if pattern not in grouped_vars:
                    # New group
                    grouped_vars[pattern] = {
                        "name": pattern,
                        "type": var["type"],
                        "entries": var.get("entries", []),
                        "count": 1,
                        "examples": [name],
                    }
                    if var["type"] == "distribution":
                        grouped_vars[pattern]["minimum"] = var.get("minimum")
                        grouped_vars[pattern]["maximum"] = var.get("maximum")
                else:
                    # Merge into existing group
                    group = grouped_vars[pattern]
                    group["count"] += 1
                    if len(group["examples"]) < 3:
                        group["examples"].append(name)

                    if "entries" in var:
                        existing = set(group.get("entries", []))
                        existing.update(var["entries"])
                        group["entries"] = sorted(list(existing))

                    if var["type"] == "distribution":
                        _merge_distribution_ranges(group, var)
            else:
                if name not in grouped_vars:
                    var["count"] = 1
                    var["examples"] = [name]
                    grouped_vars[name] = var

        results = []
        for info in grouped_vars.values():
            if info["count"] == 1 and len(info["examples"]) == 1:
                info["name"] = info["examples"][0]
            results.append(info)

        return sorted(results, key=lambda x: x["name"])


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
