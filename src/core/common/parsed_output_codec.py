"""Canonical numeric and literal-text cells for parser CSV and cache records."""

import hashlib
import json
import math
from collections.abc import Iterator, Mapping
from typing import cast
from decimal import Decimal, InvalidOperation

from src.core.common.security_limits import (
    MAX_INCREMENTAL_CACHE_COLUMNS,
    MAX_PARSED_CELL_CHARACTERS,
    MAX_PARSED_SCHEMA_BYTES,
    MAX_PARSED_DESCRIPTOR_BYTES,
    MAX_PARSE_VARIABLES,
)
from src.core.models.parse_failure_models import ParseDataValueError
from src.core.models.native_distribution_layout import DistributionLayout
from src.core.common.distribution_layout_codec import (
    decode_distribution_layout,
    encode_distribution_layout,
    iter_distribution_layout_encoding,
)
from src.core.models.parsed_output_models import (
    ParsedCell,
    ParsedColumn,
    ParsedFileResult,
    ParsedKind,
    ParsedOutput,
    ParsedSchema,
    ParsedShape,
    ParsedValue,
    ParsedVariableResult,
    ParsedVariableSchema,
)

MISSING_VALUE = "NaN"

PARSED_SCHEMA_VERSION = 2
PARSED_OUTPUT_VERSION = 1


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON fields before any typed parser record is admitted."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate parser JSON field: {key!r}.")
        result[key] = value
    return result


