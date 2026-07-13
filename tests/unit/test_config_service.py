"""
Behavioral tests for configuration persistence and validation.

Test Strategy:
- File-based configuration management testing
- tmp_path for I/O isolation
- Parametrization for various config scenarios
- AAA pattern throughout
- Error handling verification
"""

import json
from pathlib import Path
from typing import cast

import pytest

from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.data_services.config_service import ConfigService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def empty_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create empty config directory with patched PathService."""
    config_dir = tmp_path / "saved_configs"
    config_dir.mkdir()

    monkeypatch.setattr(
        "src.core.services.data_services.config_service.PathService.get_data_dir", lambda: tmp_path
    )
    # Reset class-level cache so it picks up the monkeypatched path
    monkeypatch.setattr(
        "src.core.services.data_services.config_service.ConfigService._config_dir", None
    )

    return config_dir


@pytest.fixture
def sample_config_dict() -> dict:
    """Sample configuration dictionary."""
    return {
        "name": "test_config",
        "description": "Test configuration for shapers",
        "shapers": [
            {"type": "normalize", "baseline": "config1"},
            {"type": "sort", "columns": ["benchmark"]},
        ],
        "csv_path": "/path/to/data.csv",
    }


@pytest.fixture
def populated_config_dir(empty_config_dir: Path, sample_config_dict: dict) -> Path:
    """Create config directory with sample configs."""
    for i in range(3):
        config_file = empty_config_dir / f"config_{i}_20260101_120000.json"
        with open(config_file, "w") as f:
            json.dump({**sample_config_dict, "name": f"config_{i}"}, f)

    return empty_config_dir


# ============================================================================
# Directory Management Tests
# ============================================================================


class TestConfigDirectory:
    """Test configuration directory management."""

    def test_get_config_dir_creates_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify config directory is created on first access."""
        # Arrange
        monkeypatch.setattr(
            "src.core.services.data_services.config_service.PathService.get_data_dir",
            lambda: tmp_path,
        )
        expected_dir = tmp_path / "saved_configs"

        # Act
        config_dir = ConfigService.get_config_dir()

        # Assert
        assert config_dir == expected_dir
        assert config_dir.exists()
        assert config_dir.is_dir()

    def test_get_config_dir_is_idempotent(self, empty_config_dir: Path) -> None:
        """Verify repeated calls return same directory."""
        # Act
        dir1 = ConfigService.get_config_dir()
        dir2 = ConfigService.get_config_dir()

        # Assert
        assert dir1 == dir2 == empty_config_dir


# ============================================================================
# Configuration Saving Tests
# ============================================================================


