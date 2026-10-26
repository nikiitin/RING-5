"""Declared slots match primary native text; strict codecs retain no inferred grid."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.common import distribution_layout_codec as codec
from src.core.models.distribution_geometry import DistributionGeometry, native_bucket_label
from src.core.models.native_distribution_layout import (
    DistributionColumn,
    NativeDistributionLayout,
    OpaqueDistributionLayout,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/gem5_native_text"


def _full() -> NativeDistributionLayout:
    return NativeDistributionLayout(
        DistributionGeometry(0.25, 1.25, 0.5),
        "missing",
        (
            DistributionColumn("alias..underflows", "underflows", "underflow", None),
            DistributionColumn("alias..0.25", "0.25", "bucket", 0),
            DistributionColumn("alias..0.75", "0.75", "bucket", 1),
            DistributionColumn("alias..1.25", "1.25", "bucket", 2),
            DistributionColumn("alias..1.75", "1.75", "bucket", 3),
            DistributionColumn("alias..overflows", "overflows", "overflow", None),
            DistributionColumn("alias..mean", "mean", "summary", None),
        ),
    )


@pytest.mark.parametrize(
    "fixture,geometry,sparse",
    [
        ("integer", (0, 1, 1), False),
        ("offset_unit", (0.25, 1.25, 1), False),
        ("nonunit", (0.25, 5.75, 2.5), False),
        ("negative", (-1.25, 1.25, 0.5), False),
        ("nozero", (0.25, 2.25, 1), True),
        ("nozero_half", (0.25, 2.25, 0.5), True),
        ("nozero_wider", (-0.75, 3.25, 1), True),
        ("empty_dist", (0, 1, 1), False),
    ],
)
def test_slot_labels_match_pinned_verbatim_native_printer_output(
    fixture: str, geometry: tuple[float, float, float], sparse: bool
) -> None:
    declared = DistributionGeometry(*geometry)
    labels = [native_bucket_label(declared, index) for index in range(declared.bucket_count)]
    summaries = {
        "samples",
        "mean",
        "stdev",
        "underflows",
        "overflows",
        "min_value",
        "max_value",
        "total",
    }
    observed = [
        row.split("::", 1)[1].split()[0]
        for row in (FIXTURES / f"{fixture}.txt").read_text().splitlines()
        if "::" in row and row.split("::", 1)[1].split()[0] not in summaries
    ]
    if sparse:
        assert observed and set(observed) < set(labels)
    else:
        assert observed == labels


def test_layout_retains_above_maximum_slots_and_independent_primitive_ownership() -> None:
    layout = _full()
    assert layout.columns[4].source_label == "1.75" and layout.geometry.maximum == 1.25
    payload = codec.encode_distribution_layout(layout)
    assert payload is not None
    assert payload["geometry"] == {"minimum": 0.25, "maximum": 1.25, "bucket_size": 0.5}
    restored = codec.decode_distribution_layout(payload)
    assert restored == layout
    assert isinstance(restored, NativeDistributionLayout)
    assert isinstance(payload["columns"], list)
    payload["columns"].clear()
    assert len(layout.columns) == len(restored.columns) == 7


def test_opaque_distribution_labels_carry_no_grid_policy_or_index_claim() -> None:
    opaque = OpaqueDistributionLayout((DistributionColumn("alias..0.25", "0.25", "source", None),))
    payload = codec.encode_distribution_layout(opaque)
    assert payload == {
        "kind": "distribution_source_labels",
        "basis": "request",
        "columns": [
            {
                "column": "alias..0.25",
                "source_label": "0.25",
                "role": "source",
                "native_index": None,
            }
        ],
    }
    assert codec.decode_distribution_layout(payload) == opaque
    assert codec.encode_distribution_layout(None) is None
    assert codec.decode_distribution_layout(None) is None


def test_layout_byte_admission_precedes_retained_binding_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = codec.encode_distribution_layout(_full())
    monkeypatch.setattr(codec, "MAX_PARSED_SCHEMA_BYTES", 40)
    with patch.object(codec, "DistributionColumn", side_effect=AssertionError("allocated roles")):
        with pytest.raises(ValueError, match="byte budget"):
            codec.decode_distribution_layout(payload)


@pytest.mark.parametrize("field", ["kind", "basis", "columns", "geometry", "zero_policy"])
def test_full_layout_missing_fields_reject_instead_of_adapting(field: str) -> None:
    payload = codec.encode_distribution_layout(_full())
    assert payload is not None
    del payload[field]
    with pytest.raises((ValueError, TypeError)):
        codec.decode_distribution_layout(payload)


def test_native_label_collisions_remain_visible_instead_of_merging_slots() -> None:
    geometry = DistributionGeometry(1e10, 1e10 + 1, 1)
    assert geometry.bucket_count == 2
    assert native_bucket_label(geometry, 0) == native_bucket_label(geometry, 1) == "1e+10"
    with pytest.raises(ValueError, match="source labels collide"):
        NativeDistributionLayout(
            geometry,
            "missing",
            (
                DistributionColumn("u", "underflows", "underflow", None),
                DistributionColumn("a", "1e+10", "bucket", 0),
                DistributionColumn("b", "1e+10", "bucket", 1),
                DistributionColumn("o", "overflows", "overflow", None),
            ),
        )


@pytest.mark.parametrize("mode", ["oversized", "incomplete"])
def test_native_count_admission_precedes_any_decoded_role_graph(mode, monkeypatch):
    payload = codec.encode_distribution_layout(_full())
    assert payload is not None
    if mode == "oversized":
        payload["geometry"]["maximum"] = 10000.0
    else:
        payload["columns"] = payload["columns"][:3]
    with patch.object(codec, "DistributionColumn", side_effect=AssertionError("allocated roles")):
        with pytest.raises(ValueError, match="complete slots and tails"):
            codec.decode_distribution_layout(payload)
