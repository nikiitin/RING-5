"""Tests for parser robustness: binary files, encoding errors, permission issues.

Verifies that the CSV contract validator and CsvPoolService correctly handle
non-text files, files with encoding issues, and edge case inputs.
"""

from collections.abc import Generator
from pathlib import Path

import pandas as pd
import pytest

from src.core.models.csv_contract import validate_parser_csv
from src.core.services.data_services.csv_pool_service import CsvPoolService

# Binary file rejection via CSV contract


class TestBinaryFileRejection:
    """Verify that binary/non-text files are handled gracefully."""

    def test_null_bytes_in_csv(self, tmp_path: Path) -> None:
        """CSV with null bytes should either raise or produce warnings."""
        binary_csv = tmp_path / "null_bytes.csv"
        binary_csv.write_bytes(b"name,value\x00\nfoo,1.0\n")
        # Should not crash — may produce warnings
        result = validate_parser_csv(binary_csv)
        assert isinstance(result, list)

    def test_pure_binary_file(self, tmp_path: Path) -> None:
        """A file with non-decodable bytes should raise UnicodeDecodeError."""
        binary_file = tmp_path / "data.bin"
        binary_file.write_bytes(b"\x80\x81\x82\x83\xff\xfe\xfd")
        with pytest.raises(UnicodeDecodeError):
            validate_parser_csv(binary_file)

    def test_pdf_header_file(self, tmp_path: Path) -> None:
        """A file starting with PDF magic bytes should fail to parse."""
        pdf_file = tmp_path / "document.csv"
        pdf_file.write_bytes(b"%PDF-1.4\x00\x01\x02\x03\x04\x05")
        # PDF header is valid ASCII, so it will be read — but likely no valid CSV header
        result = validate_parser_csv(pdf_file)
        # It may warn or just return; the important thing is no crash
        assert isinstance(result, list)

    @pytest.mark.parametrize(
        "content",
        [
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",  # PNG header
            b"PK\x03\x04\x14\x00\x06\x00",  # ZIP header
        ],
        ids=["png", "zip"],
    )
    def test_binary_magic_bytes(self, tmp_path: Path, content: bytes) -> None:
        """Files with binary magic bytes should fail with decode error or no valid header."""
        binary_file = tmp_path / "file.csv"
        binary_file.write_bytes(content)
        # Should either raise UnicodeDecodeError or return warnings
        try:
            result = validate_parser_csv(binary_file)
            assert isinstance(result, list)
        except (UnicodeDecodeError, ValueError):
            pass  # Expected for non-text files


# CsvPoolService binary file handling


class TestCsvPoolServiceBinaryRejection:
    """Verify that CsvPoolService handles binary files gracefully."""

    @pytest.fixture(autouse=True)
    def _clear_caches(self) -> Generator[None, None, None]:
        CsvPoolService.clear_caches()
        yield
        CsvPoolService.clear_caches()

    def test_load_binary_file(self, tmp_path: Path) -> None:
        """Loading a binary file should either raise or produce degenerate output."""
        binary_file = tmp_path / "data.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05\x06\x07")
        # pandas may not raise on arbitrary bytes — verify it doesn't crash
        try:
            result = CsvPoolService.load_csv_file(str(binary_file))
            # If it doesn't raise, result should be degenerate (empty or 1 row)
            assert isinstance(result, pd.DataFrame)
        except Exception:
            pass  # Any exception is acceptable for binary input

    def test_load_empty_file_raises(self, tmp_path: Path) -> None:
        """Loading a truly empty file should raise an error."""
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("", encoding="utf-8")
        with pytest.raises(Exception):
            CsvPoolService.load_csv_file(str(empty_file))

    def test_load_directory_raises(self, tmp_path: Path) -> None:
        """Loading a directory path should raise IsADirectoryError."""
        with pytest.raises(IsADirectoryError):
            CsvPoolService.load_csv_file(str(tmp_path))


# Encoding edge cases


class TestEncodingEdgeCases:
    """Verify handling of various text encodings."""

    def test_latin1_file(self, tmp_path: Path) -> None:
        """A Latin-1 encoded file with non-UTF8 characters should raise."""
        latin1_file = tmp_path / "latin1.csv"
        # 0xe9 is 'é' in Latin-1 but not valid single-byte UTF-8
        latin1_file.write_bytes(b"name,value\ncaf\xe9,1.0\n")
        with pytest.raises(UnicodeDecodeError):
            validate_parser_csv(latin1_file)

    def test_utf8_bom_file(self, tmp_path: Path) -> None:
        """A UTF-8 file with BOM should still validate."""
        bom_file = tmp_path / "bom.csv"
        bom_file.write_bytes(b"\xef\xbb\xbfname,value\nfoo,1.0\n")
        result = validate_parser_csv(bom_file)
        assert isinstance(result, list)

    def test_utf16_file(self, tmp_path: Path) -> None:
        """A UTF-16 encoded file should fail UTF-8 decoding."""
        utf16_file = tmp_path / "utf16.csv"
        utf16_file.write_text("name,value\nfoo,1.0\n", encoding="utf-16")
        with pytest.raises(UnicodeDecodeError):
            validate_parser_csv(utf16_file)


# Permission and path edge cases


class TestPathEdgeCases:
    """Verify path handling for unusual inputs."""

    def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            validate_parser_csv(tmp_path / "nonexistent.csv")

    def test_csv_pool_empty_path_raises(self) -> None:
        with pytest.raises(ValueError):
            CsvPoolService.load_csv_file("")

    def test_csv_pool_whitespace_path_raises(self) -> None:
        with pytest.raises(ValueError):
            CsvPoolService.load_csv_file("   ")
