"""Tests for repeated-sample statistical comparison."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.core.services.managers.statistical_comparison_service import (
    StatisticalComparisonService,
)


def test_statistics_include_intervals_effect_bootstrap_and_significance() -> None:
    # [test->req~ring5.analysis.statistical-comparison~1]
    baseline = pd.DataFrame({"benchmark": ["a"] * 5, "ipc": [1.0, 2.0, 3.0, 4.0, 5.0]})
    candidate = pd.DataFrame({"benchmark": ["a"] * 5, "ipc": [10.0, 11.0, 12.0, 13.0, 14.0]})

    result = StatisticalComparisonService.compare(
        baseline,
        candidate,
        ["benchmark"],
        ["ipc"],
        bootstrap_samples=500,
        random_seed=7,
    )

    row = result.iloc[0]
    assert row["baseline_n"] == 5
    assert row["candidate_n"] == 5
    assert row["mean_difference"] == pytest.approx(9.0)
    assert row["difference_ci_low"] < row["mean_difference"] < row["difference_ci_high"]
    assert row["effect_size_hedges_g"] > 4.0
    assert row["test"] == "welch_t"
    assert row["p_value"] < 0.001
    assert bool(row["significant"]) is True
    assert row["bootstrap_difference"] == pytest.approx(9.0, abs=0.2)
    assert row["bootstrap_ci_low"] < row["bootstrap_ci_high"]
    assert row["warning"] == ""


def test_bootstrap_results_are_deterministic() -> None:
    baseline = pd.DataFrame({"value": [1.0, 2.0, 4.0]})
    candidate = pd.DataFrame({"value": [2.0, 4.0, 8.0]})

    first = StatisticalComparisonService.compare(
        baseline, candidate, [], ["value"], bootstrap_samples=300, random_seed=19
    )
    second = StatisticalComparisonService.compare(
        baseline, candidate, [], ["value"], bootstrap_samples=300, random_seed=19
    )

    pd.testing.assert_frame_equal(first, second)


def test_group_order_and_missing_groups_are_preserved() -> None:
    baseline = pd.DataFrame({"key": ["shared", "shared", "old"], "value": [1.0, 2.0, 3.0]})
    candidate = pd.DataFrame({"key": ["shared", "shared", "new"], "value": [2.0, 3.0, 4.0]})

    result = StatisticalComparisonService.compare(
        baseline,
        candidate,
        ["key"],
        ["value"],
        bootstrap_samples=100,
    ).set_index("key")

    assert list(result.index) == ["shared", "old", "new"]
    assert "missing_candidate_group" in result.loc["old", "warning"]
    assert "missing_baseline_group" in result.loc["new", "warning"]
    assert math.isnan(result.loc["old", "p_value"])


def test_nonfinite_values_are_dropped_and_reported() -> None:
    baseline = pd.DataFrame({"value": [1.0, np.nan, np.inf]})
    candidate = pd.DataFrame({"value": [2.0, 3.0, 4.0]})

    row = StatisticalComparisonService.compare(
        baseline,
        candidate,
        [],
        ["value"],
        bootstrap_samples=100,
    ).iloc[0]

    assert row["baseline_n"] == 1
    assert "baseline_nonfinite_values_dropped" in row["warning"]
    assert "insufficient_baseline_samples" in row["warning"]


def test_small_samples_and_zero_variance_are_reported() -> None:
    baseline = pd.DataFrame({"value": [1.0, 1.0, 1.0]})
    candidate = pd.DataFrame({"value": [2.0, 2.0, 2.0]})

    row = StatisticalComparisonService.compare(
        baseline,
        candidate,
        [],
        ["value"],
        bootstrap_samples=100,
        minimum_sample_size=5,
    ).iloc[0]

    assert row["p_value"] == 0.0
    assert math.isnan(row["effect_size_hedges_g"])
    assert "small_baseline_sample" in row["warning"]
    assert "small_candidate_sample" in row["warning"]
    assert "zero_variance" in row["warning"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"confidence_level": 1.0}, "confidence_level"),
        ({"alpha": 0.0}, "alpha"),
        ({"bootstrap_samples": 99}, "greater than or equal to 100"),
        ({"bootstrap_samples": 50_001}, "cannot exceed"),
        ({"random_seed": -1}, "random_seed"),
        ({"minimum_sample_size": 1}, "minimum_sample_size"),
    ],
)
def test_invalid_statistical_options_are_rejected(kwargs: dict[str, object], message: str) -> None:
    baseline = pd.DataFrame({"value": [1.0, 2.0]})
    candidate = pd.DataFrame({"value": [2.0, 3.0]})

    with pytest.raises(ValueError, match=message):
        StatisticalComparisonService.compare(
            baseline,
            candidate,
            [],
            ["value"],
            **kwargs,  # type: ignore[arg-type]
        )


def test_invalid_columns_are_rejected() -> None:
    baseline = pd.DataFrame({"key": ["a"], "label": ["old"]})
    candidate = pd.DataFrame({"key": ["a"], "label": ["new"]})

    with pytest.raises(ValueError, match="metrics must be numeric"):
        StatisticalComparisonService.compare(baseline, candidate, ["key"], ["label"])
    with pytest.raises(ValueError, match="missing columns: value"):
        StatisticalComparisonService.compare(baseline, candidate, ["key"], ["value"])
    with pytest.raises(ValueError, match="overlap"):
        StatisticalComparisonService.compare(baseline, candidate, ["key"], ["key"])
