"""Exact current typed table values and strict malformed-payload rejection."""

import copy
import json
from typing import Any
from unittest.mock import patch

import pandas as pd
import numpy as np
import pytest

from tests.helpers.tables import scientific_frames
from src.core.common.content_identity import frame_signature
from src.core.common.typed_table_codec import TypedTableCodec


@pytest.mark.parametrize("frame", scientific_frames(), ids=lambda f: str(f.dtypes.tolist()))
def test_json_round_trip_preserves_scientific_identity(frame: pd.DataFrame) -> None:
    # [test->req~ring5.data.dataset-snapshots~1]
    payload = TypedTableCodec.encode(frame)
    restored = TypedTableCodec.decode(json.loads(json.dumps(payload, allow_nan=False)))
    pd.testing.assert_frame_equal(restored, frame)
    assert frame_signature(restored) == frame_signature(frame)


def test_absence_and_empty_frames_are_distinct() -> None:
    assert TypedTableCodec.encode(None) is None
    assert TypedTableCodec.decode(None) is None
    assert TypedTableCodec.encode(pd.DataFrame()) is not None


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.update(extra=True),
        lambda p: p.update(format_version=True),
        lambda p: p.update(format_version=0),
        lambda p: p["index"].update(step=0),
        lambda p: p["index"].update(start=True),
        lambda p: p["values"][0].append(2),
        lambda p: p["dtypes"][0].update(extra=True),
        lambda p: p["dtypes"][0].update(kind="retired"),
        lambda p: p["values"][0].__setitem__(0, {"type": "float", "value": "0x1.0p+0"}),
        lambda p: p["values"][0].__setitem__(0, {"type": "numpy", "dtype": "O", "value": "00"}),
        lambda p: p["attrs"].update(items=[["same", 1], ["same", 2]]),
    ],
)
def test_malformed_or_coercing_payloads_are_rejected(mutation: Any) -> None:
    payload = copy.deepcopy(TypedTableCodec.encode(pd.DataFrame({"value": [1]})))
    mutation(payload)
    with pytest.raises(ValueError, match="typed table"):
        TypedTableCodec.decode(payload)


@pytest.mark.parametrize("cyclic", [False, True])
def test_unsupported_and_recursive_values_are_rejected(cyclic: bool) -> None:
    frame = pd.DataFrame({"value": [1]})
    value: Any = [] if cyclic else object()
    if cyclic:
        value.append(value)
    frame.attrs = {"unsupported": value}
    with pytest.raises(ValueError):
        TypedTableCodec.encode(frame)


@pytest.mark.parametrize(
    "kind",
    [
        "range_rows",
        "range_columns",
        "padded_dtype",
        "combined_dtype_bytes",
        "category_levels",
        "multi_levels",
        "nested_array_dtype",
        "nested_array_shape",
        "combined_array_bytes",
    ],
)
def test_compact_metadata_amplification_is_rejected_before_allocation(kind: str) -> None:
    payload = copy.deepcopy(TypedTableCodec.encode(pd.DataFrame({"value": [1, 2]})))
    huge_range = {"kind": "range", "name": None, "start": 0, "stop": 10**12, "step": 1}
    array = {
        "type": "array",
        "dtype": {"kind": "numpy", "name": "|S1000000000"},
        "shape": [1],
        "items": ["x"],
    }
    if kind == "range_rows":
        payload = copy.deepcopy(TypedTableCodec.encode(pd.DataFrame()))
        payload["index"] = huge_range
    elif kind == "range_columns":
        payload["columns"] = huge_range
    elif kind in {"padded_dtype", "combined_dtype_bytes"}:
        payload["dtypes"][0] = {
            "kind": "numpy",
            "name": "|S1000000000" if kind == "padded_dtype" else "|S40000000",
        }
    elif kind == "category_levels":
        payload["dtypes"][0] = {"kind": "category", "categories": huge_range, "ordered": True}
    elif kind == "multi_levels":
        payload["index"] = {
            "kind": "multi",
            "names": [None],
            "levels": [huge_range],
            "codes": [[0, 1]],
            "sortorder": None,
        }
    else:
        if kind == "nested_array_shape":
            array["dtype"] = {"kind": "numpy", "name": "<i8"}
            array["shape"] = [10**12]
            array["items"] = []
        if kind == "combined_array_bytes":
            array["dtype"] = {"kind": "numpy", "name": "|S40000000"}
        payload["attrs"] = {"type": "dict", "items": [["array", array]]}
        if kind == "combined_array_bytes":
            payload["attrs"]["items"].append(["second", copy.deepcopy(array)])

    with (
        patch.object(
            TypedTableCodec, "_decode_axis", side_effect=AssertionError("axis allocation reached")
        ) as axes,
        patch(
            "src.core.common.typed_table_codec.frame_signature",
            side_effect=AssertionError("hash allocation reached"),
        ) as hashing,
        patch(
            "src.core.common.typed_table_codec.pd.Series",
            side_effect=AssertionError("column allocation reached"),
        ) as series,
        patch(
            "src.core.common.typed_table_codec.np.empty",
            side_effect=AssertionError("array allocation reached"),
        ) as arrays,
    ):
        with pytest.raises(ValueError, match="budget"):
            TypedTableCodec.decode(payload)
        axes.assert_not_called()
        hashing.assert_not_called()
        series.assert_not_called()
        arrays.assert_not_called()


