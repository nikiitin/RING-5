"""Expected populations and histogram geometry cannot allocate absent observations."""

from __future__ import annotations

import builtins
import importlib
import math
from collections.abc import Callable
from typing import Any

import pytest

from src.core.common.security_limits import MAX_INCREMENTAL_CACHE_COLUMNS
from src.parsing.gem5.types.base import FrameStatType, StatType
from src.parsing.gem5.types.configuration import Configuration
from src.parsing.gem5.types.distribution import Distribution
from src.parsing.gem5.types.histogram import Histogram
from src.parsing.gem5.types.scalar import Scalar
from src.parsing.gem5.types.vector import Vector

HUGE_REPEAT = 10**9
NUMERIC_CASES: list[tuple[Callable[[int], StatType[Any, Any]], Any, int]] = [
    (Scalar, 0.0, 1),
    (lambda repeat: Vector(repeat=repeat, entries=["a", "b"]), {"a": 0.0}, 2),
    (
        lambda repeat: Distribution(repeat=repeat, minimum=0, maximum=1),
        {"underflows": 0.0, "0": 1.25, "1": 0.0, "overflows": 0.0},
        4,
    ),
    (lambda repeat: Histogram(repeat=repeat, entries=["0-9"]), {"0-9": 0.0}, 1),
    (
        lambda repeat: Histogram(repeat=repeat, bins=2, max_range=10),
        {"0-9": 0.0},
        1,
    ),
]


