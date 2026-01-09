"""
CSV Pool Service
Manages CSV file storage and retrieval in the data pool.
"""

import datetime
import shutil
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.web.services.paths import PathService


class CsvPoolService:
    """Service for managing CSV files in the data pool."""

    @staticmethod
    def get_pool_dir() -> Path:
        """Get the CSV pool directory path."""
        pool_dir = PathService.get_data_dir() / "csv_pool"
        pool_dir.mkdir(parents=True, exist_ok=True)
        return pool_dir

    @staticmethod
    def load_pool() -> List[Dict[str, Any]]:
        """
        Load list of CSV files in the pool.

        Returns:
            List of dicts with 'path', 'name', 'size', 'modified' keys.
        """
        pool_dir = CsvPoolService.get_pool_dir()
        pool = []

        for csv_file in sorted(
            pool_dir.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            pool.append(
                {
                    "path": str(csv_file),
                    "name": csv_file.name,
                    "size": csv_file.stat().st_size,
                    "modified": csv_file.stat().st_mtime,
                }
            )

        return pool

    @staticmethod
    def add_to_pool(csv_path: str) -> str:
        """
        Add a CSV file to the pool with timestamp.

        Args:
            csv_path: Path to the CSV file to add.

        Returns:
            Path to the file in the pool.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        pool_path = CsvPoolService.get_pool_dir() / f"parsed_{timestamp}.csv"
        shutil.copy(csv_path, pool_path)
        return str(pool_path)

    @staticmethod
    def delete_from_pool(csv_path: str) -> bool:
        """
        Delete a CSV file from the pool.

        Args:
            csv_path: Path to the CSV file to delete.

        Returns:
            True if deleted successfully.
        """
        try:
            Path(csv_path).unlink()
            return True
        except Exception:
            return False

    @staticmethod
    def load_csv_file(csv_path: str) -> pd.DataFrame:
        """
        Load a CSV file with automatic separator detection.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            DataFrame with the CSV data.
        """
        return pd.read_csv(csv_path, sep=None, engine="python")
