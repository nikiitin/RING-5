"""Canonical numeric and literal-text cells for parser CSV and cache records."""

import hashlib
import json
import math
from decimal import Decimal, InvalidOperation

from src.core.common.security_limits import MAX_PARSED_CELL_CHARACTERS, MAX_PARSED_SCHEMA_BYTES
from src.core.models.csv_contract import MISSING_VALUE
from src.core.models.parsed_output_models import ParsedKind, ParsedSchema, ParsedValue

PARSED_SCHEMA_VERSION = 1


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
