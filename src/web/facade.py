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

from src.parsers.parser import Gem5StatsParser
from src.parsers.scanner_service import ScannerService
from src.web.services.config_service import ConfigService
from src.web.services.csv_pool_service import CsvPoolService
from src.web.services.paths import PathService
from src.web.services.shapers.factory import ShaperFactory

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
        logger.info("FACADE: Starting gem5 stats ingestion from: %s", stats_path)

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
                # Processed via previously cached async scan results
                scanned_vars = self.get_scan_results_snapshot()
                matched_ids = [
                    cv["name"] for cv in scanned_vars if re.fullmatch(var_name, cv["name"])
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
        logger.info("FACADE: Ingestion successful. CSV generated at: %s", csv_path)

        if progress_callback:
            progress_callback(10, 1.0, "Ingestion Complete.")

        return csv_path

    # ==================== Variable Discovery & Scanning ====================



    def submit_scan_async(
        self, stats_path: str, stats_pattern: str = "stats.txt", limit: int = -1
    ) -> None:
        """Submit an asynchronous scan request."""
        ScannerService.submit_scan_async(stats_path, stats_pattern, limit)

    def cancel_scan(self) -> None:
        """Cancel the currently running scan."""
        ScannerService.cancel_scan()

    def get_scan_status(self) -> Dict[str, Any]:
        """Get status of the running scan."""
        return ScannerService.get_scan_status()

    def get_scan_results_snapshot(self) -> List[Dict[str, Any]]:
        """Get snapshot of current scan results."""
        return ScannerService.get_scan_results_snapshot()

    # ==================== Utility Methods ====================

    def apply_shapers(
        self, data: pd.DataFrame, shapers_config: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """Apply a sequence of business logic transformations to a dataset."""

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


