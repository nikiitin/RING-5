"""
Unit tests for enhanced DataProcessingService.

Tests new merge_columns method and validation functions.
"""

import numpy as np
import pandas as pd
import pytest

from src.web.services.data_processing_service import DataProcessingService


class TestMergeColumns:
    """Test merge_columns method."""

    def test_merge_sum(self) -> None:
        """Test merging columns with Sum operation."""
        data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = DataProcessingService.merge_columns(data, ["a", "b"], "Sum", "total")
        assert "total" in result.columns
        assert result["total"].tolist() == [5, 7, 9]

    def test_merge_mean(self) -> None:
        """Test merging columns with Mean operation."""
        data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = DataProcessingService.merge_columns(data, ["a", "b"], "Mean", "avg")
        assert "avg" in result.columns
        assert result["avg"].tolist() == [2.5, 3.5, 4.5]

    def test_merge_concatenate(self) -> None:
        """Test merging columns with Concatenate operation."""
        data = pd.DataFrame({"a": ["x", "y", "z"], "b": ["1", "2", "3"]})
        result = DataProcessingService.merge_columns(
            data, ["a", "b"], "Concatenate", "combined", separator="-"
        )
        assert "combined" in result.columns
        assert result["combined"].tolist() == ["x-1", "y-2", "z-3"]

    def test_merge_with_sd_propagation_sum(self) -> None:
        """Test SD propagation for Sum operation."""
        data = pd.DataFrame(
            {"a": [10, 20, 30], "a.sd": [1, 2, 3], "b": [5, 10, 15], "b.sd": [0.5, 1.0, 1.5]}
        )
        result = DataProcessingService.merge_columns(data, ["a", "b"], "Sum", "total")
        assert "total" in result.columns
        assert "total.sd" in result.columns
        # SD for sum: sqrt(sd1^2 + sd2^2)
        expected_sd = np.sqrt(np.array([1, 2, 3]) ** 2 + np.array([0.5, 1.0, 1.5]) ** 2)
        np.testing.assert_array_almost_equal(result["total.sd"].values, expected_sd)

    def test_merge_with_sd_propagation_mean(self) -> None:
        """Test SD propagation for Mean operation."""
        data = pd.DataFrame(
            {"a": [10, 20, 30], "a.sd": [2, 4, 6], "b": [10, 20, 30], "b.sd": [2, 4, 6]}
        )
        result = DataProcessingService.merge_columns(data, ["a", "b"], "Mean", "avg")
        assert "avg" in result.columns
        assert "avg.sd" in result.columns
        # SD for mean: sqrt(sd1^2 + sd2^2) / n
        expected_sd = np.sqrt(np.array([2, 4, 6]) ** 2 + np.array([2, 4, 6]) ** 2) / 2
        np.testing.assert_array_almost_equal(result["avg.sd"].values, expected_sd)

    def test_merge_preserves_original_columns(self) -> None:
        """Test that merge preserves original columns."""
        data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = DataProcessingService.merge_columns(data, ["a", "b"], "Sum", "total")
        assert "a" in result.columns
        assert "b" in result.columns
        assert result["a"].tolist() == [1, 2, 3]


