"""Tests for dataset quality profiling."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.core.services.managers.quality_profile_service import QualityProfileService


def test_profile_reports_dataset_and_column_issues() -> None:
    # [test->req~ring5.data.quality-profiler~1]
    data = pd.DataFrame(
        {
            "metric": [1.0, 1.0, 1.0, 1.0, 100.0],
            "ratio": [1.0, np.inf, 2.0, np.nan, 3.0],
            "numeric_text": ["1", "bad", "2", None, "3"],
            "constant": ["x"] * 5,
        }
    )

    report = QualityProfileService.profile(
        data,
        expected_types={"metric": "numeric", "numeric_text": "numeric"},
    )

    assert report.row_count == 5
    assert report.column_count == 4
    assert report.missing_cells == 2
    assert report.infinite_cells == 1
    assert report.iqr_outlier_cells == 1
    assert report.schema_violations == 1
    assert "constant" in report.constant_columns
    assert report.has_issues is True
    profiles = report.to_frame().set_index("name")
    assert profiles.loc["metric", "iqr_outliers"] == 1
    assert profiles.loc["ratio", "infinite"] == 1
    assert profiles.loc["numeric_text", "invalid_type_values"] == 1
    assert profiles.loc["metric", "inferred_type"] == "numeric"


def test_duplicate_rows_and_missing_expected_columns_are_reported() -> None:
    data = pd.DataFrame({"name": ["a", "a"], "value": [1, 1]})

    report = QualityProfileService.profile(
        data,
        expected_types={"missing": "numeric"},
    )

    assert report.duplicate_rows == 1
    assert report.schema_violations == 1
    assert report.schema_errors == ("Missing expected column: missing",)


@pytest.mark.parametrize(
    ("values", "expected", "invalid"),
    [
        (["1", "2.5", "bad"], "numeric", 1),
        (["1", "2.5", "3"], "integer", 1),
        (["yes", "false", "maybe"], "boolean", 1),
        (["2026-01-01", "bad", "2026-03-01"], "datetime", 1),
        (["a", 1, "b"], "string", 1),
    ],
)
def test_expected_type_validation(values: list[object], expected: str, invalid: int) -> None:
    data = pd.DataFrame({"value": values})

    report = QualityProfileService.profile(
        data,
        expected_types={"value": expected},  # type: ignore[dict-item]
    )

    assert report.columns[0].invalid_type_values == invalid


def test_clean_empty_dataset_has_no_issues() -> None:
    data = pd.DataFrame({"value": pd.Series(dtype=float)})

    report = QualityProfileService.profile(data)

    assert report.row_count == 0
    assert report.missing_cells == 0
    assert report.has_issues is True
    assert report.constant_columns == ("value",)


def test_profile_does_not_mutate_input_or_expose_mutable_records() -> None:
    data = pd.DataFrame({"value": [1.0, 2.0]})
    original = data.copy(deep=True)

    report = QualityProfileService.profile(data)
    frame = report.to_frame()
    frame.loc[0, "missing"] = 99

    pd.testing.assert_frame_equal(data, original)
    assert report.columns[0].missing == 0


def test_invalid_columns_and_expectations_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique column names"):
        QualityProfileService.profile(pd.DataFrame([[1, 2]], columns=["x", "x"]))
    with pytest.raises(ValueError, match="string column names"):
        QualityProfileService.profile(pd.DataFrame([[1]], columns=[1]))
    with pytest.raises(ValueError, match="Invalid expected type"):
        QualityProfileService.profile(
            pd.DataFrame({"x": [1]}),
            expected_types={"x": "currency"},  # type: ignore[dict-item]
        )
