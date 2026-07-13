"""Repository-backed implementation of the application state contract."""

import logging
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.models import PlotProtocol, PortfolioData, RestoreReport
from src.core.models.data_models import (
    CsvPoolEntry,
    ParseVariableConfig,
    SavedConfigEntry,
    ScannedVariableDict,
)
from src.core.models.history_models import OperationRecord
from src.core.models.plot_protocol import PlotDeserializer
from src.core.models.visualization.figure_config import FigureConfig
from src.core.state.repositories.session_repository import SessionRepository

logger: logging.Logger = logging.getLogger(__name__)


class RepositoryStateManager:
    """Delegate application state operations to a session repository."""

    def __init__(self, plot_deserializer: PlotDeserializer | None = None) -> None:
        """Initialize the repository layer.

        Args:
            plot_deserializer: Optional callable that converts a dict into
                a ``PlotProtocol`` instance.  Forwarded to SessionRepository
                so portfolio restoration never imports web-layer classes.
        """
        self._session_repo = SessionRepository(plot_deserializer=plot_deserializer)

    def initialize(self) -> None:
        """Re-initialize the session to clean defaults.

        Useful for resetting state without constructing a new instance.
        """
        self._session_repo.initialize_session()

    # ==================== Data Management ====================

    def get_data(self) -> pd.DataFrame | None:
        """Return the current source data."""
        return self._session_repo.data_repo.get_data()

    def set_data(
        self, data: pd.DataFrame | None, on_change: Callable[[], None] | None = None
    ) -> None:
        """Store source data and optionally invoke a change callback."""
        # Copy + enforce configuration-column dtypes via the shared ingestion
        # helper, so fresh loads and portfolio restores agree on dtypes.
        if data is not None:
            data = self._session_repo.enforce_config_dtypes(data)

        self._session_repo.data_repo.set_data(data, on_change)

    def get_processed_data(self) -> pd.DataFrame | None:
        """Return the current processed data."""
        return self._session_repo.data_repo.get_processed_data()

    def set_processed_data(self, data: pd.DataFrame | None) -> None:
        """Store processed data."""
        self._session_repo.data_repo.set_processed_data(data)

    def has_data(self) -> bool:
        """Whether source data is available."""
        return self._session_repo.data_repo.has_data()

    def clear_data(self) -> None:
        """Clear data, plots, and temporary files owned by the session."""
        temp_dir = self._session_repo.config_repo.get_temp_dir()
        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
            except OSError as e:
                logger.warning(f"STATE: Cleanup failed for {temp_dir}: {e}")

        self._session_repo.data_repo.clear_data()
        self._session_repo.config_repo.set_csv_path("")
        self._session_repo.config_repo.set_temp_dir("")
        self._session_repo.plot_repo.clear_plots()
        self._session_repo.plot_repo.set_plot_counter(0)
        self._session_repo.plot_repo.set_current_plot_id(None)

    # ==================== Config & Parser ====================

    def get_config(self) -> dict[str, Any]:
        """Return the application configuration."""
        return self._session_repo.config_repo.get_config()

    def set_config(self, config: dict[str, Any]) -> None:
        """Replace the application configuration."""
        self._session_repo.config_repo.set_config(config)

    def update_config(self, key: str, value: object) -> None:
        """Set one application configuration value."""
        self._session_repo.config_repo.update_config(key, value)

    def get_temp_dir(self) -> str | None:
        """Return the active temporary directory."""
        return self._session_repo.config_repo.get_temp_dir()

    def set_temp_dir(self, path: str) -> None:
        """Set the active temporary directory."""
        self._session_repo.config_repo.set_temp_dir(path)

    def get_csv_path(self) -> str | None:
        """Return the active CSV path."""
        return self._session_repo.config_repo.get_csv_path()

    def set_csv_path(self, path: str) -> None:
        """Set the active CSV path."""
        self._session_repo.config_repo.set_csv_path(path)

    def get_csv_pool(self) -> list[CsvPoolEntry]:
        """Return saved CSV-pool entries."""
        return self._session_repo.config_repo.get_csv_pool()

    def set_csv_pool(self, pool: list[CsvPoolEntry]) -> None:
        """Replace saved CSV-pool entries."""
        self._session_repo.config_repo.set_csv_pool(pool)

    def get_saved_configs(self) -> list[SavedConfigEntry]:
        """Return saved application configurations."""
        return self._session_repo.config_repo.get_saved_configs()

    def set_saved_configs(self, configs: list[SavedConfigEntry]) -> None:
        """Replace saved application configurations."""
        self._session_repo.config_repo.set_saved_configs(configs)

    def is_using_parser(self) -> bool:
        """Whether the parser is the active data source."""
        return self._session_repo.parser_repo.is_using_parser()

    def set_use_parser(self, use: bool) -> None:
        """Select whether the parser is the active data source."""
        self._session_repo.parser_repo.set_using_parser(use)

    def get_parse_variables(self) -> list[ParseVariableConfig]:
        """Return variables selected for parsing."""
        return self._session_repo.parser_repo.get_parse_variables()

    def set_parse_variables(self, variables: list[ParseVariableConfig]) -> None:
        """Replace variables selected for parsing."""
        self._session_repo.parser_repo.set_parse_variables(variables)

    def get_stats_path(self) -> str:
        """Return the simulator-statistics search path."""
        return self._session_repo.parser_repo.get_stats_path()

    def set_stats_path(self, path: str) -> None:
        """Set the simulator-statistics search path."""
        self._session_repo.parser_repo.set_stats_path(path)

    def get_stats_pattern(self) -> str:
        """Return the statistics filename pattern."""
        return self._session_repo.parser_repo.get_stats_pattern()

    def set_stats_pattern(self, pattern: str) -> None:
        """Set the statistics filename pattern."""
        self._session_repo.parser_repo.set_stats_pattern(pattern)

    def get_scanned_variables(self) -> list[ScannedVariableDict]:
        """Return variables found by the latest scan."""
        return self._session_repo.parser_repo.get_scanned_variables()

    def set_scanned_variables(self, variables: list[ScannedVariableDict]) -> None:
        """Replace variables found by the latest scan."""
        self._session_repo.parser_repo.set_scanned_variables(variables)

    def get_parser_strategy(self) -> str:
        """Return the selected parser strategy."""
        return self._session_repo.parser_repo.get_parser_strategy()

    def set_parser_strategy(self, strategy: str) -> None:
        """Set the parser strategy."""
        self._session_repo.parser_repo.set_parser_strategy(strategy)

    def get_simulator(self) -> str:
        """Return the selected simulator backend."""
        return self._session_repo.parser_repo.get_simulator()

    def set_simulator(self, simulator: str) -> None:
        """Set the simulator backend."""
        self._session_repo.parser_repo.set_simulator(simulator)

    # ==================== Plots ====================

    def get_plots(self) -> list[PlotProtocol]:
        """Return registered plots."""
        return self._session_repo.plot_repo.get_plots()

    def set_plots(self, plots: list[PlotProtocol]) -> None:
        """Replace registered plots."""
        self._session_repo.plot_repo.set_plots(plots)

    def add_plot(self, plot_obj: PlotProtocol) -> None:
        """Register a plot."""
        self._session_repo.plot_repo.add_plot(plot_obj)

    def get_plot_counter(self) -> int:
        """Return the latest allocated plot identifier."""
        return self._session_repo.plot_repo.get_plot_counter()

    def set_plot_counter(self, counter: int) -> None:
        """Set the latest allocated plot identifier."""
        self._session_repo.plot_repo.set_plot_counter(counter)

    def start_next_plot_id(self) -> int:
        """Allocate and return the next plot identifier."""
        return self._session_repo.plot_repo.increment_plot_counter()

    def get_current_plot_id(self) -> int | None:
        """Return the selected plot identifier."""
        return self._session_repo.plot_repo.get_current_plot_id()

    def set_current_plot_id(self, plot_id: int | None) -> None:
        """Set the selected plot identifier."""
        self._session_repo.plot_repo.set_current_plot_id(plot_id)

    # ==================== Visualization ====================

    def get_visualization_config(self, plot_id: int) -> FigureConfig | None:
        """Return the figure configuration for a plot."""
        return self._session_repo.visualization_repo.get_config(plot_id)

    def set_visualization_config(self, plot_id: int, config: FigureConfig) -> None:
        """Store the figure configuration for a plot."""
        self._session_repo.visualization_repo.set_config(plot_id, config)

    def remove_visualization_config(self, plot_id: int) -> None:
        """Remove the figure configuration for a plot."""
        self._session_repo.visualization_repo.remove_config(plot_id)

    # ==================== Previews ====================

    def set_preview(self, operation_name: str, data: pd.DataFrame) -> None:
        """Store preview data for an operation."""
        self._session_repo.preview_repo.set_preview(operation_name, data)

    def get_preview(self, operation_name: str) -> pd.DataFrame | None:
        """Return preview data for an operation."""
        return self._session_repo.preview_repo.get_preview(operation_name)

    def has_preview(self, operation_name: str) -> bool:
        """Whether preview data exists for an operation."""
        return self._session_repo.preview_repo.has_preview(operation_name)

    def clear_preview(self, operation_name: str) -> None:
        """Remove preview data for an operation."""
        self._session_repo.preview_repo.clear_preview(operation_name)

    # ==================== History ====================

    def add_manager_history_record(self, record: OperationRecord) -> None:
        """Append a data-manager history record."""
        self._session_repo.history_repo.add_manager_record(record)

    def get_manager_history(self) -> list[OperationRecord]:
        """Return data-manager history records."""
        return self._session_repo.history_repo.get_manager_history()

    def add_portfolio_history_record(self, record: OperationRecord) -> None:
        """Append a portfolio history record."""
        self._session_repo.history_repo.add_portfolio_record(record)

    def get_portfolio_history(self) -> list[OperationRecord]:
        """Return portfolio history records."""
        return self._session_repo.history_repo.get_portfolio_history()

    def remove_manager_history_record(self, record: OperationRecord) -> None:
        """Remove a data-manager history record."""
        self._session_repo.history_repo.remove_manager_record(record)

    def remove_portfolio_history_record(self, record: OperationRecord) -> None:
        """Remove a portfolio history record."""
        self._session_repo.history_repo.remove_portfolio_record(record)

    # ==================== Session ======================================

    def clear_all(self) -> None:
        """Reset all session repositories."""
        self._session_repo.clear_all()

    def restore_session(self, portfolio_data: PortfolioData) -> RestoreReport:
        """Restore session state from a portfolio snapshot."""
        return self._session_repo.restore_from_portfolio(portfolio_data)
