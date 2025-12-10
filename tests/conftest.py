"""Pytest configuration and fixtures."""

import pytest

from src.data_management.dataManager import DataManager


@pytest.fixture(autouse=True)
def reset_data_manager():
    """Reset DataManager class variables before each test."""
    # Reset all class variables to None
    DataManager._df_data = None
    DataManager._categorical_columns_data = None
    DataManager._statistic_columns_data = None
    DataManager._csvPath_data = None
    yield
    # Cleanup after test
    DataManager._df_data = None
    DataManager._categorical_columns_data = None
    DataManager._statistic_columns_data = None
    DataManager._csvPath_data = None
