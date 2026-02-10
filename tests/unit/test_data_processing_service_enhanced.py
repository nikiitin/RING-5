"""
Unit tests for fragmented data processing services.
Replaces the old DataProcessingService tests with specific service validations.
"""

import numpy as np
import pandas as pd
import pytest

from src.core.services.managers.arithmetic_service import ArithmeticService
from src.core.services.managers.outlier_service import OutlierService
from src.core.services.managers.reduction_service import ReductionService


class TestArithmeticService:
    """Test ArithmeticService methods (formerly part of DataProcessingService)."""

    def test_merge_sum(self) -> None:
        """Test merging columns with Sum operation."""
        data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = ArithmeticService.merge_columns(data, ["a", "b"], "Sum", "total")
        assert "total" in result.columns
        assert result["total"].tolist() == [5, 7, 9]

    def test_merge_mean(self) -> None:
        """Test merging columns with Mean operation."""
        data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = ArithmeticService.merge_columns(data, ["a", "b"], "Mean", "avg")
        assert "avg" in result.columns
        assert result["avg"].tolist() == [2.5, 3.5, 4.5]

    def test_apply_operation(self) -> None:
        """Test apply_operation (basic arithmetic between two columns)."""
        data = pd.DataFrame({"a": [10, 20, 30], "b": [2, 4, 5]})
        result = ArithmeticService.apply_operation(data, "Division", "a", "b", "result")
        assert "result" in result.columns
        assert result["result"].tolist() == [5.0, 5.0, 6.0]

    def test_merge_with_sd_propagation_sum(self) -> None:
        """Test SD propagation for Sum operation."""
        data = pd.DataFrame(
            {"a": [10, 20, 30], "a.sd": [1, 2, 3], "b": [5, 10, 15], "b.sd": [0.5, 1.0, 1.5]}
        )
        result = ArithmeticService.merge_columns(data, ["a", "b"], "Sum", "total")
        assert "total.sd" in result.columns
        expected_sd = np.sqrt(np.array([1, 2, 3]) ** 2 + np.array([0.5, 1.0, 1.5]) ** 2)
        np.testing.assert_array_almost_equal(result["total.sd"].values, expected_sd)


class TestOutlierService:
    """Test OutlierService methods."""

    def test_remove_outliers(self) -> None:
        """Test removing outliers based on IQR."""
        data = pd.DataFrame(
            {
                "group": ["A", "A", "A", "A", "A"],
                "value": [1.0, 1.1, 1.2, 1.3, 100.0],  # 100 is an outlier
            }
        )
        result = OutlierService.remove_outliers(data, "value", ["group"])
        assert len(result) == 4
        assert not (result["value"] == 100.0).any()

    def test_validate_outlier_inputs_numeric(self) -> None:
        """Test validation fails for non-numeric columns."""
        data = pd.DataFrame({"val": ["a", "b", "c"]})
        errors = OutlierService.validate_outlier_inputs(data, "val", [])
        assert any("must be numeric" in e.lower() for e in errors)


class TestReductionService:
    """Test ReductionService methods (Seed reduction)."""

    def test_reduce_seeds(self) -> None:
        """Test aggregating seeds into mean/sd."""
        data = pd.DataFrame(
            {"benchmark": ["A", "A", "B", "B"], "seed": [1, 2, 1, 2], "ipc": [1.0, 1.2, 2.0, 2.2]}
        )
        result = ReductionService.reduce_seeds(data, ["benchmark"], ["ipc"])
        assert len(result) == 2
        assert "ipc" in result.columns
        assert "ipc.sd" in result.columns
        # Mean of [1.0, 1.2] is 1.1; Mean of [2.0, 2.2] is 2.1
        assert result[result["benchmark"] == "A"]["ipc"].iloc[0] == pytest.approx(1.1)
        assert result[result["benchmark"] == "B"]["ipc"].iloc[0] == pytest.approx(2.1)

    def test_validate_seeds_reducer_no_columns(self) -> None:
        """Test validation fails when no categorical columns provided."""
        data = pd.DataFrame({"ipc": [1.0, 1.2]})
        errors = ReductionService.validate_seeds_reducer_inputs(data, [], ["ipc"])
        assert any("categorical" in e.lower() for e in errors)
