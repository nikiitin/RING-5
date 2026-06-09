"""
Configuration Service
Manages saving and loading of configuration files.
"""

import datetime
import json
import logging
from pathlib import Path
from typing import cast

from src.core.common.utils import sanitize_filename, validate_path_within
from src.core.models.data_models import SavedConfigData, SavedConfigEntry
from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.data_services.path_service import PathService

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for managing saved configurations."""

    _config_dir: Path | None = None

    @staticmethod
    def reset_caches() -> None:
        """Reset the cached config directory path (for testing)."""
        ConfigService._config_dir = None

    @staticmethod
    def get_config_dir() -> Path:
        """Get the configuration pool directory path."""
        if ConfigService._config_dir is None:
            ConfigService._config_dir = PathService.get_data_dir() / "saved_configs"
            ConfigService._config_dir.mkdir(parents=True, exist_ok=True)
        return ConfigService._config_dir

    @staticmethod
    def load_saved_configs() -> list[SavedConfigEntry]:
        """
        Load list of saved configuration files.

        Returns:
            List of dicts with 'path', 'name', 'modified', 'description' keys.
        """
        config_dir = ConfigService.get_config_dir()
        configs: list[SavedConfigEntry] = []

        for config_file in sorted(
            config_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            try:
                with open(config_file) as f:
                    config_data = json.load(f)
                configs.append(
                    {
                        "path": str(config_file),
                        "name": config_file.name,
                        "modified": config_file.stat().st_mtime,
                        "description": config_data.get("description", "No description"),
                    }
                )
            except (OSError, json.JSONDecodeError) as e:
                logger.debug("Skipping unreadable config file %s: %s", config_file, e)

        return configs

    @staticmethod
    def save_configuration(
        name: str,
        description: str,
        shapers_config: list[ShaperStepConfig],
        csv_path: str | None = None,
    ) -> str:
        """
        Save a configuration to the pool.

        Args:
            name: Configuration name.
            description: Configuration description.
            shapers_config: List of shaper configurations.
            csv_path: Optional path to associated CSV file.

        Returns:
            Path to the saved configuration file.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = sanitize_filename(name)
        config_filename = f"{safe_name}_{timestamp}.json"
        config_dir = ConfigService.get_config_dir()
        config_path = validate_path_within(config_dir / config_filename, config_dir)

        config_data: SavedConfigData = {
            "name": name,
            "description": description,
            "timestamp": timestamp,
            "shapers": shapers_config,
            "csv_path": csv_path,
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)

        return str(config_path)

    @staticmethod
    def load_configuration(config_path: str) -> SavedConfigData:
        """
        Load a configuration from file.

        Args:
            config_path: Path to configuration file.

        Returns:
            Configuration dictionary.
        """
        config_dir = ConfigService.get_config_dir()
        validated_path = validate_path_within(Path(config_path), config_dir)
        with open(validated_path) as f:
            return cast(SavedConfigData, json.load(f))

    @staticmethod
    def delete_configuration(config_path: str) -> bool:
        """
        Delete a configuration file.

        Args:
            config_path: Path to configuration file.

        Returns:
            True if deleted successfully.
        """
        try:
            config_dir = ConfigService.get_config_dir()
            validated_path = validate_path_within(Path(config_path), config_dir)
            validated_path.unlink()
            return True
        except (OSError, ValueError) as e:
            logger.warning("Failed to delete config file %s: %s", config_path, e)
            return False
