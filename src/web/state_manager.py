"""
RING-5 State Manager
Centralized session state management for the Streamlit application.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


class StateManager:
    """Manages application session state with type safety and validation."""

    # State keys
    DATA = "data"
    PROCESSED_DATA = "processed_data"
    CONFIG = "config"
    TEMP_DIR = "temp_dir"
    CSV_PATH = "csv_path"
    USE_PARSER = "use_parser"
    CSV_POOL = "csv_pool"
    SAVED_CONFIGS = "saved_configs"
    PARSE_VARIABLES = "parse_variables"
    
    # Plot State Keys
    PLOTS_OBJECTS = "plots_objects"
    PLOT_COUNTER = "plot_counter"
    CURRENT_PLOT_ID = "current_plot_id"

    @staticmethod
    def initialize():
        """Initialize all session state variables with defaults."""
        defaults = {
            StateManager.DATA: None,
            StateManager.PROCESSED_DATA: None,
            StateManager.CONFIG: {},
            StateManager.TEMP_DIR: None,
            StateManager.CSV_PATH: None,
            StateManager.USE_PARSER: False,
            StateManager.CSV_POOL: [],
            StateManager.SAVED_CONFIGS: [],
            StateManager.PARSE_VARIABLES: [
                {"name": "simTicks", "type": "scalar"},
                {"name": "benchmark_name", "type": "configuration"},
                {"name": "config_description", "type": "configuration"},
            ],
            # Plot defaults
            StateManager.PLOTS_OBJECTS: [],
            StateManager.PLOT_COUNTER: 0,
            StateManager.CURRENT_PLOT_ID: None,
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def get_data() -> Optional[pd.DataFrame]:
        """Get the current data DataFrame."""
        return st.session_state.get(StateManager.DATA)

    @staticmethod
    def set_data(data: pd.DataFrame):
        """Set the current data DataFrame."""
        if data is not None:
            # Enforce configuration types as strings (categorical)
            # This ensures that even if data is reloaded, configs remain categorical
            try:
                variables = StateManager.get_parse_variables()
                if variables:
                     config_vars = [v["name"] for v in variables if v.get("type") == "configuration"]
                     for col in config_vars:
                         if col in data.columns:
                             # Cast to string to treat as categorical
                             # We use .astype(str) which converts connection-like objects properly
                             data[col] = data[col].astype(str)
            except Exception as e:
                print(f"Error enforcing configuration types: {e}")
                
        st.session_state[StateManager.DATA] = data

    @staticmethod
    def get_processed_data() -> Optional[pd.DataFrame]:
        """Get the processed data DataFrame."""
        return st.session_state.get(StateManager.PROCESSED_DATA)

    @staticmethod
    def set_processed_data(data: pd.DataFrame):
        """Set the processed data DataFrame."""
        st.session_state[StateManager.PROCESSED_DATA] = data

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get the current configuration."""
        return st.session_state.get(StateManager.CONFIG, {})

    @staticmethod
    def set_config(config: Dict[str, Any]):
        """Set the current configuration."""
        st.session_state[StateManager.CONFIG] = config

    @staticmethod
    def update_config(key: str, value: Any):
        """Update a specific configuration key."""
        config = StateManager.get_config()
        config[key] = value
        StateManager.set_config(config)

    @staticmethod
    def get_csv_path() -> Optional[str]:
        """Get the path to the current CSV file."""
        return st.session_state.get(StateManager.CSV_PATH)

    @staticmethod
    def set_csv_path(path: str):
        """Set the path to the current CSV file."""
        st.session_state[StateManager.CSV_PATH] = path

    @staticmethod
    def get_temp_dir() -> Optional[str]:
        """Get the temporary directory path."""
        return st.session_state.get(StateManager.TEMP_DIR)

    @staticmethod
    def set_temp_dir(path: str):
        """Set the temporary directory path."""
        st.session_state[StateManager.TEMP_DIR] = path

    @staticmethod
    def is_using_parser() -> bool:
        """Check if parser mode is enabled."""
        return st.session_state.get(StateManager.USE_PARSER, False)

    @staticmethod
    def set_use_parser(use: bool):
        """Set parser mode."""
        st.session_state[StateManager.USE_PARSER] = use

    @staticmethod
    def get_csv_pool() -> List[Dict[str, Any]]:
        """Get the list of CSV files in the pool."""
        return st.session_state.get(StateManager.CSV_POOL, [])

    @staticmethod
    def set_csv_pool(pool: List[Dict[str, Any]]):
        """Set the CSV pool list."""
        st.session_state[StateManager.CSV_POOL] = pool

    @staticmethod
    def get_saved_configs() -> List[Dict[str, Any]]:
        """Get the list of saved configurations."""
        return st.session_state.get(StateManager.SAVED_CONFIGS, [])

    @staticmethod
    def set_saved_configs(configs: List[Dict[str, Any]]):
        """Set the saved configurations list."""
        st.session_state[StateManager.SAVED_CONFIGS] = configs

    @staticmethod
    def get_parse_variables() -> List[Dict[str, str]]:
        """Get the parse variables configuration, ensuring each has a unique ID."""
        import uuid
        variables = st.session_state.get(StateManager.PARSE_VARIABLES, [])
        keys_updated = False
        for var in variables:
            if "_id" not in var:
                var["_id"] = str(uuid.uuid4())
                keys_updated = True
        
        if keys_updated:
            st.session_state[StateManager.PARSE_VARIABLES] = variables
            
        return variables

    @staticmethod
    def set_parse_variables(variables: List[Dict[str, str]]):
        """Set the parse variables configuration."""
        st.session_state[StateManager.PARSE_VARIABLES] = variables

    @staticmethod
    def get_scanned_variables() -> List[Dict[str, Any]]:
        """Get scanned variables results."""
        return st.session_state.get("scanned_variables", [])

    @staticmethod
    def set_scanned_variables(variables: List[Dict[str, Any]]):
        """Set scanned variables results."""
        st.session_state["scanned_variables"] = variables

    @staticmethod
    def clear_all():
        """Clear all session state (reset application)."""
        import shutil

        # Clean up temp directory
        temp_dir = StateManager.get_temp_dir()
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir)

        # Reset all state
        st.session_state[StateManager.DATA] = None
        st.session_state[StateManager.PROCESSED_DATA] = None
        st.session_state[StateManager.CONFIG] = {}
        st.session_state[StateManager.CSV_PATH] = None
        st.session_state[StateManager.USE_PARSER] = False
        st.session_state[StateManager.TEMP_DIR] = None

    @staticmethod
    def has_data() -> bool:
        """Check if data is loaded."""
        return StateManager.get_data() is not None

    @staticmethod
    def get_plots() -> List[Any]:
        """Get the list of plot objects."""
        return st.session_state.get(StateManager.PLOTS_OBJECTS, [])

    @staticmethod
    def set_plots(plots: List[Any]):
        """Set the list of plot objects."""
        st.session_state[StateManager.PLOTS_OBJECTS] = plots

    @staticmethod
    def get_plot_counter() -> int:
        """Get the current plot counter value."""
        return st.session_state.get(StateManager.PLOT_COUNTER, 0)

    @staticmethod
    def set_plot_counter(counter: int):
        """Set the plot counter value."""
        st.session_state[StateManager.PLOT_COUNTER] = counter
        
    @staticmethod
    def start_next_plot_id() -> int:
        """Increment and return the next plot ID."""
        counter = StateManager.get_plot_counter()
        StateManager.set_plot_counter(counter + 1)
        return counter

    @staticmethod
    def get_current_plot_id() -> Optional[int]:
        """Get the ID of the currently selected plot."""
        return st.session_state.get(StateManager.CURRENT_PLOT_ID)

    @staticmethod
    def set_current_plot_id(plot_id: Optional[int]):
        """Set the ID of the currently selected plot."""
        st.session_state[StateManager.CURRENT_PLOT_ID] = plot_id

    @staticmethod
    def restore_session_state(portfolio_data: Dict[str, Any]):
        """Restore session state from portfolio data."""
        import io
        from src.plotting import BasePlot

        # Restore variables configuration if present (CRITICAL for type enforcement)
        if "parse_variables" in portfolio_data:
            st.session_state[StateManager.PARSE_VARIABLES] = portfolio_data["parse_variables"]

        # Restore data
        if "data_csv" in portfolio_data:
             data = pd.read_csv(io.StringIO(portfolio_data["data_csv"]))
             StateManager.set_data(data)
        
        StateManager.set_csv_path(portfolio_data.get("csv_path"))

        # Clear stale widget states for plots to force re-initialization from config
        # This ensures advanced options (like order, legend aliases) are reflected correctly
        keys_to_clear = [
            k for k in st.session_state.keys()
            if any(marker in k for marker in [
                "_order_", "leg_ren_", "leg_orient_", "leg_x_", "leg_y_",
                "xaxis_angle_", "xaxis_font_", "ydtick_", "automargin_",
                "margin_b_", "bargap_", "bargroupgap_", "bar_border_",
                "editable_", "download_fmt_", "show_error_bars", "new_plot_name",
                "colsel_", "norm_", "mean_", "sort_", "filter_", "trans_",
                # Add new hash keys markers if any specific prefix is used, 
                # though currently they use _plot_id_hash, so clearing by plot components usually works if we reset plot objects.
                # Since we replace plot objects, new widgets will be generated if IDs change? 
                # Actually IDs might persist. Explicit clearing is safer.
                "name_", "color_", "use_col_", "sym_", "msize_", "lwidth_", "pat_", "xlabel_"
            ])
        ]
        for k in keys_to_clear:
            del st.session_state[k]

        # Restore plots
        loaded_plots_objects = []
        loaded_plots_dicts = []  # For backward compatibility if needed

        for plot_data in portfolio_data.get("plots", []):
            # Try to load as object first (Version 2.0+)
            try:
                if "plot_type" in plot_data:
                    plot_obj = BasePlot.from_dict(plot_data)
                    loaded_plots_objects.append(plot_obj)
            except Exception as e:
                # st.warning is not available here if we want to be pure, but StateManager currently uses st. 
                # Prints will show in logs.
                print(f"Could not load plot as object: {e}")

            # Also keep as dict for fallback/legacy
            # Convert processed_data CSV string back to DataFrame if it exists
            if plot_data.get("processed_data") is not None:
                if isinstance(plot_data["processed_data"], str):
                    plot_data["processed_data"] = pd.read_csv(
                        io.StringIO(plot_data["processed_data"])
                    )
            loaded_plots_dicts.append(plot_data)

        # Update session state
        StateManager.set_plots(loaded_plots_objects)
        st.session_state["plots"] = loaded_plots_dicts  # Keep for legacy compatibility

        StateManager.set_plot_counter(portfolio_data.get("plot_counter", 0))
        StateManager.set_config(portfolio_data.get("config", {}))
