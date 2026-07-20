"""
Configuration Service
Manages saving and loading of configuration files.
"""

import copy
import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import cast

from src.core.common.utils import sanitize_filename, validate_path_within
from src.core.models.data_models import (
    PipelineConfigConflictPolicy,
    PipelineConfigConflictResolution,
    PipelineConfigImportResult,
    SavedConfigData,
    SavedConfigEntry,
)
from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.data_services.path_service import PathService
from src.core.services.data_services.pipeline_config_exchange_service import (
    PIPELINE_CONFIG_FORMAT,
    PIPELINE_CONFIG_SCHEMA_VERSION,
    PipelineConfigExchangeService,
)

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
        # [impl->req~ring5.data.saved-pipeline-configurations~1]
        config_dir = ConfigService.get_config_dir()
        configs: list[SavedConfigEntry] = []

        for config_file in sorted(
            config_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            try:
                with open(config_file) as f:
                    config_data = json.load(f)
                if not isinstance(config_data, dict):
                    logger.debug("Skipping non-object config file %s", config_file)
                    continue
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
        # [impl->req~ring5.data.saved-pipeline-configurations~1]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = sanitize_filename(name)
        # uuid suffix: timestamps have 1-second resolution, so two saves of the
        # same name in the same second would silently overwrite each other.
        config_filename = f"{safe_name}_{timestamp}_{uuid.uuid4().hex[:8]}.json"
        config_dir = ConfigService.get_config_dir()
        config_path = validate_path_within(config_dir / config_filename, config_dir)

        config_data: SavedConfigData = {
            "format": PIPELINE_CONFIG_FORMAT,
            "schema_version": PIPELINE_CONFIG_SCHEMA_VERSION,
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
    def export_configuration(
        name: str,
        description: str,
        shapers_config: list[ShaperStepConfig],
        csv_path: str | None = None,
    ) -> bytes:
        """Serialize a validated configuration as portable versioned JSON.

        Args:
            name: Human-readable configuration name.
            description: Optional human-readable explanation.
            shapers_config: Ordered flat shaper configurations.
            csv_path: Optional source CSV association.

        Returns:
            Deterministic UTF-8 JSON bytes.
        """
        # [impl->req~ring5.shaping.config-import-export~1]
        return PipelineConfigExchangeService.dumps(
            name,
            description,
            shapers_config,
            csv_path,
        )

    @staticmethod
    def import_configuration(
        payload: str | bytes | bytearray,
        *,
        conflict: PipelineConfigConflictPolicy = "error",
    ) -> PipelineConfigImportResult:
        """Validate and save a current or legacy portable configuration.

        Logical-name conflicts can be rejected, renamed with a numeric suffix,
        or replaced. Replacement writes the new record before removing older
        records so a failed write cannot discard the existing configuration.

        Args:
            payload: UTF-8 JSON text or bytes, limited to 256 KiB.
            conflict: ``"error"``, ``"rename"``, or ``"replace"``.

        Returns:
            Saved path, normalized content, migration flag, and conflict result.

        Raises:
            TypeError: Payload is not text or bytes.
            ValueError: Payload, policy, or pipeline is invalid.
        """
        # [impl->req~ring5.shaping.config-import-export~1]
        if conflict not in {"error", "rename", "replace"}:
            raise ValueError(
                "Pipeline configuration conflict policy must be error, rename, or replace."
            )
        document = PipelineConfigExchangeService.loads(payload)
        conflicts = ConfigService._find_configurations_named(document.name)
        resolved_name = document.name
        resolution: PipelineConfigConflictResolution = "none"
        if conflicts and conflict == "error":
            raise ValueError(
                f"A saved pipeline configuration named {document.name!r} already exists."
            )
        if conflicts and conflict == "rename":
            resolved_name = ConfigService._next_available_name(document.name)
            resolution = "renamed"
        elif conflicts and conflict == "replace":
            resolution = "replaced"

        saved_path = ConfigService.save_configuration(
            resolved_name,
            document.description,
            list(copy.deepcopy(document.shapers)),
            document.csv_path,
        )
        if resolution == "replaced":
            for old_path in conflicts:
                if not ConfigService.delete_configuration(old_path):
                    raise OSError(
                        f"Could not replace saved pipeline configuration {document.name!r}."
                    )

        return PipelineConfigImportResult(
            path=saved_path,
            name=resolved_name,
            original_name=document.name,
            description=document.description,
            shapers=tuple(copy.deepcopy(document.shapers)),
            csv_path=document.csv_path,
            schema_version=PIPELINE_CONFIG_SCHEMA_VERSION,
            migrated=document.migrated,
            conflict_resolution=resolution,
        )

    @staticmethod
    def _find_configurations_named(name: str) -> list[str]:
        """Return readable saved records whose logical name matches exactly."""
        matches: list[str] = []
        for entry in ConfigService.load_saved_configs():
            try:
                config = ConfigService.load_configuration(entry["path"])
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if isinstance(config, dict) and config.get("name") == name:
                matches.append(entry["path"])
        return matches

    @staticmethod
    def _next_available_name(name: str) -> str:
        """Return the first bounded ``Name (N)`` without a catalog conflict."""
        from src.core.common.security_limits import MAX_PIPELINE_CONFIG_NAME_LENGTH

        existing: set[str] = set()
        for entry in ConfigService.load_saved_configs():
            config_name = ConfigService._configuration_name(entry["path"])
            if config_name is not None:
                existing.add(config_name)
        suffix_number = 2
        while True:
            suffix = f" ({suffix_number})"
            candidate = name[: MAX_PIPELINE_CONFIG_NAME_LENGTH - len(suffix)].rstrip() + suffix
            if candidate not in existing:
                return candidate
            suffix_number += 1

    @staticmethod
    def _configuration_name(path: str) -> str | None:
        """Read one logical configuration name, ignoring unreadable records."""
        try:
            config = ConfigService.load_configuration(path)
        except (OSError, json.JSONDecodeError, ValueError):
            return None
        if not isinstance(config, dict):
            return None
        name = config.get("name")
        return name if isinstance(name, str) else None

    @staticmethod
    def load_configuration(config_path: str) -> SavedConfigData:
        """
        Load a configuration from file.

        Args:
            config_path: Path to configuration file.

        Returns:
            Configuration dictionary.
        """
        # [impl->req~ring5.data.saved-pipeline-configurations~1]
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
        # [impl->req~ring5.data.saved-pipeline-configurations~1]
        try:
            config_dir = ConfigService.get_config_dir()
            validated_path = validate_path_within(Path(config_path), config_dir)
            validated_path.unlink()
            return True
        except (OSError, ValueError) as e:
            logger.warning("Failed to delete config file %s: %s", config_path, e)
            return False
