"""
Comprehensive tests for selector algorithms.
Tests ColumnSelector, ConditionSelector, and ItemSelector.
"""

import pytest
import pandas as pd
import numpy as np

from src.web.services.shapers.impl.selector_algorithms.columnSelector import ColumnSelector
from src.web.services.shapers.impl.selector_algorithms.conditionSelector import ConditionSelector
from src.web.services.shapers.impl.selector_algorithms.itemSelector import ItemSelector


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        "system_id": ["S1", "S1", "S2", "S2", "S3", "S3"],
        "benchmark": ["B1", "B2", "B1", "B2", "B1", "B2"],
        "throughput": [100, 105, 80, 82, 90, 95],
        "latency": [1.2, 1.1, 2.0, 1.9, 1.8, 1.7],
        "config": ["A1", "A2", "B1", "B2", "C1", "C2"],
    })


class TestColumnSelector:
    """Tests for ColumnSelector."""

    def test_select_single_column(self, sample_dataframe):
        """Test selecting a single column."""
        selector = ColumnSelector({"columns": ["throughput"]})
        result = selector(sample_dataframe)
        
        assert len(result.columns) == 1
        assert "throughput" in result.columns
        assert len(result) == 6

    def test_select_multiple_columns(self, sample_dataframe):
        """Test selecting multiple columns."""
        selector = ColumnSelector({"columns": ["system_id", "throughput", "latency"]})
        result = selector(sample_dataframe)
        
        assert len(result.columns) == 3
        assert "system_id" in result.columns
        assert "throughput" in result.columns
        assert "latency" in result.columns

    def test_select_all_columns(self, sample_dataframe):
        """Test selecting all columns."""
        all_cols = list(sample_dataframe.columns)
        selector = ColumnSelector({"columns": all_cols})
        result = selector(sample_dataframe)
        
        assert len(result.columns) == len(all_cols)

    def test_column_order_preserved(self, sample_dataframe):
        """Test that column order is preserved."""
        columns = ["latency", "throughput", "system_id"]
        selector = ColumnSelector({"columns": columns})
        result = selector(sample_dataframe)
        
        assert list(result.columns) == columns

    def test_missing_column_precondition(self, sample_dataframe, capsys):
        """Test warning for missing column in preconditions."""
        selector = ColumnSelector({"columns": ["nonexistent"]})
        verified = selector._verifyPreconditions(sample_dataframe)
        
        captured = capsys.readouterr()
        assert "does not exist" in captured.out
        assert verified is False

    def test_empty_columns_list_error(self):
        """Test that empty string in columns raises error."""
        with pytest.raises(ValueError, match="empty strings"):
            ColumnSelector({"columns": ["valid", ""]})

    def test_invalid_columns_type_error(self):
        """Test that non-list columns raises error."""
        with pytest.raises(Exception):
            ColumnSelector({"columns": "throughput"})


class TestConditionSelector:
    """Tests for ConditionSelector."""

    def test_greater_than_mode(self, sample_dataframe):
        """Test greater_than mode."""
        selector = ConditionSelector({
            "column": "throughput",
            "mode": "greater_than",
            "threshold": 90
        })
        result = selector(sample_dataframe)
        
        assert len(result) == 3  # 100, 105, 95
        assert all(result["throughput"] > 90)

    def test_less_than_mode(self, sample_dataframe):
        """Test less_than mode."""
        selector = ConditionSelector({
            "column": "throughput",
            "mode": "less_than",
            "threshold": 90
        })
        result = selector(sample_dataframe)
        
        assert len(result) == 2  # 80, 82
        assert all(result["throughput"] < 90)

    def test_equals_mode_numeric(self, sample_dataframe):
        """Test equals mode with numeric value."""
        selector = ConditionSelector({
            "column": "throughput",
            "mode": "equals",
            "value": 100
        })
        result = selector(sample_dataframe)
        
        assert len(result) == 1
        assert result["throughput"].iloc[0] == 100

    def test_values_list_filter(self, sample_dataframe):
        """Test filtering with list of values."""
        selector = ConditionSelector({
            "column": "system_id",
            "values": ["S1", "S3"]
        })
        result = selector(sample_dataframe)
        
        assert len(result) == 4
        assert set(result["system_id"].unique()) == {"S1", "S3"}

    def test_range_filter(self, sample_dataframe):
        """Test range filter."""
        selector = ConditionSelector({
            "column": "throughput",
            "range": [85, 100]
        })
        result = selector(sample_dataframe)
        
        # Should include 90, 95, 100
        assert len(result) == 3
        assert all((result["throughput"] >= 85) & (result["throughput"] <= 100))

    def test_legacy_condition_greater_equal(self, sample_dataframe):
        """Test legacy condition with >=."""
        selector = ConditionSelector({
            "column": "throughput",
            "condition": ">=",
            "value": 100
        })
        result = selector(sample_dataframe)
        
        assert len(result) == 2  # 100, 105
        assert all(result["throughput"] >= 100)

    def test_legacy_condition_less_equal(self, sample_dataframe):
        """Test legacy condition with <=."""
        selector = ConditionSelector({
            "column": "latency",
            "condition": "<=",
            "value": 1.5
        })
        result = selector(sample_dataframe)
        
        assert all(result["latency"] <= 1.5)

    def test_legacy_condition_not_equal(self, sample_dataframe):
        """Test legacy condition with !=."""
        selector = ConditionSelector({
            "column": "system_id",
            "condition": "!=",
            "value": "'S1'"
        })
        result = selector(sample_dataframe)
        
        assert "S1" not in result["system_id"].values

    def test_invalid_condition_error(self):
        """Test invalid condition raises error during construction."""
        with pytest.raises(ValueError, match="condition"):
            ConditionSelector({
                "column": "throughput",
                "condition": ">>",  # Invalid
                "value": 100
            })

    def test_missing_threshold_for_greater_than(self):
        """Test missing threshold for greater_than mode raises during construction."""
        with pytest.raises(ValueError, match="threshold"):
            ConditionSelector({
                "column": "throughput",
                "mode": "greater_than"
                # Missing threshold
            })

    def test_invalid_range_format(self):
        """Test invalid range format raises during construction."""
        with pytest.raises(ValueError, match="range"):
            ConditionSelector({
                "column": "throughput",
                "range": [1, 2, 3]  # Should be 2 elements
            })


