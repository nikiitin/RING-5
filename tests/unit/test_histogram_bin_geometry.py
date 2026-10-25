"""Explicit histogram label geometry and per-observation admission contracts."""

from __future__ import annotations

import math

import pytest

from src.web.pages.ui.plotting.utils.histogram_bins import (
    aggregate_histogram_observations,
    parse_histogram_bins,
    rebin_histogram,
)


@pytest.mark.parametrize(
    "labels, bounds, order",
    [
        (["0-0"], [(0, 1)], [0]),
        (["-3--1", "0-2"], [(-3, 0), (0, 3)], [0, 1]),
        (["10-19", "0-9"], [(0, 10), (10, 20)], [1, 0]),
        (["[0.25,2.75)", "[2.75,3)"], [(0.25, 2.75), (2.75, 3)], [0, 1]),
        (["[1e-3,2e-3)"], [(0.001, 0.002)], [0]),
        (["10+", "<0", "0-9"], [(None, 0), (0, 10), (10, None)], [1, 2, 0]),
        (["0-1", "[2,2.5)", "3+"], [(0, 2), (2, 2.5), (3, None)], [0, 1, 2]),
    ],
)
def test_canonical_labels_have_explicit_geometry(
    labels: list[str], bounds: list[tuple[float | None, float | None]], order: list[int]
) -> None:
    bins, actual_order = parse_histogram_bins(labels)
    assert [(bucket.lower, bucket.upper) for bucket in bins] == bounds
    assert actual_order == order
    assert [bucket.label for bucket in bins] == [labels[index] for index in order]


@pytest.mark.parametrize(
    "labels",
    [
        ["0-10", "10-20"],
        ["-10--1", "0-10", "10-20"],
        ["0-9", "[9,11)"],
        ["[0,2)", "[1,3)"],
        ["0-9", "0-9"],
        ["0-9", "9+"],
        ["<1", "0-9"],
        ["<0", "<-1"],
        ["1+", "2+"],
    ],
)
def test_overlapping_buckets_within_one_observation_fail_visibly(labels: list[str]) -> None:
    with pytest.raises(ValueError, match="Overlapping histogram buckets"):
        parse_histogram_bins(labels)


@pytest.mark.parametrize(
    "labels",
    [
        [],
        ["0.25-1.75"],
        ["0.0-1.0"],
        ["[1,1)"],
        ["2-1"],
        ["[2,1)"],
        ["[0,1e400)"],
        ["[0,inf)"],
        ["[-1e308,1e308)"],
        ["9007199254740993-9007199254740994"],
        ["9" * 400 + "-" + "9" * 401],
    ],
)
def test_ambiguous_or_unrepresentable_geometry_is_rejected(labels: list[str]) -> None:
    with pytest.raises(ValueError):
        parse_histogram_bins(labels)


def test_a_labels_geometry_does_not_depend_on_its_neighbors() -> None:
    isolated, _ = parse_histogram_bins(["0-10"])
    joined, _ = parse_histogram_bins(["-10--1", "0-10", "11-20"])
    assert isolated[0] == joined[1]
    assert isolated[0].width == 11


@pytest.mark.parametrize("bucket_size", [None, 0.5, 2.0])
def test_different_observation_schemas_preserve_measured_mass_and_tails(
    bucket_size: float | None,
) -> None:
    labels = ["<0", "0-0", "[0,2)", "2+", "1+"]
    rows = [[2, 3, math.nan, math.nan, 5], [7, math.nan, 11, 13, math.nan]]
    bins, counts = aggregate_histogram_observations(labels, rows)
    rendered, values = rebin_histogram(bins, counts, bucket_size)
    assert math.fsum(values) == pytest.approx(41)
    assert [
        (bucket.label, count)
        for bucket, count in zip(rendered, values, strict=True)
        if bucket.width is None
    ] == [("<0", 9), ("1+", 5), ("2+", 13)]


def test_zero_counts_still_declare_geometry_and_cannot_hide_overlap() -> None:
    with pytest.raises(ValueError, match="Overlapping histogram buckets"):
        aggregate_histogram_observations(["0-10", "10-20"], [[0, 1]])
    bins, counts = aggregate_histogram_observations(["0-9", "10-19"], [[0, 1]])
    assert [bucket.width for bucket in bins] == [10, 10]
    assert counts == [0, 1]
