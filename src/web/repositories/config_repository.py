"""
Config Repository
Single Responsibility: Manage application configuration state.
"""

import logging
from typing import Any, Dict, List, Optional, cast

import streamlit as st

logger = logging.getLogger(__name__)


class ConfigRepository:
    """
    Repository for managing application configuration.

    Responsibilities:
    - Store and retrieve configuration dictionary
    - Update individual config keys
    - Manage temporary directory path
    - Manage CSV file path
    - Manage CSV pool entries
    - Manage saved configuration entries

    Adheres to SRP: Only manages configuration state, nothing else.
    """

    # State keys
    CONFIG_KEY = "config"
    TEMP_DIR_KEY = "temp_dir"
    CSV_PATH_KEY = "csv_path"
    CSV_POOL_KEY = "csv_pool"
    SAVED_CONFIGS_KEY = "saved_configs"

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Get the complete configuration dictionary.

        Returns:
            Configuration dictionary (empty dict if not initialized)
        """
        config = st.session_state.get(ConfigRepository.CONFIG_KEY, {})
        if config:
            return cast(Dict[str, Any], config)
        return {}

    @staticmethod
    def set_config(config: Dict[str, Any]) -> None:
        """
        Set the complete configuration dictionary.

        Args:
            config: Configuration dictionary to store
        """
        st.session_state[ConfigRepository.CONFIG_KEY] = config
        logger.info(f"CONFIG_REPO: Configuration updated - {len(config)} keys")

    @staticmethod
    def update_config(key: str, value: Any) -> None:
        """
        Update a specific configuration key.

        Args:
            key: Configuration key to update
            value: New value for the key
        """
        config = ConfigRepository.get_config()
        config[key] = value
        ConfigRepository.set_config(config)
        logger.debug(f"CONFIG_REPO: Config key '{key}' updated")

    @staticmethod
    def get_config_value(key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value.

        Args:
            key: Configuration key to retrieve
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        config = ConfigRepository.get_config()
        return config.get(key, default)

    @staticmethod
    def clear_config() -> None:
        """Clear all configuration data."""
        st.session_state[ConfigRepository.CONFIG_KEY] = {}
        logger.info("CONFIG_REPO: Configuration cleared")

    @staticmethod
    def get_temp_dir() -> Optional[str]:
        """
        Get the temporary directory path.

        Returns:
            Temporary directory path or None if not set
        """
        result = st.session_state.get(ConfigRepository.TEMP_DIR_KEY)
        return str(result) if result is not None else None

    @staticmethod
    def set_temp_dir(path: str) -> None:
        """
        Set the temporary directory path.

        Args:
            path: Path to temporary directory
        """
        st.session_state[ConfigRepository.TEMP_DIR_KEY] = path
        logger.info(f"CONFIG_REPO: Temp dir set to '{path}'")

    @staticmethod
    def get_csv_path() -> Optional[str]:
        """
        Get the current CSV file path.

        Returns:
            CSV file path or None if not set
        """
        result = st.session_state.get(ConfigRepository.CSV_PATH_KEY)
        return str(result) if result is not None else None

    @staticmethod
    def set_csv_path(path: str) -> None:
        """
        Set the current CSV file path.

        Args:
            path: Path to CSV file
        """
        st.session_state[ConfigRepository.CSV_PATH_KEY] = path
        logger.info(f"CONFIG_REPO: CSV path set to '{path}'")

    @staticmethod
    def get_csv_pool() -> List[Dict[str, Any]]:
        """
        Get the CSV pool registry.

        Returns:
            List of CSV pool entries (empty list if not initialized)
        """
        pool = st.session_state.get(ConfigRepository.CSV_POOL_KEY, [])
        if pool:
            return cast(List[Dict[str, Any]], pool)
        return []

    @staticmethod
    def set_csv_pool(pool: List[Dict[str, Any]]) -> None:
        """
        Set the CSV pool registry.

        Args:
            pool: List of CSV pool entries
        """
        st.session_state[ConfigRepository.CSV_POOL_KEY] = pool
        logger.info(f"CONFIG_REPO: CSV pool updated - {len(pool)} entries")

    @staticmethod
    def get_saved_configs() -> List[Dict[str, Any]]:
        """
        Get saved configuration entries.

        Returns:
            List of saved configurations (empty list if not initialized)
        """
        from typing import cast

        configs = st.session_state.get(ConfigRepository.SAVED_CONFIGS_KEY, [])
        return cast(List[Dict[str, Any]], configs if configs else [])

    @staticmethod
    def set_saved_configs(configs: List[Dict[str, Any]]) -> None:
        """
        Set saved configuration entries.

        Args:
            configs: List of saved configurations
        """
        st.session_state[ConfigRepository.SAVED_CONFIGS_KEY] = configs
        logger.info(f"CONFIG_REPO: Saved configs updated - {len(configs)} entries")
