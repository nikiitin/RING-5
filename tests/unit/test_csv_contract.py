"""
Unit tests for the CSV format contract module.

Tests the validation function and contract constants that
define the boundary between Layer A (Parsing) and Layer B (Core).
"""

from pathlib import Path

import pytest

from src.parsing.csv_contract import (
    CSV_ENCODING,
    MISSING_VALUE,
    validate_parser_csv,
)


class TestConstants:
    """Verify contract constants are defined correctly."""

    def test_missing_value(self) -> None:
        assert MISSING_VALUE == ""

    def test_csv_encoding(self) -> None:
        assert CSV_ENCODING == "utf-8"


class TestValidateParserCsv:
    """Test CSV validation function."""

    def test_valid_csv(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "valid.csv"
        csv_file.write_text("name,value\nfoo,1.0\nbar,2.0\n", encoding="utf-8")
        warnings = validate_parser_csv(csv_file)
        assert warnings == []

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            validate_parser_csv(tmp_path / "nonexistent.csv")

    def test_empty_file(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            validate_parser_csv(csv_file)

    def test_empty_header(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "empty_header.csv"
        csv_file.write_text("\nfoo,1.0\n", encoding="utf-8")
        with pytest.raises(ValueError, match="empty header"):
            validate_parser_csv(csv_file)

    def test_duplicate_columns(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "dupes.csv"
        csv_file.write_text("a,b,a\n1,2,3\n", encoding="utf-8")
        warnings = validate_parser_csv(csv_file)
        assert any("Duplicate" in w for w in warnings)

    def test_no_data_rows(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "header_only.csv"
        csv_file.write_text("col1,col2\n", encoding="utf-8")
        warnings = validate_parser_csv(csv_file)
        assert any("no data rows" in w for w in warnings)

    def test_mismatched_column_count(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "mismatch.csv"
        csv_file.write_text("a,b,c\n1,2\n3,4,5\n", encoding="utf-8")
        warnings = validate_parser_csv(csv_file)
        assert any("column count" in w for w in warnings)

    def test_whitespace_column_name(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "spaces.csv"
        csv_file.write_text(" a ,b\n1,2\n", encoding="utf-8")
        warnings = validate_parser_csv(csv_file)
        assert any("whitespace" in w for w in warnings)

    def test_valid_vector_columns(self, tmp_path: Path) -> None:
        """CSV with vector entry columns should be valid."""
        csv_file = tmp_path / "vector.csv"
        csv_file.write_text(
            "system.cpu.stat..0,system.cpu.stat..1\n1.0,2.0\n",
            encoding="utf-8",
        )
        warnings = validate_parser_csv(csv_file)
        assert warnings == []
