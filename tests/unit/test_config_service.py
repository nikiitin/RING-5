"""
Comprehensive tests for ConfigService following Rule 004 (QA Testing Mastery).

Test Strategy:
- File-based configuration management testing
- tmp_path for I/O isolation
- Parametrization for various config scenarios
- AAA pattern throughout
- Error handling verification
"""

import json
from pathlib import Path

import pytest

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
    ):
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

    def test_get_config_dir_is_idempotent(self, empty_config_dir: Path):
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

    def test_save_configuration_creates_file(self, empty_config_dir: Path):
        """Verify configuration file is created."""
        # Arrange
        shapers = [{"type": "normalize", "baseline": "config1"}]

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

    def test_save_configuration_includes_timestamp(self, empty_config_dir: Path):
        """Verify saved filename includes timestamp."""
        # Act
        config_path = ConfigService.save_configuration(
            name="myconfig", description="Test", shapers_config=[]
        )

        # Assert
        filename = Path(config_path).name
        assert filename.startswith("myconfig_")
        assert filename.endswith(".json")
        assert len(filename.split("_")) >= 3  # name_date_time.json

    def test_save_configuration_stores_all_fields(self, empty_config_dir: Path):
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

    def test_save_configuration_without_csv_path(self, empty_config_dir: Path):
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
    ):
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

    def test_load_saved_configs_returns_empty_list_for_empty_dir(self, empty_config_dir: Path):
        """Verify empty directory returns empty list."""
        # Act
        configs = ConfigService.load_saved_configs()

        # Assert
        assert configs == []

    def test_load_saved_configs_lists_all_configs(self, populated_config_dir: Path):
        """Verify all config files are listed."""
        # Act
        configs = ConfigService.load_saved_configs()

        # Assert
        assert len(configs) == 3
        assert all("path" in c for c in configs)
        assert all("name" in c for c in configs)
        assert all("modified" in c for c in configs)
        assert all("description" in c for c in configs)

    def test_load_saved_configs_sorts_by_modified_time(self, populated_config_dir: Path):
        """Verify configs sorted by modification time (newest first)."""
        import time

        # Arrange - Touch one file to make it newer
        newest_file = populated_config_dir / "config_0_20260101_120000.json"
        time.sleep(0.1)  # Small delay to ensure distinct mtime
        newest_file.touch()

        # Act
        configs = ConfigService.load_saved_configs()

        # Assert
        assert configs[0]["name"] == "config_0_20260101_120000.json"
        assert configs[0]["modified"] >= configs[1]["modified"]

    def test_load_saved_configs_extracts_description(self, populated_config_dir: Path):
        """Verify description is extracted from config data."""
        # Act
        configs = ConfigService.load_saved_configs()

        # Assert
        assert all(c["description"] == "Test configuration for shapers" for c in configs)

    def test_load_saved_configs_handles_malformed_json(self, empty_config_dir: Path):
        """Verify malformed JSON files are skipped gracefully."""
        # Arrange - Create invalid JSON file
        malformed_file = empty_config_dir / "malformed.json"
        malformed_file.write_text("{ invalid json")

        # Act
        configs = ConfigService.load_saved_configs()

        # Assert - Should skip malformed file
        assert len(configs) == 0

    def test_load_saved_configs_handles_missing_description(self, empty_config_dir: Path):
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

    def test_load_saved_configs_ignores_non_json_files(self, empty_config_dir: Path):
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
    ):
        """Verify individual config file is loaded correctly."""
        # Arrange
        config_file = populated_config_dir / "config_0_20260101_120000.json"

        # Act
        loaded_config = ConfigService.load_configuration(str(config_file))

        # Assert
        assert loaded_config["name"] == "config_0"
        assert loaded_config["description"] == sample_config_dict["description"]
        assert loaded_config["shapers"] == sample_config_dict["shapers"]

    def test_load_configuration_raises_on_missing_file(self, tmp_path: Path):
        """Verify FileNotFoundError for missing config."""
        # Arrange
        missing_file = tmp_path / "missing.json"

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            ConfigService.load_configuration(str(missing_file))

    def test_load_configuration_raises_on_invalid_json(self, tmp_path: Path):
        """Verify JSONDecodeError for malformed files."""
        # Arrange
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ broken json")

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            ConfigService.load_configuration(str(invalid_file))


# ============================================================================
# Integration Tests
# ============================================================================


class TestConfigurationRoundTrip:
    """Test saving and loading configurations together."""

    def test_save_and_load_preserves_data(self, empty_config_dir: Path):
        """Verify round-trip save and load preserves all data."""
        # Arrange
        original_shapers = [
            {"type": "normalize", "baseline": "base", "column": "value"},
            {"type": "mean", "method": "geometric"},
        ]

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
        assert loaded_config["description"] == "Round trip test"
        assert loaded_config["shapers"] == original_shapers
        assert loaded_config["csv_path"] == "/data/test.csv"

    def test_multiple_saves_create_unique_files(self, empty_config_dir: Path):
        """Verify multiple saves of same config create unique files."""
        import time

        # Act
        path1 = ConfigService.save_configuration("test", "desc1", [])
        time.sleep(1.1)  # Ensure timestamp differs
        path2 = ConfigService.save_configuration("test", "desc2", [])

        # Assert
        assert path1 != path2
        assert Path(path1).exists()
        assert Path(path2).exists()

        # Verify different descriptions
        config1 = ConfigService.load_configuration(path1)
        config2 = ConfigService.load_configuration(path2)
        assert config1["description"] == "desc1"
        assert config2["description"] == "desc2"
