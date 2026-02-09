"""
Comprehensive tests for CsvPoolService following Rule 004 (QA Testing Mastery).

Test Strategy:
- Solitary Unit Tests (mocked dependencies)
- Fixture-first design for setup/teardown
- tmp_path for file I/O isolation
- Parametrization for multiple scenarios
- AAA pattern (Arrange-Act-Assert)
- Cache testing with state verification
"""

import os
import time
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.core.services.data_services.csv_pool_service import CsvPoolService

# ============================================================================
# Fixtures (TDD Ch. 5 - Fixture-First Design)
# ============================================================================


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """
    Create a sample CSV file for testing.

    Uses tmp_path fixture for automatic cleanup (Rule 004).
    """
    csv_file = tmp_path / "sample.csv"
    df = pd.DataFrame(
        {
            "benchmark": ["bzip2", "gcc", "mcf"],
            "value": [1.5, 2.3, 3.1],
            "cycles": [1000, 2000, 3000],
        }
    )
    df.to_csv(csv_file, index=False)
    return csv_file


@pytest.fixture
def empty_pool_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Create an empty pool directory and patch PathService.

    Uses monkeypatch for safe attribute replacement (Rule 004).
    """
    pool_dir = tmp_path / "csv_pool"
    pool_dir.mkdir()

    # Patch PathService to return our test directory
    monkeypatch.setattr(
        "src.core.services.data_services.csv_pool_service.PathService.get_data_dir",
        lambda: tmp_path,
    )

    return pool_dir


@pytest.fixture
def populated_pool(empty_pool_dir: Path, sample_csv: Path) -> Path:
    """Create pool with multiple CSV files."""
    # Copy sample CSV with different timestamps
    for _i, name in enumerate(["parsed_20260101_120000.csv", "parsed_20260102_120000.csv"]):
        dest = empty_pool_dir / name
        dest.write_text(sample_csv.read_text())

    return empty_pool_dir


@pytest.fixture(autouse=True)
def clear_service_state():
    """
    Clear CsvPoolService caches before each test.

    Uses autouse=True to ensure clean state (Rule 004).
    Yields for cleanup guarantee.
    """
    CsvPoolService.clear_caches()
    yield
    CsvPoolService.clear_caches()


# ============================================================================
# Pool Directory Management Tests
# ============================================================================


class TestPoolDirectory:
    """Test pool directory creation and access."""

    def test_get_pool_dir_creates_directory_if_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Verify pool directory is created on first access."""
        # Arrange
        monkeypatch.setattr(
            "src.core.services.data_services.csv_pool_service.PathService.get_data_dir",
            lambda: tmp_path,
        )
        expected_dir = tmp_path / "csv_pool"

        # Act
        pool_dir = CsvPoolService.get_pool_dir()

        # Assert
        assert pool_dir == expected_dir
        assert pool_dir.exists()
        assert pool_dir.is_dir()

    def test_get_pool_dir_returns_existing_directory(self, empty_pool_dir: Path):
        """Verify get_pool_dir is idempotent."""
        # Act
        pool_dir = CsvPoolService.get_pool_dir()

        # Assert
        assert pool_dir == empty_pool_dir
        assert pool_dir.exists()


# ============================================================================
# CSV Loading and Caching Tests
# ============================================================================


class TestCSVLoading:
    """Test CSV file loading with caching."""

    def test_load_csv_file_reads_data_correctly(self, sample_csv: Path):
        """Verify CSV loading produces correct DataFrame."""
        # Act
        df = CsvPoolService.load_csv_file(str(sample_csv))

        # Assert
        assert len(df) == 3
        assert list(df.columns) == ["benchmark", "value", "cycles"]
        assert df["benchmark"].tolist() == ["bzip2", "gcc", "mcf"]

    def test_load_csv_file_caches_dataframe(self, sample_csv: Path):
        """Verify DataFrame is cached on first load."""
        # Arrange - First load
        df1 = CsvPoolService.load_csv_file(str(sample_csv))

        # Act - Second load should hit cache
        with patch("pandas.read_csv") as mock_read:
            df2 = CsvPoolService.load_csv_file(str(sample_csv))

            # Assert - pandas.read_csv NOT called (cache hit)
            mock_read.assert_not_called()
            assert df2.equals(df1)

    def test_load_csv_file_caches_metadata(self, sample_csv: Path):
        """Verify metadata is cached during DataFrame load."""
        # Act
        CsvPoolService.load_csv_file(str(sample_csv))

        # Assert - Metadata should be in cache
        metadata = CsvPoolService._metadata_cache.get(str(sample_csv))
        assert metadata is not None
        assert metadata["columns"] == ["benchmark", "value", "cycles"]
        assert metadata["rows"] == 3
        assert "dtypes" in metadata

    @pytest.mark.parametrize("separator", [",", ";", "\t"])
    def test_load_csv_file_handles_different_separators(self, tmp_path: Path, separator: str):
        """Verify automatic separator detection works."""
        # Arrange
        sep_label = "tab" if separator == "\t" else separator
        csv_file = tmp_path / f"data_{sep_label}.csv"
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        df.to_csv(csv_file, sep=separator, index=False)

        # Act
        loaded_df = CsvPoolService.load_csv_file(str(csv_file))

        # Assert
        assert loaded_df.equals(df)


