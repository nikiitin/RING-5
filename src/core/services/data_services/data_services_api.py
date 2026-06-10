"""
Data Services API Protocol -- Interface for data storage and retrieval.

Defines the contract for data persistence operations: CSV pool management,
configuration persistence, variable management, and portfolio workspace
snapshots.
"""

from collections.abc import Callable
from typing import (
    Any,
    Protocol,
    runtime_checkable,
)

import pandas as pd

from src.core.models import PlotProtocol, PortfolioData
from src.core.models.data_models import (
    CacheStatsInfo,
    CsvPoolEntry,
    ParseVariableConfig,
    SavedConfigData,
    SavedConfigEntry,
    ScannedVariableDict,
)
from src.core.models.shaper_models import ShaperStepConfig


@runtime_checkable
class DataServicesAPI(Protocol):
    """Protocol for data storage, retrieval, and domain entity management.

    Covers CSV pool management, saved configuration persistence,
    variable management, and portfolio workspace snapshots.
    """

    # -- CSV Pool --

    def load_csv_pool(self) -> list[CsvPoolEntry]:
        """List available CSV files in the pool with metadata."""
        ...

    def add_to_csv_pool(self, file_path: str) -> str:
        """Add a CSV file to the pool. Returns pool path."""
        ...

    def delete_from_csv_pool(self, file_path: str) -> bool:
        """Delete a CSV file from the pool."""
        ...

    def load_csv_file(self, file_path: str) -> pd.DataFrame:
        """Load a CSV file returning a DataFrame."""
        ...

    # -- Configuration Persistence --

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: list[ShaperStepConfig],
        csv_path: str | None = None,
    ) -> str:
        """Save a configuration to disk. Returns saved file path."""
        ...

    def load_configuration(self, config_path: str) -> SavedConfigData:
        """Load a configuration from file."""
        ...

    def load_saved_configs(self) -> list[SavedConfigEntry]:
        """List all saved configurations."""
        ...

    def delete_configuration(self, config_path: str) -> bool:
        """Delete a configuration file."""
        ...

    # -- Cache Management --

    def get_cache_stats(self) -> CacheStatsInfo:
        """Return CSV pool cache statistics."""
        ...

    def clear_caches(self) -> None:
        """Clear all CSV pool caches."""
        ...

    # -- Variable Management --

    def generate_variable_id(self) -> str:
        """Generate a unique variable identifier."""
        ...

    def add_variable(
        self,
        variables: list[ParseVariableConfig],
        var_config: ParseVariableConfig,
    ) -> list[ParseVariableConfig]:
        """Add a new variable to the list."""
        ...

    def update_variable(
        self,
        variables: list[ParseVariableConfig],
        index: int,
        var_config: ParseVariableConfig,
    ) -> list[ParseVariableConfig]:
        """Update an existing variable at the specified index."""
        ...

    def delete_variable(
        self,
        variables: list[ParseVariableConfig],
        index: int,
    ) -> list[ParseVariableConfig]:
        """Delete a variable at the specified index."""
        ...

    def ensure_variable_ids(
        self, variables: list[ParseVariableConfig]
    ) -> list[ParseVariableConfig]:
        """Ensure all variables have unique IDs."""
        ...

    def filter_internal_stats(
        self,
        entries: list[str],
        internal_stats: frozenset[str] | None = None,
    ) -> list[str]:
        """Filter out internal simulator statistics from entry list."""
        ...

    def find_variable_by_name(
        self,
        variables: list[ParseVariableConfig],
        name: str,
        exact: bool = True,
    ) -> ParseVariableConfig | None:
        """Find a variable by name (exact or regex match)."""
        ...

    def aggregate_discovered_entries(
        self,
        snapshot: list[ScannedVariableDict],
        var_name: str,
    ) -> list[str]:
        """Aggregate entries for a variable across scanned files."""
        ...

    def aggregate_distribution_range(
        self,
        snapshot: list[ScannedVariableDict],
        var_name: str,
    ) -> tuple[float | None, float | None]:
        """Aggregate min/max range for a distribution variable."""
        ...

    def parse_comma_separated_entries(self, entries_str: str) -> list[str]:
        """Parse comma-separated entry string into list."""
        ...

    def format_entries_as_string(self, entries: list[str]) -> str:
        """Format list of entries as comma-separated string."""
        ...

    def find_entries_for_variable(
        self,
        available_variables: list[ScannedVariableDict],
        var_name: str,
    ) -> list[str]:
        """Find all entries for a variable by searching available/scanned variables."""
        ...

    def update_scanned_entries(
        self,
        scanned_vars: list[ScannedVariableDict],
        var_name: str,
        new_entries: list[str],
    ) -> list[ScannedVariableDict]:
        """Update or add entries for a variable in the scanned variables list."""
        ...

    def has_variable_with_name(
        self,
        variables: list[ParseVariableConfig],
        name: str,
    ) -> bool:
        """Check if a variable with the given name already exists."""
        ...

    def build_statistics_list(
        self,
        selected: dict[str, bool],
    ) -> list[str]:
        """Build a list of selected statistics from a boolean mapping."""
        ...

    # -- Portfolio Management --

    def list_portfolios(self) -> list[str]:
        """List all available saved portfolios."""
        ...

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
        ...

    def load_portfolio(self, name: str) -> PortfolioData:
        """Load a portfolio by name."""
        ...

    def delete_portfolio(self, name: str) -> None:
        """Delete a portfolio."""
        ...
