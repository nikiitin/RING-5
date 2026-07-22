"""Tests for machine-readable threshold comparison exports."""

from __future__ import annotations

import json
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
import pytest

from src.core.services.managers.comparison_service import ComparisonService
from src.core.services.managers.regression_result_export_service import (
    RegressionResultExportService,
)


def _comparison() -> pd.DataFrame:
    baseline = pd.DataFrame({"benchmark": ["a", "b", "c"], "ipc": [100.0, 100.0, np.nan]})
    candidate = pd.DataFrame({"benchmark": ["a", "b", "d"], "ipc": [90.0, 110.0, 5.0]})
    return ComparisonService.compare(
        baseline,
        candidate,
        ["benchmark"],
        ["ipc"],
        thresholds=5.0,
        baseline_name="main",
        candidate_name="change-42",
    )


def test_json_is_versioned_deterministic_and_retains_result_semantics() -> None:
    # [test->req~ring5.automation.machine-readable-regression~1]
    comparison = _comparison()

    first = RegressionResultExportService.export(comparison, "json")
    second = RegressionResultExportService.export(comparison.copy(), "json")
    document = json.loads(first)

    assert first == second
    assert first.endswith(b"\n")
    assert document["format"] == "ring5.regression-results"
    assert document["schema_version"] == 1
    assert document["sources"] == {"baseline": "main", "candidate": "change-42"}
    assert document["summary"] == {
        "total": 4,
        "failures": 1,
        "incomplete": 2,
        "outcomes": {
            "regression": 1,
            "improvement": 1,
            "unchanged": 0,
            "missing_baseline": 1,
            "missing_candidate": 1,
            "missing_value": 0,
            "not_comparable": 0,
        },
    }
    assert document["results"][0] == {
        "keys": {"benchmark": "a"},
        "metric": "ipc",
        "baseline_value": 100.0,
        "candidate_value": 90.0,
        "absolute_change": -10.0,
        "percentage_change": -10.0,
        "direction": "higher",
        "threshold": 5.0,
        "threshold_mode": "percentage",
        "outcome": "regression",
    }
    assert document["results"][2]["candidate_value"] is None
    assert document["results"][3]["baseline_value"] is None


def test_junit_maps_regressions_to_failures_and_incomplete_rows_to_skips() -> None:
    # [test->req~ring5.automation.machine-readable-regression~1]
    payload = RegressionResultExportService.export(_comparison(), "junit")
    suite = ET.fromstring(payload)

    assert suite.attrib == {
        "name": "RING-5 regression: main to change-42",
        "tests": "4",
        "failures": "1",
        "errors": "0",
        "skipped": "2",
    }
    suite_property_element = suite.find("properties")
    assert suite_property_element is not None
    suite_properties = {
        prop.attrib["name"]: prop.attrib["value"] for prop in suite_property_element
    }
    assert suite_properties == {
        "format": "ring5.regression-results",
        "schema_version": "1",
        "baseline_source": "main",
        "candidate_source": "change-42",
    }
    cases = suite.findall("testcase")
    assert cases[0].attrib["name"] == "ipc [benchmark=a]"
    assert cases[0].find("failure") is not None
    assert cases[1].find("failure") is None
    assert [case.find("skipped") is not None for case in cases] == [False, False, True, True]
    result_property_element = cases[0].find("properties")
    assert result_property_element is not None
    result_properties = {
        prop.attrib["name"]: prop.attrib["value"] for prop in result_property_element
    }
    assert result_properties["baseline_value"] == "100.0"
    assert result_properties["candidate_value"] == "90.0"
    assert result_properties["threshold"] == "5.0"
    assert result_properties["outcome"] == "regression"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda frame: frame.drop(columns="outcome"), "missing columns: outcome"),
        (lambda frame: frame.iloc[0:0], "at least one row"),
        (
            lambda frame: frame.assign(baseline_name=["main", "other", "main", "main"]),
            "one non-empty baseline_name",
        ),
        (lambda frame: frame.assign(metric=""), "invalid metric"),
        (lambda frame: frame.assign(direction="sideways"), "invalid direction"),
        (lambda frame: frame.assign(threshold_mode="ratio"), "invalid threshold mode"),
        (lambda frame: frame.assign(outcome="unknown"), "invalid outcome"),
        (lambda frame: frame.assign(threshold=-1.0), "invalid threshold"),
        (lambda frame: frame.assign(baseline_value="bad"), "invalid baseline_value"),
    ],
)
def test_invalid_comparison_results_are_rejected(mutate: object, message: str) -> None:
    invalid = mutate(_comparison())  # type: ignore[operator]

    with pytest.raises(ValueError, match=message):
        RegressionResultExportService.export(invalid, "json")


def test_invalid_format_and_input_type_are_rejected() -> None:
    with pytest.raises(ValueError, match="json.*junit"):
        RegressionResultExportService.export(_comparison(), "csv")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="pandas DataFrame"):
        RegressionResultExportService.export([], "json")  # type: ignore[arg-type]
