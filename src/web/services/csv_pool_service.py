"""
CSV Pool Service
Manages CSV file storage and retrieval in the data pool.

Performance optimizations:
- Metadata caching (columns, row counts, dtypes)
- Fast lookup index by filename
- Cached CSV type inference
"""

import datetime
import hashlib
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.performance import SimpleCache
from src.web.services.paths import PathService


class CsvPoolService:
    """Service for managing CSV files in the data pool with performance optimizations."""

    # Cache for CSV metadata (columns, row count, dtypes)
    _metadata_cache: SimpleCache = SimpleCache(maxsize=100, ttl=600)  # 10 min TTL

    # Cache for parsed CSV DataFrames (LRU with size limit)
    _dataframe_cache: SimpleCache = SimpleCache(maxsize=10, ttl=300)  # 5 min TTL

    # Index for fast filename lookups
    _pool_index: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def get_pool_dir() -> Path:
        """Get the CSV pool directory path."""
        pool_dir = PathService.get_data_dir() / "csv_pool"
        pool_dir.mkdir(parents=True, exist_ok=True)
        return pool_dir

    @staticmethod
    def load_pool() -> List[Dict[str, Any]]:
        """
        Load list of CSV files in the pool with metadata caching.

        Returns:
            List of dicts with 'path', 'name', 'size', 'modified', 'columns', 'rows' keys.
        """
        pool_dir = CsvPoolService.get_pool_dir()
        pool = []
        new_index: Dict[str, Dict[str, Any]] = {}

        for csv_file in sorted(
            pool_dir.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            file_info = {
                "path": str(csv_file),
                "name": csv_file.name,
                "size": csv_file.stat().st_size,
                "modified": csv_file.stat().st_mtime,
            }

            # Try to get cached metadata
            metadata = CsvPoolService._get_csv_metadata(str(csv_file))
            if metadata:
                file_info.update(metadata)

            pool.append(file_info)
            new_index[csv_file.name] = file_info

        # Update index
        CsvPoolService._pool_index = new_index

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
        Load a CSV file with automatic separator detection and caching.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            DataFrame with the CSV data.
        """
        # Check cache first
        cache_key = CsvPoolService._compute_file_hash(csv_path)
        cached_df = CsvPoolService._dataframe_cache.get(cache_key)
        if cached_df is not None:
            return cached_df

        # Load with optimizations
        # Note: low_memory doesn't work with python engine, so we use C engine when possible
        df = pd.read_csv(
            csv_path,
            sep=None,
            engine="python",
        )

        # Cache the DataFrame
        CsvPoolService._dataframe_cache.set(cache_key, df)

        # Also cache metadata
        metadata = {
            "columns": list(df.columns),
            "rows": len(df),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }
        CsvPoolService._metadata_cache.set(csv_path, metadata)

        return df

    @staticmethod
    def _compute_file_hash(file_path: str) -> str:
        """
        Compute hash of file for cache key (based on path + mtime).

        Args:
            file_path: Path to the file

        Returns:
            Hash string for cache key
        """
        path = Path(file_path)
        if path.exists():
            mtime = path.stat().st_mtime
            key = f"{file_path}_{mtime}"
            return hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()[:16]
        return file_path

    @staticmethod
    def _get_csv_metadata(csv_path: str) -> Optional[Dict[str, Any]]:
        """
        Get cached metadata for a CSV file, or compute it.

        Args:
            csv_path: Path to the CSV file

        Returns:
            Dict with 'columns', 'rows', 'dtypes' or None if error
        """
        # Check cache
        cached = CsvPoolService._metadata_cache.get(csv_path)
        if cached is not None:
            return cached

        # Compute metadata by reading just the header and counting rows
        try:
            # Fast row count without loading entire file
            with open(csv_path, "r") as f:
                row_count = sum(1 for _ in f) - 1  # Subtract header

            # Read just first row to get columns and types
            sample_df = pd.read_csv(csv_path, sep=None, engine="python", nrows=100)

            metadata = {
                "columns": list(sample_df.columns),
                "rows": row_count,
                "dtypes": {col: str(dtype) for col, dtype in sample_df.dtypes.items()},
            }

            # Cache it
            CsvPoolService._metadata_cache.set(csv_path, metadata)
            return metadata
        except Exception:
            return None

    @staticmethod
    def clear_caches() -> None:
        """Clear all CSV pool caches."""
        CsvPoolService._metadata_cache.clear()
        CsvPoolService._dataframe_cache.clear()
        CsvPoolService._pool_index.clear()

    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            "metadata_cache": CsvPoolService._metadata_cache.stats(),
            "dataframe_cache": CsvPoolService._dataframe_cache.stats(),
            "index_size": len(CsvPoolService._pool_index),
        }
