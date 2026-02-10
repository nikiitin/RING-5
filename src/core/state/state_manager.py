"""
State Manager Protocol - Interface Contract.

Defines the StateManager protocol that establishes the contract
for all state management implementations. Layer B (ApplicationAPI) depends
on this protocol, not on any concrete implementation.

This separation ensures the interface is fully agnostic of the implementation,
following the Dependency Inversion Principle.
"""

from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

import pandas as pd

from src.core.models import PlotProtocol, PortfolioData


@runtime_checkable
class StateManager(Protocol):
    """
    Protocol defining the contract for State Management.
    Layer B (ApplicationAPI) depends on this protocol, not the implementation.
    """

    def initialize(self) -> None:
        """Initialize the state manager."""

    # Data

    def get_data(self) -> Optional[pd.DataFrame]:
        """Get the current raw DataFrame."""

    def set_data(
        self, data: Optional[pd.DataFrame], on_change: Optional[Callable[[], None]] = None
    ) -> None:
        """Set the raw DataFrame with optional change callback."""

    def get_processed_data(self) -> Optional[pd.DataFrame]:
        """Get the current processed DataFrame."""

    def set_processed_data(self, data: Optional[pd.DataFrame]) -> None:
        """Set the processed DataFrame."""

    def has_data(self) -> bool:
        """Check if data is loaded."""

    def clear_data(self) -> None:
        """Clear all loaded data."""

    # Config
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration dictionary."""

    def set_config(self, config: Dict[str, Any]) -> None:
        """Set the configuration dictionary."""

    def update_config(self, key: str, value: Any) -> None:
        """Update a single configuration key."""

    def get_temp_dir(self) -> Optional[str]:
        """Get the temporary directory path."""

    def set_temp_dir(self, path: str) -> None:
        """Set the temporary directory path."""

    def get_csv_path(self) -> Optional[str]:
        """Get the current CSV file path."""

    def set_csv_path(self, path: str) -> None:
        """Set the current CSV file path."""

    def get_csv_pool(self) -> List[Dict[str, Any]]:
        """Get the CSV file pool."""

    def set_csv_pool(self, pool: List[Dict[str, Any]]) -> None:
        """Set the CSV file pool."""

    def get_saved_configs(self) -> List[Dict[str, Any]]:
        """Get list of saved configurations."""

    def set_saved_configs(self, configs: List[Dict[str, Any]]) -> None:
        """Set the saved configurations list."""

    # Parser
    def is_using_parser(self) -> bool:
        """Check if parser mode is active."""

    def set_use_parser(self, use: bool) -> None:
        """Enable or disable parser mode."""

    def get_parse_variables(self) -> List[Dict[str, Any]]:
        """Get the list of parse variable configurations."""

    def set_parse_variables(self, variables: List[Dict[str, Any]]) -> None:
        """Set the parse variable configurations."""

    def get_stats_path(self) -> str:
        """Get the stats file search path."""

    def set_stats_path(self, path: str) -> None:
        """Set the stats file search path."""

    def get_stats_pattern(self) -> str:
        """Get the stats filename pattern."""

    def set_stats_pattern(self, pattern: str) -> None:
        """Set the stats filename pattern."""

    def get_scanned_variables(self) -> List[Dict[str, Any]]:
        """Get the list of scanned variables."""

    def set_scanned_variables(self, variables: List[Dict[str, Any]]) -> None:
        """Set the scanned variables list."""

    def get_parser_strategy(self) -> str:
        """Get the current parser strategy type."""

    def set_parser_strategy(self, strategy: str) -> None:
        """Set the parser strategy type."""

    # Plots
    def get_plots(self) -> List[PlotProtocol]:
        """Get the list of plot objects."""

    def set_plots(self, plots: List[PlotProtocol]) -> None:
        """Set the list of plot objects."""

    def add_plot(self, plot_obj: PlotProtocol) -> None:
        """Add a plot object to the list."""

    def get_plot_counter(self) -> int:
        """Get the current plot ID counter."""

    def set_plot_counter(self, counter: int) -> None:
        """Set the plot ID counter."""

    def start_next_plot_id(self) -> int:
        """Increment and return the next plot ID."""

    def get_current_plot_id(self) -> Optional[int]:
        """Get the currently selected plot ID."""

    def set_current_plot_id(self, plot_id: Optional[int]) -> None:
        """Set the currently selected plot ID."""

    # Previews
    def set_preview(self, operation_name: str, data: pd.DataFrame) -> None:
        """Store a preview DataFrame for an operation."""

    def get_preview(self, operation_name: str) -> Optional[pd.DataFrame]:
        """Get a preview DataFrame for an operation."""

    def has_preview(self, operation_name: str) -> bool:
        """Check if a preview exists for an operation."""

    def clear_preview(self, operation_name: str) -> None:
        """Clear a preview for an operation."""

    # Session
    def clear_all(self) -> None:
        """Clear all state."""

    def restore_session(self, portfolio_data: PortfolioData) -> None:
        """Restore state from a portfolio snapshot."""
