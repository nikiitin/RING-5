"""Tests for selector algorithms.

Verify DataFrame return types after pd.DataFrame() wrapper removal.
"""

import pandas as pd
import pytest

from src.core.services.shapers.impl.selector_algorithms.column_selector import (
    ColumnSelector,
)
from src.core.services.shapers.impl.selector_algorithms.condition_selector import (
    ConditionSelector,
)
from src.core.services.shapers.impl.selector_algorithms.item_selector import (
    ItemSelector,
)


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create a sample DataFrame for selector tests."""
    return pd.DataFrame(
        {
            "name": ["alpha", "beta", "gamma", "delta", "epsilon"],
            "score": [10, 25, 50, 75, 90],
            "category": ["A", "B", "A", "C", "B"],
        }
    )


class TestConditionSelector:
    """Tests for ConditionSelector with various filter modes."""

    def test_condition_selector_isin_returns_dataframe(
        self, sample_dataframe: pd.DataFrame
    ) -> None:
        """Values-based selection using 'values' parameter returns a DataFrame."""
        selector = ConditionSelector({"column": "category", "values": ["A", "C"]})
        result = selector(sample_dataframe)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert set(result["category"]) == {"A", "C"}

    def test_condition_selector_range_returns_dataframe(
        self, sample_dataframe: pd.DataFrame
    ) -> None:
        """Numeric range selection returns a DataFrame with rows within [min, max]."""
        selector = ConditionSelector({"column": "score", "range": [20, 80]})
        result = selector(sample_dataframe)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert all(20 <= v <= 80 for v in result["score"])

    def test_condition_selector_greater_than_returns_dataframe(
        self, sample_dataframe: pd.DataFrame
    ) -> None:
        """Greater-than mode returns a DataFrame with rows above the threshold."""
        selector = ConditionSelector({"column": "score", "mode": "greater_than", "threshold": 50})
        result = selector(sample_dataframe)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert all(v > 50 for v in result["score"])

    def test_condition_selector_less_than_returns_dataframe(
        self, sample_dataframe: pd.DataFrame
    ) -> None:
        """Less-than mode returns a DataFrame with rows below the threshold."""
        selector = ConditionSelector({"column": "score", "mode": "less_than", "threshold": 50})
        result = selector(sample_dataframe)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert all(v < 50 for v in result["score"])

    def test_condition_selector_equals_returns_dataframe(
        self, sample_dataframe: pd.DataFrame
    ) -> None:
        """Equals mode returns a DataFrame with rows matching the exact value."""
        selector = ConditionSelector({"column": "score", "mode": "equals", "value": 50})
        result = selector(sample_dataframe)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["score"] == 50

    def test_condition_selector_contains_returns_dataframe(
        self, sample_dataframe: pd.DataFrame
    ) -> None:
        """Contains mode returns a DataFrame with rows whose column value contains the substring."""
        selector = ConditionSelector({"column": "name", "mode": "contains", "value": "ta"})
        result = selector(sample_dataframe)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert set(result["name"]) == {"beta", "delta"}


class TestItemSelector:
    """Tests for ItemSelector with exact and contains modes."""

    def test_item_selector_exact_returns_dataframe(self, sample_dataframe: pd.DataFrame) -> None:
        """Exact match mode returns a DataFrame with only matching rows."""
        selector = ItemSelector({"column": "name", "strings": ["alpha", "gamma"]})
        result = selector(sample_dataframe)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert set(result["name"]) == {"alpha", "gamma"}

    def test_item_selector_contains_returns_dataframe(self, sample_dataframe: pd.DataFrame) -> None:
        """Contains mode returns a DataFrame with rows matching substring patterns."""
        selector = ItemSelector({"column": "name", "strings": ["alph", "gamm"], "mode": "contains"})
        result = selector(sample_dataframe)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert set(result["name"]) == {"alpha", "gamma"}


class TestColumnSelector:
    """Tests for ColumnSelector column subsetting."""

    def test_column_selector_returns_dataframe(self, sample_dataframe: pd.DataFrame) -> None:
        """Column subsetting returns a DataFrame with only the specified columns."""
        selector = ColumnSelector({"columns": ["name", "score"]})
        result = selector(sample_dataframe)

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["name", "score"]
        assert len(result) == 5
        assert result["name"].tolist() == ["alpha", "beta", "gamma", "delta", "epsilon"]
        assert result["score"].tolist() == [10, 25, 50, 75, 90]