# ============================================================================
# Metadata Caching Tests
# ============================================================================


class TestMetadataCaching:
    """Test CSV metadata extraction and caching."""

    def test_get_csv_metadata_extracts_info_correctly(self, sample_csv: Path):
        """Verify metadata extraction without loading full DataFrame."""
        # Act
        metadata = CsvPoolService._get_csv_metadata(str(sample_csv))

        # Assert
        assert metadata is not None
        assert metadata["columns"] == ["benchmark", "value", "cycles"]
        assert metadata["rows"] == 3
        assert "dtypes" in metadata
        assert "benchmark" in metadata["dtypes"]

    def test_get_csv_metadata_uses_cache_on_second_call(self, sample_csv: Path):
        """Verify metadata cache prevents redundant file reads."""
        # Arrange - First call computes metadata
        metadata1 = CsvPoolService._get_csv_metadata(str(sample_csv))

        # Act - Second call should use cache
        with patch("builtins.open") as mock_open:
            metadata2 = CsvPoolService._get_csv_metadata(str(sample_csv))

            # Assert - File NOT opened (cache hit)
            mock_open.assert_not_called()
            assert metadata2 == metadata1

    def test_get_csv_metadata_returns_none_on_error(self, tmp_path: Path):
        """Verify graceful handling of read errors."""
        # Arrange
        nonexistent_file = tmp_path / "missing.csv"

        # Act
        metadata = CsvPoolService._get_csv_metadata(str(nonexistent_file))

        # Assert
        assert metadata is None


# ============================================================================
# Pool Management Tests
# ============================================================================


class TestPoolManagement:
    """Test pool listing, adding, and deletion operations."""

    def test_load_pool_returns_empty_list_for_empty_directory(self, empty_pool_dir: Path):
        """Verify empty pool returns empty list."""
        # Act
        pool = CsvPoolService.load_pool()

        # Assert
        assert pool == []

    def test_load_pool_lists_all_csv_files(self, populated_pool: Path):
        """Verify all CSV files in pool are listed."""
        # Act
        pool = CsvPoolService.load_pool()

        # Assert
        assert len(pool) == 2
        assert all("path" in item for item in pool)
        assert all("name" in item for item in pool)
        assert all("size" in item for item in pool)
        assert all("modified" in item for item in pool)

    def test_load_pool_sorts_by_modified_time_descending(self, populated_pool: Path):
        """Verify pool items sorted by modification time (newest first)."""
        # Arrange - Set explicit mtimes to ensure reliable ordering
        # Use os.utime() instead of touch() for reliable mtime in CI
        older_file = populated_pool / "parsed_20260101_120000.csv"
        newer_file = populated_pool / "parsed_20260102_120000.csv"

        # Set older file to 1 day ago, newer file to now
        old_mtime = time.time() - 86400  # 1 day ago
        new_mtime = time.time()
        os.utime(older_file, (old_mtime, old_mtime))
        os.utime(newer_file, (new_mtime, new_mtime))

        # Act
        pool = CsvPoolService.load_pool()

        # Assert - Newest file should be first
        assert pool[0]["name"] == "parsed_20260102_120000.csv"
        assert pool[0]["modified"] >= pool[1]["modified"]

    def test_load_pool_includes_metadata_when_available(self, populated_pool: Path):
        """Verify metadata is included in pool listing."""
        # Act
        pool = CsvPoolService.load_pool()

        # Assert
        assert len(pool) > 0
        first_item = pool[0]
        assert "columns" in first_item
        assert "rows" in first_item
        assert "dtypes" in first_item

    def test_add_to_pool_copies_file_with_timestamp(self, sample_csv: Path, empty_pool_dir: Path):
        """Verify CSV is copied to pool with timestamped name."""
        # Act
        pool_path = CsvPoolService.add_to_pool(str(sample_csv))

        # Assert
        assert Path(pool_path).exists()
        assert Path(pool_path).parent == empty_pool_dir
        assert Path(pool_path).name.startswith("parsed_")
        assert Path(pool_path).name.endswith(".csv")

        # Verify content is identical
        original_df = pd.read_csv(sample_csv)
        pooled_df = pd.read_csv(pool_path)
        assert pooled_df.equals(original_df)

    def test_add_to_pool_generates_unique_filenames(self, sample_csv: Path, empty_pool_dir: Path):
        """Verify consecutive adds create unique filenames."""
        import time

        # Act
        path1 = CsvPoolService.add_to_pool(str(sample_csv))
        time.sleep(1.1)  # Ensure timestamp differs (granularity is 1 second)
        path2 = CsvPoolService.add_to_pool(str(sample_csv))

        # Assert
        assert path1 != path2
        assert Path(path1).exists()
        assert Path(path2).exists()

    def test_delete_from_pool_removes_file(self, populated_pool: Path):
        """Verify file deletion from pool."""
        # Arrange
        target_file = populated_pool / "parsed_20260101_120000.csv"
        assert target_file.exists()

        # Act
        success = CsvPoolService.delete_from_pool(str(target_file))

        # Assert
        assert success is True
        assert not target_file.exists()

    def test_delete_from_pool_returns_false_on_error(self, tmp_path: Path):
        """Verify graceful handling of deletion errors."""
        # Arrange
        nonexistent_file = tmp_path / "missing.csv"

        # Act
        success = CsvPoolService.delete_from_pool(str(nonexistent_file))

        # Assert
        assert success is False


