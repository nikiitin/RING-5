"""
Application API Layer - Single Entry Point for UI.

Provides a unified facade for the presentation layer (web/UI) to interact with
core domain services. Acts as the orchestrator between UI and business logic,
enforcing clean architecture boundaries and managing application state.

Key Responsibilities:
- Parse and load simulator statistics from various sources
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
from collections.abc import Sequence
from concurrent.futures import Future
from typing import Any, cast

import numpy as np
import pandas as pd

from src.core.common.utils import normalize_user_path, sanitize_glob_pattern
from src.core.models import (
    ParseBatchResult,
    ScanFileResult,
    ScannedVariable,
    ScanResult,
    StatConfig,
)
from src.core.models.pattern_index_service import PatternIndexService
from src.core.models.data_models import (
    ColumnInfoResult,
    CsvPoolEntry,
    ParseVariableConfig,
    SavedConfigData,
    SavedConfigEntry,
    ScannedVariableDict,
    ShaperStepConfig,
)
from src.core.models.history_models import OperationRecord
from src.core.models.parsing_models import StatParamValue
from src.core.models.plot_protocol import PlotDeserializer
from src.core.models.visualization import FigureConfig
from src.core.services.data_services.data_services_api import DataServicesAPI
from src.core.services.managers.managers_api import ManagersAPI
from src.core.services.services_impl import DefaultServicesAPI
from src.core.services.shapers.shapers_api import ShapersAPI
from src.core.state.repository_state_manager import RepositoryStateManager
from src.parsing.parser_protocol import SimulationParser
from src.parsing.registry import SimulatorInfo, SimulatorRegistry

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

    def __init__(
        self,
        plot_deserializer: PlotDeserializer | None = None,
        parser: SimulationParser | None = None,
    ) -> None:
        """
        Initialize the Application API.

        Args:
            plot_deserializer: Optional callable that converts a dict into
                a ``PlotProtocol`` instance.  Injected into the repository
                layer so that portfolio restoration never imports web-layer
                classes directly.
            parser: Optional simulator parser backend.  Defaults to the
                gem5 parser from the ``SimulatorRegistry``.
        """
        self.state_manager = RepositoryStateManager(plot_deserializer=plot_deserializer)

        # Initialize services via unified facade
        self._services = DefaultServicesAPI(self.state_manager)

        # Simulator parser backend (lazy default to gem5 via registry)
        self._parser: SimulationParser = parser or SimulatorRegistry.get_parser("gem5")

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

    def get_current_view(self) -> dict[str, Any]:
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
        variables: Sequence[ParseVariableConfig | StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | list[ScannedVariableDict] | None = None,
    ) -> ParseBatchResult:
        """
        Submit parsing job to the service.

        Converts variable dictionaries to StatConfig objects.
        Repetition and regex expansion are handled by the parsing module.
        """
        stat_configs: list[StatConfig] = []
        for var in variables:
            if isinstance(var, dict):
                # Normalize type for consistency
                v_type = str(var.get("type", "scalar")).lower()

                # Check for aliasing (legacy compatibility)
                name = str(var.get("name", ""))
                alias = var.get("alias")
                params: dict[str, StatParamValue] = cast(dict[str, StatParamValue], dict(var))

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
                    is_regex=PatternIndexService.is_pattern_variable(name),
                    keep_indices=bool(var.get("keep_indices", var.get("keepIndices", False))),
                )
            elif hasattr(var, "name") and hasattr(var, "type") and not hasattr(var, "params"):
                # It's likely a ScannedVariable, convert to StatConfig
                config = StatConfig(
                    name=var.name,
                    type=var.type,
                    params={"entries": getattr(var, "entries", [])},
                    is_regex=PatternIndexService.is_pattern_variable(var.name),
                )
            else:
                config = var

            stat_configs.append(config)

        # Convert ScannedVariableDict to ScannedVariable if needed
        resolved_scanned: list[ScannedVariable] | None = None
        if scanned_vars is not None:
            resolved_scanned = [
                ScannedVariable.from_dict(sv) if isinstance(sv, dict) else sv for sv in scanned_vars
            ]

        return self._parser.submit_parse_async(
            stats_path, stats_pattern, stat_configs, output_dir, strategy_type, resolved_scanned
        )

    def finalize_parsing(
        self,
        output_dir: str,
        results: list[dict[str, Any]],
        strategy_type: str = "simple",
        var_names: list[str] | None = None,
    ) -> str | None:
        """Finalize parsing results into a CSV."""
        return self._parser.finalize_parsing(
            output_dir, results, strategy_type, var_names=var_names
        )

    def submit_scan_async(
        self, stats_path: str, stats_pattern: str = "stats.txt", limit: int = 5
    ) -> list[Future[ScanFileResult]]:
        """Submit scanning job. Each future resolves to a ``ScanFileResult``."""
        return self._parser.submit_scan_async(stats_path, stats_pattern, limit)

    def finalize_scan(self, results: list[ScanFileResult]) -> ScanResult:
        """Aggregate per-file scan results into a ``ScanResult``."""
        return self._parser.aggregate_scan_results(results)

    def get_parse_status(self) -> str:
        """Get current parsing status.

        Returns a static 'idle' status. Status tracking is handled
        at the UI layer via session state.
        """
        return "idle"

    def get_scanner_status(self) -> str:
        """Get current scanner status."""
        return "idle"

    # =========================================================================
    # Shapers & Pipelines
    # =========================================================================

    def apply_shapers(
        self, data: pd.DataFrame, pipeline_config: list[ShaperStepConfig]
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame."""
        return self._services.shapers.process_pipeline(data, pipeline_config)

    # =========================================================================
    # Configuration Management
    # =========================================================================

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: list[ShaperStepConfig],
        csv_path: str | None = None,
    ) -> str:
        """Save current configuration to disk."""
        return self._services.data_services.save_configuration(
            name, description, shapers_config, csv_path
        )

    def load_configuration(self, config_path: str) -> SavedConfigData:
        """Load configuration from file."""
        return self._services.data_services.load_configuration(config_path)

    def load_csv_pool(self) -> list[CsvPoolEntry]:
        """List available CSV files in the pool."""
        return self._services.data_services.load_csv_pool()

    def load_saved_configs(self) -> list[SavedConfigEntry]:
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

    def load_csv_file(self, file_path: str) -> pd.DataFrame:
        """Load a CSV file directly returning DataFrame."""
        return self._services.data_services.load_csv_file(file_path)

    def get_column_info(self, df: pd.DataFrame | None) -> ColumnInfoResult:
        """Get summary information about DataFrame columns for UI."""
        if df is None:
            return ColumnInfoResult(
                total_columns=0,
                total_rows=0,
                numeric_columns=[],
                categorical_columns=[],
                columns=[],
            )

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

        return ColumnInfoResult(
            total_columns=len(df.columns),
            total_rows=len(df),
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            columns=df.columns.tolist(),
        )

    # =========================================================================
    # Visualization Config (Delegated to StateManager)
    # =========================================================================

    def get_visualization_config(self, plot_id: int) -> "FigureConfig | None":
        """Retrieve the visualization config for a plot."""
        return self.state_manager.get_visualization_config(plot_id)

    def set_visualization_config(self, plot_id: int, config: FigureConfig) -> None:
        """Store the visualization config for a plot."""
        self.state_manager.set_visualization_config(plot_id, config)

    def remove_visualization_config(self, plot_id: int) -> None:
        """Remove the visualization config for a plot."""
        self.state_manager.remove_visualization_config(plot_id)

    # =========================================================================
    # Previews (Delegated to StateManager)
    # =========================================================================

    def set_preview(self, operation_name: str, data: pd.DataFrame) -> None:
        """Store a preview DataFrame for an operation."""
        self.state_manager.set_preview(operation_name, data)

    def get_preview(self, operation_name: str) -> pd.DataFrame | None:
        """Retrieve a preview DataFrame for an operation."""
        return self.state_manager.get_preview(operation_name)

    def has_preview(self, operation_name: str) -> bool:
        """Check if a preview exists for an operation."""
        return self.state_manager.has_preview(operation_name)

    def clear_preview(self, operation_name: str) -> None:
        """Clear a preview for an operation."""
        self.state_manager.clear_preview(operation_name)

    # =========================================================================
    # History (Delegated to StateManager)
    # =========================================================================

    def add_manager_history_record(self, record: OperationRecord) -> None:
        """Record a manager operation in both manager and portfolio history."""
        self.state_manager.add_manager_history_record(record)
        self.state_manager.add_portfolio_history_record(record)

    def get_manager_history(self) -> list[OperationRecord]:
        """Get the rolling manager operation history (last 10)."""
        return self.state_manager.get_manager_history()

    def get_portfolio_history(self) -> list[OperationRecord]:
        """Get the full portfolio operation history."""
        return self.state_manager.get_portfolio_history()

    def remove_manager_history_record(self, record: OperationRecord) -> None:
        """Remove a specific record from both manager and portfolio history."""
        self.state_manager.remove_manager_history_record(record)
        self.state_manager.remove_portfolio_history_record(record)

    # =========================================================================
    # Simulator Registry Facades (so web layer avoids parsing imports)
    # =========================================================================

    @staticmethod
    def available_simulators() -> list[str]:
        """Return the list of registered simulator names."""
        return SimulatorRegistry.available_simulators()

    @staticmethod
    def available_simulator_info() -> list[SimulatorInfo]:
        """Return metadata for all registered simulators."""
        return SimulatorRegistry.available_simulator_info()

    @staticmethod
    def get_simulator_info(name: str) -> SimulatorInfo:
        """Return metadata for a specific simulator."""
        return SimulatorRegistry.get_info(name)

    @staticmethod
    def cancel_pending_scans() -> None:
        """Cancel all pending scan futures to release memory."""
        from src.parsing.gem5.impl.pool.pool import ScanWorkPool

        ScanWorkPool.get_instance().cancel_all()
