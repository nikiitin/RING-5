"""Inspect and correct bounded delimited-text imports before loading them."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.core.common.security_limits import (
    MAX_IMPORT_COLUMNS,
    MAX_IMPORT_FILE_BYTES,
    MAX_IMPORT_REJECTION_DETAILS,
    MAX_IMPORT_ROWS,
)
from src.core.models.import_models import (
    ImportColumn,
    ImportColumnType,
    ImportOptions,
    ImportPreview,
    ImportRejectedRow,
)

_INTEGER = re.compile(r"^[+-]?\d+$")
_DELIMITERS = (",", ";", "\t", "|")


@dataclass
class _TypeCandidate:
    """Streaming type-inference state for one column."""

    saw_value: bool = False
    nullable: bool = False
    integer: bool = True
    number: bool = True
    boolean: bool = True
    datetime: bool = True

    def add(self, value: str | None) -> None:
        """Fold one normalized source value into this candidate."""
        if value is None:
            self.nullable = True
            return
        self.saw_value = True
        self.integer = self.integer and _is_integer(value)
        self.number = self.number and _is_number(value)
        self.boolean = self.boolean and _is_boolean(value)
        self.datetime = self.datetime and _is_datetime(value)

    def inferred(self) -> ImportColumnType:
        """Return the narrowest type supported by every non-null value."""
        if not self.saw_value:
            return "text"
        if self.boolean:
            return "boolean"
        if self.integer:
            return "integer"
        if self.number:
            return "number"
        if self.datetime:
            return "datetime"
        return "text"


@dataclass(frozen=True)
class _Source:
    """One bounded, decoded source snapshot."""

    path: str
    digest: str
    text: str
    encoding: str
    delimiter: str


def _is_integer(value: str) -> bool:
    return _INTEGER.fullmatch(value) is not None


def _is_number(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except ValueError:
        return False


def _is_boolean(value: str) -> bool:
    return value.casefold() in {"true", "false", "yes", "no", "y", "n"}


def _is_datetime(value: str) -> bool:
    if not any(character in value for character in "-/:T"):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _decode(raw: bytes, requested: str | None) -> tuple[str, str]:
    """Decode bytes with an explicit or deterministic detected encoding."""
    if requested is not None:
        return raw.decode(requested), requested
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeError("Could not decode the import with a supported text encoding.")


def _detect_delimiter(text: str, header_row: int) -> str:
    """Detect one supported delimiter, with a stable single-column fallback."""
    sample = text[:65_536]
    lines = sample.splitlines()
    relevant_sample = "\n".join(lines[header_row - 1 :])
    try:
        return (
            csv.Sniffer()
            .sniff(
                relevant_sample,
                delimiters="".join(_DELIMITERS),
            )
            .delimiter
        )
    except csv.Error:
        scores: list[tuple[int, int, int, int, str]] = []
        for index, delimiter in enumerate(_DELIMITERS):
            try:
                records = list(
                    csv.reader(
                        io.StringIO(relevant_sample, newline=""),
                        delimiter=delimiter,
                        strict=True,
                    )
                )[:25]
            except csv.Error:
                continue
            width = len(records[0]) if records else 0
            matching = sum(len(record) == width for record in records[1:])
            scores.append((int(width > 1), matching, width, -index, delimiter))
        structured, _matching, _width, _priority, detected = max(
            scores,
            default=(0, 0, 0, 0, ","),
        )
        return detected if structured else ","


def _source(path: str, options: ImportOptions) -> _Source:
    """Read, bound, decode, and fingerprint a source file."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Import path must be non-empty text.")
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Import file not found: {resolved}")
    if not resolved.is_file():
        raise IsADirectoryError(f"Import path is not a file: {resolved}")
    size = resolved.stat().st_size
    if size == 0:
        raise ValueError("Import file is empty.")
    if size > MAX_IMPORT_FILE_BYTES:
        raise ValueError(
            f"Import file exceeds the {MAX_IMPORT_FILE_BYTES // (1024 * 1024)} MiB limit."
        )
    raw = resolved.read_bytes()
    if len(raw) > MAX_IMPORT_FILE_BYTES:
        raise ValueError("Import file grew beyond the size limit while it was read.")
    text, encoding = _decode(raw, options.encoding)
    delimiter = options.delimiter or _detect_delimiter(text, options.header_row)
    return _Source(
        path=str(resolved),
        digest=hashlib.sha256(raw).hexdigest(),
        text=text,
        encoding=encoding,
        delimiter=delimiter,
    )


