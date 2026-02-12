"""Tests for ConditionSelector — 85% → 100% branch coverage."""

import pandas as pd
import pytest

from src.core.services.shapers.impl.selector_algorithms.condition_selector import (
    ConditionSelector,
)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "value": [10, 20, 30, 40, 50],
            "name": ["alpha", "beta", "gamma", "delta", "epsilon"],
        }
    )


class TestConditionSelectorModes:
    """Test all filter modes."""

    def test_greater_than(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector({"column": "value", "mode": "greater_than", "threshold": 25})
        result = sel(sample_data)
        assert list(result["value"]) == [30, 40, 50]

    def test_less_than(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector({"column": "value", "mode": "less_than", "threshold": 30})
        result = sel(sample_data)
        assert list(result["value"]) == [10, 20]

    def test_equals(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector({"column": "value", "mode": "equals", "value": 30})
        result = sel(sample_data)
        assert list(result["value"]) == [30]

    def test_contains(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector({"column": "name", "mode": "contains", "value": "eta"})
        result = sel(sample_data)
        assert list(result["name"]) == ["beta"]

    def test_values_isin(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector({"column": "name", "values": ["alpha", "gamma"]})
        result = sel(sample_data)
        assert list(result["name"]) == ["alpha", "gamma"]

    def test_range(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector({"column": "value", "range": [20, 40]})
        result = sel(sample_data)
        assert list(result["value"]) == [20, 30, 40]

    def test_legacy_operator_lt(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector(
            {"column": "value", "mode": "legacy", "condition": "<", "value": 25}
        )
        result = sel(sample_data)
        assert list(result["value"]) == [10, 20]

    def test_legacy_operator_gt(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector(
            {"column": "value", "mode": "legacy", "condition": ">", "value": 35}
        )
        result = sel(sample_data)
        assert list(result["value"]) == [40, 50]

    def test_legacy_operator_eq(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector(
            {"column": "value", "mode": "legacy", "condition": "==", "value": 20}
        )
        result = sel(sample_data)
        assert list(result["value"]) == [20]

    def test_legacy_operator_ne(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector(
            {"column": "value", "mode": "legacy", "condition": "!=", "value": 20}
        )
        result = sel(sample_data)
        assert list(result["value"]) == [10, 30, 40, 50]

    def test_legacy_operator_le(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector(
            {"column": "value", "mode": "legacy", "condition": "<=", "value": 30}
        )
        result = sel(sample_data)
        assert list(result["value"]) == [10, 20, 30]

    def test_legacy_operator_ge(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector(
            {"column": "value", "mode": "legacy", "condition": ">=", "value": 30}
        )
        result = sel(sample_data)
        assert list(result["value"]) == [30, 40, 50]

    def test_legacy_quoted_string_value(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector(
            {"column": "name", "mode": "legacy", "condition": "==", "value": "'beta'"}
        )
        result = sel(sample_data)
        assert list(result["name"]) == ["beta"]

    def test_legacy_double_quoted_value(self, sample_data: pd.DataFrame) -> None:
        sel = ConditionSelector(
            {"column": "name", "mode": "legacy", "condition": "==", "value": '"gamma"'}
        )
        result = sel(sample_data)
        assert list(result["name"]) == ["gamma"]

    def test_no_matching_mode_returns_original(self, sample_data: pd.DataFrame) -> None:
        """If no mode matches and no legacy condition, returns full DataFrame."""
        sel = ConditionSelector({"column": "value", "mode": "legacy"})
        result = sel(sample_data)
        assert len(result) == 5


class TestConditionSelectorValidation:
    """Test validation errors."""

    def test_values_not_list_raises(self) -> None:
        with pytest.raises(TypeError, match="must be a list"):
            ConditionSelector({"column": "x", "values": "not_a_list"})

    def test_range_not_two_elements_raises(self) -> None:
        with pytest.raises(ValueError, match="list of 2"):
            ConditionSelector({"column": "x", "range": [1]})

    def test_greater_than_no_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold"):
            ConditionSelector({"column": "x", "mode": "greater_than"})

    def test_equals_no_value_raises(self) -> None:
        with pytest.raises(ValueError, match="value"):
            ConditionSelector({"column": "x", "mode": "equals"})

    def test_contains_no_value_raises(self) -> None:
        with pytest.raises(ValueError, match="value"):
            ConditionSelector({"column": "x", "mode": "contains"})

    def test_invalid_legacy_operator_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid legacy operator"):
            ConditionSelector({"column": "x", "mode": "legacy", "condition": "~=", "value": 5})
