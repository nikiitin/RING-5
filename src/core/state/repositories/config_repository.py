"""In-memory repository for application configuration."""

import logging
from typing import Any

from src.core.models.data_models import CsvPoolEntry, SavedConfigEntry

logger = logging.getLogger(__name__)


class ConfigRepository:
    """Store configuration, paths, and saved configuration entries."""

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self._config: dict[str, Any] = {}
        self._temp_dir: str | None = None
        self._csv_path: str | None = None
        self._csv_pool: list[CsvPoolEntry] = []
        self._saved_configs: list[SavedConfigEntry] = []

    def get_config(self) -> dict[str, Any]:
        """
        Get the complete configuration dictionary.

        Returns:
            A shallow copy of the configuration dictionary (defensive copy-on-read).
        """
        return dict(self._config)

    def set_config(self, config: dict[str, Any]) -> None:
        """
        Set the complete configuration dictionary.

        Args:
            config: Configuration dictionary to store
        """
        self._config = config
        logger.info("CONFIG_REPO: Configuration updated - %d keys", len(config))

    def update_config(self, key: str, value: object) -> None:
        """
        Update a specific configuration key.

        Args:
            key: Configuration key to update
            value: New value for the key
        """
        self._config[key] = value
        logger.debug(f"CONFIG_REPO: Config key '{key}' updated")

    def get_config_value(self, key: str, default: object = None) -> object:
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

    def get_temp_dir(self) -> str | None:
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
        if self._temp_dir == path:
            return
        self._temp_dir = path
        logger.info("CONFIG_REPO: Temp dir set to '%s'", path)

    def get_csv_path(self) -> str | None:
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
        if self._csv_path == path:
            return
        self._csv_path = path

    def get_csv_pool(self) -> list[CsvPoolEntry]:
        """
        Get the CSV pool registry.

        Returns:
            A shallow copy of the CSV pool list (defensive copy-on-read).
        """
        return list(self._csv_pool)

    def set_csv_pool(self, pool: list[CsvPoolEntry]) -> None:
        """
        Set the CSV pool registry.

        Args:
            pool: List of CSV pool entries
        """
        self._csv_pool = pool
        logger.info("CONFIG_REPO: CSV pool updated - %d entries", len(pool))

    def get_saved_configs(self) -> list[SavedConfigEntry]:
        """
        Get saved configuration entries.

        Returns:
            A shallow copy of the saved-config list (defensive copy-on-read).
        """
        return list(self._saved_configs)

    def set_saved_configs(self, configs: list[SavedConfigEntry]) -> None:
        """
        Set saved configuration entries.

        Args:
            configs: List of saved configurations
        """
        self._saved_configs = configs
        logger.info("CONFIG_REPO: Saved configs updated - %d entries", len(configs))