def _clean(value: str, options: ImportOptions) -> str | None:
    """Apply whitespace and missing-value corrections to one cell."""
    normalized = value.strip() if options.trim_whitespace else value
    return None if normalized in options.null_values else normalized


def _header(source: _Source, options: ImportOptions) -> tuple[str, ...]:
    """Read and validate the configured header record."""
    reader = csv.reader(
        io.StringIO(source.text, newline=""),
        delimiter=source.delimiter,
        strict=True,
    )
    try:
        for index, record in enumerate(reader, start=1):
            if index == options.header_row:
                header = tuple(
                    value.strip() if options.trim_whitespace else value for value in record
                )
                break
        else:
            raise ValueError(f"Import does not contain header row {options.header_row}.")
    except csv.Error as exc:
        raise ValueError(f"Could not parse import header: {exc}.") from exc
    if not header or len(header) > MAX_IMPORT_COLUMNS:
        raise ValueError(f"Import header must contain from 1 through {MAX_IMPORT_COLUMNS} columns.")
    if any(not value for value in header):
        raise ValueError("Import header contains an empty column name.")
    if len(set(header)) != len(header):
        raise ValueError("Import header contains duplicate column names.")
    return header


def _records(source: _Source, options: ImportOptions) -> Iterator[tuple[int, tuple[str, ...]]]:
    """Yield bounded non-empty records after the configured header."""
    reader = csv.reader(
        io.StringIO(source.text, newline=""),
        delimiter=source.delimiter,
        strict=True,
    )
    count = 0
    try:
        for index, record in enumerate(reader, start=1):
            if index <= options.header_row or not record:
                continue
            if count >= MAX_IMPORT_ROWS:
                raise ValueError(f"Import contains more than {MAX_IMPORT_ROWS:,} data rows.")
            count += 1
            yield reader.line_num, tuple(record)
    except csv.Error as exc:
        raise ValueError(f"Could not parse import near line {reader.line_num}: {exc}.") from exc


def _convert(value: str | None, import_as: ImportColumnType) -> object | None:
    """Convert one corrected value or raise a concise row-level error."""
    if value is None:
        return None
    if import_as == "text":
        return value
    if import_as == "integer":
        if not _is_integer(value):
            raise ValueError("integer")
        return int(value)
    if import_as == "number":
        if not _is_number(value):
            raise ValueError("number")
        return float(value)
    if import_as == "boolean":
        normalized = value.casefold()
        if normalized not in {"true", "false", "yes", "no", "y", "n"}:
            raise ValueError("boolean")
        return normalized in {"true", "yes", "y"}
    if import_as == "datetime":
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("datetime") from exc
    raise ValueError(f"Unsupported effective import type: {import_as!r}.")


