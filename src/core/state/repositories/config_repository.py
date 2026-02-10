"""
Config Repository
Single Responsibility: Manage application configuration state.
"""

import logging
from typing import Any, Dict, List, Optional

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

    Adheres to SRP: Only manages configuration state in memory.
    """

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self._config: Dict[str, Any] = {}
        self._temp_dir: Optional[str] = None
        self._csv_path: Optional[str] = None
        self._csv_pool: List[Dict[str, Any]] = []
        self._saved_configs: List[Dict[str, Any]] = []

    def get_config(self) -> Dict[str, Any]:
        """
        Get the complete configuration dictionary.

        Returns:
            Configuration dictionary (empty dict if not initialized)
        """
        return self._config

    def set_config(self, config: Dict[str, Any]) -> None:
        """
        Set the complete configuration dictionary.

        Args:
            config: Configuration dictionary to store
        """
        self._config = config
        logger.info(f"CONFIG_REPO: Configuration updated - {len(config)} keys")

    def update_config(self, key: str, value: Any) -> None:
        """
        Update a specific configuration key.

        Args:
            key: Configuration key to update
            value: New value for the key
        """
        self._config[key] = value
        logger.debug(f"CONFIG_REPO: Config key '{key}' updated")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value.

        Args:
            key: Configuration key to retrieve
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def clear_config(self) -> None:
        """Clear all configuration data."""
        self._config = {}
        logger.info("CONFIG_REPO: Configuration cleared")

    def get_temp_dir(self) -> Optional[str]:
        """
        Get the temporary directory path.

        Returns:
            Temporary directory path or None if not set
        """
        return self._temp_dir

    def set_temp_dir(self, path: str) -> None:
        """
        Set the temporary directory path.

        Args:
            path: Path to temporary directory
        """
        self._temp_dir = path
        logger.info(f"CONFIG_REPO: Temp dir set to '{path}'")

    def get_csv_path(self) -> Optional[str]:
        """
        Get the current CSV file path.

        Returns:
            CSV file path or None if not set
        """
        return self._csv_path

    def set_csv_path(self, path: str) -> None:
        """
        Set the current CSV file path.

        Args:
            path: Path to CSV file
        """
        self._csv_path = path

    def get_csv_pool(self) -> List[Dict[str, Any]]:
        """
        Get the CSV pool registry.

        Returns:
            List of CSV pool entries (empty list if not initialized)
        """
        return self._csv_pool

    def set_csv_pool(self, pool: List[Dict[str, Any]]) -> None:
        """
        Set the CSV pool registry.

        Args:
            pool: List of CSV pool entries
        """
        self._csv_pool = pool
        logger.info(f"CONFIG_REPO: CSV pool updated - {len(pool)} entries")

    def get_saved_configs(self) -> List[Dict[str, Any]]:
        """
        Get saved configuration entries.

        Returns:
            List of saved configurations (empty list if not initialized)
        """
        return self._saved_configs

    def set_saved_configs(self, configs: List[Dict[str, Any]]) -> None:
        """
        Set saved configuration entries.

        Args:
            configs: List of saved configurations
        """
        self._saved_configs = configs
        logger.info(f"CONFIG_REPO: Saved configs updated - {len(configs)} entries")
