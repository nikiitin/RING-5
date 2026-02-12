"""
Integration tests for the refactored RING-5 web application.
Tests the complete workflow with new features.
"""

import shutil
import tempfile
from pathlib import Path

import pandas as pd


def test_complete_workflow_integration():
    """Test complete workflow: load CSV, configure pipeline, apply transformations."""

    from src.core.application_api import ApplicationAPI

    # Setup
    test_dir = Path(tempfile.mkdtemp())
    facade = ApplicationAPI()

    try:
        # Create test CSV
        test_data = pd.DataFrame(
            {
                "benchmark": ["bm1", "bm2", "bm3", "bm4"],
                "config": ["A", "B", "A", "B"],
                "ipc": [1.5, 2.0, 1.8, 2.2],
                "latency": [100, 80, 90, 75],
            }
        )

        test_csv = test_dir / "test.csv"
        test_data.to_csv(test_csv, index=False)

        # Test 1: Load CSV
        loaded_data = facade.load_csv_file(str(test_csv))
        assert len(loaded_data) == 4
        assert list(loaded_data.columns) == ["benchmark", "config", "ipc", "latency"]

        # Test 2: Add to CSV pool
        pool_path = facade.add_to_csv_pool(str(test_csv))
        assert Path(pool_path).exists()

        # Test 3: Load CSV pool
        pool = facade.load_csv_pool()
        assert len(pool) > 0

        # Test 4: Create dynamic pipeline
        pipeline = [
            {"type": "columnSelector", "columns": ["benchmark", "ipc"]},
            {"type": "columnSelector", "columns": ["benchmark", "ipc"]},  # Multiple of same type
        ]

        # Test 5: Apply pipeline
        result = facade.apply_shapers(test_data, pipeline)
        assert "benchmark" in result.columns
        assert "ipc" in result.columns

        # Test 6: Save configuration
        config_path = facade.save_configuration(
            name="test_pipeline",
            description="Test dynamic pipeline",
            shapers_config=pipeline,
            csv_path=str(test_csv),
        )
        assert Path(config_path).exists()

        # Test 7: Load configuration
        loaded_config = facade.load_configuration(config_path)
        assert loaded_config["name"] == "test_pipeline"
        assert len(loaded_config["shapers"]) == 2

        # Test 8: Preview transformations (step by step)
        step1_result = facade.apply_shapers(test_data, pipeline[:1])
        assert len(step1_result.columns) == 2

        step2_result = facade.apply_shapers(test_data, pipeline[:2])
        assert len(step2_result.columns) == 2

        # Test 9: Data manager operations
        # Test filtering
        filtered = test_data[test_data["ipc"] > 1.7]
        assert len(filtered) == 3  # ipc values: 2.0, 1.8, 2.2 are > 1.7

        # Test column operations
        test_data_copy = test_data.copy()
        test_data_copy["new_col"] = test_data_copy["ipc"] * 2
        assert "new_col" in test_data_copy.columns

    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_pipeline_reordering():
    """Test pipeline reordering functionality."""
    pipeline = [
        {"type": "columnSelector", "columns": ["a", "b"]},
        {"type": "sort", "order_dict": {"col": ["x", "y"]}},
        {"type": "normalize", "normalizeVars": ["val"]},
    ]

    # Simulate moving item up
    pipeline[1], pipeline[0] = pipeline[0], pipeline[1]

    assert pipeline[0]["type"] == "sort"
    assert pipeline[1]["type"] == "columnSelector"


def test_multiple_same_shapers():
    """Test adding multiple shapers of the same type."""
    from src.core.application_api import ApplicationAPI

    facade = ApplicationAPI()

    test_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9], "d": [10, 11, 12]})

    # Pipeline with multiple column selectors
    pipeline = [
        {"type": "columnSelector", "columns": ["a", "b", "c"]},
        {"type": "columnSelector", "columns": ["a", "b"]},
    ]

    result = facade.apply_shapers(test_data, pipeline)

    assert len(result.columns) == 2
    assert "a" in result.columns
    assert "b" in result.columns
    assert "c" not in result.columns
