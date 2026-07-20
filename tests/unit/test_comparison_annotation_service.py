"""Tests for accessible regression outcome annotations."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.core.services.managers.comparison_annotation_service import (
    ComparisonAnnotationService,
)
from src.core.services.managers.comparison_service import ComparisonService


def _comparison(*, threshold_mode: str = "percentage") -> pd.DataFrame:
    baseline = pd.DataFrame({"benchmark": ["a", "b", "c"], "value": [10.0, 10.0, 10.0]})
    candidate = pd.DataFrame({"benchmark": ["a", "b", "c"], "value": [12.0, 8.0, 10.2]})
    return ComparisonService.compare(
        baseline,
        candidate,
        ["benchmark"],
        ["value"],
        thresholds=5.0 if threshold_mode == "percentage" else 1.0,
        threshold_mode=threshold_mode,  # type: ignore[arg-type]
    )


def test_annotations_encode_outcomes_with_text_shape_and_color() -> None:
    # [test->req~ring5.analysis.regression-annotations~1]
    comparison = _comparison()

    result = ComparisonAnnotationService.annotate(
        comparison,
        label_columns=["benchmark"],
    )

    assert result["annotation_label"].tolist() == ["a · value", "b · value", "c · value"]
    assert result["annotation_change"].tolist() == pytest.approx([20.0, -20.0, 2.0])
    assert result["annotation_symbol"].tolist() == ["▲", "▼", "●"]
    assert result["annotation_marker"].tolist() == [
        "triangle-up",
        "triangle-down",
        "circle",
    ]
    assert result["annotation_color"].tolist() == ["#0072B2", "#D55E00", "#6B7280"]
    assert result["annotation_text"].tolist() == [
        "▲ Improvement: +20.00%",
        "▼ Regression: -20.00%",
        "● Unchanged: +2.00%",
    ]


def test_default_labels_and_forced_change_modes() -> None:
    comparison = _comparison(threshold_mode="absolute")

    threshold = ComparisonAnnotationService.annotate(comparison)
    percentage = ComparisonAnnotationService.annotate(comparison, change_mode="percentage")
    absolute = ComparisonAnnotationService.annotate(comparison, change_mode="absolute")

    assert threshold["annotation_label"].tolist() == [
        "a · value",
        "b · value",
        "c · value",
    ]
    assert threshold["annotation_change"].tolist() == pytest.approx([2.0, -2.0, 0.2])
    assert threshold["annotation_text"].iloc[0] == "▲ Improvement: +2.00"
    assert percentage["annotation_change"].tolist() == pytest.approx([20.0, -20.0, 2.0])
    assert percentage["annotation_text"].iloc[0].endswith("+20.00%")
    assert absolute["annotation_change"].tolist() == pytest.approx([2.0, -2.0, 0.2])


def test_missing_values_remain_explicit_and_input_is_not_mutated() -> None:
    baseline = pd.DataFrame({"key": ["shared", "old"], "value": [1.0, 2.0]})
    candidate = pd.DataFrame({"key": ["shared", "new"], "value": [1.2, 3.0]})
    comparison = ComparisonService.compare(baseline, candidate, ["key"], ["value"])
    original = comparison.copy(deep=True)

    result = ComparisonAnnotationService.annotate(comparison, label_columns=["key"])

    missing = result.loc[result["outcome"].eq("missing_candidate")].iloc[0]
    assert np.isnan(missing["annotation_change"])
    assert missing["annotation_text"] == "? Missing Candidate"
    pd.testing.assert_frame_equal(comparison, original)


def test_empty_label_selection_uses_metric_only() -> None:
    result = ComparisonAnnotationService.annotate(_comparison(), label_columns=[])

    assert set(result["annotation_label"]) == {"value"}


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda frame: frame.drop(columns="metric"), "missing columns: metric"),
        (
            lambda frame: frame.assign(annotation_text="existing"),
            "already contains annotation columns",
        ),
        (lambda frame: frame.assign(outcome="surprise"), "invalid outcomes: surprise"),
        (lambda frame: frame.assign(outcome=None), "missing outcome"),
        (lambda frame: frame.assign(threshold_mode="ratio"), "invalid threshold modes"),
        (lambda frame: frame.assign(threshold_mode=None), "invalid threshold modes"),
        (
            lambda frame: frame.rename(columns={"metric": 1}),
            "non-empty string column names",
        ),
        (
            lambda frame: pd.concat([frame, frame[["metric"]]], axis=1),
            "unique column names",
        ),
    ],
)
def test_invalid_comparison_schema_is_rejected(mutate: object, message: str) -> None:
    invalid = mutate(_comparison())  # type: ignore[operator]

    with pytest.raises(ValueError, match=message):
        ComparisonAnnotationService.annotate(invalid)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"label_columns": [""]}, "non-empty string"),
        ({"label_columns": ["benchmark", "benchmark"]}, "Duplicate label"),
        ({"label_columns": ["missing"]}, "missing label columns: missing"),
        ({"change_mode": "ratio"}, "change_mode"),
    ],
)
def test_invalid_annotation_options_are_rejected(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ComparisonAnnotationService.annotate(
            _comparison(),
            **kwargs,  # type: ignore[arg-type]
        )
