"""
State Manager Protocol - Interface Contract.

Defines the StateManager protocol that establishes the contract
for all state management implementations. Layer B (ApplicationAPI) depends
on this protocol, not on any concrete implementation.

This separation ensures the interface is fully agnostic of the implementation,
following the Dependency Inversion Principle.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import pandas as pd

from src.core.models import PlotProtocol, PortfolioData, RestoreReport
from src.core.models.data_models import (
    CsvPoolEntry,
    ParseVariableConfig,
    SavedConfigEntry,
    ScannedVariableDict,
)
from src.core.models.history_models import OperationRecord

if TYPE_CHECKING:
    from src.core.models.visualization.figure_config import FigureConfig


@runtime_checkable
class StateManager(Protocol):
    """
    Protocol defining the contract for State Management.
    Layer B (ApplicationAPI) depends on this protocol, not the implementation.
    """

    def initialize(self) -> None:
        """Initialize the state manager."""
        raise NotImplementedError

    # Data

    def get_data(self) -> pd.DataFrame | None:
        """Get the current raw DataFrame."""
        raise NotImplementedError

    def set_data(
        self, data: pd.DataFrame | None, on_change: Callable[[], None] | None = None
    ) -> None:
        """Set the raw DataFrame with optional change callback."""
        raise NotImplementedError

    def get_processed_data(self) -> pd.DataFrame | None:
        """Get the current processed DataFrame."""
        raise NotImplementedError

    def set_processed_data(self, data: pd.DataFrame | None) -> None:
        """Set the processed DataFrame."""
        raise NotImplementedError

    def has_data(self) -> bool:
        """Check if data is loaded."""
        raise NotImplementedError

    def clear_data(self) -> None:
        """Clear all loaded data."""
        raise NotImplementedError

    # Config
    def get_config(self) -> dict[str, Any]:
        """Get the current configuration dictionary."""
        raise NotImplementedError

    def set_config(self, config: dict[str, Any]) -> None:
        """Set the configuration dictionary."""
        raise NotImplementedError

    def update_config(self, key: str, value: object) -> None:
        """Update a single configuration key."""
        raise NotImplementedError

    def get_temp_dir(self) -> str | None:
        """Get the temporary directory path."""
        raise NotImplementedError

    def set_temp_dir(self, path: str) -> None:
        """Set the temporary directory path."""
        raise NotImplementedError

    def get_csv_path(self) -> str | None:
        """Get the current CSV file path."""
        raise NotImplementedError

    def set_csv_path(self, path: str) -> None:
        """Set the current CSV file path."""
        raise NotImplementedError

    def get_csv_pool(self) -> list[CsvPoolEntry]:
        """Get the CSV file pool."""
        raise NotImplementedError

    def set_csv_pool(self, pool: list[CsvPoolEntry]) -> None:
        """Set the CSV file pool."""
        raise NotImplementedError

    def get_saved_configs(self) -> list[SavedConfigEntry]:
        """Get list of saved configurations."""
        raise NotImplementedError

    def set_saved_configs(self, configs: list[SavedConfigEntry]) -> None:
        """Set the saved configurations list."""
        raise NotImplementedError

    # Parser
    def is_using_parser(self) -> bool:
        """Check if parser mode is active."""
        raise NotImplementedError

    def set_use_parser(self, use: bool) -> None:
        """Enable or disable parser mode."""
        raise NotImplementedError

    def get_parse_variables(self) -> list[ParseVariableConfig]:
        """Get the list of parse variable configurations."""
        raise NotImplementedError

    def set_parse_variables(self, variables: list[ParseVariableConfig]) -> None:
        """Set the parse variable configurations."""
        raise NotImplementedError

    def get_stats_path(self) -> str:
        """Get the stats file search path."""
        raise NotImplementedError

    def set_stats_path(self, path: str) -> None:
        """Set the stats file search path."""
        raise NotImplementedError

    def get_stats_pattern(self) -> str:
        """Get the stats filename pattern."""
        raise NotImplementedError

    def set_stats_pattern(self, pattern: str) -> None:
        """Set the stats filename pattern."""
        raise NotImplementedError

    def get_scanned_variables(self) -> list[ScannedVariableDict]:
        """Get the list of scanned variables."""
        raise NotImplementedError

    def set_scanned_variables(self, variables: list[ScannedVariableDict]) -> None:
        """Set the scanned variables list."""
        raise NotImplementedError

    def get_parser_strategy(self) -> str:
        """Get the current parser strategy type."""
        raise NotImplementedError

    def set_parser_strategy(self, strategy: str) -> None:
        """Set the parser strategy type."""
        raise NotImplementedError

    def get_simulator(self) -> str:
        """Get the currently selected simulator backend."""
        raise NotImplementedError

    def set_simulator(self, simulator: str) -> None:
        """Set the simulator backend to use for parsing."""
        raise NotImplementedError

    # Plots
    def get_plots(self) -> list[PlotProtocol]:
        """Get the list of plot objects."""
        raise NotImplementedError

    def set_plots(self, plots: list[PlotProtocol]) -> None:
        """Set the list of plot objects."""
        raise NotImplementedError

    def add_plot(self, plot_obj: PlotProtocol) -> None:
        """Add a plot object to the list."""
        raise NotImplementedError

    def get_plot_counter(self) -> int:
        """Get the current plot ID counter."""
        raise NotImplementedError

    def set_plot_counter(self, counter: int) -> None:
        """Set the plot ID counter."""
        raise NotImplementedError

    def start_next_plot_id(self) -> int:
        """Increment and return the next plot ID."""
        raise NotImplementedError

    def get_current_plot_id(self) -> int | None:
        """Get the currently selected plot ID."""
        raise NotImplementedError

    def set_current_plot_id(self, plot_id: int | None) -> None:
        """Set the currently selected plot ID."""
        raise NotImplementedError

    # Visualization config
    def get_visualization_config(self, plot_id: int) -> "FigureConfig | None":
        """Get the resolved visualization config for a plot, if any."""
        raise NotImplementedError

    def set_visualization_config(self, plot_id: int, config: "FigureConfig") -> None:
        """Store the visualization config for a plot."""
        raise NotImplementedError

    def remove_visualization_config(self, plot_id: int) -> None:
        """Remove the visualization config for a plot."""
        raise NotImplementedError

    # Previews
    def set_preview(self, operation_name: str, data: pd.DataFrame) -> None:
        """Store a preview DataFrame for an operation."""
        raise NotImplementedError

    def get_preview(self, operation_name: str) -> pd.DataFrame | None:
        """Get a preview DataFrame for an operation."""
        raise NotImplementedError

    def has_preview(self, operation_name: str) -> bool:
        """Check if a preview exists for an operation."""
        raise NotImplementedError

    def clear_preview(self, operation_name: str) -> None:
        """Clear a preview for an operation."""
        raise NotImplementedError

    # History
    def add_manager_history_record(self, record: OperationRecord) -> None:
        """Add an operation record to the manager history (rolling 10)."""
        raise NotImplementedError

    def get_manager_history(self) -> list[OperationRecord]:
        """Get the manager operation history."""
        raise NotImplementedError

    def add_portfolio_history_record(self, record: OperationRecord) -> None:
        """Add an operation record to the portfolio history (unbounded)."""
        raise NotImplementedError

    def get_portfolio_history(self) -> list[OperationRecord]:
        """Get the portfolio operation history."""
        raise NotImplementedError

    def remove_manager_history_record(self, record: OperationRecord) -> None:
        """Remove a specific record from manager history."""
        raise NotImplementedError

    def remove_portfolio_history_record(self, record: OperationRecord) -> None:
        """Remove a specific record from portfolio history."""
        raise NotImplementedError

    # Session
    def clear_all(self) -> None:
        """Clear all state."""
        raise NotImplementedError

    def restore_session(self, portfolio_data: PortfolioData) -> RestoreReport:
        """Restore state from a portfolio snapshot.

        Returns:
            A :class:`RestoreReport` recording what was restored and what
            was skipped (and why) — restore is best-effort per item.
        """
        raise NotImplementedError
