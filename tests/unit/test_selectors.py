"""
Comprehensive tests for selector algorithms.
Tests ColumnSelector, ConditionSelector, and ItemSelector.
"""

from typing import Any

import pandas as pd
import pytest
from pandas import DataFrame

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
def sample_dataframe() -> DataFrame:
    """Create a sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "system_id": ["S1", "S1", "S2", "S2", "S3", "S3"],
            "benchmark": ["B1", "B2", "B1", "B2", "B1", "B2"],
            "throughput": [100.0, 105.0, 80.0, 82.0, 90.0, 95.0],
            "latency": [1.2, 1.1, 2.0, 1.9, 1.8, 1.7],
            "config": ["A1", "A2", "B1", "B2", "C1", "C2"],
        }
    )


class TestColumnSelector:
    """Tests for ColumnSelector."""

    def test_select_single_column(self, sample_dataframe: Any) -> None:
        """Test selecting a single column."""
        selector = ColumnSelector({"columns": ["throughput"]})
        result = selector(sample_dataframe)

        assert len(result.columns) == 1
        assert "throughput" in result.columns
        assert len(result) == 6

    def test_select_multiple_columns(self, sample_dataframe: Any) -> None:
        """Test selecting multiple columns."""
        # [test->req~ring5.shaping.column-selector~1]
        selector = ColumnSelector({"columns": ["system_id", "throughput", "latency"]})
        result = selector(sample_dataframe)

        assert len(result.columns) == 3
        assert "system_id" in result.columns
        assert "throughput" in result.columns
        assert "latency" in result.columns

    def test_select_all_columns(self, sample_dataframe: Any) -> None:
        """Test selecting all columns."""
        all_cols = list(sample_dataframe.columns)
        selector = ColumnSelector({"columns": all_cols})
        result = selector(sample_dataframe)

        assert len(result.columns) == len(all_cols)

    def test_column_order_preserved(self, sample_dataframe: Any) -> None:
        """Test that column order is preserved."""
        # [test->req~ring5.shaping.column-selector~1]
        columns = ["latency", "throughput", "system_id"]
        selector = ColumnSelector({"columns": columns})
        result = selector(sample_dataframe)

        assert list(result.columns) == columns

    def test_missing_column_error(self, sample_dataframe: Any) -> None:
        """Test error for missing column."""
        selector = ColumnSelector({"columns": ["nonexistent"]})
        with pytest.raises(ValueError, match="not found"):
            selector(sample_dataframe)

    def test_invalid_columns_type_error(self) -> None:
        """Test that non-list columns raises error."""
        with pytest.raises(TypeError):
            ColumnSelector({"columns": "throughput"})


class TestConditionSelector:
    """Tests for ConditionSelector."""

    def test_greater_than_mode(self, sample_dataframe: Any) -> None:
        """Test greater_than mode."""
        selector = ConditionSelector(
            {"column": "throughput", "mode": "greater_than", "threshold": 90}
        )
        result = selector(sample_dataframe)

        assert len(result) == 3  # 100, 105, 95
        assert all(result["throughput"] > 90)

    def test_less_than_mode(self, sample_dataframe: Any) -> None:
        """Test less_than mode."""
        selector = ConditionSelector({"column": "throughput", "mode": "less_than", "threshold": 90})
        result = selector(sample_dataframe)

        assert len(result) == 2  # 80, 82
        assert all(result["throughput"] < 90)

    def test_equals_mode_numeric(self, sample_dataframe: Any) -> None:
        """Test equals mode with numeric value."""
        selector = ConditionSelector({"column": "throughput", "mode": "equals", "value": 100.0})
        result = selector(sample_dataframe)

        assert len(result) == 1
        assert result["throughput"].iloc[0] == 100.0

    def test_values_list_filter(self, sample_dataframe: Any) -> None:
        """Test filtering with list of values."""
        selector = ConditionSelector({"column": "system_id", "values": ["S1", "S3"]})
        result = selector(sample_dataframe)

        assert len(result) == 4
        assert set(result["system_id"].unique()) == {"S1", "S3"}

    def test_range_filter(self, sample_dataframe: Any) -> None:
        """Test range filter."""
        selector = ConditionSelector({"column": "throughput", "range": [85.0, 100.0]})
        result = selector(sample_dataframe)

        # Should include 90, 95, 100
        assert len(result) == 3
        assert all((result["throughput"] >= 85) & (result["throughput"] <= 100))

    def test_legacy_condition_greater_equal(self, sample_dataframe: Any) -> None:
        """Test legacy condition with >=."""
        selector = ConditionSelector({"column": "throughput", "condition": ">=", "value": 100.0})
        result = selector(sample_dataframe)

        assert len(result) == 2  # 100, 105
        assert all(result["throughput"] >= 100)

    def test_legacy_condition_not_equal_quoted(self, sample_dataframe: Any) -> None:
        """Test legacy condition with != and quotes."""
        selector = ConditionSelector({"column": "system_id", "condition": "!=", "value": "'S1'"})
        result = selector(sample_dataframe)

        assert "S1" not in result["system_id"].values
        assert len(result) == 4

    def test_contains_mode(self, sample_dataframe: Any) -> None:
        """Test explicit contains mode."""
        selector = ConditionSelector({"column": "config", "mode": "contains", "value": "A"})
        result = selector(sample_dataframe)
        assert len(result) == 2
        assert all(result["config"].str.startswith("A"))


class TestItemSelector:
    """Tests for ItemSelector."""

    def test_select_single_item(self, sample_dataframe: Any) -> None:
        """Test selecting rows matching a single string."""
        selector = ItemSelector({"column": "system_id", "strings": ["S1"]})
        result = selector(sample_dataframe)

        assert len(result) == 2
        assert all(result["system_id"] == "S1")

    def test_select_multiple_items(self, sample_dataframe: Any) -> None:
        """Test selecting rows matching multiple strings."""
        # [test->req~ring5.shaping.item-selector~1]
        selector = ItemSelector({"column": "system_id", "strings": ["S1", "S2"]})
        result = selector(sample_dataframe)

        assert len(result) == 4
        assert set(result["system_id"].unique()) == {"S1", "S2"}

    def test_partial_match_contains_mode(self, sample_dataframe: Any) -> None:
        """Test partial string matching using mode='contains'."""
        # [test->req~ring5.shaping.item-selector~1]
        selector = ItemSelector({"column": "config", "strings": ["A"], "mode": "contains"})
        result = selector(sample_dataframe)

        assert len(result) == 2
        assert all(result["config"].str.contains("A"))

    def test_no_match_warning(self, sample_dataframe: Any, caplog: Any) -> None:
        """Test warning log when no items match."""
        selector = ItemSelector({"column": "system_id", "strings": ["nonexistent"]})
        result = selector(sample_dataframe)

        assert result.empty
        assert "None of the strings" in caplog.text

    def test_missing_column_parameter(self) -> None:
        """Test missing column parameter."""
        with pytest.raises(ValueError, match="column"):
            ItemSelector({"strings": ["S1"]})


class TestSelectorIntegration:
    """Integration tests using selectors together."""

    def test_chain_column_then_condition(self, sample_dataframe: Any) -> None:
        """Test chaining ColumnSelector then ConditionSelector."""
        col_selector = ColumnSelector({"columns": ["system_id", "throughput"]})
        df1 = col_selector(sample_dataframe)

        cond_selector = ConditionSelector(
            {"column": "throughput", "mode": "greater_than", "threshold": 90}
        )
        df2 = cond_selector(df1)

        assert len(df2.columns) == 2
        assert all(df2["throughput"] > 90)
