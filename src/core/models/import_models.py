"""Immutable contracts for inspecting a tabular import before loading it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.core.common.security_limits import (
    MAX_IMPORT_COLUMNS,
    MAX_IMPORT_PREVIEW_ROWS,
    MAX_IMPORT_REJECTION_DETAILS,
)

ImportColumnType = Literal["auto", "text", "integer", "number", "boolean", "datetime"]


@dataclass(frozen=True)
class ImportColumnCorrection:
    """Requested type correction for one named import column."""

    column: str
    import_as: ImportColumnType

    def __post_init__(self) -> None:
        """Reject ambiguous or unsupported corrections."""
        if not isinstance(self.column, str) or not self.column.strip():
            raise ValueError("Import correction column must be non-empty text.")
        if self.import_as not in {"auto", "text", "integer", "number", "boolean", "datetime"}:
            raise ValueError(f"Unsupported import type: {self.import_as!r}.")


@dataclass(frozen=True)
class ImportOptions:
    """Corrections applied while inspecting and loading a delimited table."""

    encoding: str | None = None
    delimiter: str | None = None
    header_row: int = 1
    trim_whitespace: bool = True
    null_values: tuple[str, ...] = ("", "NA", "N/A", "null", "None")
    column_types: tuple[ImportColumnCorrection, ...] = ()
    preview_rows: int = 50

    def __post_init__(self) -> None:
        """Validate bounded and deterministic import controls."""
        if self.encoding is not None and self.encoding not in {
            "utf-8",
            "utf-8-sig",
            "cp1252",
            "latin-1",
        }:
            raise ValueError(f"Unsupported import encoding: {self.encoding!r}.")
        if self.delimiter is not None and self.delimiter not in {",", ";", "\t", "|"}:
            raise ValueError("Import delimiter must be comma, semicolon, tab, or pipe.")
        if isinstance(self.header_row, bool) or not 1 <= self.header_row <= 100:
            raise ValueError("Import header_row must be from 1 through 100.")
        if (
            isinstance(self.preview_rows, bool)
            or not 1 <= self.preview_rows <= MAX_IMPORT_PREVIEW_ROWS
        ):
            raise ValueError(
                f"Import preview_rows must be from 1 through {MAX_IMPORT_PREVIEW_ROWS}."
            )
        if len(self.null_values) > 50:
            raise ValueError("Imports support at most 50 missing-value tokens.")
        if any(not isinstance(value, str) or len(value) > 100 for value in self.null_values):
            raise ValueError("Import missing-value tokens must be text up to 100 characters.")
        columns = [correction.column for correction in self.column_types]
        if len(columns) > MAX_IMPORT_COLUMNS or len(set(columns)) != len(columns):
            raise ValueError("Import column corrections must be unique and bounded.")


@dataclass(frozen=True)
class ImportColumn:
    """Inferred and effective type information for one import column."""

    name: str
    inferred_type: ImportColumnType
    import_as: ImportColumnType
    nullable: bool


@dataclass(frozen=True)
class ImportRejectedRow:
    """One rejected source row with its physical line and reason."""

    line_number: int
    values: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class ImportPreview:
    # [impl->req~ring5.ingestion.import-preview~1]
    """Complete, bounded inspection result for one source snapshot."""

    source_path: str
    source_sha256: str
    encoding: str
    delimiter: str
    options: ImportOptions
    columns: tuple[ImportColumn, ...]
    rows: tuple[tuple[str, ...], ...]
    accepted_row_count: int
    rejected_row_count: int
    total_row_count: int
    rejected_rows: tuple[ImportRejectedRow, ...]

    def __post_init__(self) -> None:
        """Validate counts and preview shape."""
        if len(self.source_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.source_sha256
        ):
            raise ValueError("Import source_sha256 must be a lowercase SHA-256 digest.")
        if self.accepted_row_count + self.rejected_row_count != self.total_row_count:
            raise ValueError("Import accepted and rejected counts must equal total rows.")
        if len(self.rows) > self.options.preview_rows:
            raise ValueError("Import preview contains more rows than requested.")
        if any(len(row) != len(self.columns) for row in self.rows):
            raise ValueError("Import preview rows must align with preview columns.")
        if len(self.rejected_rows) > self.rejected_row_count:
            raise ValueError("Import rejection details cannot exceed rejected rows.")
        if len(self.rejected_rows) > MAX_IMPORT_REJECTION_DETAILS:
            raise ValueError("Import contains too many rejection details.")

    @property
    def preview_truncated(self) -> bool:
        """Whether more accepted rows exist than are displayed."""
        return self.accepted_row_count > len(self.rows)

    @property
    def rejection_details_truncated(self) -> bool:
        """Whether additional rejected rows exist beyond displayed details."""
        return self.rejected_row_count > len(self.rejected_rows)