def _record(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise ValueError(f"Parser record requires exactly these fields: {sorted(fields)}.")
    return cast(dict[str, object], value)


def _kind_value(value: object) -> ParsedKind:
    if type(value) is not str or value not in ("number", "text"):
        raise ValueError("Parsed cell kind must be 'number' or 'text'.")
    return cast(ParsedKind, value)


def _text(value: object) -> str:
    if type(value) is not str:
        raise TypeError("Encoded parser text fields must be exact strings.")
    return value


def _cells(value: object) -> tuple[ParsedCell, ...]:
    if type(value) is not list or len(value) > MAX_INCREMENTAL_CACHE_COLUMNS:
        raise ValueError("Encoded parser cells require a bounded array.")
    result: list[ParsedCell] = []
    for raw in value:
        record = _record(raw, {"column", "kind", "value"})
        kind = _kind_value(record["kind"])
        cell_value = _text(record["value"])
        if len(cell_value) > MAX_PARSED_CELL_CHARACTERS:
            raise ValueError("Encoded parser cell exceeds the character limit.")
        result.append(
            ParsedCell(_text(record["column"]), kind, read_parsed_value(kind, cell_value))
        )
    return tuple(result)


def parsed_file_payload(result: ParsedFileResult) -> dict[str, object]:
    """Project one bounded file into current typed cache records, including absence evidence."""
    if type(result) is not ParsedFileResult:
        raise TypeError("Parser file encoding requires ParsedFileResult.")

    budget = ParsedSchemaBudget()
    for variable in result.variables:
        budget.variable(variable.name, variable.kind, variable.shape)
        for fragment in iter_distribution_layout_encoding(variable.layout):
            budget.admit(fragment)
        for cell in variable.cells:
            budget.column(ParsedColumn(cell.column, cell.kind, variable.name))
    for cell in result.metadata:
        budget.column(ParsedColumn(cell.column, cell.kind, None))

    def cell_payload(cell: ParsedCell) -> dict[str, object]:
        value = render_parsed_value(cell.kind, cell.value)
        if len(value) > MAX_PARSED_CELL_CHARACTERS:
            raise ParseDataValueError("Encoded parser cell exceeds the character limit.")
        return {"column": cell.column, "kind": cell.kind, "value": value}

    return {
        "source_path": result.source_path,
        "variables": [
            {
                "name": variable.name,
                "kind": variable.kind,
                "shape": variable.shape,
                "missing_measurements": variable.missing_measurements,
                "layout": encode_distribution_layout(variable.layout),
                "cells": [cell_payload(cell) for cell in variable.cells],
            }
            for variable in result.variables
        ],
        "metadata": [cell_payload(cell) for cell in result.metadata],
    }


def iter_parsed_file_encoding(result: ParsedFileResult) -> Iterator[bytes]:
    """Yield the complete canonical UTF-8 file record for cache and admission sizing."""
    encoder = json.JSONEncoder(
        ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
    )
    for fragment in encoder.iterencode(parsed_file_payload(result)):
        yield fragment.encode("utf-8")


def parsed_file_from_payload(
    value: object,
    *,
    layout_declarations: Mapping[str, DistributionLayout | None] | None = None,
) -> ParsedFileResult:
    """Decode exactly the current typed file payload without scalar or owner inference."""
    record = _record(value, {"source_path", "variables", "metadata"})
    raw_variables = record["variables"]
    if type(raw_variables) is not list or len(raw_variables) > MAX_PARSE_VARIABLES:
        raise ValueError("Encoded parser variables require a bounded array.")
    variables: list[ParsedVariableResult] = []
    budget = ParsedSchemaBudget()
    cell_count = 0
    for raw in raw_variables:
        variable = _record(
            raw, {"name", "kind", "shape", "missing_measurements", "cells", "layout"}
        )
        kind = _kind_value(variable["kind"])
        shape = variable["shape"]
        if type(shape) is not str or shape not in ("scalar", "entries"):
            raise ValueError("Encoded variable requires an explicit scalar/entries shape.")
        missing = variable["missing_measurements"]
        if type(missing) is not int or missing < 0:
            raise ValueError("Encoded missing measurements must be a non-negative integer.")
        raw_cells = variable["cells"]
        if type(raw_cells) is not list:
            raise ValueError("Encoded parser cells require an array.")
        cell_count += len(raw_cells)
        if cell_count > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ValueError("Encoded file exceeds the physical column limit.")
        name = _text(variable["name"])
        budget.variable(name, kind, cast(ParsedShape, shape))
        for raw_cell in raw_cells:
            cell_record = _record(raw_cell, {"column", "kind", "value"})
            budget.column(ParsedColumn(_text(cell_record["column"]), kind, name))
        expected = None
        if layout_declarations is not None:
            if name not in layout_declarations:
                raise ValueError("Cached variable is absent from the current source plan.")
            expected = layout_declarations[name]
            if expected is None and variable["layout"] is not None:
                raise ValueError("Cached layout contradicts ordinary request ownership.")
        layout = decode_distribution_layout(
            variable["layout"], admit=budget.admit, expected=expected
        )
        variables.append(
            ParsedVariableResult(
                _text(variable["name"]),
                kind,
                cast(ParsedShape, shape),
                _cells(raw_cells),
                missing,
                layout=layout,
            )
        )
    metadata = record["metadata"]
    if type(metadata) is not list or cell_count + len(metadata) > MAX_INCREMENTAL_CACHE_COLUMNS:
        raise ValueError("Encoded file exceeds the physical column limit.")
    for raw_cell in metadata:
        cell_record = _record(raw_cell, {"column", "kind", "value"})
        budget.column(
            ParsedColumn(_text(cell_record["column"]), _kind_value(cell_record["kind"]), None)
        )
    return ParsedFileResult(_text(record["source_path"]), tuple(variables), _cells(metadata))


PARSED_SCHEMA_PREFIX = (
    b'{"format":"ring5.parsed-schema","version":'
    + str(PARSED_SCHEMA_VERSION).encode("ascii")
    + b',"variables":['
)
PARSED_SCHEMA_COLUMNS = b'],"columns":['
PARSED_SCHEMA_SUFFIX = b"]}"


def _schema_record(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def parsed_variable_frame(name: str, kind: ParsedKind, shape: ParsedShape) -> tuple[bytes, bytes]:
    """Return canonical variable framing around its required layout encoding."""
    return (
        b'{"kind":' + _schema_record(kind) + b',"layout":',
        b',"name":' + _schema_record(name) + b',"shape":' + _schema_record(shape) + b"}",
    )


def encode_parsed_column(column: ParsedColumn) -> bytes:
    """Encode exact ownership for schema publication and preallocation admission."""
    return _schema_record({"name": column.name, "kind": column.kind, "owner": column.owner})


class ParsedSchemaBudget:
    """Charge the real schema framing before retaining planned bindings.

    Dynamic output columns are admitted when resolved. Known declarations and
    physical columns use these same fragments as the actual schema encoder.
    """

    def __init__(self) -> None:
        self._size = 0
        self._variables = 0
        self._columns = 0
        self.admit(PARSED_SCHEMA_PREFIX + PARSED_SCHEMA_COLUMNS + PARSED_SCHEMA_SUFFIX)

    def admit(self, fragment: bytes) -> None:
        """Charge exact bytes without retaining the fragment or committing a failed charge."""
        if self._size + len(fragment) > MAX_PARSED_SCHEMA_BYTES:
            raise ParseDataValueError("Parsed schema exceeds its byte budget.")
        self._size += len(fragment)

    def variable(self, name: str, kind: ParsedKind, shape: ParsedShape) -> None:
        """Charge a variable's actual framing; its layout fragments are charged separately."""
        ParsedVariableSchema(name, kind, shape, layout=None)
        prefix, suffix = parsed_variable_frame(name, kind, shape)
        self.admit((b"," if self._variables else b"") + prefix + suffix)
        self._variables += 1

    def column(self, column: ParsedColumn) -> None:
        """Charge one actual physical declaration before its binding is retained."""
        self.admit((b"," if self._columns else b"") + encode_parsed_column(column))
        self._columns += 1


def encode_parsed_schema(schema: ParsedSchema) -> bytes:
    """Encode one bounded current schema without building an unbounded JSON graph."""
    if type(schema) is not ParsedSchema:
        raise TypeError("Parser schema encoding requires ParsedSchema.")
    encoded = bytearray()

    def append(value: bytes) -> None:
        if len(encoded) + len(value) > MAX_PARSED_SCHEMA_BYTES:
            raise ValueError("Parsed schema exceeds the descriptor byte limit.")
        encoded.extend(value)

    append(PARSED_SCHEMA_PREFIX)
    for index, variable in enumerate(schema.variables):
        if index:
            append(b",")
        prefix, suffix = parsed_variable_frame(variable.name, variable.kind, variable.shape)
        append(prefix)
        for fragment in iter_distribution_layout_encoding(variable.layout):
            append(fragment)
        append(suffix)
    append(PARSED_SCHEMA_COLUMNS)
    for index, column in enumerate(schema.columns):
        if index:
            append(b",")
        append(encode_parsed_column(column))
    append(PARSED_SCHEMA_SUFFIX)
    return bytes(encoded)


def _decode_document(payload: bytes, limit: int) -> object:
    if type(payload) is not bytes or len(payload) > limit:
        raise ValueError("Parser descriptor document exceeds its byte limit.")
    try:
        return json.loads(payload, object_pairs_hook=unique_json_object)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise ValueError("Parser descriptor document is invalid JSON.") from exc


def _schema_from_payload(value: object) -> ParsedSchema:
    document = _record(value, {"format", "version", "variables", "columns"})
    if (
        document["format"] != "ring5.parsed-schema"
        or type(document["version"]) is not int
        or document["version"] != PARSED_SCHEMA_VERSION
    ):
        raise ValueError("Unsupported parser schema format/version.")
    variables, columns = document["variables"], document["columns"]
    if type(variables) is not list or len(variables) > MAX_PARSE_VARIABLES:
        raise ValueError("Parser schema variables require a bounded array.")
    if type(columns) is not list or len(columns) > MAX_INCREMENTAL_CACHE_COLUMNS:
        raise ValueError("Parser schema columns require a bounded array.")
    declarations: list[ParsedVariableSchema] = []
    budget = ParsedSchemaBudget()
    for raw in variables:
        record = _record(raw, {"name", "kind", "shape", "layout"})
        shape = record["shape"]
        if type(shape) is not str or shape not in ("scalar", "entries"):
            raise ValueError("Parser schema shape must be scalar or entries.")
        budget.variable(
            _text(record["name"]), _kind_value(record["kind"]), cast(ParsedShape, shape)
        )
        layout = decode_distribution_layout(record["layout"], admit=budget.admit)
        declarations.append(
            ParsedVariableSchema(
                _text(record["name"]),
                _kind_value(record["kind"]),
                cast(ParsedShape, shape),
                layout=layout,
            )
        )
    fields: list[ParsedColumn] = []
    for raw in columns:
        record = _record(raw, {"name", "kind", "owner"})
        owner = record["owner"]
        column = ParsedColumn(
            _text(record["name"]),
            _kind_value(record["kind"]),
            None if owner is None else _text(owner),
        )
        budget.column(column)
        fields.append(column)
    return ParsedSchema(tuple(declarations), tuple(fields))


def encode_parsed_output(output: ParsedOutput) -> str:
    """Encode a bounded current path/digest/schema descriptor for existing owners."""
    if type(output) is not ParsedOutput:
        raise TypeError("Parser output encoding requires ParsedOutput.")
    document = (
        b'{"format":"ring5.parsed-output","version":'
        + str(PARSED_OUTPUT_VERSION).encode("ascii")
        + b',"csv_path":'
        + json.dumps(output.csv_path, ensure_ascii=False).encode("utf-8")
        + b',"sha256":'
        + json.dumps(output.sha256).encode("ascii")
        + b',"schema":'
        + encode_parsed_schema(output.schema)
        + b"}"
    )
    if len(document) > MAX_PARSED_DESCRIPTOR_BYTES:
        raise ValueError("Parser output descriptor exceeds its byte limit.")
    return document.decode("utf-8")


def decode_parsed_output(payload: str) -> ParsedOutput:
    """Decode the current descriptor without consulting files or filename history."""
    if type(payload) is not str or len(payload) > MAX_PARSED_DESCRIPTOR_BYTES:
        raise ValueError("Parser output descriptor requires bounded text.")
    document = _record(
        _decode_document(payload.encode("utf-8"), MAX_PARSED_DESCRIPTOR_BYTES),
        {"format", "version", "csv_path", "sha256", "schema"},
    )
    if (
        document["format"] != "ring5.parsed-output"
        or type(document["version"]) is not int
        or document["version"] != PARSED_OUTPUT_VERSION
    ):
        raise ValueError("Unsupported parser output format/version.")
    output = ParsedOutput(
        _text(document["csv_path"]),
        _text(document["sha256"]),
        _schema_from_payload(document["schema"]),
    )
    encode_parsed_output(output)
    return output


class ParsedOutputDigest:
    """Bind canonical schema meaning and CSV bytes with unambiguous framing."""

    def __init__(self, schema: ParsedSchema) -> None:
        encoded = encode_parsed_schema(schema)
        self._hash = hashlib.sha256(b"ring5.parsed-output.v1\x00")
        self._hash.update(len(encoded).to_bytes(8, "big"))
        self._hash.update(encoded)
        self._hash.update(b"\x00csv\x00")

    def update(self, value: bytes) -> None:
        """Include the next exact CSV byte chunk."""
        self._hash.update(value)

    def hexdigest(self) -> str:
        """Return the schema-bound typed-content digest."""
        return self._hash.hexdigest()


def read_numeric_wire(value: str) -> float:
    """Decode a numeric wire token without silently changing its finite range."""
    if type(value) is not str or len(value) > MAX_PARSED_CELL_CHARACTERS:
        raise ParseDataValueError("Numeric parser tokens must be bounded strings.")
    try:
        number = float(value)
    except ValueError as exc:
        raise ParseDataValueError("Invalid numeric parser token.") from exc
    overflow = math.isinf(number)
    if overflow or number == 0.0:
        try:
            exact = Decimal(value if overflow else value.lower().partition("e")[0])
        except InvalidOperation as exc:
            raise ParseDataValueError("Invalid numeric parser token.") from exc
        if (overflow and not exact.is_infinite()) or (number == 0.0 and not exact.is_zero()):
            raise ParseDataValueError("Finite parser token is outside the nonzero Float64 range.")
    return number


def render_parsed_value(kind: ParsedKind, value: ParsedValue) -> str:
    """Render an already typed cell without applying text null or inference rules."""
    if kind == "text" and type(value) is str:
        return value
    if kind == "number" and type(value) is float:
        return MISSING_VALUE if math.isnan(value) else str(value)
    raise TypeError("Parsed value does not match its declared cell kind.")


def read_parsed_value(kind: ParsedKind, value: str) -> ParsedValue:
    """Decode the unique current cell representation using its explicit kind."""
    if type(value) is not str:
        raise TypeError("Encoded parser cells must be strings.")
    if kind == "text":
        return value
    if kind != "number":
        raise ValueError("Unknown parsed cell kind.")
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric parser cell: {value!r}.") from exc
    if render_parsed_value(kind, number) != value:
        raise ValueError(f"Non-canonical numeric parser cell: {value!r}.")
    return number
