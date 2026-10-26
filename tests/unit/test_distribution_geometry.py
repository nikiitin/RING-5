"""Native-double grid geometry and strict current codec admission."""

from __future__ import annotations

import json
import math
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from src.core.models.distribution_geometry import (
    MAX_DISTRIBUTION_BUCKETS,
    DistributionGeometry,
    decode_distribution_geometry,
    encode_distribution_geometry,
)


@pytest.mark.parametrize(
    "minimum,maximum,bucket_size,count",
    [
        (0, 4, 1, 5),
        (0, 4, 2, 3),
        (0.25, 1.25, 0.5, 4),
        (-0.75, 3.25, 1, 5),
        (0.25, 2.25, 1, 3),
        (0.25, 2.25, 0.5, 6),
        (0.25, 4.25, 2.5, 2),
        (0, 0, 0.25, 4),
        (0, MAX_DISTRIBUTION_BUCKETS - 1, 1, MAX_DISTRIBUTION_BUCKETS),
        (0, 0, 1e308, 1),
    ],
)
def test_native_grid_count_preserves_offset_nonunit_and_narrow_semantics(
    minimum: float, maximum: float, bucket_size: float, count: int
) -> None:
    geometry = DistributionGeometry(minimum, maximum, bucket_size)
    assert geometry.bucket_count == count
    assert all(
        type(value) is float for value in (geometry.minimum, geometry.maximum, geometry.bucket_size)
    )
    assert decode_distribution_geometry(encode_distribution_geometry(geometry)) == geometry


def test_narrow_native_storage_keeps_cells_above_the_tracked_maximum() -> None:
    geometry = DistributionGeometry(0.25, 1.25, 0.5)
    positions = [geometry.minimum + index * geometry.bucket_size for index in range(4)]
    assert positions == [0.25, 0.75, 1.25, 1.75]
    assert positions[-1] > geometry.maximum


@pytest.mark.parametrize("field", ["minimum", "maximum", "bucket_size"])
@pytest.mark.parametrize("invalid", [True, False, "0.25", None, [], {}])
def test_fields_never_coerce_non_numeric_values(field: str, invalid: object) -> None:
    payload: dict[str, object] = {"minimum": 0.25, "maximum": 1.25, "bucket_size": 0.5}
    payload[field] = invalid
    with pytest.raises(TypeError, match="actual finite number"):
        decode_distribution_geometry(payload)


@pytest.mark.parametrize("field", ["minimum", "maximum", "bucket_size"])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf, 10**400, 2**53 + 1])
def test_nonfinite_and_lossy_fields_fail_before_layout_allocation(
    field: str, invalid: float
) -> None:
    payload = {"minimum": 0.25, "maximum": 1.25, "bucket_size": 0.5}
    payload[field] = invalid
    with pytest.raises(ValueError, match="finite|range|exactly"):
        decode_distribution_geometry(payload)


@pytest.mark.parametrize(
    "geometry",
    [
        (2, 1, 1),
        (0, 1, 0),
        (0, 1, -1),
        (0, MAX_DISTRIBUTION_BUCKETS, 1),
        (-1e308, 1e308, 1),
        (0, 1, math.ulp(0.0)),
    ],
)
def test_reversed_invalid_and_unbounded_native_arithmetic_is_rejected(
    geometry: tuple[float, float, float],
) -> None:
    with pytest.raises(ValueError):
        DistributionGeometry(*geometry)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"minimum": 0, "maximum": 1},
        {"minimum": 0, "maximum": 1, "bucket_size": 1, "bucket_count": 2},
        {"offset": 0, "maximum": 1, "bucket_size": 1},
        {"minimum": 0, "maximum": 1, "bucketSize": 1},
        {"minimum": 0, "maximum": 1, "bucket_size": 1, "entries": ["0", "1"]},
    ],
)
def test_codec_requires_exact_authoritative_fields(payload: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="exactly"):
        decode_distribution_geometry(payload)


@pytest.mark.parametrize("payload", [None, [], (), "0,1,1"])
def test_codec_requires_a_current_json_object(payload: object) -> None:
    with pytest.raises(TypeError, match="object"):
        decode_distribution_geometry(payload)


def test_geometry_codec_owns_values_and_has_no_derived_or_legacy_route() -> None:
    payload = {"minimum": 0.25, "maximum": 1.25, "bucket_size": 0.5}
    geometry = decode_distribution_geometry(payload)
    payload["maximum"] = 100
    encoded = encode_distribution_geometry(geometry)
    assert encoded == {"minimum": 0.25, "maximum": 1.25, "bucket_size": 0.5}
    encoded["bucket_size"] = 1
    assert geometry.bucket_size == 0.5
    assert (
        decode_distribution_geometry(json.loads(json.dumps(encode_distribution_geometry(geometry))))
        == geometry
    )
    with pytest.raises(FrozenInstanceError):
        setattr(geometry, "maximum", 2)
    with pytest.raises(TypeError):
        DistributionGeometry(0, 1, 1, bucket_count=2)  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="typed model"):
        encode_distribution_geometry(cast(DistributionGeometry, payload))


def test_geometry_does_not_treat_equal_printed_labels_as_equal_grids() -> None:
    unit = DistributionGeometry(0.25, 2.25, 1)
    narrow = DistributionGeometry(0.25, 2.25, 0.5)
    shifted = DistributionGeometry(-0.75, 3.25, 1)
    assert len({unit, narrow, shifted}) == 3
    assert encode_distribution_geometry(unit) != encode_distribution_geometry(narrow)


def test_lossless_integer_endpoints_keep_native_precision() -> None:
    geometry = DistributionGeometry(2**53, 2**53, 1)
    assert geometry.minimum == 2**53
    assert geometry.bucket_count == 1
