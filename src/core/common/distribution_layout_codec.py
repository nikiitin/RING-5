"""One bounded current codec for full and geometry-free Distribution declarations."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import cast

from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.common.security_limits import MAX_INCREMENTAL_CACHE_COLUMNS, MAX_PARSED_SCHEMA_BYTES
from src.core.models.distribution_geometry import (
    MAX_DISTRIBUTION_BUCKETS,
    DistributionGeometry,
    decode_distribution_geometry,
    encode_distribution_geometry,
)
from src.core.models.native_distribution_layout import (
    DistributionColumn,
    DistributionLayout,
    DistributionRole,
    NativeDistributionLayout,
    OpaqueDistributionLayout,
    ZeroPolicy,
)


def _json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def column_payload(column: DistributionColumn) -> dict[str, object]:
    """Encode one already validated binding with its explicit role and slot."""
    if type(column) is not DistributionColumn:
        raise TypeError("Distribution encoding requires a typed column binding.")
    return {
        "column": column.column,
        "source_label": column.source_label,
        "role": column.role,
        "native_index": column.native_index,
    }


DISTRIBUTION_LAYOUT_PREFIX = b'{"basis":"request","columns":['


def encode_distribution_column(column: DistributionColumn) -> bytes:
    """Encode one exact binding for publication and preallocation byte admission."""
    return _json(column_payload(column))


def distribution_layout_suffix(
    geometry: DistributionGeometry | None, zero_policy: ZeroPolicy | None
) -> bytes:
    """Return the shared canonical framing after the ordered column array."""
    if geometry is None:
        if zero_policy is not None:
            raise ValueError("Opaque source labels cannot declare an omission policy.")
        return b'],"kind":"distribution_source_labels"}'
    if type(geometry) is not DistributionGeometry or type(zero_policy) is not str:
        raise TypeError("Native layout framing requires typed geometry and a policy.")
    if zero_policy not in {"missing", "nozero"}:
        raise ValueError("Native layout framing requires a current omission policy.")
    return (
        b'],"geometry":'
        + _json(encode_distribution_geometry(geometry))
        + b',"kind":"gem5_distribution","zero_policy":'
        + _json(zero_policy)
        + b"}"
    )


def iter_distribution_layout_encoding(layout: DistributionLayout | None) -> Iterator[bytes]:
    """Yield exact canonical fragments without materializing the full role graph."""
    if layout is None:
        yield b"null"
        return
    if type(layout) not in (NativeDistributionLayout, OpaqueDistributionLayout):
        raise TypeError("Distribution encoding requires a current typed layout or None.")
    yield DISTRIBUTION_LAYOUT_PREFIX
    for index, column in enumerate(layout.columns):
        if index:
            yield b","
        yield encode_distribution_column(column)
    if type(layout) is NativeDistributionLayout:
        yield distribution_layout_suffix(layout.geometry, layout.zero_policy)
    else:
        yield distribution_layout_suffix(None, None)


def encode_distribution_layout(layout: DistributionLayout | None) -> dict[str, object] | None:
    """Return one independently owned bounded primitive declaration.

    Args:
        layout: Current full/opaque declaration, or explicit absence.

    Returns:
        Exact current JSON fields suitable for typed files, schemas and table attrs.

    Raises:
        TypeError: A declaration is not a current typed variant.
        ValueError: Its exact canonical encoding exceeds the schema budget.
    """
    encoded = bytearray()
    for fragment in iter_distribution_layout_encoding(layout):
        if len(encoded) + len(fragment) > MAX_PARSED_SCHEMA_BYTES:
            raise ValueError("Distribution layout exceeds its schema byte budget.")
        encoded.extend(fragment)
    return cast(dict[str, object] | None, json.loads(encoded))


def decode_distribution_layout(
    value: object,
    *,
    admit: Callable[[bytes], None] | None = None,
    expected: DistributionLayout | None = None,
) -> DistributionLayout | None:
    """Validate exact fields and bytes before retaining typed column bindings.

    Args:
        value: One current primitive declaration or explicit null.
        admit: Existing owner budget, charged before retaining typed bindings.
        expected: Already admitted request layout to reuse after exact validation.

    Returns:
        Its immutable current layout, without inferring geometry or producer kind.

    Raises:
        TypeError: Containers or bindings have invalid exact types.
        ValueError: Fields, roles, geometry, ownership or byte/width budgets are invalid.
    """
    if expected is not None and type(expected) not in (
        NativeDistributionLayout,
        OpaqueDistributionLayout,
    ):
        raise TypeError("Expected Distribution layout must be a current immutable variant.")
    if value is None:
        if expected is not None:
            raise ValueError("Cached layout omits the declared request layout.")
        if admit is not None:
            admit(b"null")
        return None
    if type(value) is not dict:
        raise TypeError("Distribution layout must be an object or null.")
    kind = value.get("kind")
    if type(kind) is not str:
        raise ValueError("Distribution layout requires a current explicit kind.")
    fields = {"kind", "basis", "columns"}
    if kind == "gem5_distribution":
        fields |= {"geometry", "zero_policy"}
    elif kind != "distribution_source_labels":
        raise ValueError("Unsupported Distribution layout kind.")
    if set(value) != fields or type(value["basis"]) is not str or value["basis"] != "request":
        raise ValueError("Distribution layout requires exactly its current request-basis fields.")
    raw_columns = value["columns"]
    if type(raw_columns) is not list or not 0 < len(raw_columns) <= MAX_INCREMENTAL_CACHE_COLUMNS:
        raise ValueError("Distribution layout exceeds its physical column budget.")
    geometry = None
    if kind == "gem5_distribution":
        geometry = decode_distribution_geometry(value["geometry"])
        required_columns = geometry.bucket_count + 2
        if required_columns > MAX_INCREMENTAL_CACHE_COLUMNS or len(raw_columns) < required_columns:
            raise ValueError(
                "Native layout cannot fit its complete slots and tails in the physical budget."
            )
        if type(value["zero_policy"]) is not str or value["zero_policy"] not in {
            "missing",
            "nozero",
        }:
            raise ValueError("Native layouts require an explicit current zero policy.")
    for raw in raw_columns:
        if type(raw) is not dict or set(raw) != {"column", "source_label", "role", "native_index"}:
            raise ValueError("Distribution bindings require exactly the current fields.")
        for field in ("column", "source_label"):
            if type(raw[field]) is not str or not raw[field] or len(raw[field]) > MAX_INPUT_LENGTH:
                raise ValueError("Distribution bindings require bounded non-empty text.")
        if type(raw["role"]) is not str or raw["role"] not in {
            "bucket",
            "underflow",
            "overflow",
            "summary",
            "source",
        }:
            raise ValueError("Distribution bindings require a current explicit role.")
        if raw["native_index"] is not None and (
            type(raw["native_index"]) is not int
            or not 0 <= raw["native_index"] < MAX_DISTRIBUTION_BUCKETS
        ):
            raise ValueError("Distribution slot indices must be bounded native integers or null.")
    # Admit primitive width/text/bytes before building the retained typed role graph.
    size = 0
    for fragment in json.JSONEncoder(
        ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).iterencode(value):
        if len(fragment) > MAX_PARSED_SCHEMA_BYTES:
            raise ValueError("Distribution layout exceeds its schema byte budget.")
        encoded = fragment.encode("utf-8")
        size += len(encoded)
        if size > MAX_PARSED_SCHEMA_BYTES:
            raise ValueError("Distribution layout exceeds its schema byte budget.")
        if admit is not None:
            admit(encoded)
    if expected is not None:
        if kind != expected.kind or len(raw_columns) != len(expected.columns):
            raise ValueError("Cached layout contradicts the declared request layout.")
        if type(expected) is NativeDistributionLayout and (
            geometry is None
            or _json(encode_distribution_geometry(geometry))
            != _json(encode_distribution_geometry(expected.geometry))
            or value["zero_policy"] != expected.zero_policy
        ):
            raise ValueError("Cached geometry contradicts the declared request layout.")
        # Every primitive has already passed exact type/field/role/index admission.
        # Comparing individual fields cannot admit bool/int equivalence or coercion.
        if any(
            (raw["column"], raw["source_label"], raw["role"], raw["native_index"])
            != (column.column, column.source_label, column.role, column.native_index)
            for raw, column in zip(raw_columns, expected.columns, strict=True)
        ):
            raise ValueError("Cached bindings contradict the declared request layout.")
        return expected
    columns = tuple(
        DistributionColumn(
            raw["column"],
            raw["source_label"],
            cast(DistributionRole, raw["role"]),
            raw["native_index"],
        )
        for raw in raw_columns
    )
    if kind == "gem5_distribution":
        assert geometry is not None
        return NativeDistributionLayout(
            geometry,
            cast(ZeroPolicy, value["zero_policy"]),
            columns,
        )
    return OpaqueDistributionLayout(columns)