@pytest.mark.parametrize("factory,sample,entry_count", NUMERIC_CASES)
@pytest.mark.parametrize("observed", [False, True])
def test_huge_repeat_keeps_only_actual_observations(
    factory: Callable[[int], StatType[Any, Any]],
    sample: Any,
    entry_count: int,
    observed: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stat = factory(HUGE_REPEAT)
    if observed:
        stat.add_observation(sample)
    expected_missing = entry_count * HUGE_REPEAT - (len(sample) if isinstance(sample, dict) else 1)
    if not observed:
        # Explicit schemas count each absent field; a dynamic empty histogram counts its source.
        expected_missing = entry_count * HUGE_REPEAT
    assert stat.missing_measurement_count == expected_missing

    def bounded_range(*args: int) -> range:
        result = builtins.range(*args)
        assert len(result) < 100, "Absent observations must not drive iteration."
        return result

    class BalanceMath:
        @property
        def nan(self) -> float:
            raise AssertionError("Balancing must not construct scalar NaN padding.")

    with monkeypatch.context() as guard:
        guard.setattr(
            importlib.import_module("src.parsing.gem5.types.base"),
            "range",
            bounded_range,
            raising=False,
        )
        guard.setattr(
            importlib.import_module("src.parsing.gem5.types.histogram"),
            "range",
            bounded_range,
            raising=False,
        )
        guard.setattr(
            importlib.import_module("src.parsing.gem5.types.scalar"), "math", BalanceMath()
        )
        stat.balance_content()
    assert stat.padded_count == stat.missing_measurement_count == expected_missing
    if isinstance(stat, FrameStatType):
        assert len(stat._frames) == int(observed)
        snapshot = stat.content
        expected_entries = (
            0 if isinstance(stat, Histogram) and not observed and not stat._entries else entry_count
        )
        assert len(snapshot) == expected_entries
        assert {len(values) for values in snapshot.values()} == (
            {int(observed)} if expected_entries else set()
        )
    else:
        assert len(stat.content) == int(observed)
    with monkeypatch.context() as guard:
        guard.setattr(
            importlib.import_module("src.parsing.gem5.types.histogram"),
            "range",
            bounded_range,
            raising=False,
        )
        stat.reduce_duplicates()
    result = stat.reduced_content
    if isinstance(result, dict):
        assert result
        assert all(math.isnan(value) for value in result.values())
    else:
        assert math.isnan(result)
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.padded_count == expected_missing
    with pytest.raises(RuntimeError, match="after balancing"):
        stat.add_observation(sample)


def test_huge_configuration_repeat_retains_explicit_empty_fallback() -> None:
    stat = Configuration(repeat=HUGE_REPEAT, on_empty="")
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.content == []
    assert stat.padded_count == stat.missing_measurement_count == 0
    assert stat.reduced_content == ""


@pytest.mark.parametrize("factory,sample,entry_count", NUMERIC_CASES)
def test_balanced_content_and_reduced_views_remain_defensive(
    factory: Callable[[int], StatType[Any, Any]], sample: Any, entry_count: int
) -> None:
    stat = factory(2)
    stat.add_observation(sample)
    stat.balance_content()
    snapshot = stat.content
    if isinstance(snapshot, dict):
        assert snapshot
        for values in snapshot.values():
            values.clear()
        snapshot.clear()
        assert stat.content
        assert {len(values) for values in stat.content.values()} == {1}
    else:
        snapshot.clear()
        assert stat.content == [0.0]
    missing = stat.padded_count
    stat.reduce_duplicates()
    result = stat.reduced_content
    if isinstance(result, dict):
        assert result
        result.clear()
        assert stat.reduced_content
        assert all(math.isnan(value) for value in stat.reduced_content.values())
    else:
        assert math.isnan(result)
    assert stat.padded_count == stat.missing_measurement_count == missing


@pytest.mark.parametrize("factory,sample,entry_count", NUMERIC_CASES)
def test_observed_nan_is_distinct_from_absence(
    factory: Callable[[int], StatType[Any, Any]], sample: Any, entry_count: int
) -> None:
    stat = factory(1)
    if isinstance(sample, dict):
        sample = dict.fromkeys(sample, math.nan)
        if isinstance(stat, Vector):
            sample["b"] = math.nan
    else:
        sample = math.nan
    stat.add_observation(sample)
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.padded_count == stat.missing_measurement_count == 0
    result = stat.reduced_content
    if isinstance(stat, Histogram) and stat.entries == ["0-9", "10+"]:
        assert math.isnan(result["0-9"])
        assert result["10+"] == 0.0
    elif isinstance(result, dict):
        assert result
        assert all(math.isnan(value) for value in result.values())
    else:
        assert math.isnan(result)


def test_repr_does_not_request_observation_snapshots(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_snapshot(_self: Any) -> Any:
        raise AssertionError("Representations must not inspect raw content.")

    for kind in (Scalar, Vector, Configuration, Distribution, Histogram):
        monkeypatch.setattr(kind, "content", property(no_snapshot))
        stat = kind(repeat=HUGE_REPEAT, entries=[]) if kind is Vector else kind(repeat=HUGE_REPEAT)
        assert len(str(stat)) < 150
        assert repr(stat) == str(stat)
        assert str(HUGE_REPEAT) in str(stat)


def test_complete_disjoint_histogram_frames_keep_justified_zero_contributions() -> None:
    stat = Histogram(repeat=2, bins=3, max_range=20, statistics=["mean"])
    stat.add_observation({"0-9": 6.0, "mean": 2.0})
    stat.add_observation({"10-19": 8.0})
    assert stat.missing_measurement_count == 3
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.padded_count == 3
    assert stat.reduced_content["0-9"] == 3.0
    assert stat.reduced_content["10-19"] == 4.0
    assert stat.reduced_content["20+"] == 0.0
    assert math.isnan(stat.reduced_content["mean"])


def test_huge_active_histogram_geometry_rejects_before_label_iteration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_range(*args: int) -> range:
        raise AssertionError(f"Unbounded geometry reached range{args}.")

    module = importlib.import_module("src.parsing.gem5.types.histogram")
    monkeypatch.setattr(module, "range", no_range, raising=False)
    with pytest.raises(ValueError, match="physical column limit"):
        Histogram(bins=HUGE_REPEAT, max_range=10)
    selected = Histogram(bins=HUGE_REPEAT, max_range=10, entries=["0-9"])
    selected.add_observation({"0-9": 2.0})
    summary = Histogram(bins=HUGE_REPEAT, max_range=10, statistics_only=True, statistics=["mean"])
    summary.add_observation({"mean": 3.0})
    inactive = Histogram(bins=HUGE_REPEAT, max_range=0)
    inactive.add_observation({"0-9": 4.0})
    for stat, expected in (
        (selected, {"0-9": 2.0}),
        (summary, {"mean": 3.0}),
        (inactive, {"0-9": 4.0}),
    ):
        stat.balance_content()
        stat.reduce_duplicates()
        assert stat.entries == list(expected)
        assert stat.reduced_content == expected


@pytest.mark.parametrize("extra", ["negative", "configured_summary"])
def test_exact_histogram_width_rejects_before_bucket_mapping(
    extra: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    stat = Histogram(
        bins=MAX_INCREMENTAL_CACHE_COLUMNS,
        max_range=MAX_INCREMENTAL_CACHE_COLUMNS - 1,
        statistics=["mean"] if extra == "configured_summary" else None,
    )
    stat.add_observation({"-1--1": 1.0} if extra == "negative" else {"unknown": 1.0})
    stat.balance_content()

    def no_mapping(_self: Histogram, _bins: int, _maximum: float) -> dict[str, Any]:
        raise AssertionError("Over-budget output must reject before mapping raw buckets.")

    monkeypatch.setattr(Histogram, "_compute_bin_mapping", no_mapping)
    with pytest.raises(ValueError, match="physical column limit"):
        stat.reduce_duplicates()
    assert not stat.is_reduced
    with pytest.raises(AttributeError):
        _ = stat.reduced_content


def test_histogram_width_counts_duplicate_summary_once() -> None:
    stat = Histogram(bins=MAX_INCREMENTAL_CACHE_COLUMNS, max_range=9999, statistics=["9999+"])
    assert len(stat.entries) == MAX_INCREMENTAL_CACHE_COLUMNS


def test_histogram_negative_bucket_fits_exact_remaining_column_budget() -> None:
    stat = Histogram(bins=MAX_INCREMENTAL_CACHE_COLUMNS - 1, max_range=9998)
    stat.add_observation({"-1--1": 2.0})
    stat.balance_content()
    stat.reduce_duplicates()
    assert len(stat.entries) == len(stat.reduced_content) == MAX_INCREMENTAL_CACHE_COLUMNS
    assert stat.reduced_content["<0"] == 2.0
    assert stat.reduced_content["9998+"] == 0.0


def test_unemitted_discovered_summary_does_not_consume_physical_column_budget() -> None:
    stat = Histogram(bins=MAX_INCREMENTAL_CACHE_COLUMNS, max_range=9999)
    stat.add_observation({"unknown": 2.0})
    stat.balance_content()
    stat.reduce_duplicates()
    assert len(stat.entries) == MAX_INCREMENTAL_CACHE_COLUMNS
    assert len(stat.reduced_content) == MAX_INCREMENTAL_CACHE_COLUMNS + 1
    assert stat.reduced_content["unknown"] == 2.0


def test_empty_dynamic_frame_kind_keeps_empty_schema_and_exact_source_missingness() -> None:
    for stat in (Vector(repeat=HUGE_REPEAT, entries=[]), Histogram(repeat=HUGE_REPEAT)):
        stat.balance_content()
        stat.reduce_duplicates()
        assert stat.content == stat.reduced_content == {}
        assert stat.padded_count == stat.missing_measurement_count == HUGE_REPEAT
