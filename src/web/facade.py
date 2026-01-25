"""
RING-5 Backend Facade
Simplified interface to all backend operations (Facade Pattern).
Decouples the web interface from complex backend implementations.
"""

import glob
import logging
import re
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
        Delegates to ScannerService.
        """
        from src.parsers.scanner_service import ScannerService

        return ScannerService.scan_stats_variables(stats_path, stats_pattern, limit)

    def scan_stats_variables_with_grouping(
        self, stats_path: str, file_pattern: str = "stats.txt", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Scan and group variables using Regex (heuristic for reduction).
        Delegates to ScannerService.
        """
        from src.parsers.scanner_service import ScannerService

        return ScannerService.scan_stats_variables_with_grouping(stats_path, file_pattern, limit)

    def scan_entries_for_variable(
        self, stats_path: str, var_name: str, file_pattern: str = "stats.txt", limit: int = 10
    ) -> List[str]:
        """
        Deep scan to find all unique sub-keys (entries) for a complex variable.
        Uses ScannerService's deep scan capability (via scan_stats_variables primarily).
        """
        # Filter logic is here but deep scan delegated to Service

        from src.parsers.scanner_service import ScannerService

        # Refactoring to use ScannerService for raw data
        raw_vars = ScannerService.scan_stats_variables(stats_path, file_pattern, limit)
        found_entries: set[str] = set()

        for var in raw_vars:
            if var["name"] == var_name and "entries" in var:
                found_entries.update(var["entries"])

        return sorted(list(found_entries))

    def scan_distribution_range(
        self, stats_path: str, var_name: str, file_pattern: str = "stats.txt"
    ) -> Dict[str, Optional[int]]:
        """
        Determine the global operational range for a distribution variable.
        """
        from src.parsers.scanner_service import ScannerService

        # Deep scan across 20 samples to ensure range coverage
        discovered_vars = ScannerService.scan_stats_variables(stats_path, file_pattern, limit=20)

        global_min: Optional[int] = None
        global_max: Optional[int] = None

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
            shaper = ShaperFactory.create_shaper(cfg["type"], cfg)
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
