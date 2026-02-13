"""
Data Services API Protocol -- Interface for data storage and retrieval.

Defines the contract for data persistence operations: CSV pool management,
configuration persistence, variable management, and portfolio workspace
snapshots.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

import pandas as pd

from src.core.models import PlotProtocol


@runtime_checkable
class DataServicesAPI(Protocol):
    """Protocol for data storage, retrieval, and domain entity management.

    Covers CSV pool management, saved configuration persistence,
    gem5 variable management, and portfolio workspace snapshots.
    """

    # -- CSV Pool --

    def load_csv_pool(self) -> List[Dict[str, Any]]:
        """List available CSV files in the pool with metadata."""

    def add_to_csv_pool(self, file_path: str) -> str:
        """Add a CSV file to the pool. Returns pool path."""

    def delete_from_csv_pool(self, file_path: str) -> bool:
        """Delete a CSV file from the pool."""

    def load_csv_file(self, file_path: str) -> pd.DataFrame:
        """Load a CSV file returning a DataFrame."""

    # -- Configuration Persistence --

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: List[Dict[str, Any]],
        csv_path: Optional[str] = None,
    ) -> str:
        """Save a configuration to disk. Returns saved file path."""

    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """Load a configuration from file."""

    def load_saved_configs(self) -> List[Dict[str, Any]]:
        """List all saved configurations."""

    def delete_configuration(self, config_path: str) -> bool:
        """Delete a configuration file."""

    # -- Cache Management --

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return CSV pool cache statistics."""

    def clear_caches(self) -> None:
        """Clear all CSV pool caches."""

    # -- Variable Management --

    def generate_variable_id(self) -> str:
        """Generate a unique variable identifier."""

    def add_variable(
        self,
        variables: List[Dict[str, Any]],
        var_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Add a new variable to the list."""

    def update_variable(
        self,
        variables: List[Dict[str, Any]],
        index: int,
        var_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Update an existing variable at the specified index."""

    def delete_variable(
        self,
        variables: List[Dict[str, Any]],
        index: int,
    ) -> List[Dict[str, Any]]:
        """Delete a variable at the specified index."""

    def ensure_variable_ids(self, variables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure all variables have unique IDs."""

    def filter_internal_stats(self, entries: List[str]) -> List[str]:
        """Filter out internal gem5 statistics from entry list."""

    def find_variable_by_name(
        self,
        variables: List[Dict[str, Any]],
        name: str,
        exact: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Find a variable by name (exact or regex match)."""

    def aggregate_discovered_entries(
        self,
        snapshot: List[Dict[str, Any]],
        var_name: str,
    ) -> List[str]:
        """Aggregate entries for a variable across scanned files."""

    def aggregate_distribution_range(
        self,
        snapshot: List[Dict[str, Any]],
        var_name: str,
    ) -> Tuple[Optional[float], Optional[float]]:
        """Aggregate min/max range for a distribution variable."""

    def parse_comma_separated_entries(self, entries_str: str) -> List[str]:
        """Parse comma-separated entry string into list."""

    def format_entries_as_string(self, entries: List[str]) -> str:
        """Format list of entries as comma-separated string."""

    def find_entries_for_variable(
        self,
        available_variables: List[Dict[str, Any]],
        var_name: str,
    ) -> List[str]:
        """Find all entries for a variable by searching available/scanned variables."""

    def update_scanned_entries(
        self,
        scanned_vars: List[Dict[str, Any]],
        var_name: str,
        new_entries: List[str],
    ) -> List[Dict[str, Any]]:
        """Update or add entries for a variable in the scanned variables list."""

    def has_variable_with_name(
        self,
        variables: List[Dict[str, Any]],
        name: str,
    ) -> bool:
        """Check if a variable with the given name already exists."""

    def build_statistics_list(
        self,
        selected: Dict[str, bool],
    ) -> List[str]:
        """Build a list of selected statistics from a boolean mapping."""

    # -- Portfolio Management --

    def list_portfolios(self) -> List[str]:
        """List all available saved portfolios."""

    def save_portfolio(
        self,
        name: str,
        data: pd.DataFrame,
        plots: List[PlotProtocol],
        config: Dict[str, Any],
        plot_counter: int,
        csv_path: Optional[str] = None,
        parse_variables: Optional[List[str]] = None,
    ) -> None:
        """Serialize and save the current workspace state."""

    def load_portfolio(self, name: str) -> Dict[str, Any]:
        """Load a portfolio by name."""

    def delete_portfolio(self, name: str) -> None:
        """Delete a portfolio."""
