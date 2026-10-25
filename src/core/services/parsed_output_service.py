"""Resolve, atomically publish and integrity-check explicitly typed parser output."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import os
import tempfile
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import IO, Protocol

import pandas as pd

from src.core.common.file_lock import file_lock
from src.core.common.parsed_output_codec import (
    ParsedOutputDigest,
    encode_parsed_schema,
    read_parsed_value,
    render_parsed_value,
)
from src.core.common.security_limits import (
    MAX_INCREMENTAL_CACHE_COLUMNS,
    MAX_PARSED_CELL_CHARACTERS,
    MAX_PARSED_OUTPUT_BYTES,
    MAX_PARSE_FILES,
    MAX_PARSE_MATRIX_CELLS,
    MAX_PARSE_VARIABLES,
)
from src.core.models.parsed_output_models import (
    ParsedCell,
    ParsedColumn,
    ParsedFileResult,
    ParsedOutput,
    ParsedSchema,
    ParsedValue,
    ParsedVariableSchema,
    ResolvedParsedRows,
)

_publication_state = threading.local()


class _CsvSink(Protocol):
    def write(self, value: str) -> int:
        """Accept one text fragment from the canonical CSV writer."""
        raise NotImplementedError


class _DigestWriter:
    def __init__(self, stream: IO[bytes] | None, schema: ParsedSchema) -> None:
        self.stream = stream
        self.digest = ParsedOutputDigest(schema)
        self.byte_count = 0

    def write(self, value: str) -> int:
        """Write and hash a CSV fragment within the byte budget."""
        encoded = value.encode("utf-8")
        self.byte_count += len(encoded)
        if self.byte_count > MAX_PARSED_OUTPUT_BYTES:
            raise ValueError("Parsed CSV exceeds the output byte limit.")
        if self.stream is not None and self.stream.write(encoded) != len(encoded):
            raise OSError("Incomplete parser CSV write.")
        self.digest.update(encoded)
        return len(value)


def _write_csv(
    schema: ParsedSchema, rows: Sequence[tuple[ParsedValue, ...]], target: _CsvSink
) -> None:
    """Write the one canonical schema header and literal/numeric row encoding."""
    writer = csv.writer(target)
    writer.writerow([column.name for column in schema.columns])
    for row in rows:
        writer.writerow(
            [
                render_parsed_value(column.kind, value)
                for column, value in zip(schema.columns, row, strict=True)
            ]
        )


class ParsedOutputService:
    """Preserve typed parser cells within bounded canonical CSV output.

    Each literal cell allows 4,194,304 Unicode characters,
    including configuration JSON. The entire UTF-8 CSV is limited to 256 MiB;
    source-row, column and matrix limits apply independently. Reading uses the
    same bounds without changing the process-global stdlib CSV field limit.
    """

    @staticmethod
    def resolve(
        results: Sequence[ParsedFileResult],
        variable_order: Sequence[str],
    ) -> ResolvedParsedRows:
        """Resolve explicit ownership and kinds before allocating a rectangular table.

        Numeric union gaps are NaN. Missing text cells are invalid because an
        explicit string, including an empty fallback, is required from producers.
        """
        if not results or len(results) > MAX_PARSE_FILES:
            raise ValueError("Parser output requires a bounded non-empty file result set.")
        if len(variable_order) > MAX_PARSE_VARIABLES:
            raise ValueError("Parser output exceeds the logical variable limit.")
        if isinstance(variable_order, (str, bytes)):
            raise TypeError("Logical variable order must be a sequence of names.")
        order = tuple(variable_order)
        if any(type(name) is not str or not name for name in order):
            raise TypeError("Requested logical variable names must be non-empty strings.")
        if len(order) != len(set(order)):
            raise ValueError("Requested logical variable names must be unique.")
        declarations: dict[str, ParsedVariableSchema] = {}
        columns: dict[str, ParsedColumn] = {}
        entry_orders: dict[str, set[tuple[str, ...]]] = {name: set() for name in order}
        rows: dict[str, dict[str, ParsedCell]] = {}
        observed_cells = 0
        for result in results:
            if type(result) is not ParsedFileResult:
                raise TypeError("Parser workers must return ParsedFileResult values.")
            if result.source_path in rows:
                raise ValueError(f"Duplicate parser source provenance: {result.source_path!r}.")
            if {value.name for value in result.variables} != set(order):
                raise ValueError("File variables do not match the requested logical declarations.")
            row: dict[str, ParsedCell] = {}
            for variable in result.variables:
                previous = declarations.setdefault(variable.name, variable.schema)
                if previous != variable.schema:
                    raise ValueError(f"Conflicting declaration for variable {variable.name!r}.")
                entry_orders[variable.name].add(tuple(cell.column for cell in variable.cells))
                for cell in variable.cells:
                    ParsedOutputService._admit_column(columns, cell, variable.name)
                    row[cell.column] = cell
            for cell in result.metadata:
                ParsedOutputService._admit_column(columns, cell, None)
                row[cell.column] = cell
            observed_cells += len(row)
            if observed_cells > MAX_PARSE_MATRIX_CELLS:
                raise ValueError("Parser output exceeds the matrix cell limit.")
            rows[result.source_path] = row

        names: list[str] = []
        for name in order:
            names.extend(
                dict.fromkeys(column for schema in sorted(entry_orders[name]) for column in schema)
            )
        names.extend(sorted(name for name, column in columns.items() if column.owner is None))
        if len(names) * len(rows) > MAX_PARSE_MATRIX_CELLS:
            raise ValueError("Parser output exceeds the matrix cell limit.")
        schema = ParsedSchema(
            tuple(declarations[name] for name in order), tuple(columns[name] for name in names)
        )
        paths = tuple(sorted(rows))
        values: list[tuple[ParsedValue, ...]] = []
        for source_path in paths:
            row_values: list[ParsedValue] = []
            for column in schema.columns:
                selected_cell = rows[source_path].get(column.name)
                if selected_cell is None:
                    if column.kind == "text":
                        raise ValueError(
                            f"Missing explicit text cell {column.name!r} in {source_path!r}."
                        )
                    row_values.append(math.nan)
                else:
                    row_values.append(selected_cell.value)
            values.append(tuple(row_values))
        frozen_rows = tuple(values)
        resolved = ResolvedParsedRows(
            schema, frozen_rows, paths, ParsedOutputService._missing_variables(schema, frozen_rows)
        )
        ParsedOutputService._check_wire_budget(resolved)
        return resolved

    @staticmethod
    def _admit_column(
        columns: dict[str, ParsedColumn], cell: ParsedCell, owner: str | None
    ) -> None:
        column = ParsedColumn(cell.column, cell.kind, owner)
        previous = columns.setdefault(cell.column, column)
        if previous != column:
            raise ValueError(f"Parser column ownership/kind collision: {cell.column!r}.")
        if len(columns) > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ValueError("Parser output exceeds the column limit.")

    @staticmethod
    def _check_wire_budget(table: ResolvedParsedRows) -> None:
        if type(table) is not ResolvedParsedRows:
            raise TypeError("Parser publication requires resolved typed rows.")
        if table.missing_variables != ParsedOutputService._missing_variables(
            table.schema, table.rows
        ):
            raise ValueError("Resolved missing-variable facts do not match the typed rows.")
        encode_parsed_schema(table.schema)
        remaining = MAX_PARSED_OUTPUT_BYTES

        def charge(value: str) -> None:
            nonlocal remaining
            if len(value) > MAX_PARSED_CELL_CHARACTERS:
                raise ValueError("Parsed CSV cell exceeds the character limit.")
            # Quotes can double; count their exact overhead before csv.writer
            # materializes a record. Chunked UTF-8 sizing bounds temporary memory.
            remaining -= value.count('"') + 3
            for start in range(0, len(value), 4096):
                remaining -= len(value[start : start + 4096].encode("utf-8"))
                if remaining < 0:
                    raise ValueError("Parsed CSV exceeds the output byte limit.")

        for column in table.schema.columns:
            charge(column.name)
        remaining -= 2
        for row in table.rows:
            remaining -= 2
            for column, value in zip(table.schema.columns, row, strict=True):
                charge(render_parsed_value(column.kind, value))
        if remaining < 0:
            raise ValueError("Parsed CSV exceeds the output byte limit.")

    @staticmethod
    def publish(
        output_path: Path,
        table: ResolvedParsedRows,
        *,
        after_publish: Callable[[ParsedOutput], None] | None = None,
    ) -> ParsedOutput:
        """Publish one CSV atomically, preserving old output if metadata promotion fails.

        The path is expanded and resolved once, so aliases share one target and
        thread/process transaction lock. Reentering that target in the callback
        raises RuntimeError before publication. Lock files are operational only;
        reading an output requires its descriptor and CSV file.

        The optional callback belongs to the existing cache/job transaction owner.
        It executes after the new file is visible and must promote its own record
        atomically. A callback failure restores the previous output file.
        """
        ParsedOutputService._check_wire_budget(table)
        output_path = output_path.expanduser().resolve()
        identity = os.path.normcase(str(output_path))
        active: set[str] = getattr(_publication_state, "active", set())
        if identity in active:
            raise RuntimeError("Cannot reenter publication for the same parsed CSV target.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lock_name = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        lock_path = output_path.parent / f".parsed-publish-{lock_name}.lock"
        _publication_state.active = {*active, identity}
        try:
            with file_lock(lock_path):
                return ParsedOutputService._publish_locked(output_path, table, after_publish)
        finally:
            _publication_state.active = active

    @staticmethod
    def _publish_locked(
        output_path: Path,
        table: ResolvedParsedRows,
        after_publish: Callable[[ParsedOutput], None] | None,
    ) -> ParsedOutput:
        staged: str | None = None
        backup: str | None = None
        replaced = False
        committed = False
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=output_path.parent, prefix=".parsed-", suffix=".csv", delete=False
            ) as stream:
                staged = stream.name
                target = _DigestWriter(stream.file, table.schema)
                _write_csv(table.schema, table.rows, target)
                stream.flush()
                os.fsync(stream.fileno())
                digest = target.digest.hexdigest()
            result = ParsedOutput(str(output_path), digest, table.schema)
            if after_publish is not None and output_path.exists():
                descriptor, backup = tempfile.mkstemp(dir=output_path.parent, prefix=".parsed-old-")
                os.close(descriptor)
                Path(backup).unlink()
                os.link(output_path, backup)
            os.replace(staged, output_path)
            staged = None
            replaced = True
            if after_publish is not None:
                after_publish(result)
            committed = True
            return result
        finally:
            if replaced and not committed:
                if backup is None:
                    output_path.unlink(missing_ok=True)
                else:
                    os.replace(backup, output_path)
                    backup = None
            if staged is not None:
                Path(staged).unlink(missing_ok=True)
            if backup is not None:
                Path(backup).unlink(missing_ok=True)

    @staticmethod
    def read(output: ParsedOutput) -> ResolvedParsedRows:
        """Verify exact file bytes and stability before decoding its explicit cell kinds."""
        if type(output) is not ParsedOutput:
            raise TypeError("Typed parser loading requires ParsedOutput.")
        digest = ParsedOutputDigest(output.schema)
        path = Path(output.csv_path)
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > MAX_PARSED_OUTPUT_BYTES:
                raise ValueError("Parsed CSV exceeds the output byte limit.")
            encoded = stream.read(MAX_PARSED_OUTPUT_BYTES + 1)
            after = os.fstat(stream.fileno())
        current = path.stat()
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        signature = tuple(getattr(before, field) for field in fields)
        if (
            tuple(getattr(after, field) for field in fields) != signature
            or tuple(getattr(current, field) for field in fields) != signature
        ):
            raise ValueError("Parsed CSV changed while it was being read.")
        if len(encoded) > MAX_PARSED_OUTPUT_BYTES:
            raise ValueError("Parsed CSV exceeds the output byte limit.")
        digest.update(encoded)
        if digest.hexdigest() != output.sha256:
            raise ValueError("Parsed CSV digest does not match its descriptor.")
        header = io.StringIO(newline="")
        _write_csv(output.schema, (), header)
        header_bytes = header.getvalue().encode("utf-8")
        if not encoded.startswith(header_bytes):
            raise ValueError("Parsed CSV header does not match its typed schema.")
        if not output.schema.columns:
            # A declared zero-column table has only canonical empty CSV records.
            records, remainder = divmod(len(encoded), 2)
            if records <= 1 or records > MAX_PARSE_FILES + 1:
                raise ValueError("Parsed CSV requires a bounded non-empty source row set.")
            if remainder or encoded != b"\r\n" * records:
                raise ValueError("Malformed zero-column typed parser CSV.")
            frozen_rows: tuple[tuple[ParsedValue, ...], ...] = ((),) * (records - 1)
        else:
            row_limit = min(MAX_PARSE_FILES, MAX_PARSE_MATRIX_CELLS // len(output.schema.columns))
            try:
                # The C reader has no process-global csv.field_size_limit. Exact
                # string settings preserve literal null tokens and control bytes.
                # The canonical header bounds width before pandas allocates data;
                # nrows bounds row allocation even for a forged descriptor.
                frame = pd.read_csv(
                    io.BytesIO(encoded),
                    engine="c",
                    dtype=str,
                    keep_default_na=False,
                    na_filter=False,
                    skip_blank_lines=False,
                    header=0,
                    names=[column.name for column in output.schema.columns],
                    index_col=False,
                    on_bad_lines="error",
                    encoding="utf-8",
                    encoding_errors="strict",
                    nrows=row_limit + 1,
                )
            except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError) as exc:
                raise ValueError(f"Malformed typed parser CSV: {exc}") from exc
            if frame.empty or len(frame) > row_limit:
                raise ValueError("Parsed CSV requires a bounded non-empty source row set.")
            frozen_rows = tuple(
                tuple(
                    read_parsed_value(column.kind, cell)
                    for column, cell in zip(output.schema.columns, row, strict=True)
                )
                for row in frame.itertuples(index=False, name=None)
            )
        table = ResolvedParsedRows(
            output.schema,
            frozen_rows,
            (),
            ParsedOutputService._missing_variables(output.schema, frozen_rows),
        )
        ParsedOutputService._check_wire_budget(table)
        canonical = _DigestWriter(None, output.schema)
        _write_csv(table.schema, table.rows, canonical)
        if canonical.digest.hexdigest() != output.sha256:
            raise ValueError("Parsed CSV does not match the canonical typed row encoding.")
        return table

    @staticmethod
    def to_frame(output: ParsedOutput) -> pd.DataFrame:
        """Read a verified output into explicitly numeric or literal-text columns."""
        table = ParsedOutputService.read(output)
        frame = pd.DataFrame(table.rows, columns=[column.name for column in table.schema.columns])
        for column in table.schema.columns:
            frame[column.name] = frame[column.name].astype(
                float if column.kind == "number" else str
            )
        return frame

    @staticmethod
    def _missing_variables(
        schema: ParsedSchema, rows: tuple[tuple[ParsedValue, ...], ...]
    ) -> tuple[str, ...]:
        """Find logical variables without values using ownership rather than column spelling."""

        def is_missing(value: ParsedValue) -> bool:
            return type(value) is float and math.isnan(value)

        found = dict.fromkeys((variable.name for variable in schema.variables), False)
        for row in rows:
            for column, value in zip(schema.columns, row, strict=True):
                if column.owner is not None and not is_missing(value):
                    found[column.owner] = True
        return tuple(variable.name for variable in schema.variables if not found[variable.name])