class TestItemSelector:
    """Tests for ItemSelector."""

    def test_select_single_item(self, sample_dataframe):
        """Test selecting rows matching a single string."""
        selector = ItemSelector({
            "column": "system_id",
            "strings": ["S1"]
        })
        result = selector(sample_dataframe)
        
        assert len(result) == 2
        assert all(result["system_id"] == "S1")

    def test_select_multiple_items(self, sample_dataframe):
        """Test selecting rows matching multiple strings."""
        selector = ItemSelector({
            "column": "system_id",
            "strings": ["S1", "S2"]
        })
        result = selector(sample_dataframe)
        
        assert len(result) == 4
        assert set(result["system_id"].unique()) == {"S1", "S2"}

    def test_partial_match(self, sample_dataframe):
        """Test partial string matching."""
        selector = ItemSelector({
            "column": "config",
            "strings": ["A"]  # Should match A1, A2
        })
        result = selector(sample_dataframe)
        
        assert len(result) == 2
        assert all(result["config"].str.contains("A"))

    def test_no_match_warning(self, sample_dataframe, capsys):
        """Test warning when no items match."""
        selector = ItemSelector({
            "column": "system_id",
            "strings": ["nonexistent"]
        })
        selector._verifyPreconditions(sample_dataframe)
        
        captured = capsys.readouterr()
        assert "not present" in captured.out

    def test_empty_strings_list(self):
        """Test initialization with empty strings list - matches all (regex quirk)."""
        selector = ItemSelector({
            "column": "system_id",
            "strings": []
        })
        # Empty pattern matches everything in regex
        result = selector(pd.DataFrame({"system_id": ["S1"]}))
        # Note: Empty join creates pattern that matches all rows
        assert len(result) == 1  # Quirk: empty pattern matches all

    def test_missing_column_parameter(self):
        """Test missing column parameter."""
        with pytest.raises(Exception):
            ItemSelector({"strings": ["S1"]})

    def test_missing_strings_parameter(self):
        """Test missing strings parameter."""
        with pytest.raises(Exception):
            ItemSelector({"column": "system_id"})

    def test_case_sensitive_matching(self, sample_dataframe):
        """Test that matching is case-sensitive and stops if no match."""
        selector = ItemSelector({
            "column": "system_id",
            "strings": ["s1"]  # lowercase
        })
        # Preconditions fail because no match found, raises ValueError
        with pytest.raises(ValueError):
            selector(sample_dataframe)


class TestSelectorIntegration:
    """Integration tests using selectors together."""

    def test_chain_column_then_condition(self, sample_dataframe):
        """Test chaining ColumnSelector then ConditionSelector."""
        # First select columns
        col_selector = ColumnSelector({
            "columns": ["system_id", "throughput"]
        })
        df1 = col_selector(sample_dataframe)
        
        # Then filter rows
        cond_selector = ConditionSelector({
            "column": "throughput",
            "mode": "greater_than",
            "threshold": 90
        })
        df2 = cond_selector(df1)
        
        assert len(df2.columns) == 2
        assert all(df2["throughput"] > 90)

    def test_chain_item_then_condition(self, sample_dataframe):
        """Test chaining ItemSelector then ConditionSelector."""
        # First select by system_id
        item_selector = ItemSelector({
            "column": "system_id",
            "strings": ["S1", "S2"]
        })
        df1 = item_selector(sample_dataframe)
        
        # Then filter by throughput
        cond_selector = ConditionSelector({
            "column": "throughput",
            "mode": "greater_than",
            "threshold": 95
        })
        df2 = cond_selector(df1)
        
        assert len(df2) == 2  # 100, 105 from S1
        assert all(df2["system_id"] == "S1")
