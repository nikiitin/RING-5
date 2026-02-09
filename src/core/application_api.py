"""
Application API Layer - Single Entry Point for UI.

Provides a unified facade for the presentation layer (web/UI) to interact with
core domain services. Acts as the orchestrator between UI and business logic,
enforcing clean architecture boundaries and managing application state.

Key Responsibilities:
- Parse and load gem5 statistics from various sources
- Manage data pipelines (scanning, parsing, transformations)
- Orchestrate portfolio management and plotting
- Maintain application state and session persistence

Architecture:
    ApplicationAPI composes:
    - ServicesAPI:  Unified facade for all service operations
    - ParseService / ScannerService: Parsing subsystem
    - RepositoryStateManager: Application state

    The ServicesAPI sub-APIs are exposed as properties for direct access:
    - api.managers       -> ManagersAPI
    - api.data_services  -> DataServicesAPI
    - api.shapers        -> ShapersAPI
"""

import logging
from typing import Any, Dict, List, cast

import numpy as np

from src.core.common.utils import normalize_user_path, sanitize_glob_pattern
from src.core.models import StatConfig
from src.core.parsing import ParseService, ScannerService
from src.core.services.data_services.data_services_api import DataServicesAPI
from src.core.services.managers.managers_api import ManagersAPI
from src.core.services.services_impl import DefaultServicesAPI
from src.core.services.shapers.shapers_api import ShapersAPI
from src.core.state.repository_state_manager import RepositoryStateManager

logger = logging.getLogger(__name__)


