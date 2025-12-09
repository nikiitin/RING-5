"""
RING-5 State Manager
Centralized session state management for the Streamlit application.
"""
import streamlit as st
from pathlib import Path
import json
import pandas as pd
from typing import Optional, List, Dict, Any


class StateManager:
    """Manages application session state with type safety and validation."""
    
    # State keys
    DATA = 'data'
    PROCESSED_DATA = 'processed_data'
    CONFIG = 'config'
    TEMP_DIR = 'temp_dir'
    CSV_PATH = 'csv_path'
    USE_PARSER = 'use_parser'
    CSV_POOL = 'csv_pool'
    SAVED_CONFIGS = 'saved_configs'
    PARSE_VARIABLES = 'parse_variables'
    
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
                {"name": "config_description", "type": "configuration"}
            ]
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
        """Get the parse variables configuration."""
        return st.session_state.get(StateManager.PARSE_VARIABLES, [])
    
    @staticmethod
    def set_parse_variables(variables: List[Dict[str, str]]):
        """Set the parse variables configuration."""
        st.session_state[StateManager.PARSE_VARIABLES] = variables
    
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
    def has_processed_data() -> bool:
        """Check if processed data exists."""
        return StateManager.get_processed_data() is not None