class TestConfigurationSaving:
    """Test configuration saving functionality."""

    def test_save_configuration_creates_file(self, empty_config_dir: Path) -> None:
        """Verify configuration file is created."""
        # Arrange
        shapers = cast(
            list[ShaperStepConfig],
            [{"type": "normalize", "baseline": "config1"}],
        )

        # Act
        config_path = ConfigService.save_configuration(
            name="test",
            description="Test config",
            shapers_config=shapers,
            csv_path="/path/to/data.csv",
        )

        # Assert
        assert Path(config_path).exists()
        assert Path(config_path).parent == empty_config_dir

    def test_save_configuration_includes_timestamp(self, empty_config_dir: Path) -> None:
        """Verify saved filename includes timestamp."""
        # Act
        config_path = ConfigService.save_configuration(
            name="myconfig", description="Test", shapers_config=[]
        )

        # Assert
        filename = Path(config_path).name
        assert filename.startswith("myconfig_")
        assert filename.endswith(".json")
        assert len(filename.split("_")) >= 3  # name_date_time_uid.json

    def test_save_configuration_same_name_same_second_no_overwrite(
        self, empty_config_dir: Path
    ) -> None:
        """Two same-name saves within one second must yield distinct files.

        Timestamps have 1-second resolution; without a uniqueness suffix the
        second save would silently replace the first.
        """
        # Act — back-to-back saves land within the same wall-clock second
        path1 = ConfigService.save_configuration(name="dup", description="a", shapers_config=[])
        path2 = ConfigService.save_configuration(name="dup", description="b", shapers_config=[])

        # Assert
        assert path1 != path2
        assert Path(path1).exists()
        assert Path(path2).exists()

    def test_save_configuration_stores_all_fields(self, empty_config_dir: Path) -> None:
        """Verify all configuration fields are saved."""
        # Arrange
        name = "test_config"
        description = "Test description"
        shapers = [
            {"type": "normalize", "baseline": "baseline"},
            {"type": "sort", "columns": ["benchmark"]},
        ]
        csv_path = "/path/data.csv"

        # Act
        config_path = ConfigService.save_configuration(
            name=name, description=description, shapers_config=shapers, csv_path=csv_path
        )

        # Assert
        with open(config_path) as f:
            saved_data = json.load(f)

        assert saved_data["name"] == name
        assert saved_data["description"] == description
        assert saved_data["shapers"] == shapers
        assert saved_data["csv_path"] == csv_path
        assert "timestamp" in saved_data

    def test_save_configuration_without_csv_path(self, empty_config_dir: Path) -> None:
        """Verify csv_path is optional."""
        # Act
        config_path = ConfigService.save_configuration(
            name="test", description="Test", shapers_config=[]
        )

        # Assert
        with open(config_path) as f:
            saved_data = json.load(f)

        assert saved_data["csv_path"] is None

    @pytest.mark.parametrize(
        "special_chars", ["config-with-dashes", "config_with_underscores", "ConfigMixedCase"]
    )
    def test_save_configuration_handles_special_names(
        self, empty_config_dir: Path, special_chars: str
    ) -> None:
        """Verify various naming formats are handled."""
        # Act
        config_path = ConfigService.save_configuration(
            name=special_chars, description="Test", shapers_config=[]
        )

        # Assert
        assert Path(config_path).exists()
        assert special_chars in Path(config_path).name


# ============================================================================
# Configuration Loading Tests
# ============================================================================


class TestConfigurationLoading:
    """Test configuration loading functionality."""

    def test_load_saved_configs_returns_empty_list_for_empty_dir(
        self, empty_config_dir: Path
    ) -> None:
        """Verify empty directory returns empty list."""
        # Act
        configs = ConfigService.load_saved_configs()

        # Assert
        assert configs == []

    def test_load_saved_configs_lists_all_configs(self, populated_config_dir: Path) -> None:
        """Verify all config files are listed."""
        # Act
        configs = ConfigService.load_saved_configs()

        # Assert
        assert len(configs) == 3
        assert all("path" in c for c in configs)
        assert all("name" in c for c in configs)
        assert all("modified" in c for c in configs)
        assert all("description" in c for c in configs)

    def test_load_saved_configs_sorts_by_modified_time(self, populated_config_dir: Path) -> None:
        """Verify configs sorted by modification time (newest first)."""
        import os

        # Arrange - Set explicit mtime to make one file clearly newest
        newest_file = populated_config_dir / "config_0_20260101_120000.json"
        os.utime(newest_file, (9999999999, 9999999999))

        # Act
        configs = ConfigService.load_saved_configs()

        # Assert
        assert configs[0]["name"] == "config_0_20260101_120000.json"
        assert configs[0]["modified"] >= configs[1]["modified"]

    def test_load_saved_configs_extracts_description(self, populated_config_dir: Path) -> None:
        """Verify description is extracted from config data."""
        # Act
        configs = ConfigService.load_saved_configs()

        # Assert
        assert all(c["description"] == "Test configuration for shapers" for c in configs)

    def test_load_saved_configs_handles_malformed_json(self, empty_config_dir: Path) -> None:
        """Verify malformed JSON files are skipped gracefully."""
        # Arrange - Create invalid JSON file
        malformed_file = empty_config_dir / "malformed.json"
        malformed_file.write_text("{ invalid json")

        # Act
        configs = ConfigService.load_saved_configs()

        # Assert - Should skip malformed file
        assert len(configs) == 0

    def test_load_saved_configs_handles_missing_description(self, empty_config_dir: Path) -> None:
        """Verify configs without description get default value."""
        # Arrange
        config_file = empty_config_dir / "nodesc.json"
        with open(config_file, "w") as f:
            json.dump({"name": "test"}, f)

        # Act
        configs = ConfigService.load_saved_configs()

        # Assert
        assert len(configs) == 1
        assert configs[0]["description"] == "No description"

    def test_load_saved_configs_ignores_non_json_files(self, empty_config_dir: Path) -> None:
        """Verify only .json files are processed."""
        # Arrange
        (empty_config_dir / "config.txt").write_text("not json")
        (empty_config_dir / "config.json").write_text('{"name": "test"}')

        # Act
        configs = ConfigService.load_saved_configs()

        # Assert
        assert len(configs) == 1
        assert configs[0]["name"] == "config.json"

    def test_load_configuration_reads_file_correctly(
        self, populated_config_dir: Path, sample_config_dict: dict
    ) -> None:
        """Verify individual config file is loaded correctly."""
        # Arrange
        config_file = populated_config_dir / "config_0_20260101_120000.json"

        # Act
        loaded_config = ConfigService.load_configuration(str(config_file))

        # Assert
        assert loaded_config["name"] == "config_0"
        assert loaded_config.get("description") == sample_config_dict["description"]
        assert loaded_config["shapers"] == sample_config_dict["shapers"]

    def test_load_configuration_raises_on_missing_file(self, empty_config_dir: Path) -> None:
        """Verify FileNotFoundError for missing config."""
        # Arrange - use a path within the config dir (matching real usage)
        missing_file = empty_config_dir / "missing.json"

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            ConfigService.load_configuration(str(missing_file))

    def test_load_configuration_raises_on_invalid_json(self, empty_config_dir: Path) -> None:
        """Verify JSONDecodeError for malformed files."""
        # Arrange - create invalid JSON within the config dir
        invalid_file = empty_config_dir / "invalid.json"
        invalid_file.write_text("{ broken json")

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            ConfigService.load_configuration(str(invalid_file))


