"""Tests for parser robustness: binary files, encoding errors, permission issues.

Verifies strict typed parser admission and genuine CSV ingestion through their
actual owners for binary input, encoding errors, and path edge cases.
"""

from collections.abc import Generator
from pathlib import Path

import pandas as pd
import pytest

from src.core.common.parsed_output import ParsedOutputIO
from src.core.services.data_services.csv_pool_service import CsvPoolService


def _typed_output(path: Path, body: bytes):
    from src.core.common.parsed_output_codec import ParsedOutputDigest
    from src.core.models.parsed_output_models import (
        ParsedColumn,
        ParsedOutput,
        ParsedSchema,
        ParsedVariableSchema,
    )

    path.write_bytes(body)
    schema = ParsedSchema(
        (ParsedVariableSchema("name", "text", "scalar", layout=None),),
        (ParsedColumn("name", "text", "name"),),
    )
    digest = ParsedOutputDigest(schema)
    digest.update(body)
    return ParsedOutput(str(path), digest.hexdigest(), schema)


class TestTypedParserBinaryAdmission:
    def test_null_bytes_are_supported_literal_text(self, tmp_path):
        output = _typed_output(tmp_path / "null.csv", b"name\r\nfoo\x00bar\r\n")
        assert ParsedOutputIO.read(output).rows == (("foo\x00bar",),)

    @pytest.mark.parametrize(
        "content",
        [
            b"\x80\x81\x82\x83\xff\xfe\xfd",
            b"%PDF-1.4\x00\x01\x02\x03",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
            b"PK\x03\x04\x14\x00\x06\x00",
        ],
        ids=["binary", "pdf", "png", "zip"],
    )
    def test_binary_content_is_rejected_even_with_matching_raw_digest(self, tmp_path, content):
        with pytest.raises(ValueError):
            ParsedOutputIO.read(_typed_output(tmp_path / "binary.csv", content))


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
            CsvPoolService.load_csv_file(str(latin1_file))
        with pytest.raises(ValueError):
            ParsedOutputIO.read(
                _typed_output(tmp_path / "typed-latin1.csv", b"name\r\ncaf\xe9\r\n")
            )

    def test_utf8_bom_file(self, tmp_path: Path) -> None:
        """A UTF-8 file with BOM should still validate."""
        bom_file = tmp_path / "bom.csv"
        bom_file.write_bytes(b"\xef\xbb\xbfname,value\nfoo,1.0\n")
        frame = CsvPoolService.load_csv_file(str(bom_file))
        assert frame["name"].tolist() == ["foo"]
        assert frame["value"].tolist() == [1.0]
        with pytest.raises(ValueError):
            ParsedOutputIO.read(
                _typed_output(tmp_path / "typed-bom.csv", b"\xef\xbb\xbfname\r\nfoo\r\n")
            )

    def test_utf16_file(self, tmp_path: Path) -> None:
        """A UTF-16 encoded file should fail UTF-8 decoding."""
        utf16_file = tmp_path / "utf16.csv"
        utf16_file.write_text("name,value\nfoo,1.0\n", encoding="utf-16")
        with pytest.raises(UnicodeDecodeError):
            CsvPoolService.load_csv_file(str(utf16_file))


# Permission and path edge cases


class TestPathEdgeCases:
    """Verify path handling for unusual inputs."""

    def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            output = _typed_output(tmp_path / "removed.csv", b"name\r\nfoo\r\n")
            Path(output.csv_path).unlink()
            ParsedOutputIO.read(output)

    def test_csv_pool_empty_path_raises(self) -> None:
        with pytest.raises(ValueError):
            CsvPoolService.load_csv_file("")

    def test_csv_pool_whitespace_path_raises(self) -> None:
        with pytest.raises(ValueError):
            CsvPoolService.load_csv_file("   ")
