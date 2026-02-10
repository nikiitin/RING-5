"""
Default implementation of the DataServicesAPI protocol.

Delegates to CsvPoolService, ConfigService, VariableService,
and PortfolioService.
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.core.models import PlotProtocol
from src.core.services.data_services.config_service import ConfigService
from src.core.services.data_services.csv_pool_service import CsvPoolService
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.services.data_services.variable_service import VariableService
from src.core.state.state_manager import StateManager


class DefaultDataServicesAPI:
    """Default implementation of DataServicesAPI.

    Delegates to CsvPoolService, ConfigService, VariableService,
    and PortfolioService.
    """

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize with a StateManager for portfolio serialization."""
        self._portfolio_service = PortfolioService(state_manager)

    # -- CSV Pool --

    def load_csv_pool(self) -> List[Dict[str, Any]]:
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
        shapers_config: List[Dict[str, Any]],
        csv_path: Optional[str] = None,
    ) -> str:
        """Save a configuration to disk. Returns saved file path."""
        return ConfigService.save_configuration(name, description, shapers_config, csv_path)

    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """Load a configuration from file."""
        return ConfigService.load_configuration(config_path)

    def load_saved_configs(self) -> List[Dict[str, Any]]:
        """List all saved configurations."""
        return ConfigService.load_saved_configs()

    def delete_configuration(self, config_path: str) -> bool:
        """Delete a configuration file."""
        return ConfigService.delete_configuration(config_path)

    # -- Cache Management --

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return CSV pool cache statistics."""
        return CsvPoolService.get_cache_stats()

    def clear_caches(self) -> None:
        """Clear all CSV pool caches."""
        CsvPoolService.clear_caches()

    # -- Variable Management --

    def generate_variable_id(self) -> str:
        """Generate a unique variable identifier."""
        return VariableService.generate_variable_id()

    def add_variable(
        self,
        variables: List[Dict[str, Any]],
        var_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Add a new variable to the list."""
        return VariableService.add_variable(variables, var_config)

    def update_variable(
        self,
        variables: List[Dict[str, Any]],
        index: int,
        var_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Update an existing variable at the specified index."""
        return VariableService.update_variable(variables, index, var_config)

    def delete_variable(
        self,
        variables: List[Dict[str, Any]],
        index: int,
    ) -> List[Dict[str, Any]]:
        """Delete a variable at the specified index."""
        return VariableService.delete_variable(variables, index)

    def ensure_variable_ids(self, variables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure all variables have unique IDs."""
        return VariableService.ensure_variable_ids(variables)

    def filter_internal_stats(self, entries: List[str]) -> List[str]:
        """Filter out internal gem5 statistics from entry list."""
        return VariableService.filter_internal_stats(entries)

    def find_variable_by_name(
        self,
        variables: List[Dict[str, Any]],
        name: str,
        exact: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Find a variable by name (exact or regex match)."""
        return VariableService.find_variable_by_name(variables, name, exact)

    def aggregate_discovered_entries(
        self,
        snapshot: List[Dict[str, Any]],
        var_name: str,
    ) -> List[str]:
        """Aggregate entries for a variable across scanned files."""
        return VariableService.aggregate_discovered_entries(snapshot, var_name)

    def aggregate_distribution_range(
        self,
        snapshot: List[Dict[str, Any]],
        var_name: str,
    ) -> Tuple[Optional[float], Optional[float]]:
        """Aggregate min/max range for a distribution variable."""
        return VariableService.aggregate_distribution_range(snapshot, var_name)

    def parse_comma_separated_entries(self, entries_str: str) -> List[str]:
        """Parse comma-separated entry string into list."""
        return VariableService.parse_comma_separated_entries(entries_str)

    def format_entries_as_string(self, entries: List[str]) -> str:
        """Format list of entries as comma-separated string."""
        return VariableService.format_entries_as_string(entries)

    # -- Portfolio Management --

    def list_portfolios(self) -> List[str]:
        """List all available saved portfolios."""
        return self._portfolio_service.list_portfolios()

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
        self._portfolio_service.save_portfolio(
            name, data, plots, config, plot_counter, csv_path, parse_variables
        )

    def load_portfolio(self, name: str) -> Dict[str, Any]:
        """Load a portfolio by name."""
        return self._portfolio_service.load_portfolio(name)

    def delete_portfolio(self, name: str) -> None:
        """Delete a portfolio."""
        self._portfolio_service.delete_portfolio(name)