def _display(value: object | None) -> str:
    """Format a bounded preview cell without changing loaded values."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        text = value.isoformat()
    elif isinstance(value, float):
        text = format(value, ".12g")
    elif isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    return text if len(text) <= 500 else text[:499] + "…"


def _inspect(
    source: _Source,
    options: ImportOptions,
    *,
    collect_all: bool,
) -> tuple[ImportPreview, list[list[object | None]]]:
    """Infer types, apply corrections, and classify every bounded row."""
    header = _header(source, options)
    candidates = [_TypeCandidate() for _column in header]
    for _line_number, raw_values in _records(source, options):
        if len(raw_values) != len(header):
            continue
        for candidate, value in zip(candidates, raw_values, strict=True):
            candidate.add(_clean(value, options))

    corrections = {item.column: item.import_as for item in options.column_types}
    unknown = sorted(set(corrections) - set(header))
    if unknown:
        raise ValueError("Import type corrections name unknown columns: " + ", ".join(unknown))
    inferred = tuple(candidate.inferred() for candidate in candidates)
    effective = tuple(
        corrections.get(column, "auto") if corrections.get(column, "auto") != "auto" else kind
        for column, kind in zip(header, inferred, strict=True)
    )
    columns = tuple(
        ImportColumn(name, kind, selected, candidate.nullable)
        for name, kind, selected, candidate in zip(
            header, inferred, effective, candidates, strict=True
        )
    )

    accepted = 0
    rejected = 0
    preview_rows: list[tuple[str, ...]] = []
    rejected_rows: list[ImportRejectedRow] = []
    loaded_rows: list[list[object | None]] = []
    for line_number, raw_values in _records(source, options):
        display_values = tuple(_display(value) for value in raw_values)
        if len(raw_values) != len(header):
            rejected += 1
            if len(rejected_rows) < MAX_IMPORT_REJECTION_DETAILS:
                rejected_rows.append(
                    ImportRejectedRow(
                        line_number,
                        display_values,
                        f"Expected {len(header)} fields but found {len(raw_values)}.",
                    )
                )
            continue
        cleaned = [_clean(value, options) for value in raw_values]
        converted: list[object | None] = []
        try:
            for column, cleaned_value, import_as in zip(header, cleaned, effective, strict=True):
                try:
                    converted.append(_convert(cleaned_value, import_as))
                except ValueError as exc:
                    shown = _display(cleaned_value)
                    raise ValueError(
                        f"Column {column!r} expects {import_as}; found {shown!r}."
                    ) from exc
        except ValueError as exc:
            rejected += 1
            if len(rejected_rows) < MAX_IMPORT_REJECTION_DETAILS:
                rejected_rows.append(ImportRejectedRow(line_number, display_values, str(exc)))
            continue
        accepted += 1
        if len(preview_rows) < options.preview_rows:
            preview_rows.append(tuple(_display(value) for value in converted))
        if collect_all:
            loaded_rows.append(converted)

    preview = ImportPreview(
        source_path=source.path,
        source_sha256=source.digest,
        encoding=source.encoding,
        delimiter=source.delimiter,
        options=options,
        columns=columns,
        rows=tuple(preview_rows),
        accepted_row_count=accepted,
        rejected_row_count=rejected,
        total_row_count=accepted + rejected,
        rejected_rows=tuple(rejected_rows),
    )
    return preview, loaded_rows


class ImportPreviewService:
    """Preview and load one unchanged delimited-text source."""

    @staticmethod
    def preview(path: str, options: ImportOptions | None = None) -> ImportPreview:
        # [impl->req~ring5.ingestion.import-preview~1]
        """Inspect a delimited table without mutating application state."""
        selected = options or ImportOptions()
        preview, _rows = _inspect(_source(path, selected), selected, collect_all=False)
        return preview

    @staticmethod
    def load(preview: ImportPreview) -> pd.DataFrame:
        # [impl->req~ring5.ingestion.import-preview~1]
        """Load accepted rows after verifying that the source did not change."""
        source = _source(preview.source_path, preview.options)
        if source.digest != preview.source_sha256:
            raise ValueError("Import source changed after preview; review it again before loading.")
        current, rows = _inspect(source, preview.options, collect_all=True)
        if current != preview:
            raise ValueError("Import result changed after preview; review it again before loading.")
        if not rows:
            raise ValueError("Import has no accepted rows to load.")
        frame = pd.DataFrame(rows, columns=[column.name for column in preview.columns])
        for column in preview.columns:
            if column.import_as == "integer":
                frame[column.name] = frame[column.name].astype("Int64")
            elif column.import_as == "number":
                frame[column.name] = frame[column.name].astype("Float64")
            elif column.import_as == "boolean":
                frame[column.name] = frame[column.name].astype("boolean")
            elif column.import_as == "datetime":
                frame[column.name] = pd.to_datetime(frame[column.name])
        return frame
