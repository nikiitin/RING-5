"""
RING-5 State Manager
Centralized session state management for the Streamlit application.
Ensures Backend-Frontend synchronization and type safety.

ARCHITECTURE NOTE:
This class acts as a FACADE over specialized repositories:
- DataRepository: Primary and processed data
- PlotRepository: Plot objects and counters
- ParserStateRepository: gem5 parser state
- ConfigRepository: Configuration management
- SessionRepository: Session lifecycle
"""

import logging
import shutil
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypedDict

import pandas as pd

from src.plotting import BasePlot

# Import new repository layer
from src.web.repositories import (
    ConfigRepository,
    DataRepository,
    ParserStateRepository,
    PlotRepository,
    SessionRepository,
)

# Import shared types
from src.web.types import PortfolioData

logger: logging.Logger = logging.getLogger(__name__)


class ParseVariable(TypedDict, total=False):
    """Type definition for a parse variable configuration."""

    name: str
    type: str  # "scalar", "vector", "distribution", "histogram", "configuration"
    _id: str  # UUID for UI tracking
    entries: List[str]  # For vector types
    minimum: Optional[float]  # For distribution types
    maximum: Optional[float]  # For distribution types


class CsvPoolEntry(TypedDict):
    """Type definition for CSV pool registry entry."""

    path: str
    name: str
    added_at: str


class ConfigEntry(TypedDict):
    """Type definition for saved configuration entry."""

    path: str
    name: str
    description: str


class StateKey(Enum):
    """Enumerate all valid session state keys to prevent typos."""

    DATA = "data"
    PROCESSED_DATA = "processed_data"
    CONFIG = "config"
    TEMP_DIR = "temp_dir"
    CSV_PATH = "csv_path"
    USE_PARSER = "use_parser"
    CSV_POOL = "csv_pool"
    SAVED_CONFIGS = "saved_configs"
    PARSE_VARIABLES = "parse_variables"
    STATS_PATH = "stats_path"
    STATS_PATTERN = "stats_pattern"
    SCANNED_VARIABLES = "scanned_variables"
    PLOTS_OBJECTS = "plots_objects"
    PLOT_COUNTER = "plot_counter"
    CURRENT_PLOT_ID = "current_plot_id"


