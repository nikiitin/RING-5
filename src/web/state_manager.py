"""
RING-5 State Manager
Centralized session state management for the Streamlit application.
Ensures Backend-Frontend synchronization and type safety.
"""

import io
import logging
import shutil
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypedDict, cast

import pandas as pd
import streamlit as st

from src.plotting import BasePlot

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


class PortfolioData(TypedDict, total=False):
    """Type definition for portfolio restoration data."""

    parse_variables: List[ParseVariable]
    stats_path: str
    stats_pattern: str
    csv_path: str
    use_parser: bool
    scanned_variables: List[Dict[str, Any]]
    data_csv: str
    plots: List[Dict[str, Any]]
    plot_counter: int
    config: Dict[str, Any]


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
        """Initialize all session state variables with scientific defaults."""
        defaults: Dict[str, Any] = {
            StateManager.DATA: None,
            StateManager.PROCESSED_DATA: None,
            StateManager.CONFIG: {},
            StateManager.TEMP_DIR: None,
            StateManager.CSV_PATH: None,
            StateManager.USE_PARSER: False,
            StateManager.CSV_POOL: [],
            StateManager.SAVED_CONFIGS: [],
            StateManager.PARSE_VARIABLES: [
                {"name": "simTicks", "type": "scalar", "_id": str(uuid.uuid4())},
                {"name": "benchmark_name", "type": "configuration", "_id": str(uuid.uuid4())},
                {"name": "config_description", "type": "configuration", "_id": str(uuid.uuid4())},
            ],
            StateManager.PLOTS_OBJECTS: [],
            StateManager.PLOT_COUNTER: 0,
            StateManager.CURRENT_PLOT_ID: None,
            StateManager.STATS_PATH: "/path/to/gem5/stats",
            StateManager.STATS_PATTERN: "stats.txt",
            StateManager.SCANNED_VARIABLES: [],
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    # ==================== Data Management ====================

    @staticmethod
    def get_data() -> Optional[pd.DataFrame]:
        """Get the current base dataset."""
        return st.session_state.get(StateManager.DATA)

    @staticmethod
    def set_data(
        data: Optional[pd.DataFrame], on_change: Optional[Callable[[], None]] = None
    ) -> None:
        """Set the current data and enforce categorical constraints."""
        if data is not None:
            try:
                variables: List[Dict[str, Any]] = StateManager.get_parse_variables()
                config_vars: List[str] = [
                    v["name"] for v in variables if v.get("type") == "configuration"
                ]
                for col in config_vars:
                    if col in data.columns:
                        data[col] = data[col].astype(str)
            except Exception as e:
                logger.error(f"STATE: Type enforcement failed: {e}")

        st.session_state[StateManager.DATA] = data
        if on_change:
            on_change()

    @staticmethod
    def get_processed_data() -> Optional[pd.DataFrame]:
        """Get the processed/transformed dataset."""
        return st.session_state.get(StateManager.PROCESSED_DATA)

    @staticmethod
    def set_processed_data(data: Optional[pd.DataFrame]) -> None:
        """Set the processed/transformed dataset."""
        st.session_state[StateManager.PROCESSED_DATA] = data

    @staticmethod
    def has_data() -> bool:
        """Check if any data is loaded."""
        return StateManager.get_data() is not None

    @staticmethod
    def clear_data() -> None:
        """Reset data-related state and clean up temp storage."""
        temp_dir = st.session_state.get(StateManager.TEMP_DIR)
        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
            except OSError as e:
                logger.warning(f"STATE: Cleanup failed for {temp_dir}: {e}")

        st.session_state[StateManager.DATA] = None
        st.session_state[StateManager.PROCESSED_DATA] = None
        st.session_state[StateManager.CSV_PATH] = None
        st.session_state[StateManager.TEMP_DIR] = None
        st.session_state[StateManager.PLOTS_OBJECTS] = []
        st.session_state[StateManager.PLOT_COUNTER] = 0
        st.session_state[StateManager.CURRENT_PLOT_ID] = None

    @staticmethod
    def clear_all() -> None:
        """Clear all session state."""
        StateManager.clear_data()
        st.session_state[StateManager.CONFIG] = {}
        st.session_state[StateManager.USE_PARSER] = False
        st.session_state[StateManager.STATS_PATH] = "/path/to/gem5/stats"
        st.session_state[StateManager.STATS_PATTERN] = "stats.txt"
        st.session_state[StateManager.SCANNED_VARIABLES] = []
        st.session_state[StateManager.PARSE_VARIABLES] = [
            {"name": "simTicks", "type": "scalar", "_id": str(uuid.uuid4())},
            {"name": "benchmark_name", "type": "configuration", "_id": str(uuid.uuid4())},
            {"name": "config_description", "type": "configuration", "_id": str(uuid.uuid4())},
        ]

    # ==================== Configuration & Parser State ====================

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get the complete configuration dictionary."""
        return cast(Dict[str, Any], st.session_state.get(StateManager.CONFIG, {}))

    @staticmethod
    def set_config(config: Dict[str, Any]) -> None:
        """Set the complete configuration dictionary."""
        st.session_state[StateManager.CONFIG] = config

    @staticmethod
    def update_config(key: str, value: Any) -> None:
        """Update a specific configuration key."""
        config: Dict[str, Any] = StateManager.get_config()
        config[key] = value
        StateManager.set_config(config)

    @staticmethod
    def get_temp_dir() -> Optional[str]:
        return st.session_state.get(StateManager.TEMP_DIR)

    @staticmethod
    def set_temp_dir(path: str) -> None:
        """Set the temporary directory path."""
        st.session_state[StateManager.TEMP_DIR] = path

    @staticmethod
    def get_csv_path() -> Optional[str]:
        """Get the current CSV file path."""
        return st.session_state.get(StateManager.CSV_PATH)

    @staticmethod
    def set_csv_path(path: str) -> None:
        """Set the current CSV file path."""
        st.session_state[StateManager.CSV_PATH] = path

    @staticmethod
    def is_using_parser() -> bool:
        """Check if using gem5 parser mode."""
        return cast(bool, st.session_state.get(StateManager.USE_PARSER, False))

    @staticmethod
    def set_use_parser(use: bool) -> None:
        """Set parser mode flag."""
        st.session_state[StateManager.USE_PARSER] = use

    @staticmethod
    def get_csv_pool() -> List[Dict[str, Any]]:
        """Get the CSV pool registry."""
        return cast(List[Dict[str, Any]], st.session_state.get(StateManager.CSV_POOL, []))

    @staticmethod
    def set_csv_pool(pool: List[Dict[str, Any]]) -> None:
        """Set the CSV pool registry."""
        st.session_state[StateManager.CSV_POOL] = pool

    @staticmethod
    def get_saved_configs() -> List[Dict[str, Any]]:
        """Get list of saved configurations."""
        return cast(List[Dict[str, Any]], st.session_state.get(StateManager.SAVED_CONFIGS, []))

    @staticmethod
    def set_saved_configs(configs: List[Dict[str, Any]]) -> None:
        """Set the list of saved configurations."""
        st.session_state[StateManager.SAVED_CONFIGS] = configs

    @staticmethod
    def get_parse_variables() -> List[Dict[str, Any]]:
        """Get parse variables list."""
        return cast(List[Dict[str, Any]], st.session_state.get(StateManager.PARSE_VARIABLES, []))

    @staticmethod
    def set_parse_variables(variables: List[Dict[str, Any]]) -> None:
        """Set parse variables, ensuring each has a unique ID."""
        for var in variables:
            if "_id" not in var:
                var["_id"] = str(uuid.uuid4())
        st.session_state[StateManager.PARSE_VARIABLES] = variables

    @staticmethod
    def get_stats_path() -> str:
        """Get the gem5 stats base path."""
        return cast(str, st.session_state.get(StateManager.STATS_PATH, ""))

    @staticmethod
    def set_stats_path(path: str) -> None:
        """Set the gem5 stats base path."""
        st.session_state[StateManager.STATS_PATH] = path

    @staticmethod
    def get_stats_pattern() -> str:
        """Get the stats file pattern."""
        return cast(str, st.session_state.get(StateManager.STATS_PATTERN, "stats.txt"))

    @staticmethod
    def set_stats_pattern(pattern: str) -> None:
        """Set the stats file pattern."""
        st.session_state[StateManager.STATS_PATTERN] = pattern

    @staticmethod
    def get_scanned_variables() -> List[Dict[str, Any]]:
        """Get the scanned variables list."""
        return cast(List[Dict[str, Any]], st.session_state.get(StateManager.SCANNED_VARIABLES, []))

    @staticmethod
    def set_scanned_variables(variables: List[Dict[str, Any]]) -> None:
        """Set the scanned variables list."""
        st.session_state[StateManager.SCANNED_VARIABLES] = variables

    # ==================== Plot Orchestration ====================

    @staticmethod
    def get_plots() -> List[BasePlot]:
        """Get all plot objects."""
        return cast(List[BasePlot], st.session_state.get(StateManager.PLOTS_OBJECTS, []))

    @staticmethod
    def set_plots(plots: List[BasePlot]) -> None:
        """Set the complete list of plot objects."""
        st.session_state[StateManager.PLOTS_OBJECTS] = plots

    @staticmethod
    def add_plot(plot_obj: BasePlot) -> None:
        """Add a new plot to the collection."""
        plots: List[BasePlot] = StateManager.get_plots()
        plots.append(plot_obj)
        st.session_state[StateManager.PLOTS_OBJECTS] = plots

    @staticmethod
    def get_plot_counter() -> int:
        """Get the current plot counter."""
        return cast(int, st.session_state.get(StateManager.PLOT_COUNTER, 0))

    @staticmethod
    def set_plot_counter(counter: int) -> None:
        """Set the plot counter."""
        st.session_state[StateManager.PLOT_COUNTER] = counter

    @staticmethod
    def start_next_plot_id() -> int:
        """Increment and return next plot ID."""
        counter: int = StateManager.get_plot_counter()
        StateManager.set_plot_counter(counter + 1)
        return counter

    @staticmethod
    def get_current_plot_id() -> Optional[int]:
        """Get the currently active plot ID."""
        return st.session_state.get(StateManager.CURRENT_PLOT_ID)

    @staticmethod
    def set_current_plot_id(plot_id: Optional[int]) -> None:
        """Set the currently active plot ID."""
        st.session_state[StateManager.CURRENT_PLOT_ID] = plot_id

    # ==================== Session Restoration ====================

    @staticmethod
    def clear_widget_state() -> None:
        """Clear widget-specific state markers from session."""
        markers: List[str] = [
            "_order_",
            "leg_ren_",
            "xaxis_angle_",
            "ydtick_",
            "bargap_",
            "editable_",
            "show_error_bars",
            "colsel_",
            "norm_",
            "mean_",
            "sort_",
            "filter_",
            "trans_",
            "leg_x_",
            "leg_y_",
            "leg_orient_",
        ]
        keys_to_del: List[str] = [
            k
            for k in st.session_state.keys()
            if isinstance(k, str) and any(marker in k for marker in markers)
        ]
        for k in keys_to_del:
            del st.session_state[k]

    @staticmethod
    def restore_session(portfolio_data: PortfolioData) -> None:
        """Restore complete session state from portfolio data."""
        StateManager.clear_widget_state()
        st.session_state[StateManager.PARSE_VARIABLES] = portfolio_data.get("parse_variables", [])
        st.session_state[StateManager.STATS_PATH] = portfolio_data.get("stats_path", "")
        st.session_state[StateManager.STATS_PATTERN] = portfolio_data.get(
            "stats_pattern", "stats.txt"
        )
        st.session_state[StateManager.CSV_PATH] = portfolio_data.get("csv_path", "")
        st.session_state[StateManager.USE_PARSER] = portfolio_data.get("use_parser", False)
        st.session_state[StateManager.SCANNED_VARIABLES] = portfolio_data.get(
            "scanned_variables", []
        )

        if "data_csv" in portfolio_data:
            df: pd.DataFrame = pd.read_csv(io.StringIO(portfolio_data["data_csv"]))
            StateManager.set_data(df)

        loaded_plots: List[BasePlot] = []
        for plot_data in portfolio_data.get("plots", []):
            try:
                if "plot_type" in plot_data:
                    loaded_plots.append(BasePlot.from_dict(plot_data))
            except Exception as e:
                logger.error(f"STATE: Failed to restore plot: {e}")

        st.session_state[StateManager.PLOTS_OBJECTS] = loaded_plots
        st.session_state[StateManager.PLOT_COUNTER] = portfolio_data.get(
            "plot_counter", len(loaded_plots)
        )
        st.session_state[StateManager.CONFIG] = portfolio_data.get("config", {})

    @staticmethod
    def restore_session_state(portfolio_data: PortfolioData) -> None:
        """Legacy alias for restore_session."""
        StateManager.restore_session(portfolio_data)
