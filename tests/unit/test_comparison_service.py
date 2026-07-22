"""Tests for aligned baseline and candidate comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.core.services.managers.comparison_service import ComparisonService


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    baseline = pd.DataFrame(
        {
            "benchmark": ["a", "b"],
            "ipc": [1.0, 2.0],
            "latency": [10.0, 20.0],
        }
    )
    candidate = pd.DataFrame(
        {
            "benchmark": ["a", "b"],
            "ipc": [1.2, 1.9],
            "latency": [9.0, 22.0],
        }
    )
    return baseline, candidate


def test_compare_calculates_changes_and_directional_outcomes() -> None:
    # [test->req~ring5.analysis.regression-comparison~1]
    baseline, candidate = _frames()

    result = ComparisonService.compare(
        baseline,
        candidate,
        ["benchmark"],
        ["ipc", "latency"],
        directions={"ipc": "higher", "latency": "lower"},
        thresholds={"ipc": 5.0, "latency": 5.0},
        baseline_name="v1",
        candidate_name="v2",
    )

    assert len(result) == 4
    indexed = result.set_index(["benchmark", "metric"])
    assert indexed.loc[("a", "ipc"), "absolute_change"] == pytest.approx(0.2)
    assert indexed.loc[("a", "ipc"), "percentage_change"] == pytest.approx(20.0)
    assert indexed.loc[("a", "ipc"), "outcome"] == "improvement"
    assert indexed.loc[("b", "ipc"), "outcome"] == "unchanged"
    assert indexed.loc[("a", "latency"), "outcome"] == "improvement"
    assert indexed.loc[("b", "latency"), "outcome"] == "regression"
    assert set(result["baseline_name"]) == {"v1"}
    assert set(result["candidate_name"]) == {"v2"}


def test_compare_preserves_unmatched_keys() -> None:
    baseline = pd.DataFrame({"key": ["shared", "old"], "value": [1.0, 2.0]})
    candidate = pd.DataFrame({"key": ["shared", "new"], "value": [1.1, 3.0]})

    result = ComparisonService.compare(baseline, candidate, ["key"], ["value"])

    outcomes = result.set_index("key")["outcome"].to_dict()
    assert outcomes == {
        "shared": "improvement",
        "old": "missing_candidate",
        "new": "missing_baseline",
    }


def test_absolute_threshold_handles_zero_baseline() -> None:
    baseline = pd.DataFrame({"key": ["a", "b"], "value": [0.0, 0.0]})
    candidate = pd.DataFrame({"key": ["a", "b"], "value": [0.0, 0.5]})

    result = ComparisonService.compare(
        baseline,
        candidate,
        ["key"],
        ["value"],
        thresholds=0.4,
        threshold_mode="absolute",
    ).set_index("key")

    assert result.loc["a", "percentage_change"] == 0.0
    assert result.loc["a", "outcome"] == "unchanged"
    assert np.isnan(result.loc["b", "percentage_change"])
    assert result.loc["b", "outcome"] == "improvement"


def test_percentage_threshold_marks_nonzero_change_from_zero_not_comparable() -> None:
    baseline = pd.DataFrame({"key": ["a"], "value": [0.0]})
    candidate = pd.DataFrame({"key": ["a"], "value": [1.0]})

    result = ComparisonService.compare(baseline, candidate, ["key"], ["value"])

    assert result.loc[0, "outcome"] == "not_comparable"


def test_nonfinite_metric_values_remain_visible() -> None:
    baseline = pd.DataFrame({"key": ["a", "b"], "value": [1.0, np.inf]})
    candidate = pd.DataFrame({"key": ["a", "b"], "value": [np.nan, 2.0]})

    result = ComparisonService.compare(baseline, candidate, ["key"], ["value"])

    assert result["outcome"].tolist() == ["missing_value", "missing_value"]


def test_compare_rejects_duplicate_alignment_keys() -> None:
    baseline = pd.DataFrame({"key": ["a", "a"], "value": [1.0, 2.0]})
    candidate = pd.DataFrame({"key": ["a"], "value": [1.5]})

    with pytest.raises(ValueError, match="Baseline key columns are not unique"):
        ComparisonService.compare(baseline, candidate, ["key"], ["value"])


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"thresholds": -1.0}, "finite non-negative"),
        ({"threshold_mode": "ratio"}, "percentage.*absolute"),
        ({"directions": "sideways"}, "Invalid metric directions"),
        ({"thresholds": {"unknown": 1.0}}, "unknown metrics"),
    ],
)
def test_compare_rejects_invalid_options(kwargs: dict[str, object], message: str) -> None:
    baseline, candidate = _frames()

    with pytest.raises(ValueError, match=message):
        ComparisonService.compare(
            baseline,
            candidate,
            ["benchmark"],
            ["ipc"],
            **kwargs,  # type: ignore[arg-type]
        )


def test_compare_rejects_missing_or_non_numeric_metrics() -> None:
    baseline = pd.DataFrame({"key": ["a"], "label": ["old"]})
    candidate = pd.DataFrame({"key": ["a"], "label": ["new"]})

    with pytest.raises(ValueError, match="metrics must be numeric"):
        ComparisonService.compare(baseline, candidate, ["key"], ["label"])
    with pytest.raises(ValueError, match="missing columns: value"):
        ComparisonService.compare(baseline, candidate, ["key"], ["value"])


def test_compare_does_not_mutate_inputs() -> None:
    baseline, candidate = _frames()
    original_baseline = baseline.copy(deep=True)
    original_candidate = candidate.copy(deep=True)

    ComparisonService.compare(baseline, candidate, ["benchmark"], ["ipc"])

    pd.testing.assert_frame_equal(baseline, original_baseline)
    pd.testing.assert_frame_equal(candidate, original_candidate)
