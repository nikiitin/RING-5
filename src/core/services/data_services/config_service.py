"""
Configuration Service
Manages saving and loading of configuration files.
"""

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from src.core.common.utils import sanitize_filename, validate_path_within
from src.core.services.data_services.path_service import PathService


class ConfigService:
    """Service for managing saved configurations."""

    @staticmethod
    def get_config_dir() -> Path:
        """Get the configuration pool directory path."""
        config_dir = PathService.get_data_dir() / "saved_configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @staticmethod
    def load_saved_configs() -> List[Dict[str, Any]]:
        """
        Load list of saved configuration files.

        Returns:
            List of dicts with 'path', 'name', 'modified', 'description' keys.
        """
        config_dir = ConfigService.get_config_dir()
        configs = []

        for config_file in sorted(
            config_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            try:
                with open(config_file, "r") as f:
                    config_data = json.load(f)
                configs.append(
                    {
                        "path": str(config_file),
                        "name": config_file.name,
                        "modified": config_file.stat().st_mtime,
                        "description": config_data.get("description", "No description"),
                    }
                )
            except (OSError, json.JSONDecodeError):
                pass  # Skip unreadable/invalid config files gracefully

        return configs

    @staticmethod
    def save_configuration(
        name: str,
        description: str,
        shapers_config: List[Dict[str, Any]],
        csv_path: Optional[str] = None,
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

        config_data = {
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
    def load_configuration(config_path: str) -> Dict[str, Any]:
        """
        Load a configuration from file.

        Args:
            config_path: Path to configuration file.

        Returns:
            Configuration dictionary.
        """
        config_dir = ConfigService.get_config_dir()
        validated_path = validate_path_within(Path(config_path), config_dir)
        with open(validated_path, "r") as f:
            return cast(Dict[str, Any], json.load(f))

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
        except Exception:
            return False
