"""Observable predicate behavior and rejection of ambiguous configurations."""

import pandas as pd
import pytest

from src.core.common.security_limits import MAX_SEARCH_TERM_LENGTH
from src.core.services.shapers.impl.selector_algorithms.condition_selector import ConditionSelector


class TestConditionSelectorModes:
    # [test->req~ring5.shaping.condition-selector~1]
    """Each predicate has one explicit representation and preserves input data."""

    @pytest.mark.parametrize(
        ("mode", "operand", "expected"),
        [
            ("greater_than", {"threshold": 20}, [30]),
            ("less_than", {"threshold": 20}, [10]),
            ("greater_or_equal", {"threshold": 20}, [20, 30]),
            ("less_or_equal", {"threshold": 20}, [10, 20]),
            ("equals", {"value": 20}, [20]),
            ("not_equals", {"value": 20}, [10, 30]),
            ("range", {"range": [10, 20]}, [10, 20]),
            ("in", {"values": [10, 30]}, [10, 30]),
            ("in", {"values": []}, []),
        ],
    )
    def test_numeric_predicate(self, mode, operand, expected) -> None:
        data = pd.DataFrame({"x": [10, 20, 30]}, index=[4, 5, 6])
        before = data.copy(deep=True)
        result = ConditionSelector({"column": "x", "mode": mode, **operand})(data)
        assert result["x"].tolist() == expected
        pd.testing.assert_frame_equal(data, before)
        if not result.empty:
            result.iloc[0, 0] = 99
            pd.testing.assert_frame_equal(data, before)

    def test_contains_uses_literal_text(self) -> None:
        data = pd.DataFrame({"name": ["value[0]", "value0", None]})
        result = ConditionSelector({"column": "name", "mode": "contains", "value": "["})(data)
        assert result["name"].tolist() == ["value[0]"]

    @pytest.mark.parametrize("quoted", ["'beta'", '"beta"'])
    def test_equality_preserves_literal_quotes(self, quoted: str) -> None:
        data = pd.DataFrame({"name": ["beta", quoted]})
        result = ConditionSelector({"column": "name", "mode": "equals", "value": quoted})(data)
        assert result["name"].tolist() == [quoted]

    def test_membership_preserves_explicit_missing_selection(self) -> None:
        data = pd.DataFrame({"name": ["beta", None]})
        result = ConditionSelector({"column": "name", "mode": "in", "values": [None]})(data)
        assert len(result) == 1
        assert result["name"].isna().all()


class TestConditionSelectorValidation:
    """Invalid predicates fail before they can act as an identity transformation."""

    @pytest.mark.parametrize(
        "config",
        [
            {},
            {"mode": "undefined"},
            {"mode": "legacy", "condition": ">", "value": 1},
            {"condition": ">", "value": 1},
            {"operator": ">", "value": 1},
            {"values": [1]},
            {"range": [0, 1]},
            {"mode": "greater_than"},
            {"mode": "equals"},
            {"mode": "contains"},
            {"mode": "in", "values": "one"},
            {"mode": "in", "values": [{"name": "one"}]},
            {"mode": "equals", "value": [1, 2]},
            {"mode": "range", "range": [1]},
            {"mode": "range", "range": [2, 1]},
            {"mode": "range", "range": [0, float("nan")]},
            {"mode": "range", "range": [False, 1]},
            {"mode": "greater_than", "threshold": float("inf")},
            {"mode": "greater_than", "threshold": 10**1000},
            {"mode": "greater_than", "threshold": True},
            {"mode": "equals", "value": None},
            {"mode": "contains", "value": 1},
            {"mode": "contains", "value": "x" * (MAX_SEARCH_TERM_LENGTH + 1)},
            {"mode": "in", "values": [1], "range": [0, 2]},
            {"mode": "range", "range": [0, 2], "threshold": None},
            {"mode": "equals", "value": 1, "condition": "=="},
        ],
    )
    def test_invalid_predicate_is_rejected(self, config) -> None:
        with pytest.raises((TypeError, ValueError)):
            ConditionSelector({"column": "x", **config})
