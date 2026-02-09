"""
Tests for MixerService - Column merge and mixing operations.

Following Rule 004 (QA Testing Mastery):
- Fixture-first design for test data
- AAA pattern (Arrange-Act-Assert)
- Parametrization for multiple scenarios
- Edge case and error handling tests
- No mocks needed (pure data transformations)
"""

import numpy as np
import pandas as pd
import pytest

from src.core.services.managers.arithmetic_service import ArithmeticService as MixerService


@pytest.fixture
def sample_dataframe():
    """Basic DataFrame with numeric columns."""
    return pd.DataFrame(
        {
            "A": [10.0, 20.0, 30.0],
            "B": [5.0, 10.0, 15.0],
            "C": [2.0, 4.0, 6.0],
            "name": ["x", "y", "z"],
        }
    )


@pytest.fixture
def dataframe_with_sd():
    """DataFrame with SD columns for variance propagation."""
    return pd.DataFrame(
        {
            "A": [10.0, 20.0],
            "A.sd": [1.0, 2.0],
            "B": [20.0, 40.0],
            "B.sd": [2.0, 4.0],
            "C": [5.0, 10.0],
            "C_stdev": [0.5, 1.0],  # Alternative SD naming
        }
    )


class TestApplyMixerSumOperation:
    """Test apply_mixer with Sum operation."""

    def test_sum_two_columns(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        result = MixerService.apply_mixer(
            df, dest_col="AB_sum", source_cols=["A", "B"], operation="Sum"
        )

        # Assert
        assert "AB_sum" in result.columns
        assert result["AB_sum"].tolist() == [15.0, 30.0, 45.0]
        assert len(result.columns) == len(df.columns) + 1  # Original + new col

    def test_sum_three_columns(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        result = MixerService.apply_mixer(
            df, dest_col="total", source_cols=["A", "B", "C"], operation="Sum"
        )

        # Assert
        assert result["total"].tolist() == [17.0, 34.0, 51.0]

    def test_sum_with_sd_propagation(self, dataframe_with_sd):
        # Arrange
        df = dataframe_with_sd

        # Act
        result = MixerService.apply_mixer(
            df, dest_col="AB_sum", source_cols=["A", "B"], operation="Sum"
        )

        # Assert
        assert "AB_sum" in result.columns
        assert "AB_sum.sd" in result.columns
        # Sum values: 10+20=30, 20+40=60
        assert result["AB_sum"].tolist() == [30.0, 60.0]
        # SD propagation: sqrt(1^2 + 2^2) = sqrt(5) ≈ 2.236
        assert np.isclose(result["AB_sum.sd"].iloc[0], 2.2360679)
        # SD propagation: sqrt(2^2 + 4^2) = sqrt(20) ≈ 4.472
        assert np.isclose(result["AB_sum.sd"].iloc[1], 4.4721359)

    def test_sum_mixed_sd_naming(self, dataframe_with_sd):
        # Arrange - Mix .sd and _stdev columns
        df = dataframe_with_sd

        # Act
        result = MixerService.apply_mixer(
            df, dest_col="AC_sum", source_cols=["A", "C"], operation="Sum"
        )

        # Assert
        assert "AC_sum.sd" in result.columns
        # A.sd=1.0, C_stdev=0.5 → sqrt(1^2 + 0.5^2) = sqrt(1.25) ≈ 1.118
        assert np.isclose(result["AC_sum.sd"].iloc[0], 1.1180339)

    def test_sum_without_sd_columns(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        result = MixerService.apply_mixer(
            df, dest_col="total", source_cols=["A", "B"], operation="Sum"
        )

        # Assert
        assert "total.sd" not in result.columns  # No SD if source has none


class TestApplyMixerMeanOperation:
    """Test apply_mixer with Mean operations."""

    def test_mean_two_columns(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        result = MixerService.apply_mixer(
            df, dest_col="mean_AB", source_cols=["A", "B"], operation="Mean"
        )

        # Assert
        assert "mean_AB" in result.columns
        assert result["mean_AB"].tolist() == [7.5, 15.0, 22.5]

    def test_mean_average_alias(self, sample_dataframe):
        # Arrange - "Mean (Average)" is accepted alias
        df = sample_dataframe

        # Act
        result = MixerService.apply_mixer(
            df, dest_col="avg", source_cols=["A", "B"], operation="Mean (Average)"
        )

        # Assert
        assert result["avg"].tolist() == [7.5, 15.0, 22.5]

    def test_mean_with_sd_propagation(self, dataframe_with_sd):
        # Arrange
        df = dataframe_with_sd

        # Act
        result = MixerService.apply_mixer(
            df, dest_col="AB_mean", source_cols=["A", "B"], operation="Mean"
        )

        # Assert
        assert "AB_mean.sd" in result.columns
        # Mean values: (10+20)/2=15, (20+40)/2=30
        assert result["AB_mean"].tolist() == [15.0, 30.0]
        # SD propagation for mean: sqrt(1^2 + 2^2) / 2 = 2.236 / 2 = 1.118
        assert np.isclose(result["AB_mean.sd"].iloc[0], 1.1180339)
        # SD propagation: sqrt(2^2 + 4^2) / 2 = 4.472 / 2 = 2.236
        assert np.isclose(result["AB_mean.sd"].iloc[1], 2.2360679)


class TestApplyMixerConcatenateOperation:
    """Test apply_mixer with Concatenate operation."""

    def test_concatenate_default_separator(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        result = MixerService.apply_mixer(
            df, dest_col="concat", source_cols=["A", "name"], operation="Concatenate"
        )

        # Assert
        assert result["concat"].tolist() == ["10.0_x", "20.0_y", "30.0_z"]

    def test_concatenate_custom_separator(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        result = MixerService.apply_mixer(
            df,
            dest_col="joined",
            source_cols=["name", "A"],
            operation="Concatenate",
            separator="|",
        )

        # Assert
        assert result["joined"].tolist() == ["x|10.0", "y|20.0", "z|30.0"]

    def test_concatenate_no_sd_propagation(self, dataframe_with_sd):
        # Arrange - Concatenate should not produce SD columns
        df = dataframe_with_sd

        # Act
        result = MixerService.apply_mixer(
            df, dest_col="concat", source_cols=["A", "B"], operation="Concatenate"
        )

        # Assert
        assert "concat" in result.columns
        assert "concat.sd" not in result.columns


class TestApplyMixerEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_source_cols_returns_unchanged(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        result = MixerService.apply_mixer(df, dest_col="empty", source_cols=[], operation="Sum")

        # Assert
        pd.testing.assert_frame_equal(result, df)  # Unchanged

    def test_invalid_operation_raises_error(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown mixer operation"):
            MixerService.apply_mixer(df, dest_col="bad", source_cols=["A"], operation="Invalid")

    def test_single_column_sum(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        result = MixerService.apply_mixer(df, dest_col="single", source_cols=["A"], operation="Sum")

        # Assert
        assert result["single"].tolist() == [10.0, 20.0, 30.0]

    def test_partial_sd_columns_skips_propagation(self):
        # Arrange - Only one column has SD
        df = pd.DataFrame(
            {
                "A": [10.0],
                "A.sd": [1.0],
                "B": [20.0],  # No B.sd
            }
        )

        # Act
        result = MixerService.apply_mixer(
            df, dest_col="sum", source_cols=["A", "B"], operation="Sum"
        )

        # Assert
        assert "sum.sd" in result.columns  # Still creates SD from available
        # Should only use A's variance: sqrt(1^2) = 1.0
        assert result["sum.sd"].iloc[0] == 1.0


class TestMergeColumnsAlias:
    """Test merge_columns as alias for apply_mixer."""

    def test_merge_columns_delegates_to_apply_mixer(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        result = MixerService.merge_columns(
            df=df,
            columns=["A", "B"],
            operation="Sum",
            new_column_name="merged",
            separator="-",
        )

        # Assert
        assert "merged" in result.columns
        assert result["merged"].tolist() == [15.0, 30.0, 45.0]


class TestValidateMergeInputs:
    """Test input validation for merge operations."""

    def test_validate_success_with_valid_inputs(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        errors = MixerService.validate_merge_inputs(
            df, columns=["A", "B"], operation="Sum", new_column_name="result"
        )

        # Assert
        assert errors == []

    def test_validate_empty_columns_list(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        errors = MixerService.validate_merge_inputs(
            df, columns=[], operation="Sum", new_column_name="result"
        )

        # Assert
        assert len(errors) == 1
        assert "At least one column must be selected" in errors[0]

    def test_validate_single_column_error(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        errors = MixerService.validate_merge_inputs(
            df, columns=["A"], operation="Sum", new_column_name="result"
        )

        # Assert
        assert len(errors) == 1
        assert "At least two columns must be selected" in errors[0]

    def test_validate_missing_columns(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        errors = MixerService.validate_merge_inputs(
            df, columns=["A", "Z", "Y"], operation="Sum", new_column_name="result"
        )

        # Assert
        assert len(errors) == 1
        assert "Columns not found" in errors[0]
        assert "Z" in errors[0] and "Y" in errors[0]

    def test_validate_invalid_operation(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        errors = MixerService.validate_merge_inputs(
            df, columns=["A", "B"], operation="Multiply", new_column_name="result"
        )

        # Assert
        assert len(errors) == 1
        assert "Invalid operation" in errors[0]

    def test_validate_empty_new_column_name(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        errors = MixerService.validate_merge_inputs(
            df, columns=["A", "B"], operation="Sum", new_column_name=""
        )

        # Assert
        assert len(errors) == 1
        assert "cannot be empty" in errors[0]

    def test_validate_existing_column_name(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        errors = MixerService.validate_merge_inputs(
            df, columns=["A", "B"], operation="Sum", new_column_name="A"
        )

        # Assert
        assert len(errors) == 1
        assert "already exists" in errors[0]

    def test_validate_multiple_errors(self, sample_dataframe):
        # Arrange
        df = sample_dataframe

        # Act
        errors = MixerService.validate_merge_inputs(
            df, columns=["Z"], operation="Invalid", new_column_name=""
        )

        # Assert
        assert len(errors) >= 3  # Multiple validation failures
        error_text = " ".join(errors)
        assert "two columns" in error_text
        assert "Invalid operation" in error_text
        assert "cannot be empty" in error_text