@pytest.mark.parametrize("rows", [10**12, 10**30])
def test_oversized_compact_source_axis_is_rejected_before_hashing(rows: int) -> None:
    source = pd.DataFrame(index=pd.RangeIndex(rows))
    with patch("src.core.common.typed_table_codec.frame_signature") as hashing:
        with pytest.raises(ValueError, match="budget"):
            TypedTableCodec.encode(source)
        hashing.assert_not_called()


@pytest.mark.parametrize("kind", ["category", "multi"])
def test_nested_multi_index_levels_are_explicitly_rejected(kind: str) -> None:
    payload = TypedTableCodec.encode(pd.DataFrame({"x": [1]}))
    nested = TypedTableCodec.encode(
        pd.DataFrame({"x": [1]}, index=pd.MultiIndex.from_tuples([("a", 1)]))
    )["index"]
    if kind == "category":
        payload["dtypes"][0] = {"kind": "category", "categories": nested, "ordered": True}
    else:
        payload["index"] = {
            "kind": "multi",
            "levels": [nested],
            "codes": [[0]],
            "names": [None],
            "sortorder": None,
        }
    with pytest.raises(ValueError, match="levels"):
        TypedTableCodec.decode(payload)


def test_invalid_numpy_unicode_is_rejected_before_scalar_construction() -> None:
    payload = TypedTableCodec.encode(pd.DataFrame({"x": pd.Series(["valid"], dtype=object)}))
    payload["values"][0][0] = {"type": "numpy", "dtype": "<U1", "value": "ffffffff"}
    with patch("src.core.common.typed_table_codec.np.frombuffer") as construct:
        with pytest.raises(ValueError, match="typed table"):
            TypedTableCodec.decode(payload)
        construct.assert_not_called()


@pytest.mark.parametrize("kind", ["frame", "attribute_array"])
def test_source_encoding_stops_before_materializing_the_full_tagged_graph(
    kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = pd.DataFrame({"value": np.linspace(1.25, 2.5, 100)})
    if kind == "attribute_array":
        frame = pd.DataFrame()
        frame.attrs = {"array": np.linspace(1.25, 2.5, 100)}
    monkeypatch.setattr("src.core.common.typed_table_codec.MAX_TYPED_TABLE_BYTES", 4096)
    original = TypedTableCodec._encode_scalar
    with (
        patch.object(TypedTableCodec, "_encode_scalar", wraps=original) as scalars,
        patch.object(pd.Series, "tolist", side_effect=AssertionError("bulk values materialized")),
        patch("src.core.common.typed_table_codec.frame_signature") as hashing,
    ):
        with pytest.raises(ValueError, match="budget"):
            TypedTableCodec.encode(frame)
        encoded_values = [
            call
            for call in scalars.call_args_list
            if isinstance(call.args[0], (float, np.floating))
        ]
        assert 0 < len(encoded_values) < 100
        hashing.assert_not_called()