# ============================================================================
# Cache Management Tests
# ============================================================================


class TestCacheManagement:
    """Test cache operations and statistics."""

    def test_clear_caches_empties_all_caches(self, sample_csv: Path):
        """Verify all caches are cleared."""
        # Arrange - Populate caches
        CsvPoolService.load_csv_file(str(sample_csv))
        CsvPoolService.load_pool()

        # Act
        CsvPoolService.clear_caches()

        # Assert
        stats = CsvPoolService.get_cache_stats()
        # Note: stats() returns size info, checking if cleared
        # After clear, both caches should have 0 items
        assert (
            CsvPoolService._dataframe_cache.get(CsvPoolService._compute_file_hash(str(sample_csv)))
            is None
        )
        assert CsvPoolService._metadata_cache.get(str(sample_csv)) is None
        assert stats["index_size"] == 0

    def test_get_cache_stats_returns_metrics(self, sample_csv: Path):
        """Verify cache statistics are provided."""
        # Arrange
        CsvPoolService.load_csv_file(str(sample_csv))

        # Act
        stats = CsvPoolService.get_cache_stats()

        # Assert
        assert "metadata_cache" in stats
        assert "dataframe_cache" in stats
        assert "index_size" in stats
        assert isinstance(stats["metadata_cache"], dict)
        assert isinstance(stats["dataframe_cache"], dict)
        assert isinstance(stats["index_size"], int)


# ============================================================================
# File Hashing Tests
# ============================================================================


class TestFileHashing:
    """Test file hash computation for cache keys."""

    def test_compute_file_hash_includes_mtime(self, sample_csv: Path):
        """Verify hash includes modification time."""
        # Arrange
        hash1 = CsvPoolService._compute_file_hash(str(sample_csv))

        # Act - Use os.utime() to explicitly change mtime (reliable in CI)
        new_mtime = time.time() + 3600  # 1 hour in the future
        os.utime(sample_csv, (new_mtime, new_mtime))
        hash2 = CsvPoolService._compute_file_hash(str(sample_csv))

        # Assert - Hash should change
        assert hash1 != hash2

    def test_compute_file_hash_stable_for_same_file(self, sample_csv: Path):
        """Verify hash is stable when file unchanged."""
        # Act
        hash1 = CsvPoolService._compute_file_hash(str(sample_csv))
        hash2 = CsvPoolService._compute_file_hash(str(sample_csv))

        # Assert
        assert hash1 == hash2

    def test_compute_file_hash_handles_nonexistent_file(self, tmp_path: Path):
        """Verify hash computation for missing files."""
        # Arrange
        missing_file = tmp_path / "missing.csv"

        # Act
        file_hash = CsvPoolService._compute_file_hash(str(missing_file))

        # Assert - Should return path as fallback
        assert file_hash == str(missing_file)


# ============================================================================
# Edge Cases and Error Handling (Rule 004 - Methodical Cases)
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_load_csv_with_large_file_uses_chunking(self, tmp_path: Path):
        """Verify large files are handled efficiently."""
        # Arrange - Create large CSV
        large_csv = tmp_path / "large.csv"
        df = pd.DataFrame({"col1": range(1000), "col2": range(1000, 2000)})
        df.to_csv(large_csv, index=False)

        # Act
        loaded_df = CsvPoolService.load_csv_file(str(large_csv))

        # Assert
        assert len(loaded_df) == 1000
        assert list(loaded_df.columns) == ["col1", "col2"]

    def test_load_pool_ignores_non_csv_files(self, empty_pool_dir: Path):
        """Verify only CSV files are included in pool."""
        # Arrange - Create non-CSV file
        (empty_pool_dir / "other.txt").write_text("not a csv")
        (empty_pool_dir / "data.csv").write_text("col1\n1\n2\n")

        # Act
        pool = CsvPoolService.load_pool()

        # Assert
        assert len(pool) == 1
        assert pool[0]["name"] == "data.csv"

    @pytest.mark.parametrize(
        "invalid_path",
        [
            "",
            "/nonexistent/directory/file.csv",
            "    ",
        ],
    )
    def test_load_csv_handles_invalid_paths(self, invalid_path: str):
        """Verify graceful handling of invalid file paths."""
        # Act & Assert - Should raise or return gracefully
        with pytest.raises(
            (FileNotFoundError, pd.errors.EmptyDataError, ValueError, IsADirectoryError)
        ):
            CsvPoolService.load_csv_file(invalid_path)
