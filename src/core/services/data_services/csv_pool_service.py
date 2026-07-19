"""Cached storage and metadata access for the CSV data pool."""

import csv
import datetime
import hashlib
import logging
import shutil
import threading
import uuid
from pathlib import Path
from typing import cast

import pandas as pd
from pandas import DataFrame

from src.core.common.utils import validate_path_within
from src.core.models.data_models import CacheStatsInfo, CsvMetadata, CsvPoolEntry
from src.core.performance import SimpleCache
from src.core.services.data_services.path_service import PathService

logger = logging.getLogger(__name__)


class CsvPoolService:
    """Service for managing CSV files in the data pool with performance optimizations."""

    # [impl->req~ring5.ingestion.csv-pool~1]

    # Cache for CSV metadata (columns, row count, dtypes)
    _metadata_cache: SimpleCache = SimpleCache(maxsize=100, ttl=600)  # 10 min TTL

    # Cache for parsed CSV DataFrames (LRU with size limit)
    _dataframe_cache: SimpleCache = SimpleCache(maxsize=10, ttl=300)  # 5 min TTL

    # Index for fast filename lookups
    _pool_index: dict[str, CsvPoolEntry] = {}
    _pool_lock: threading.Lock = threading.Lock()

    _pool_dir: Path | None = None

    @staticmethod
    def get_pool_dir() -> Path:
        """Get the CSV pool directory path."""
        if CsvPoolService._pool_dir is None:
            CsvPoolService._pool_dir = PathService.get_data_dir() / "csv_pool"
            CsvPoolService._pool_dir.mkdir(parents=True, exist_ok=True)
        return CsvPoolService._pool_dir

    @staticmethod
    def load_pool() -> list[CsvPoolEntry]:
        """
        Load list of CSV files in the pool with metadata caching.

        Returns:
            List of dicts with 'path', 'name', 'size', 'modified', 'columns', 'rows' keys.
        """
        pool_dir = CsvPoolService.get_pool_dir()
        pool: list[CsvPoolEntry] = []
        new_index: dict[str, CsvPoolEntry] = {}

        for csv_file in sorted(
            pool_dir.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            file_info: CsvPoolEntry = {
                "path": str(csv_file),
                "name": csv_file.name,
                "size": csv_file.stat().st_size,
                "modified": csv_file.stat().st_mtime,
            }

            # Try to get cached metadata
            metadata = CsvPoolService._get_csv_metadata(str(csv_file))
            if metadata:
                file_info["columns"] = metadata["columns"]
                file_info["rows"] = metadata["rows"]
                file_info["dtypes"] = metadata["dtypes"]

            pool.append(file_info)
            new_index[csv_file.name] = file_info

        # Update index
        with CsvPoolService._pool_lock:
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
        # uuid suffix: timestamps have 1-second resolution, so two adds in the
        # same second (parallel sessions / batch CLI) would silently overwrite.
        unique = uuid.uuid4().hex[:8]
        pool_dir = CsvPoolService.get_pool_dir()
        pool_path = validate_path_within(pool_dir / f"parsed_{timestamp}_{unique}.csv", pool_dir)
        source_path = Path(csv_path).resolve()
        shutil.copy(str(source_path), pool_path)
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
            pool_dir = CsvPoolService.get_pool_dir()
            validated_path = validate_path_within(Path(csv_path), pool_dir)
            validated_path.unlink()
            return True
        except (OSError, ValueError) as e:
            logger.warning("Failed to delete CSV file %s: %s", csv_path, e)
            return False

    @staticmethod
    def load_csv_file(csv_path: str) -> pd.DataFrame:
        """
        Load a CSV file with automatic separator detection and caching.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            DataFrame with the CSV data.

        Raises:
            ValueError: If the path is empty or whitespace-only.
            FileNotFoundError: If the resolved path does not exist.
            IsADirectoryError: If the resolved path is a directory.
        """
        # [impl->req~ring5.ingestion.csv-delimiter-detection~1]
        # Validate input before resolving
        if not csv_path or not csv_path.strip():
            raise ValueError(f"Invalid CSV path: '{csv_path}'")

        # Resolve path to prevent traversal in any path components
        resolved_path = str(Path(csv_path).resolve())

        # Validate the resolved path points to an existing file
        resolved = Path(resolved_path)
        if not resolved.exists():
            raise FileNotFoundError(f"CSV file not found: {resolved_path}")
        if resolved.is_dir():
            raise IsADirectoryError(f"Path is a directory, not a file: {resolved_path}")

        # Check cache first
        cache_key = CsvPoolService._compute_file_hash(resolved_path)
        cached_df = CsvPoolService._dataframe_cache.get(cache_key)
        if cached_df is not None:
            # Defensive copy: the cache holds one pristine frame shared by every
            # caller (and every session) — handing out the cached object itself
            # would let one caller's in-place mutation corrupt all the others.
            # Shallow (deep=False) is sufficient and ~1000× cheaper: pandas 3
            # Copy-on-Write isolates every mutation path through the new frame.
            return cast(DataFrame, cached_df).copy(deep=False)

        # Automatic delimiter detection requires pandas' Python parser.
        result: DataFrame = pd.read_csv(
            resolved_path,
            sep=None,
            engine="python",
        )

        # Cache the DataFrame
        CsvPoolService._dataframe_cache.set(cache_key, result)

        # Also cache metadata
        metadata: CsvMetadata = {
            "columns": list(result.columns),
            "rows": len(result),
            "dtypes": {str(col): str(dtype) for col, dtype in result.dtypes.items()},
        }
        CsvPoolService._metadata_cache.set(resolved_path, metadata)

        return result.copy(deep=False)

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
    def _get_csv_metadata(csv_path: str) -> CsvMetadata | None:
        """
        Get cached metadata for a CSV file, or compute it.

        Args:
            csv_path: Path to the CSV file

        Returns:
            Dict with 'columns', 'rows', 'dtypes' or None if error
        """
        # [impl->req~ring5.ingestion.csv-delimiter-detection~1]
        # Use the resolved path as the canonical cache key, matching
        # the key load_csv_file writes under, so a load followed by a listing actually hits.
        resolved_path = str(Path(csv_path).resolve())

        # Check cache
        cached = CsvPoolService._metadata_cache.get(resolved_path)
        if cached is not None:
            return cast(CsvMetadata, cached)

        # Compute metadata by reading just the header and counting rows
        try:

            # Fast row count without loading entire file
            with open(resolved_path) as f:
                row_count = max(0, sum(1 for _ in f) - 1)  # Subtract header

            # Read just first row to get columns and types
            sample_df = pd.read_csv(resolved_path, sep=None, engine="python", nrows=100)

            metadata: CsvMetadata = {
                "columns": list(sample_df.columns),
                "rows": row_count,
                "dtypes": {str(col): str(dtype) for col, dtype in sample_df.dtypes.items()},
            }

            # Cache it under the resolved key (consistent with the lookup above).
            CsvPoolService._metadata_cache.set(resolved_path, metadata)
            return metadata
        except (OSError, pd.errors.ParserError, csv.Error, KeyError) as e:
            logger.debug("Failed to read CSV metadata for %s: %s", csv_path, e)
            return None

    @staticmethod
    def clear_caches() -> None:
        """Clear all CSV pool caches."""
        CsvPoolService._metadata_cache.clear()
        CsvPoolService._dataframe_cache.clear()
        with CsvPoolService._pool_lock:
            CsvPoolService._pool_index.clear()
        CsvPoolService._pool_dir = None

    @staticmethod
    def get_cache_stats() -> CacheStatsInfo:
        """Get cache statistics for monitoring."""
        with CsvPoolService._pool_lock:
            index_size = len(CsvPoolService._pool_index)
        return cast(
            CacheStatsInfo,
            {
                "metadata_cache": CsvPoolService._metadata_cache.stats(),
                "dataframe_cache": CsvPoolService._dataframe_cache.stats(),
                "index_size": index_size,
            },
        )