class TestValidateMergeInputs:
    """Test merge_columns validation."""

    def test_validate_valid_inputs(self) -> None:
        """Test validation passes for valid inputs."""
        data = pd.DataFrame({"a": [1], "b": [2]})
        errors = DataProcessingService.validate_merge_inputs(data, ["a", "b"], "Sum", "total")
        assert len(errors) == 0

    def test_validate_no_columns(self) -> None:
        """Test validation fails when no columns selected."""
        data = pd.DataFrame({"a": [1], "b": [2]})
        errors = DataProcessingService.validate_merge_inputs(data, [], "Sum", "total")
        assert len(errors) >= 1
        assert any("at least one column" in e.lower() for e in errors)

    def test_validate_single_column(self) -> None:
        """Test validation fails when only one column selected."""
        data = pd.DataFrame({"a": [1], "b": [2]})
        errors = DataProcessingService.validate_merge_inputs(data, ["a"], "Sum", "total")
        assert len(errors) >= 1
        assert any("at least two columns" in e.lower() for e in errors)

    def test_validate_missing_columns(self) -> None:
        """Test validation fails when columns don't exist."""
        data = pd.DataFrame({"a": [1], "b": [2]})
        errors = DataProcessingService.validate_merge_inputs(data, ["a", "c"], "Sum", "total")
        assert len(errors) >= 1
        assert any("not found" in e.lower() and "c" in e for e in errors)

    def test_validate_invalid_operation(self) -> None:
        """Test validation fails for invalid operation."""
        data = pd.DataFrame({"a": [1], "b": [2]})
        errors = DataProcessingService.validate_merge_inputs(data, ["a", "b"], "Invalid", "total")
        assert len(errors) >= 1
        assert any("invalid operation" in e.lower() for e in errors)

    def test_validate_empty_column_name(self) -> None:
        """Test validation fails when new column name is empty."""
        data = pd.DataFrame({"a": [1], "b": [2]})
        errors = DataProcessingService.validate_merge_inputs(data, ["a", "b"], "Sum", "")
        assert len(errors) >= 1
        assert any("cannot be empty" in e.lower() for e in errors)

    def test_validate_duplicate_column_name(self) -> None:
        """Test validation fails when new column already exists."""
        data = pd.DataFrame({"a": [1], "b": [2]})
        errors = DataProcessingService.validate_merge_inputs(data, ["a", "b"], "Sum", "a")
        assert len(errors) >= 1
        assert any("already exists" in e.lower() for e in errors)


class TestValidateOutlierInputs:
    """Test outlier removal validation."""

    def test_validate_valid_inputs(self) -> None:
        """Test validation passes for valid inputs."""
        data = pd.DataFrame({"val": [1.0, 2.0, 100.0], "group": ["A", "A", "A"]})
        errors = DataProcessingService.validate_outlier_inputs(data, "val", ["group"])
        assert len(errors) == 0

    def test_validate_no_outlier_column(self) -> None:
        """Test validation fails when outlier column not specified."""
        data = pd.DataFrame({"val": [1.0, 2.0, 3.0]})
        errors = DataProcessingService.validate_outlier_inputs(data, "", [])
        assert len(errors) >= 1
        assert any("must be specified" in e.lower() for e in errors)

    def test_validate_outlier_column_not_found(self) -> None:
        """Test validation fails when outlier column doesn't exist."""
        data = pd.DataFrame({"val": [1.0, 2.0, 3.0]})
        errors = DataProcessingService.validate_outlier_inputs(data, "missing", [])
        assert len(errors) >= 1
        assert any("not found" in e.lower() for e in errors)

    def test_validate_outlier_column_not_numeric(self) -> None:
        """Test validation fails when outlier column is not numeric."""
        data = pd.DataFrame({"val": ["a", "b", "c"]})
        errors = DataProcessingService.validate_outlier_inputs(data, "val", [])
        assert len(errors) >= 1
        assert any("must be numeric" in e.lower() for e in errors)

    def test_validate_group_by_columns_not_found(self) -> None:
        """Test validation fails when group by columns don't exist."""
        data = pd.DataFrame({"val": [1.0, 2.0, 3.0]})
        errors = DataProcessingService.validate_outlier_inputs(data, "val", ["missing"])
        assert len(errors) >= 1
        assert any("group by" in e.lower() and "not found" in e.lower() for e in errors)

    def test_validate_empty_group_by_allowed(self) -> None:
        """Test validation passes when group by is empty (global outlier removal)."""
        data = pd.DataFrame({"val": [1.0, 2.0, 3.0]})
        errors = DataProcessingService.validate_outlier_inputs(data, "val", [])
        assert len(errors) == 0


