from pathlib import Path

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.core.services.data_services.config_service import ConfigService
from src.core.services.data_services.csv_pool_service import CsvPoolService

pytestmark = pytest.mark.usefixtures("isolated_application_data")


def test_csv_pool_operations(
    facade: ApplicationAPI, tmp_path: Path, isolated_application_data: Path
) -> None:
    """Test adding, listing, loading, and deleting CSV files."""

    # Create a dummy CSV
    dummy_csv = tmp_path / "test_data.csv"
    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    df.to_csv(dummy_csv, index=False)

    # Add to pool
    added_path = facade.data_services.add_to_csv_pool(str(dummy_csv))
    assert Path(added_path).exists()
    assert Path(added_path).parent == CsvPoolService.get_pool_dir()
    assert CsvPoolService.get_pool_dir() == isolated_application_data / "csv_pool"

    # List pool
    pool = facade.data_services.load_csv_pool()
    assert len(pool) == 1
    assert pool[0]["path"] == str(added_path)
    # Logic: f"parsed_{timestamp}.csv" -> Name is changed.
    assert "parsed_" in pool[0]["name"]

    # Load CSV file content
    loaded_df = facade.data_services.load_csv_file(added_path)
    pd.testing.assert_frame_equal(df, loaded_df)

    # Delete from pool
    assert facade.data_services.delete_from_csv_pool(added_path) is True
    assert not Path(added_path).exists()
    assert len(facade.data_services.load_csv_pool()) == 0


def test_configuration_operations(
    facade: ApplicationAPI, tmp_path: Path, isolated_application_data: Path
) -> None:
    """Test saving, listing, loading, and deleting configurations."""

    # Save Config
    shapers_config = [{"type": "columnSelector", "columns": ["ipc"]}]
    # Use valid path string, doesn't need to exist for this test usually, but safer
    csv_path = str(tmp_path / "fake.csv")
    config_path = facade.data_services.save_configuration(
        name="Test Config",
        description="A test description",
        shapers_config=shapers_config,
        csv_path=csv_path,
    )

    assert Path(config_path).exists()
    assert Path(config_path).parent == ConfigService.get_config_dir()
    assert ConfigService.get_config_dir() == isolated_application_data / "saved_configs"

    # List Configs
    configs = facade.data_services.load_saved_configs()
    assert len(configs) == 1
    assert configs[0]["description"] == "A test description"
    assert "Test Config" in configs[0]["name"]

    # Load Config
    loaded_config = facade.data_services.load_configuration(config_path)
    assert loaded_config["name"] == "Test Config"
    assert loaded_config["shapers"] == shapers_config
    assert loaded_config["csv_path"] == str(tmp_path / "fake.csv")

    # Delete Config
    assert facade.data_services.delete_configuration(config_path) is True
    assert not Path(config_path).exists()
    assert len(facade.data_services.load_saved_configs()) == 0


def test_csv_pool_sorting(facade: ApplicationAPI, tmp_path: Path) -> None:
    """Test that CSV pool is sorted by modification time (reverse)."""

    # Create 3 files with different times
    for i in range(3):
        p = CsvPoolService.get_pool_dir() / f"file_{i}.csv"
        p.touch()
        # Force mtime difference
        import os

        os.utime(p, (1000 + i * 100, 1000 + i * 100))

    pool = facade.data_services.load_csv_pool()
    assert len(pool) == 3
    # Check descending order
    assert pool[0]["name"] == "file_2.csv"
    assert pool[1]["name"] == "file_1.csv"
    assert pool[2]["name"] == "file_0.csv"
