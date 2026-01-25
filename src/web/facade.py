"""
RING-5 Backend Facade
Simplified interface to all backend operations (Facade Pattern).
Decouples the web interface from complex backend implementations.
"""

import glob
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.web.services.config_service import ConfigService
from src.web.services.csv_pool_service import CsvPoolService
from src.web.services.paths import PathService

logger = logging.getLogger(__name__)


class BackendFacade:
    """
    Facade providing simplified access to all backend operations.

    Following the Facade Pattern, this class provides a single point of entry
    for the presentation layer to interact with the scientific domain logic
    (Layer B) and ingestion (Layer A).
    """

    def __init__(self):
        """Initialize the facade with persistent storage paths."""
        self.ring5_data_dir = PathService.get_data_dir()
        self.csv_pool_dir = CsvPoolService.get_pool_dir()
        self.config_pool_dir = ConfigService.get_config_dir()

    # ==================== CSV & Configuration Services (Delegated) ====================

    def load_csv_pool(self) -> List[Dict[str, Any]]:
        """Fetch the registry of available ingested datasets."""
        return CsvPoolService.load_pool()

    def add_to_csv_pool(self, csv_path: str) -> str:
        """Register a new CSV results file into the pool."""
        return CsvPoolService.add_to_pool(csv_path)

    def delete_from_csv_pool(self, csv_path: str) -> bool:
        """Remove an ingested dataset from the pool."""
        return CsvPoolService.delete_from_pool(csv_path)

    def load_csv_file(self, csv_path: str) -> pd.DataFrame:
        """Load a dataset into a Pandas DataFrame with automatic schema detection."""
        return CsvPoolService.load_csv_file(csv_path)

    def load_saved_configs(self) -> List[Dict[str, Any]]:
        """List all persisted simulation configurations."""
        return ConfigService.load_saved_configs()

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: List[Dict[str, Any]],
        csv_path: Optional[str] = None,
    ) -> str:
        """Persist a simulation analyzer configuration."""
        return ConfigService.save_configuration(name, description, shapers_config, csv_path)

    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """Retrieve a specific configuration schema."""
        return ConfigService.load_configuration(config_path)

    def delete_configuration(self, config_path: str) -> bool:
        """Delete a saved configuration."""
        return ConfigService.delete_configuration(config_path)

    # ==================== Data Parsing ====================

    def find_stats_files(self, stats_path: str, stats_pattern: str) -> List[str]:
        """
        Find gem5 stats files matching the pattern.

        Args:
            stats_path: Base directory path
            stats_pattern: File pattern (e.g., "stats.txt")

        Returns:
            List of file paths
        """
        pattern = f"{stats_path}/**/{stats_pattern}"
        return glob.glob(pattern, recursive=True)

    # ==================== Core Extraction Orchestration ====================

    def parse_gem5_stats(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: List[Dict[str, Any]],
        output_dir: str,
        progress_callback: Optional[Any] = None,
    ) -> Optional[str]:
        """
        Execute the parallel gem5 stats ingestion pipeline.

        Args:
            stats_path: Root directory of simulation folders.
            stats_pattern: Filename filter (e.g. stats.txt).
            variables: List of variable definitions from the UI.
            output_dir: Destination for results.csv.
            progress_callback: UI hook for status updates.

        Returns:
            Path to the generated results file.
        """
        from src.parsers.parser import Gem5StatsParser

        Gem5StatsParser.reset()

        if progress_callback:
            progress_callback(1, 0.1, "Analyzing Variable Patterns...")

        # Scientific Variable Resolution:
        # Before parsing, we must expand regex patterns into concrete variable identifiers.
        processed_vars = []
        for var in variables:
            var_name = var["name"]

            # Pattern Recognition: Identify variables meant for cross-controller aggregation
            # e.g. system.cpu\d+.ipc
            if "\\d+" in var_name or "*" in var_name:
                # Discover concrete matches to determine 'repeat' factor and IDs
                concrete_matches = self.scan_stats_variables(stats_path, stats_pattern, limit=3)
                matched_ids = [
                    cv["name"] for cv in concrete_matches if re.fullmatch(var_name, cv["name"])
                ]

                if matched_ids:
                    var_config = {
                        "name": var_name,
                        "type": var["type"],
                        "parsed_ids": matched_ids,
                        "repeat": len(matched_ids),
                    }
                    # Propagate type-specific configurations
                    for key in [
                        "bins",
                        "max_range",
                        "minimum",
                        "maximum",
                        "vectorEntries",
                        "statistics",
                    ]:
                        if key in var:
                            var_config[key] = var[key]

                    processed_vars.append(var_config)
                    continue

            # Standard Fixed-ID Variable
            var_config = {"name": var_name, "type": var["type"]}
            if var.get("alias"):
                var_config["name"] = var["alias"]
                var_config["parsed_ids"] = [var_name]

            # Copy all extra attributes (bins, ranges, etc.)
            for key, val in var.items():
                if key not in ("name", "alias", "type"):
                    var_config[key] = val

            processed_vars.append(var_config)

        if progress_callback:
            progress_callback(3, 0.5, "Executing Parallel Ingestion...")

        parser = (
            Gem5StatsParser.builder()
            .with_path(stats_path)
            .with_pattern(stats_pattern)
            .with_variables(processed_vars)
            .with_output(output_dir)
            .build()
        )

        csv_path = parser.parse()

        if progress_callback:
            progress_callback(10, 1.0, "Ingestion Complete.")

        return csv_path

    # ==================== Variable Discovery & Scanning ====================

    def scan_stats_variables(
        self, stats_path: str, stats_pattern: str = "stats.txt", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Parallel scan of stats files to discover available metrics.

        Uses the parallel ScanWorkPool for research-scale efficiency.
        """
        search_path = Path(stats_path)
        if not search_path.exists():
            logger.error(f"FACADE: Stats path does not exist: {stats_path}")
            return []

        files = list(search_path.rglob(stats_pattern))
        if not files:
            return []

        # Optimization: Scan few samples to build the schema quickly
        files_to_sample = files[:limit]

        from src.parsers.workers.gem5_scan_work import Gem5ScanWork
        from src.parsers.workers.pool import ScanWorkPool

        pool = ScanWorkPool.getInstance()
        for file_path in files_to_sample:
            pool.addWork(Gem5ScanWork(str(file_path)))

        results = pool.getResults()

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
                        if "minimum" in var:
                            cur_min = merged_registry[name].get("minimum")
                            merged_registry[name]["minimum"] = (
                                min(cur_min, var["minimum"])
                                if cur_min is not None
                                else var["minimum"]
                            )
                        if "maximum" in var:
                            cur_max = merged_registry[name].get("maximum")
                            merged_registry[name]["maximum"] = (
                                max(cur_max, var["maximum"])
                                if cur_max is not None
                                else var["maximum"]
                            )

        return sorted(list(merged_registry.values()), key=lambda x: x["name"])

    def scan_stats_variables_with_grouping(
        self, stats_path: str, file_pattern: str = "stats.txt", limit: int = 5
    ) -> List[Dict[str, Any]]:
        r"""
        Scan and group variables using Regex (heuristic for reduction).
        e.g. system.cpu0.ipc and system.cpu1.ipc -> system.cpu\d+.ipc

        Note: This is a heuristic discovery method.
        """
        raw_vars = self.scan_stats_variables(stats_path, file_pattern, limit)
        if not raw_vars:
            return []

        grouped_vars: Dict[str, Dict[str, Any]] = {}

        for var in raw_vars:
            name = var["name"]
            if re.search(r"\d+", name):
                pattern = re.sub(r"\d+", r"\\d+", name)

                if pattern not in grouped_vars:
                    grouped_vars[pattern] = {
                        "name": pattern,
                        "type": var["type"],
                        "entries": var.get("entries", []),
                        "count": 1,
                        "examples": [name],
                    }
                    if var["type"] == "distribution":
                        if "minimum" in var:
                            grouped_vars[pattern]["minimum"] = var["minimum"]
                        if "maximum" in var:
                            grouped_vars[pattern]["maximum"] = var["maximum"]
                else:
                    grouped_vars[pattern]["count"] += 1
                    if len(grouped_vars[pattern]["examples"]) < 3:
                        grouped_vars[pattern]["examples"].append(name)

                    if "entries" in var:
                        existing = set(grouped_vars[pattern].get("entries", []))
                        existing.update(var["entries"])
                        grouped_vars[pattern]["entries"] = sorted(list(existing))

                    if var["type"] == "distribution":
                        if "minimum" in var:
                            cur_min = grouped_vars[pattern].get("minimum")
                            grouped_vars[pattern]["minimum"] = (
                                min(cur_min, var["minimum"])
                                if cur_min is not None
                                else var["minimum"]
                            )
                        if "maximum" in var:
                            cur_max = grouped_vars[pattern].get("maximum")
                            grouped_vars[pattern]["maximum"] = (
                                max(cur_max, var["maximum"])
                                if cur_max is not None
                                else var["maximum"]
                            )
            else:
                if name not in grouped_vars:
                    grouped_vars[name] = var
                    grouped_vars[name]["count"] = 1
                    grouped_vars[name]["examples"] = [name]

        results = []
        for info in grouped_vars.values():
            if info["count"] == 1 and len(info["examples"]) == 1:
                info["name"] = info["examples"][0]
            results.append(info)

        return sorted(results, key=lambda x: x["name"])

    def scan_entries_for_variable(
        self, stats_path: str, var_name: str, file_pattern: str = "stats.txt", limit: int = 10
    ) -> List[str]:
        """
        Deep scan to find all unique sub-keys (entries) for a complex variable.
        """
        found_entries: set[str] = set()

        search_path = Path(stats_path)
        if not search_path.exists():
            return []

        # Sampling for discovery speed
        files = list(search_path.rglob(file_pattern))[:limit]

        from src.parsers.workers.gem5_scan_work import Gem5ScanWork
        from src.parsers.workers.pool import ScanWorkPool

        pool = ScanWorkPool.getInstance()
        for f in files:
            pool.addWork(Gem5ScanWork(str(f)))

        results = pool.getResults()
        for file_vars in results:
            for var in file_vars:
                if var["name"] == var_name and "entries" in var:
                    found_entries.update(var["entries"])

        return sorted(list(found_entries))

    def scan_distribution_range(
        self, stats_path: str, var_name: str, file_pattern: str = "stats.txt"
    ) -> Dict[str, Optional[int]]:
        """
        Determine the global operational range for a distribution variable.
        """
        global_min: Optional[int] = None
        global_max: Optional[int] = None

        # Deep scan across 20 samples to ensure range coverage
        discovered_vars = self.scan_stats_variables(stats_path, file_pattern, limit=20)

        for var in discovered_vars:
            if var["name"] == var_name and var.get("type") == "distribution":
                global_min = var.get("minimum")
                global_max = var.get("maximum")
                break

        return {"minimum": global_min, "maximum": global_max}

    # ==================== Utility Methods ====================

    def apply_shapers(
        self, data: pd.DataFrame, shapers_config: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """Apply a sequence of business logic transformations to a dataset."""
        from src.web.services.shapers.factory import ShaperFactory

        result = data.copy()
        for cfg in shapers_config:
            shaper = ShaperFactory.createShaper(cfg["type"], cfg)
            result = shaper(result)
        return result

    def get_column_info(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Retrieve structural metadata for the current dataset."""
        return {
            "total_columns": len(data.columns),
            "numeric_columns": data.select_dtypes(include=["number"]).columns.tolist(),
            "categorical_columns": data.select_dtypes(include=["object"]).columns.tolist(),
            "total_rows": len(data),
            "null_counts": data.isnull().sum().to_dict(),
        }

    def scan_vector_entries(self, *args, **kwargs) -> List[str]:
        """Backward compatibility alias."""
        return self.scan_entries_for_variable(*args, **kwargs)