class TestValidateSeedsReducerInputs:
    """Test seeds reducer validation."""

    def test_validate_valid_inputs(self) -> None:
        """Test validation passes for valid inputs."""
        data = pd.DataFrame({"bench": ["A", "A", "B"], "value": [1.0, 2.0, 3.0], "seed": [1, 2, 1]})
        errors = DataProcessingService.validate_seeds_reducer_inputs(data, ["bench"], ["value"])
        assert len(errors) == 0

    def test_validate_no_categorical_columns(self) -> None:
        """Test validation fails when no categorical columns selected."""
        data = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
        errors = DataProcessingService.validate_seeds_reducer_inputs(data, [], ["value"])
        assert len(errors) >= 1
        assert any("categorical" in e.lower() for e in errors)

    def test_validate_no_statistic_columns(self) -> None:
        """Test validation fails when no statistic columns selected."""
        data = pd.DataFrame({"bench": ["A", "B", "C"]})
        errors = DataProcessingService.validate_seeds_reducer_inputs(data, ["bench"], [])
        assert len(errors) >= 1
        assert any("statistic" in e.lower() for e in errors)

    def test_validate_categorical_columns_not_found(self) -> None:
        """Test validation fails when categorical columns don't exist."""
        data = pd.DataFrame({"bench": ["A", "B"], "value": [1.0, 2.0]})
        errors = DataProcessingService.validate_seeds_reducer_inputs(data, ["missing"], ["value"])
        assert len(errors) >= 1
        assert any("categorical" in e.lower() and "not found" in e.lower() for e in errors)

    def test_validate_statistic_columns_not_found(self) -> None:
        """Test validation fails when statistic columns don't exist."""
        data = pd.DataFrame({"bench": ["A", "B"], "value": [1.0, 2.0]})
        errors = DataProcessingService.validate_seeds_reducer_inputs(data, ["bench"], ["missing"])
        assert len(errors) >= 1
        assert any("statistic" in e.lower() and "not found" in e.lower() for e in errors)

    def test_validate_statistic_column_not_numeric(self) -> None:
        """Test validation fails when statistic column is not numeric."""
        data = pd.DataFrame({"bench": ["A", "B"], "value": ["x", "y"]})
        errors = DataProcessingService.validate_seeds_reducer_inputs(data, ["bench"], ["value"])
        assert len(errors) >= 1
        assert any("must be numeric" in e.lower() for e in errors)


class TestExistingFunctionality:
    """Test that existing DataProcessingService functionality still works."""

    def test_reduce_seeds(self) -> None:
        """Test reduce_seeds still works."""
        data = pd.DataFrame(
            {"benchmark": ["A", "A", "B", "B"], "seed": [1, 2, 1, 2], "ipc": [1.0, 1.2, 2.0, 2.2]}
        )
        result = DataProcessingService.reduce_seeds(data, ["benchmark"], ["ipc"])
        assert len(result) == 2
        assert "ipc.sd" in result.columns

    def test_remove_outliers(self) -> None:
        """Test remove_outliers still works."""
        data = pd.DataFrame({"group": ["A", "A", "A", "A"], "value": [1.0, 2.0, 3.0, 100.0]})
        result = DataProcessingService.remove_outliers(data, "value", ["group"])
        assert len(result) < len(data)

    def test_apply_mixer(self) -> None:
        """Test apply_mixer still works."""
        data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = DataProcessingService.apply_mixer(data, "total", ["a", "b"], "Sum")
        assert "total" in result.columns
        assert result["total"].tolist() == [5, 7, 9]

    def test_apply_operation(self) -> None:
        """Test apply_operation still works."""
        data = pd.DataFrame({"a": [10, 20, 30], "b": [2, 4, 5]})
        result = DataProcessingService.apply_operation(data, "Division", "a", "b", "result")
        assert "result" in result.columns
        assert result["result"].tolist() == [5.0, 5.0, 6.0]