# ============================================================================
# Integration Tests
# ============================================================================


class TestConfigurationRoundTrip:
    """Test saving and loading configurations together."""

    def test_save_and_load_preserves_data(self, empty_config_dir: Path) -> None:
        """Verify round-trip save and load preserves all data."""
        # Arrange
        original_shapers = cast(
            list[ShaperStepConfig],
            [
                {"type": "normalize", "baseline": "base", "column": "value"},
                {"type": "mean", "method": "geometric"},
            ],
        )

        # Act - Save
        saved_path = ConfigService.save_configuration(
            name="roundtrip",
            description="Round trip test",
            shapers_config=original_shapers,
            csv_path="/data/test.csv",
        )

        # Act - Load
        loaded_config = ConfigService.load_configuration(saved_path)

        # Assert - Data preserved
        assert loaded_config["name"] == "roundtrip"
        assert loaded_config.get("description") == "Round trip test"
        assert loaded_config["shapers"] == original_shapers
        assert loaded_config.get("csv_path") == "/data/test.csv"

    def test_multiple_saves_create_unique_files(self, empty_config_dir: Path) -> None:
        """Verify multiple saves of same config create unique files."""
        import datetime
        from unittest.mock import patch

        # Act - Mock datetime.now to return distinct timestamps
        fake_time1 = datetime.datetime(2026, 1, 1, 12, 0, 0)
        fake_time2 = datetime.datetime(2026, 1, 1, 12, 0, 5)

        with patch("src.core.services.data_services.config_service.datetime.datetime") as mock_dt:
            mock_dt.now.return_value = fake_time1
            mock_dt.strftime = datetime.datetime.strftime
            path1 = ConfigService.save_configuration("test", "desc1", [])

            mock_dt.now.return_value = fake_time2
            path2 = ConfigService.save_configuration("test", "desc2", [])

        # Assert
        assert path1 != path2
        assert Path(path1).exists()
        assert Path(path2).exists()

        # Verify different descriptions
        config1 = ConfigService.load_configuration(path1)
        config2 = ConfigService.load_configuration(path2)
        assert config1.get("description") == "desc1"
        assert config2.get("description") == "desc2"
