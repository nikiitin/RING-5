from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.web.facade import BackendFacade


@pytest.fixture
def facade(tmp_path):
    """
    Fixture creates a BackendFacade instance with temporary directories.
    Patches PathService to use temp directories for isolation.
    """
    # Create temp structure
    ring5_dir = tmp_path / ".ring5"
    ring5_dir.mkdir()
    csv_pool = ring5_dir / "csv_pool"
    csv_pool.mkdir()
    config_pool = ring5_dir / "saved_configs"
    config_pool.mkdir()

    # Patch PathService.get_data_dir to return our temp dir
    with patch("src.web.services.paths.PathService.get_data_dir", return_value=ring5_dir):
        with patch(
            "src.web.services.csv_pool_service.PathService.get_data_dir", return_value=ring5_dir
        ):
            with patch(
                "src.web.services.config_service.PathService.get_data_dir", return_value=ring5_dir
            ):
                # Initialize facade (will use patched paths)
                f = BackendFacade()
                # Override paths on facade too for backward compatibility
                f.ring5_data_dir = ring5_dir
                f.csv_pool_dir = csv_pool
                f.config_pool_dir = config_pool
                yield f


def test_csv_pool_operations(facade, tmp_path):
    """Test adding, listing, loading, and deleting CSV files."""

    # 1. Create a dummy CSV
    dummy_csv = tmp_path / "test_data.csv"
    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    df.to_csv(dummy_csv, index=False)

    # 2. Add to pool
    added_path = facade.add_to_csv_pool(str(dummy_csv))
    assert Path(added_path).exists()
    assert Path(added_path).parent == facade.csv_pool_dir

    # 3. List pool
    pool = facade.load_csv_pool()
    assert len(pool) == 1
    assert pool[0]["path"] == str(added_path)
    # Logic: f"parsed_{timestamp}.csv" -> Name is changed.
    assert "parsed_" in pool[0]["name"]

    # 4. Load CSV file content
    loaded_df = facade.load_csv_file(added_path)
    pd.testing.assert_frame_equal(df, loaded_df)

    # 5. Delete from pool
    assert facade.delete_from_csv_pool(added_path) is True
    assert not Path(added_path).exists()
    assert len(facade.load_csv_pool()) == 0


def test_configuration_operations(facade, tmp_path):
    """Test saving, listing, loading, and deleting configurations."""

    # 1. Save Config
    shapers_config = [{"type": "filter", "id": "1"}]
    # Use valid path string, doesn't need to exist for this test usually, but safer
    csv_path = str(tmp_path / "fake.csv")
    config_path = facade.save_configuration(
        name="Test Config",
        description="A test description",
        shapers_config=shapers_config,
        csv_path=csv_path,
    )

    assert Path(config_path).exists()

    # 2. List Configs
    configs = facade.load_saved_configs()
    assert len(configs) == 1
    assert configs[0]["description"] == "A test description"
    assert "Test Config" in configs[0]["name"]

    # 3. Load Config
    loaded_config = facade.load_configuration(config_path)
    assert loaded_config["name"] == "Test Config"
    assert loaded_config["shapers"] == shapers_config
    assert loaded_config["csv_path"] == str(tmp_path / "fake.csv")

    # 4. Delete Config
    assert facade.delete_configuration(config_path) is True
    assert not Path(config_path).exists()
    assert len(facade.load_saved_configs()) == 0


def test_csv_pool_sorting(facade, tmp_path):
    """Test that CSV pool is sorted by modification time (reverse)."""

    # Create 3 files with different times
    for i in range(3):
        p = facade.csv_pool_dir / f"file_{i}.csv"
        p.touch()
        # Force mtime difference
        import os

        os.utime(p, (1000 + i * 100, 1000 + i * 100))

    pool = facade.load_csv_pool()
    assert len(pool) == 3
    # Check descending order
    assert pool[0]["name"] == "file_2.csv"
    assert pool[1]["name"] == "file_1.csv"
    assert pool[2]["name"] == "file_0.csv"