class StateManager:
    """
    Manages application session state with type safety and validation.

    Adheres to Rule #1: Ensures backend changes trigger immediate frontend updates
    by providing a centralized state transition layer.
    """

    # Constants for direct access if needed
    DATA = StateKey.DATA.value
    PROCESSED_DATA = StateKey.PROCESSED_DATA.value
    CONFIG = StateKey.CONFIG.value
    TEMP_DIR = StateKey.TEMP_DIR.value
    CSV_PATH = StateKey.CSV_PATH.value
    USE_PARSER = StateKey.USE_PARSER.value
    CSV_POOL = StateKey.CSV_POOL.value
    SAVED_CONFIGS = StateKey.SAVED_CONFIGS.value
    PARSE_VARIABLES = StateKey.PARSE_VARIABLES.value
    STATS_PATH = StateKey.STATS_PATH.value
    STATS_PATTERN = StateKey.STATS_PATTERN.value
    SCANNED_VARIABLES = StateKey.SCANNED_VARIABLES.value
    PLOTS_OBJECTS = StateKey.PLOTS_OBJECTS.value
    PLOT_COUNTER = StateKey.PLOT_COUNTER.value
    CURRENT_PLOT_ID = StateKey.CURRENT_PLOT_ID.value

    @staticmethod
    def initialize() -> None:
        """
        Initialize all session state variables with scientific defaults.

        DELEGATED TO: SessionRepository
        """
        SessionRepository.initialize_session()

    # ==================== Data Management ====================
    # DELEGATED TO: DataRepository

    @staticmethod
    def get_data() -> Optional[pd.DataFrame]:
        """
        Get the current base dataset.

        DELEGATED TO: DataRepository
        """
        return DataRepository.get_data()

    @staticmethod
    def set_data(
        data: Optional[pd.DataFrame], on_change: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Set the current data and enforce categorical constraints.

        DELEGATED TO: DataRepository
        Note: Type enforcement for configuration variables applied here
        """
        if data is not None:
            try:
                variables: List[Dict[str, Any]] = ParserStateRepository.get_parse_variables()
                config_vars: List[str] = [
                    v["name"] for v in variables if v.get("type") == "configuration"
                ]
                for col in config_vars:
                    if col in data.columns:
                        data[col] = data[col].astype(str)
            except Exception as e:
                logger.error(f"STATE: Type enforcement failed: {e}")

        DataRepository.set_data(data, on_change)

    @staticmethod
    def get_processed_data() -> Optional[pd.DataFrame]:
        """
        Get the processed/transformed dataset.

        DELEGATED TO: DataRepository
        """
        return DataRepository.get_processed_data()

    @staticmethod
    def set_processed_data(data: Optional[pd.DataFrame]) -> None:
        """
        Set the processed/transformed dataset.

        DELEGATED TO: DataRepository
        """
        DataRepository.set_processed_data(data)

    @staticmethod
    def has_data() -> bool:
        """
        Check if any data is loaded.

        DELEGATED TO: DataRepository
        """
        return DataRepository.has_data()

    @staticmethod
    def clear_data() -> None:
        """
        Reset data-related state and clean up temp storage.

        PARTIALLY DELEGATED: Temp dir cleanup here, data clearing to DataRepository
        """
        temp_dir = ConfigRepository.get_temp_dir()
        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
            except OSError as e:
                logger.warning(f"STATE: Cleanup failed for {temp_dir}: {e}")

        DataRepository.clear_data()
        ConfigRepository.set_csv_path("")
        ConfigRepository.set_temp_dir("")
        PlotRepository.clear_plots()
        PlotRepository.set_plot_counter(0)
        PlotRepository.set_current_plot_id(None)

    @staticmethod
    def clear_all() -> None:
        """
        Clear all session state.

        DELEGATED TO: SessionRepository
        """
        SessionRepository.clear_all()

    # ==================== Configuration & Parser State ====================
    # DELEGATED TO: ConfigRepository and ParserStateRepository

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Get the complete configuration dictionary.

        DELEGATED TO: ConfigRepository
        """
        return ConfigRepository.get_config()

    @staticmethod
    def set_config(config: Dict[str, Any]) -> None:
        """
        Set the complete configuration dictionary.

        DELEGATED TO: ConfigRepository
        """
        ConfigRepository.set_config(config)

    @staticmethod
    def update_config(key: str, value: Any) -> None:
        """
        Update a specific configuration key.

        DELEGATED TO: ConfigRepository
        """
        ConfigRepository.update_config(key, value)

    @staticmethod
    def get_temp_dir() -> Optional[str]:
        """
        Get temporary directory path.

        DELEGATED TO: ConfigRepository
        """
        return ConfigRepository.get_temp_dir()

    @staticmethod
    def set_temp_dir(path: str) -> None:
        """
        Set the temporary directory path.

        DELEGATED TO: ConfigRepository
        """
        ConfigRepository.set_temp_dir(path)

    @staticmethod
    def get_csv_path() -> Optional[str]:
        """
        Get the current CSV file path.

        DELEGATED TO: ConfigRepository
        """
        return ConfigRepository.get_csv_path()

    @staticmethod
    def set_csv_path(path: str) -> None:
        """
        Set the current CSV file path.

        DELEGATED TO: ConfigRepository
        """
        ConfigRepository.set_csv_path(path)

    @staticmethod
    def is_using_parser() -> bool:
        """
        Check if using gem5 parser mode.

        DELEGATED TO: ParserStateRepository
        """
        return ParserStateRepository.is_using_parser()

    @staticmethod
    def set_use_parser(use: bool) -> None:
        """
        Set parser mode flag.

        DELEGATED TO: ParserStateRepository
        """
        ParserStateRepository.set_using_parser(use)

    @staticmethod
    def get_csv_pool() -> List[Dict[str, Any]]:
        """
        Get the CSV pool registry.

        DELEGATED TO: ConfigRepository
        """
        return ConfigRepository.get_csv_pool()

    @staticmethod
    def set_csv_pool(pool: List[Dict[str, Any]]) -> None:
        """
        Set the CSV pool registry.

        DELEGATED TO: ConfigRepository
        """
        ConfigRepository.set_csv_pool(pool)

    @staticmethod
    def get_saved_configs() -> List[Dict[str, Any]]:
        """
        Get list of saved configurations.

        DELEGATED TO: ConfigRepository
        """
        return ConfigRepository.get_saved_configs()

    @staticmethod
    def set_saved_configs(configs: List[Dict[str, Any]]) -> None:
        """
        Set the list of saved configurations.

        DELEGATED TO: ConfigRepository
        """
        ConfigRepository.set_saved_configs(configs)

    @staticmethod
    def get_parse_variables() -> List[Dict[str, Any]]:
        """
        Get parse variables list.

        DELEGATED TO: ParserStateRepository
        """
        return ParserStateRepository.get_parse_variables()

    @staticmethod
    def set_parse_variables(variables: List[Dict[str, Any]]) -> None:
        """
        Set parse variables.

        DELEGATED TO: ParserStateRepository
        """
        ParserStateRepository.set_parse_variables(variables)

    @staticmethod
    def get_stats_path() -> str:
        """
        Get the gem5 stats base path.

        DELEGATED TO: ParserStateRepository
        """
        return ParserStateRepository.get_stats_path()

    @staticmethod
    def set_stats_path(path: str) -> None:
        """
        Set the gem5 stats base path.

        DELEGATED TO: ParserStateRepository
        """
        ParserStateRepository.set_stats_path(path)

    @staticmethod
    def get_stats_pattern() -> str:
        """
        Get the stats file pattern.

        DELEGATED TO: ParserStateRepository
        """
        return ParserStateRepository.get_stats_pattern()

    @staticmethod
    def set_stats_pattern(pattern: str) -> None:
        """
        Set the stats file pattern.

        DELEGATED TO: ParserStateRepository
        """
        ParserStateRepository.set_stats_pattern(pattern)

    @staticmethod
    def get_scanned_variables() -> List[Dict[str, Any]]:
        """
        Get the scanned variables list.

        DELEGATED TO: ParserStateRepository
        """
        return ParserStateRepository.get_scanned_variables()

    @staticmethod
    def set_scanned_variables(variables: List[Dict[str, Any]]) -> None:
        """
        Set the scanned variables list.

        DELEGATED TO: ParserStateRepository
        """
        ParserStateRepository.set_scanned_variables(variables)

    # ==================== Plot Orchestration ====================

    @staticmethod
    def get_plots() -> List[BasePlot]:
        """
        Get all plot objects.

        DELEGATED TO: PlotRepository
        """
        return PlotRepository.get_plots()

    @staticmethod
    def set_plots(plots: List[BasePlot]) -> None:
        """
        Set the complete list of plot objects.

        DELEGATED TO: PlotRepository
        """
        PlotRepository.set_plots(plots)

    @staticmethod
    def add_plot(plot_obj: BasePlot) -> None:
        """
        Add a new plot to the collection.

        DELEGATED TO: PlotRepository
        """
        PlotRepository.add_plot(plot_obj)

    @staticmethod
    def get_plot_counter() -> int:
        """
        Get the current plot counter.

        DELEGATED TO: PlotRepository
        """
        return PlotRepository.get_plot_counter()

    @staticmethod
    def set_plot_counter(counter: int) -> None:
        """
        Set the plot counter.

        DELEGATED TO: PlotRepository
        """
        PlotRepository.set_plot_counter(counter)

    @staticmethod
    def start_next_plot_id() -> int:
        """
        Increment and return next plot ID.

        DELEGATED TO: PlotRepository
        """
        return PlotRepository.increment_plot_counter()

    @staticmethod
    def get_current_plot_id() -> Optional[int]:
        """
        Get the currently active plot ID.

        DELEGATED TO: PlotRepository
        """
        return PlotRepository.get_current_plot_id()

    @staticmethod
    def set_current_plot_id(plot_id: Optional[int]) -> None:
        """
        Set the currently active plot ID.

        DELEGATED TO: PlotRepository
        """
        PlotRepository.set_current_plot_id(plot_id)

    # ==================== Session Restoration ====================

    @staticmethod
    def clear_widget_state() -> None:
        """
        Clear widget-specific state markers from session.

        DELEGATED TO: SessionRepository
        """
        SessionRepository.clear_widget_state()

    @staticmethod
    def restore_session(portfolio_data: PortfolioData) -> None:
        """
        Restore complete session state from portfolio data.

        DELEGATED TO: SessionRepository
        """
        SessionRepository.restore_from_portfolio(portfolio_data)

    @staticmethod
    def restore_session_state(portfolio_data: PortfolioData) -> None:
        """
        Legacy alias for restore_session.

        DELEGATED TO: SessionRepository
        """
        SessionRepository.restore_from_portfolio(portfolio_data)