class ApplicationAPI:
    """
    Layer B Orchestrator: The single entry point for the Presentation Layer (UI).

    Responsibilities:
    1. Holds the single source of truth (RepositoryStateManager).
    2. Orchestrates data flow between Core Services and StateManager (Persistence/Memory).
    3. Provides semantic actions for the UI.
    4. Enforce the boundary between UI and Domain.
    5. Exposes ServicesAPI sub-APIs for direct service access.
    """

    def __init__(self) -> None:
        """
        Initialize the Application API.

        Creates the state manager and wires up the services facade.
        """
        self.state_manager = RepositoryStateManager()

        # Initialize services via unified facade
        self._services = DefaultServicesAPI(self.state_manager)

        logger.info("ApplicationAPI initialized (Singleton Service)")

    # =========================================================================
    # ServicesAPI sub-API access (for UI components)
    # =========================================================================

    @property
    def managers(self) -> ManagersAPI:
        """Access stateless data transformation operations."""
        return self._services.managers

    @property
    def data_services(self) -> DataServicesAPI:
        """Access data storage, retrieval, and domain entity management."""
        return self._services.data_services

    @property
    def shapers(self) -> ShapersAPI:
        """Access pipeline and shaper operations."""
        return self._services.shapers

    def load_data(self, csv_path: str) -> None:
        """
        Orchestrate loading data from a file path:
        1. Load via data services
        2. Persist via StateManager
        """
        try:
            # 1. Operation: Load
            df = self._services.data_services.load_csv_file(csv_path)

            # 2. Persistence: Save
            self.state_manager.set_data(df)
            self.state_manager.set_processed_data(None)  # Reset derived state
            self.state_manager.set_csv_path(csv_path)

            logger.info(f"Loaded and registered data from {csv_path}")
        except Exception as e:
            logger.error(f"Failed to load data from {csv_path}: {e}")
            raise

    def load_from_pool(self, csv_path: str) -> None:
        """Load a dataset from the CSV pool."""
        # Using pure string path from pool
        self.load_data(csv_path)

    def get_current_view(self) -> Dict[str, Any]:
        """Assemble the current data pipeline state for UI consumption."""
        return {
            "raw_data": self.state_manager.get_data(),
            "processed_data": self.state_manager.get_processed_data(),
            "config": self.state_manager.get_config(),
        }

    def reset_session(self) -> None:
        """Clear all session data."""
        self.state_manager.clear_data()
        self.state_manager.clear_all()

    # =========================================================================
    # Parsing & Scanning
    # =========================================================================

    def find_stats_files(self, search_path: str, pattern: str = "stats.txt") -> list[str]:
        """Find stats files in a directory."""
        path = normalize_user_path(search_path)
        if not path.exists():
            return []
        safe_pattern = sanitize_glob_pattern(pattern)
        return [str(p) for p in path.rglob(safe_pattern)]

    def submit_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: list[Any],
        output_dir: str,
        strategy_type: str = "simple",
        **kwargs: Any,
    ) -> list[Any]:
        """
        Submit parsing job to the service.

        Converts variable dictionaries to StatConfig objects.
        Repetition and regex expansion are handled by the parsing module.
        """
        stat_configs: List[StatConfig] = []
        for var in variables:
            if isinstance(var, dict):
                # Normalize type for consistency
                v_type = str(var.get("type", "scalar")).lower()

                # Check for aliasing (legacy compatibility)
                name = str(var.get("name", ""))
                alias = var.get("alias")
                params = var.copy()

                if alias:
                    params["parsed_ids"] = [name]
                    name = alias

                config = StatConfig(
                    name=name,
                    type=v_type,
                    repeat=int(var.get("repeat", 1)),
                    statistics_only=bool(
                        var.get("statistics_only", var.get("statisticsOnly", False))
                    ),
                    params=params,
                )
            elif hasattr(var, "name") and hasattr(var, "type") and not hasattr(var, "params"):
                # It's likely a ScannedVariable, convert to StatConfig
                config = StatConfig(
                    name=var.name,
                    type=var.type,
                    params={"entries": getattr(var, "entries", [])},
                )
            else:
                config = cast(StatConfig, var)

            stat_configs.append(config)

        scanned_vars = kwargs.get("scanned_vars")
        return ParseService.submit_parse_async(
            stats_path, stats_pattern, stat_configs, output_dir, strategy_type, scanned_vars
        )

    def finalize_parsing(
        self, output_dir: str, results: list[Any], strategy_type: str = "simple"
    ) -> str | None:
        """Finalize parsing results into a CSV."""
        return ParseService.finalize_parsing(output_dir, results, strategy_type)

    def submit_scan_async(
        self, stats_path: str, stats_pattern: str = "stats.txt", limit: int = 5
    ) -> list[Any]:
        """Submit scanning job."""
        return ScannerService.submit_scan_async(stats_path, stats_pattern, limit)

    def finalize_scan(self, results: list[list[Any]]) -> list[Any]:
        """Aggregate scan results."""
        return ScannerService.aggregate_scan_results(results)

    def get_parse_status(self) -> str:
        """Get current parsing status."""
        # TODO: Implement proper status tracking if needed by UI
        return "idle"

    def get_scanner_status(self) -> str:
        """Get current scanner status."""
        return "idle"

    # =========================================================================
    # Shapers & Pipelines
    # =========================================================================

    def apply_shapers(self, data: Any, pipeline_config: list[dict[str, Any]]) -> Any:
        """Apply a sequence of shapers to a DataFrame."""
        return self._services.shapers.process_pipeline(data, pipeline_config)

    # =========================================================================
    # Configuration Management
    # =========================================================================

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: list[dict[str, Any]],
        csv_path: str | None = None,
    ) -> str:
        """Save current configuration to disk."""
        return self._services.data_services.save_configuration(
            name, description, shapers_config, csv_path
        )

    def load_configuration(self, config_path: str) -> dict[str, Any]:
        """Load configuration from file."""
        return self._services.data_services.load_configuration(config_path)

    def load_csv_pool(self) -> list[dict[str, Any]]:
        """List available CSV files in the pool."""
        return self._services.data_services.load_csv_pool()

    def load_saved_configs(self) -> list[dict[str, Any]]:
        """List all saved configurations."""
        return self._services.data_services.load_saved_configs()

    def delete_configuration(self, config_path: str) -> bool:
        """Delete a configuration file."""
        return self._services.data_services.delete_configuration(config_path)

    def add_to_csv_pool(self, file_path: str) -> str:
        """Add a file to the CSV pool."""
        return self._services.data_services.add_to_csv_pool(file_path)

    def delete_from_pool(self, file_path: str) -> bool:
        """Delete a file from the CSV pool."""
        return self._services.data_services.delete_from_csv_pool(file_path)

    def delete_from_csv_pool(self, file_path: str) -> bool:
        """Alias for delete_from_pool."""
        return self.delete_from_pool(file_path)

    def load_csv_file(self, file_path: str) -> Any:
        """Load a CSV file directly returning DataFrame."""
        return self._services.data_services.load_csv_file(file_path)

    def get_column_info(self, df: Any) -> Dict[str, Any]:
        """Get summary information about DataFrame columns for UI."""
        if df is None:
            return {
                "total_columns": 0,
                "total_rows": 0,
                "numeric_columns": [],
                "categorical_columns": [],
                "columns": [],
            }

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

        return {
            "total_columns": len(df.columns),
            "total_rows": len(df),
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "columns": df.columns.tolist(),
        }

    # =========================================================================
    # Previews (Delegated to StateManager)
    # =========================================================================

    def set_preview(self, operation_name: str, data: Any) -> None:
        """Store a preview DataFrame for an operation."""
        self.state_manager.set_preview(operation_name, data)

    def get_preview(self, operation_name: str) -> Any:
        """Retrieve a preview DataFrame for an operation."""
        return self.state_manager.get_preview(operation_name)

    def has_preview(self, operation_name: str) -> bool:
        """Check if a preview exists for an operation."""
        return self.state_manager.has_preview(operation_name)

    def clear_preview(self, operation_name: str) -> None:
        """Clear a preview for an operation."""
        self.state_manager.clear_preview(operation_name)
