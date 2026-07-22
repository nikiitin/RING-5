"""Tests for OutlierService — IQR-based outlier removal."""

import pandas as pd
import pytest

from src.core.services.managers.outlier_service import OutlierService


class TestRemoveOutliers:
    """Tests for OutlierService.remove_outliers."""

    def test_empty_dataframe_returns_empty(self) -> None:
        df = pd.DataFrame({"val": pd.Series([], dtype=float)})
        result = OutlierService.remove_outliers(df, "val", [])
        assert result.empty

    def test_column_not_in_df_raises(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        with pytest.raises(ValueError, match="'missing' not found"):
            OutlierService.remove_outliers(df, "missing", [])

    def test_non_numeric_column_raises(self) -> None:
        df = pd.DataFrame({"a": ["x", "y", "z"]})
        with pytest.raises(ValueError, match="must be numeric"):
            OutlierService.remove_outliers(df, "a", [])

    def test_missing_group_by_column_raises(self) -> None:
        df = pd.DataFrame({"val": [1.0, 2.0, 3.0]})
        with pytest.raises(ValueError, match="Group by columns not found"):
            OutlierService.remove_outliers(df, "val", ["nope"])

    def test_no_group_by_removes_iqr_outliers(self) -> None:
        # Data: [1, 2, 3, 4, 5, 6, 7, 100]
        # Q1=2.25, Q3=6.25, IQR=4.0, lower=-3.75, upper=12.25
        # Only 100 is above upper bound
        df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 6, 7, 100]})
        result = OutlierService.remove_outliers(df, "val", [])
        assert 100 not in result["val"].values
        # Values 1-7 should all be kept (within IQR bounds)
        assert len(result) == 7

    def test_with_group_by_uses_group_iqr(self) -> None:
        # [test->req~ring5.data.outlier-removal~1]
        df = pd.DataFrame(
            {
                "group": ["A", "A", "A", "A", "B", "B", "B", "B"],
                "val": [1, 2, 3, 100, 10, 20, 30, 200],
            }
        )
        result = OutlierService.remove_outliers(df, "val", ["group"])
        assert 100 not in result["val"].values
        assert 200 not in result["val"].values

    def test_all_values_equal_keeps_all(self) -> None:
        df = pd.DataFrame({"val": [1, 1, 1, 1]})
        result = OutlierService.remove_outliers(df, "val", [])
        assert len(result) == 4

    def test_iqr_keeps_values_within_bounds(self) -> None:
        """Normal distribution: IQR should keep ~95% of values."""
        # Values well within IQR 1.5x bounds
        df = pd.DataFrame({"val": list(range(1, 21))})  # 1..20
        result = OutlierService.remove_outliers(df, "val", [])
        # All values should be kept (no outliers in evenly spaced data)
        assert len(result) == 20

    def test_custom_multiplier(self) -> None:
        # With multiplier=0, only values exactly at Q1..Q3 are kept
        # With multiplier=3 (extreme), more values are kept
        df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 6, 7, 100]})
        result_strict = OutlierService.remove_outliers(df, "val", [], multiplier=1.5)
        result_extreme = OutlierService.remove_outliers(df, "val", [], multiplier=3.0)
        assert len(result_strict) <= len(result_extreme)


class TestValidateOutlierInputs:
    """Tests for OutlierService.validate_outlier_inputs."""

    def test_empty_outlier_col(self) -> None:
        df = pd.DataFrame({"a": [1]})
        errors = OutlierService.validate_outlier_inputs(df, "", [])
        assert any("must be specified" in e for e in errors)

    def test_outlier_col_not_found(self) -> None:
        df = pd.DataFrame({"a": [1]})
        errors = OutlierService.validate_outlier_inputs(df, "missing", [])
        assert any("not found" in e for e in errors)

    def test_outlier_col_not_numeric(self) -> None:
        df = pd.DataFrame({"a": ["x", "y"]})
        errors = OutlierService.validate_outlier_inputs(df, "a", [])
        assert any("numeric" in e for e in errors)

    def test_group_by_col_not_found(self) -> None:
        df = pd.DataFrame({"a": [1, 2]})
        errors = OutlierService.validate_outlier_inputs(df, "a", ["missing"])
        assert any("not found" in e for e in errors)

    def test_valid_inputs_no_errors(self) -> None:
        df = pd.DataFrame({"val": [1, 2], "grp": ["A", "B"]})
        errors = OutlierService.validate_outlier_inputs(df, "val", ["grp"])
        assert errors == []

    def test_valid_no_group_by(self) -> None:
        df = pd.DataFrame({"val": [1, 2, 3]})
        errors = OutlierService.validate_outlier_inputs(df, "val", [])
        assert errors == []
