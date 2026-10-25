"""Canonical numeric and literal-text cells for parser CSV and cache records."""

import hashlib
import json
import math
from collections.abc import Iterator
from typing import cast
from decimal import Decimal, InvalidOperation

from src.core.common.security_limits import (
    MAX_INCREMENTAL_CACHE_COLUMNS,
    MAX_PARSED_CELL_CHARACTERS,
    MAX_PARSED_SCHEMA_BYTES,
    MAX_PARSE_VARIABLES,
)
from src.core.models.csv_contract import MISSING_VALUE
from src.core.models.parsed_output_models import (
    ParsedCell,
    ParsedFileResult,
    ParsedKind,
    ParsedSchema,
    ParsedShape,
    ParsedValue,
    ParsedVariableResult,
)

PARSED_SCHEMA_VERSION = 1


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

    def cell_payload(cell: ParsedCell) -> dict[str, object]:
        value = render_parsed_value(cell.kind, cell.value)
        if len(value) > MAX_PARSED_CELL_CHARACTERS:
            raise ValueError("Encoded parser cell exceeds the character limit.")
        return {"column": cell.column, "kind": cell.kind, "value": value}

    return {
        "source_path": result.source_path,
        "variables": [
            {
                "name": variable.name,
                "kind": variable.kind,
                "shape": variable.shape,
                "missing_measurements": variable.missing_measurements,
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


def parsed_file_from_payload(value: object) -> ParsedFileResult:
    """Decode exactly the current typed file payload without scalar or owner inference."""
    record = _record(value, {"source_path", "variables", "metadata"})
    raw_variables = record["variables"]
    if type(raw_variables) is not list or len(raw_variables) > MAX_PARSE_VARIABLES:
        raise ValueError("Encoded parser variables require a bounded array.")
    variables: list[ParsedVariableResult] = []
    cell_count = 0
    for raw in raw_variables:
        variable = _record(raw, {"name", "kind", "shape", "missing_measurements", "cells"})
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
        variables.append(
            ParsedVariableResult(
                _text(variable["name"]), kind, cast(ParsedShape, shape), _cells(raw_cells), missing
            )
        )
    metadata = record["metadata"]
    if type(metadata) is not list or cell_count + len(metadata) > MAX_INCREMENTAL_CACHE_COLUMNS:
        raise ValueError("Encoded file exceeds the physical column limit.")
    return ParsedFileResult(_text(record["source_path"]), tuple(variables), _cells(metadata))


def encode_parsed_schema(schema: ParsedSchema) -> bytes:
    """Encode one bounded current schema without building an unbounded JSON graph."""
    if type(schema) is not ParsedSchema:
        raise TypeError("Parser schema encoding requires ParsedSchema.")
    encoded = bytearray()

    def append(value: bytes) -> None:
        if len(encoded) + len(value) > MAX_PARSED_SCHEMA_BYTES:
            raise ValueError("Parsed schema exceeds the descriptor byte limit.")
        encoded.extend(value)

    def record(value: dict[str, object]) -> None:
        append(
            json.dumps(
                value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        )

    append(
        b'{"format":"ring5.parsed-schema","version":'
        + str(PARSED_SCHEMA_VERSION).encode("ascii")
        + b',"variables":['
    )
    for index, variable in enumerate(schema.variables):
        if index:
            append(b",")
        record({"name": variable.name, "kind": variable.kind, "shape": variable.shape})
    append(b'],"columns":[')
    for index, column in enumerate(schema.columns):
        if index:
            append(b",")
        record({"name": column.name, "kind": column.kind, "owner": column.owner})
    append(b"]}")
    return bytes(encoded)


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
        raise ValueError("Numeric parser tokens must be bounded strings.")
    number = float(value)
    overflow = math.isinf(number)
    if overflow or number == 0.0:
        try:
            exact = Decimal(value if overflow else value.lower().partition("e")[0])
        except InvalidOperation as exc:
            raise ValueError("Invalid numeric parser token.") from exc
        if (overflow and not exact.is_infinite()) or (number == 0.0 and not exact.is_zero()):
            raise ValueError("Finite parser token is outside the nonzero Float64 range.")
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
