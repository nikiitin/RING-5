"""Tests for OutlierService — target branches at 60% coverage."""

import pandas as pd

from src.core.services.managers.outlier_service import OutlierService


class TestRemoveOutliers:
    """Tests for OutlierService.remove_outliers."""

    def test_empty_dataframe_returns_empty(self) -> None:
        df = pd.DataFrame({"val": pd.Series([], dtype=float)})
        result = OutlierService.remove_outliers(df, "val", [])
        assert result.empty

    def test_column_not_in_df_returns_original(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = OutlierService.remove_outliers(df, "missing", [])
        assert len(result) == 3

    def test_no_group_by_uses_global_q3(self) -> None:
        # Q3 of [1,2,3,4,5,6,7,8] = 6.25
        df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 6, 7, 100]})
        result = OutlierService.remove_outliers(df, "val", [])
        # 100 > Q3, should be removed
        assert 100 not in result["val"].values

    def test_with_group_by_uses_group_q3(self) -> None:
        df = pd.DataFrame(
            {
                "group": ["A", "A", "A", "A", "B", "B", "B", "B"],
                "val": [1, 2, 3, 100, 10, 20, 30, 200],
            }
        )
        result = OutlierService.remove_outliers(df, "val", ["group"])
        # 100 and 200 exceed their respective group Q3
        assert 100 not in result["val"].values
        assert 200 not in result["val"].values

    def test_all_values_below_q3(self) -> None:
        df = pd.DataFrame({"val": [1, 1, 1, 1]})
        result = OutlierService.remove_outliers(df, "val", [])
        assert len(result) == 4


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
