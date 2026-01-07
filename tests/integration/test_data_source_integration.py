
import pytest
import shutil
import json
import pandas as pd
from pathlib import Path
from src.web.facade import BackendFacade

@pytest.fixture
def facade(tmp_path):
    """
    Fixture creates a BackendFacade instance with temporary directories.
    """
    # Create temp structure
    ring5_dir = tmp_path / ".ring5"
    ring5_dir.mkdir()
    
    # Initialize facade
    f = BackendFacade()
    
    # Override paths to use temp dir
    f.ring5_data_dir = ring5_dir
    f.csv_pool_dir = ring5_dir / "csv_pool"
    f.config_pool_dir = ring5_dir / "saved_configs"
    
    # Create directories
    f.csv_pool_dir.mkdir()
    f.config_pool_dir.mkdir()
    
    return f

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
    # Check if original name is preserved or timestamp added? 
    # Logic: f"parsed_{timestamp}.csv" -> Name is changed.
    assert "parsed_" in pool[0]["name"]
    
    # 4. Load CSV file content
    loaded_df = facade.load_csv_file(added_path)
    pd.testing.assert_frame_equal(df, loaded_df)
    
    # 5. Delete from pool
    assert facade.delete_from_csv_pool(added_path) is True
    assert not Path(added_path).exists()
    assert len(facade.load_csv_pool()) == 0

def test_configuration_operations(facade):
    """Test saving, listing, loading, and deleting configurations."""
    
    # 1. Save Config
    shapers_config = [{"type": "filter", "id": "1"}]
    config_path = facade.save_configuration(
        name="Test Config",
        description="A test description",
        shapers_config=shapers_config,
        csv_path="/tmp/fake.csv"
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
    assert loaded_config["csv_path"] == "/tmp/fake.csv"
    
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
        os.utime(p, (1000 + i*100, 1000 + i*100))
        
    pool = facade.load_csv_pool()
    assert len(pool) == 3
    # Check descending order
    assert pool[0]["name"] == "file_2.csv"
    assert pool[1]["name"] == "file_1.csv"
    assert pool[2]["name"] == "file_0.csv"
