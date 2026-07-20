"""
Default implementation of the DataServicesAPI protocol.

Delegates to CsvPoolService, ConfigService, DatasetSnapshotService,
VariableService, and PortfolioService.
"""

from collections.abc import Callable
from typing import Any

import pandas as pd

from src.core.models import DatasetSnapshotInfo, PlotProtocol, PortfolioData
from src.core.models.data_models import (
    CacheStatsInfo,
    CsvPoolEntry,
    ParseVariableConfig,
    SavedConfigData,
    SavedConfigEntry,
    ScannedVariableDict,
)
from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.data_services.config_service import ConfigService
from src.core.services.data_services.csv_pool_service import CsvPoolService
from src.core.services.data_services.dataset_snapshot_service import DatasetSnapshotService
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.services.data_services.variable_service import VariableService
from src.core.state.state_manager import StateManager


class DefaultDataServicesAPI:
    """Default implementation of DataServicesAPI.

    Delegates to CsvPoolService, ConfigService, DatasetSnapshotService,
    VariableService, and PortfolioService.
    """

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize with a StateManager for portfolio serialization."""
        self._portfolio_service = PortfolioService(state_manager)

    # -- CSV Pool --

    def load_csv_pool(self) -> list[CsvPoolEntry]:
        """List available CSV files in the pool with metadata."""
        return CsvPoolService.load_pool()

    def add_to_csv_pool(self, file_path: str) -> str:
        """Add a CSV file to the pool. Returns pool path."""
        return CsvPoolService.add_to_pool(file_path)

    def delete_from_csv_pool(self, file_path: str) -> bool:
        """Delete a CSV file from the pool."""
        return CsvPoolService.delete_from_pool(file_path)

    def load_csv_file(self, file_path: str) -> pd.DataFrame:
        """Load a CSV file returning a DataFrame."""
        return CsvPoolService.load_csv_file(file_path)

    # -- Configuration Persistence --

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: list[ShaperStepConfig],
        csv_path: str | None = None,
    ) -> str:
        """Save a configuration to disk. Returns saved file path."""
        return ConfigService.save_configuration(name, description, shapers_config, csv_path)

    def load_configuration(self, config_path: str) -> SavedConfigData:
        """Load a configuration from file."""
        return ConfigService.load_configuration(config_path)

    def load_saved_configs(self) -> list[SavedConfigEntry]:
        """List all saved configurations."""
        return ConfigService.load_saved_configs()

    def delete_configuration(self, config_path: str) -> bool:
        """Delete a configuration file."""
        return ConfigService.delete_configuration(config_path)

    # -- Cache Management --

    def get_cache_stats(self) -> CacheStatsInfo:
        """Return CSV pool cache statistics."""
        return CsvPoolService.get_cache_stats()

    def clear_caches(self) -> None:
        """Clear all CSV pool caches."""
        CsvPoolService.clear_caches()

    # -- Reusable Dataset Snapshots --

    def list_dataset_snapshots(self) -> tuple[DatasetSnapshotInfo, ...]:
        """List locally saved dataset snapshots without loading payloads."""
        return DatasetSnapshotService.list_snapshots()

    def save_dataset_snapshot(
        self,
        name: str,
        data: pd.DataFrame,
        *,
        source_dataset: str,
        overwrite: bool = False,
    ) -> DatasetSnapshotInfo:
        """Persist an exact fingerprinted dataset snapshot."""
        return DatasetSnapshotService.save_snapshot(
            name,
            data,
            source_dataset=source_dataset,
            overwrite=overwrite,
        )

    def load_dataset_snapshot(self, name: str) -> tuple[DatasetSnapshotInfo, pd.DataFrame]:
        """Load and verify a fingerprinted dataset snapshot."""
        return DatasetSnapshotService.load_snapshot(name)

    def delete_dataset_snapshot(self, name: str) -> None:
        """Delete one locally saved dataset snapshot."""
        DatasetSnapshotService.delete_snapshot(name)

    # -- Variable Management --

    def generate_variable_id(self) -> str:
        """Generate a unique variable identifier."""
        return VariableService.generate_variable_id()

    def add_variable(
        self,
        variables: list[ParseVariableConfig],
        var_config: ParseVariableConfig,
    ) -> list[ParseVariableConfig]:
        """Add a new variable to the list."""
        return VariableService.add_variable(variables, var_config)

    def update_variable(
        self,
        variables: list[ParseVariableConfig],
        index: int,
        var_config: ParseVariableConfig,
    ) -> list[ParseVariableConfig]:
        """Update an existing variable at the specified index."""
        return VariableService.update_variable(variables, index, var_config)

    def delete_variable(
        self,
        variables: list[ParseVariableConfig],
        index: int,
    ) -> list[ParseVariableConfig]:
        """Delete a variable at the specified index."""
        return VariableService.delete_variable(variables, index)

    def ensure_variable_ids(
        self, variables: list[ParseVariableConfig]
    ) -> list[ParseVariableConfig]:
        """Ensure all variables have unique IDs."""
        return VariableService.ensure_variable_ids(variables)

    def filter_internal_stats(
        self,
        entries: list[str],
        internal_stats: frozenset[str] | None = None,
    ) -> list[str]:
        """Filter out internal simulator statistics from entry list."""
        return VariableService.filter_internal_stats(entries, internal_stats)

    def find_variable_by_name(
        self,
        variables: list[ParseVariableConfig],
        name: str,
        exact: bool = True,
    ) -> ParseVariableConfig | None:
        """Find a variable by name (exact or regex match)."""
        return VariableService.find_variable_by_name(variables, name, exact)

    def aggregate_discovered_entries(
        self,
        snapshot: list[ScannedVariableDict],
        var_name: str,
    ) -> list[str]:
        """Aggregate entries for a variable across scanned files."""
        return VariableService.aggregate_discovered_entries(snapshot, var_name)

    def aggregate_distribution_range(
        self,
        snapshot: list[ScannedVariableDict],
        var_name: str,
    ) -> tuple[float | None, float | None]:
        """Aggregate min/max range for a distribution variable."""
        return VariableService.aggregate_distribution_range(snapshot, var_name)

    def parse_comma_separated_entries(self, entries_str: str) -> list[str]:
        """Parse comma-separated entry string into list."""
        return VariableService.parse_comma_separated_entries(entries_str)

    def format_entries_as_string(self, entries: list[str]) -> str:
        """Format list of entries as comma-separated string."""
        return VariableService.format_entries_as_string(entries)

    def find_entries_for_variable(
        self,
        available_variables: list[ScannedVariableDict],
        var_name: str,
    ) -> list[str]:
        """Find all entries for a variable by searching available/scanned variables."""
        return VariableService.find_entries_for_variable(available_variables, var_name)

    def update_scanned_entries(
        self,
        scanned_vars: list[ScannedVariableDict],
        var_name: str,
        new_entries: list[str],
    ) -> list[ScannedVariableDict]:
        """Update or add entries for a variable in the scanned variables list."""
        return VariableService.update_scanned_entries(scanned_vars, var_name, new_entries)

    def has_variable_with_name(
        self,
        variables: list[ParseVariableConfig],
        name: str,
    ) -> bool:
        """Check if a variable with the given name already exists."""
        return VariableService.has_variable_with_name(variables, name)

    def build_statistics_list(
        self,
        selected: dict[str, bool],
    ) -> list[str]:
        """Build a list of selected statistics from a boolean mapping."""
        return VariableService.build_statistics_list(selected)

    # -- Portfolio Management --

    def list_portfolios(self) -> list[str]:
        """List all available saved portfolios."""
        return self._portfolio_service.list_portfolios()

    def save_portfolio(
        self,
        name: str,
        data: pd.DataFrame | None,
        plots: list[PlotProtocol],
        config: dict[str, Any],
        plot_counter: int,
        csv_path: str | None = None,
        parse_variables: list[ParseVariableConfig] | None = None,
        figure_spec_enricher: None | (
            Callable[[dict[str, Any], str], dict[str, Any] | None]
        ) = None,
        overwrite: bool = True,
    ) -> None:
        """Serialize and save the current workspace state."""
        self._portfolio_service.save_portfolio(
            name,
            data,
            plots,
            config,
            plot_counter,
            csv_path,
            parse_variables,
            figure_spec_enricher,
            overwrite,
        )

    def load_portfolio(self, name: str) -> PortfolioData:
        """Load a portfolio by name."""
        return self._portfolio_service.load_portfolio(name)

    def delete_portfolio(self, name: str) -> None:
        """Delete a portfolio."""
        self._portfolio_service.delete_portfolio(name)
