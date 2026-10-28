"""One scientific identity contract across cache and dataset boundaries."""

from enum import IntEnum, StrEnum

import numpy as np
import pandas as pd
import pytest

from src.core.common.content_identity import content_signature, frame_signature
from src.core.performance import SimpleCache, cached, compute_data_fingerprint
from src.core.state.repositories.data_repository import DataRepository


@pytest.mark.parametrize(
    "change",
    ["typed_value", "axis_type", "axis_name", "category_order", "attrs", "null_type"],
)
def test_retained_scientific_differences_reach_every_identity_consumer(change: str) -> None:
    # [test->req~ring5.quality.bounded-caching~1]
    before = pd.DataFrame(
        {
            "value": pd.Series([1, None], dtype=object),
            "category": pd.Categorical(["a", "b"], categories=["a", "b"], ordered=True),
        }
    )
    after = before.copy(deep=True)
    if change == "typed_value":
        after.at[0, "value"] = "1"
    elif change == "axis_type":
        after.index = pd.Index(list(before.index))
    elif change == "axis_name":
        after.columns.name = "measurements"
    elif change == "category_order":
        after["category"] = after["category"].cat.reorder_categories(["b", "a"])
    elif change == "attrs":
        after.attrs = {"units": {"value": "cycles"}}
    else:
        after.at[1, "value"] = np.nan

    assert frame_signature(before) != frame_signature(after)
    assert compute_data_fingerprint(before, {}, ["value"]) != compute_data_fingerprint(
        after, {}, ["value"]
    )
    repository = DataRepository()
    repository.add_dataset("before", before)
    repository.add_dataset("after", after)
    revisions = {
        name: repository.get_dataset_lineage(name).revisions[0].fingerprint
        for name in ("before", "after")
    }
    assert revisions == {"before": frame_signature(before), "after": frame_signature(after)}


def test_shaper_identity_includes_typed_parameters_and_selected_column_order() -> None:
    frame = pd.DataFrame({"x": [1], "y": [2]})
    first = compute_data_fingerprint(frame, {"parameter": 1}, ["x", "y"])
    assert first == compute_data_fingerprint(frame.copy(), {"parameter": 1}, ["x", "y"])
    assert first != compute_data_fingerprint(frame, {"parameter": "1"}, ["x", "y"])
    assert first != compute_data_fingerprint(frame, {"parameter": 1}, ["y", "x"])


def test_supported_binary_and_complex_scalars_keep_distinct_typed_identity() -> None:
    values = [b"1", "1", 1, complex(1), complex(1, 2), np.complex128(1)]
    assert len({content_signature(value) for value in values}) == len(values)


def test_temporal_axis_frequency_is_retained_in_the_identity() -> None:
    frame = pd.DataFrame({"value": [1, 2]}, index=pd.date_range("2026-01-01", periods=2))
    without_frequency = frame.copy()
    without_frequency.index = pd.DatetimeIndex(frame.index.values)
    assert frame_signature(frame) != frame_signature(without_frequency)


class _TextEnum(StrEnum):
    VALUE = "same"


class _NumberEnum(IntEnum):
    VALUE = 1


@pytest.mark.parametrize("value", [_TextEnum.VALUE, _NumberEnum.VALUE, object()])
def test_unsupported_metadata_is_rejected_without_scalar_coercion(value: object) -> None:
    with pytest.raises(ValueError, match="unsupported"):
        content_signature({"metadata": value})
    frame = pd.DataFrame({"value": [1]})
    frame.attrs = {"metadata": value}
    with pytest.raises(ValueError, match="unsupported"):
        frame_signature(frame)
    assert compute_data_fingerprint(frame, {}, ["value"]) is None


def test_failed_revision_identity_does_not_publish_or_consume_a_revision() -> None:
    repository = DataRepository()
    frame = pd.DataFrame({"value": [1]})
    repository.add_dataset("kept", frame)
    original = repository.get_dataset_lineage("kept")
    unsupported = frame.copy()
    cycle: list[object] = []
    cycle.append(cycle)
    unsupported.attrs = {"cycle": cycle}

    with pytest.raises(ValueError, match="recursive"):
        repository.add_dataset("kept", unsupported, replace=True)

    assert repository.get_dataset_lineage("kept") == original
    assert repository.get_dataset("kept").attrs == {}
    repository.add_dataset("kept", frame, replace=True)
    assert repository.get_dataset_lineage("kept").revisions[-1].revision_id == "rev-000002"


def test_unsupported_default_and_explicit_keys_bypass_cache_storage() -> None:
    cache = SimpleCache()
    calls: list[object] = []

    @cached(cache_instance=cache)
    def default_key(value: object) -> int:
        calls.append(value)
        return len(calls)

    unsupported = object()
    assert default_key(unsupported) == 1
    assert default_key(unsupported) == 2

    @cached(cache_instance=cache, key_func=lambda value: None)
    def explicit_bypass(value: int) -> int:
        calls.append(value)
        return len(calls)

    assert explicit_bypass(1) == 3
    assert explicit_bypass(1) == 4
    assert cache.stats()["size"] == 0


def test_default_cache_keys_distinguish_equal_string_representations() -> None:
    @cached()
    def scalar_type(value: object) -> type:
        return type(value)

    assert scalar_type(1) is int
    assert scalar_type("1") is str
    assert scalar_type(True) is bool


def test_frame_identity_rejects_invalid_input_types() -> None:
    assert frame_signature(None) is None
    with pytest.raises(TypeError, match="DataFrame"):
        frame_signature("invalid")  # type: ignore[call-overload]
