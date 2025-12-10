"""
Integration tests for BackendFacade data manager methods.
Tests proper integration with DataManagerParams classes.
"""

import numpy as np
import pandas as pd
import pytest

from src.web.facade import BackendFacade


@pytest.fixture
def facade():
    """Create a BackendFacade instance."""
    return BackendFacade()


@pytest.fixture
def sample_data_with_seeds():
    """Create sample data with random_seed column for seeds reducer test."""
    return pd.DataFrame(
        {
            "benchmark": ["bench1", "bench1", "bench1", "bench2", "bench2", "bench2"],
            "config": ["cfg1", "cfg1", "cfg1", "cfg2", "cfg2", "cfg2"],
            "random_seed": [1, 2, 3, 1, 2, 3],
            "cycles": [100, 110, 105, 200, 190, 210],
            "instructions": [1000, 1100, 1050, 2000, 1900, 2100],
        }
    )


@pytest.fixture
def sample_data_with_outliers():
    """Create sample data with outliers for outlier remover test."""
    return pd.DataFrame(
        {
            "benchmark": ["bench1", "bench1", "bench1", "bench1"],
            "config": ["cfg1", "cfg1", "cfg1", "cfg1"],
            "cycles": [100, 110, 105, 1000],  # 1000 is outlier
            "instructions": [1000, 1100, 1050, 10000],
        }
    )


@pytest.fixture
def sample_data_for_preprocess():
    """Create sample data for preprocessor test."""
    return pd.DataFrame(
        {
            "benchmark": ["bench1", "bench2"],
            "config": ["cfg1", "cfg2"],
            "cycles": [100, 200],
            "instructions": [1000, 2000],
        }
    )


class TestFacadeSeedsReducer:
    """Test seeds reducer integration via facade."""

    def test_seeds_reducer_basic(self, facade, sample_data_with_seeds):
        """Test basic seeds reduction."""
        result = facade.apply_seeds_reducer(
            data=sample_data_with_seeds,
            categorical_cols=["benchmark", "config"],
            statistic_cols=["cycles", "instructions"],
        )

        # Should have 2 rows (one per benchmark+config combo)
        assert len(result) == 2

        # Should have mean and std columns
        assert "cycles" in result.columns
        assert "cycles.sd" in result.columns
        assert "instructions" in result.columns
        assert "instructions.sd" in result.columns

        # Verify mean calculation for bench1
        bench1_row = result[result["benchmark"] == "bench1"]
        expected_mean = np.mean([100, 110, 105])
        assert np.isclose(bench1_row["cycles"].values[0], expected_mean)

    def test_seeds_reducer_with_normalization(self, facade, sample_data_with_seeds):
        """Test seeds reduction - std columns created but NOT pre-normalized."""
        result = facade.apply_seeds_reducer(
            data=sample_data_with_seeds,
            categorical_cols=["benchmark", "config"],
            statistic_cols=["cycles", "instructions"],
        )

        # Check that std columns exist
        bench1_row = result[result["benchmark"] == "bench1"]
        assert "cycles.sd" in result.columns
        assert "instructions.sd" in result.columns

        # Std should be absolute values, NOT normalized
        # For cycles [100, 110, 105], mean=105, std≈5
        sd_cycles = bench1_row["cycles.sd"].values[0]
        assert sd_cycles > 1.0  # Should be absolute std, not relative


class TestFacadeOutlierRemover:
    """Test outlier remover integration via facade."""

    def test_outlier_remover_removes_high_values(self, facade, sample_data_with_outliers):
        """Test that outlier remover removes values above Q3."""
        result = facade.apply_outlier_remover(
            data=sample_data_with_outliers,
            outlier_column="cycles",
            categorical_cols=["benchmark", "config"],
        )

        # Should remove the row with cycles=1000
        assert len(result) < len(sample_data_with_outliers)
        assert 1000 not in result["cycles"].values

    def test_outlier_remover_keeps_normal_data(self, facade, sample_data_with_outliers):
        """Test that normal data is preserved."""
        result = facade.apply_outlier_remover(
            data=sample_data_with_outliers,
            outlier_column="cycles",
            categorical_cols=["benchmark", "config"],
        )

        # Normal values should still be present
        assert 100 in result["cycles"].values or 110 in result["cycles"].values


class TestFacadePreprocessor:
    """Test preprocessor integration via facade."""

    def test_preprocessor_divide_operation(self, facade, sample_data_for_preprocess):
        """Test divide operation creates correct new column."""
        result = facade.apply_preprocessor(
            data=sample_data_for_preprocess,
            operation="divide",
            src_col1="instructions",
            src_col2="cycles",
            dst_col="ipc",
        )

        # Should have new column
        assert "ipc" in result.columns

        # Verify calculation: instructions / cycles
        expected_ipc = (
            sample_data_for_preprocess["instructions"] / sample_data_for_preprocess["cycles"]
        )
        assert np.allclose(result["ipc"], expected_ipc)

    def test_preprocessor_sum_operation(self, facade, sample_data_for_preprocess):
        """Test sum operation creates correct new column."""
        result = facade.apply_preprocessor(
            data=sample_data_for_preprocess,
            operation="sum",
            src_col1="cycles",
            src_col2="instructions",
            dst_col="total",
        )

        # Should have new column
        assert "total" in result.columns

        # Verify calculation: cycles + instructions
        expected_total = (
            sample_data_for_preprocess["cycles"] + sample_data_for_preprocess["instructions"]
        )
        assert np.allclose(result["total"], expected_total)

    def test_preprocessor_preserves_original_columns(self, facade, sample_data_for_preprocess):
        """Test that original columns are preserved."""
        result = facade.apply_preprocessor(
            data=sample_data_for_preprocess,
            operation="divide",
            src_col1="instructions",
            src_col2="cycles",
            dst_col="ipc",
        )

        # Original columns should still exist
        assert "benchmark" in result.columns
        assert "config" in result.columns
        assert "cycles" in result.columns
        assert "instructions" in result.columns


class TestFacadeManagersIntegration:
    """Test integration between multiple data managers."""

    def test_pipeline_seeds_then_outlier(self, facade, sample_data_with_seeds):
        """Test applying seeds reducer followed by outlier remover."""
        # First reduce seeds
        after_seeds = facade.apply_seeds_reducer(
            data=sample_data_with_seeds,
            categorical_cols=["benchmark", "config"],
            statistic_cols=["cycles", "instructions"],
        )

        assert len(after_seeds) == 2
        assert "cycles.sd" in after_seeds.columns

        # Then remove outliers (though there shouldn't be any in this case)
        after_outlier = facade.apply_outlier_remover(
            data=after_seeds, outlier_column="cycles", categorical_cols=["benchmark", "config"]
        )

        # Should still have data
        assert len(after_outlier) > 0

    def test_pipeline_preprocess_then_seeds(self, facade, sample_data_with_seeds):
        """Test applying preprocessor followed by seeds reducer."""
        # First add IPC column
        after_preprocess = facade.apply_preprocessor(
            data=sample_data_with_seeds,
            operation="divide",
            src_col1="instructions",
            src_col2="cycles",
            dst_col="ipc",
        )

        assert "ipc" in after_preprocess.columns

        # Then reduce seeds (should include new IPC column)
        after_seeds = facade.apply_seeds_reducer(
            data=after_preprocess,
            categorical_cols=["benchmark", "config"],
            statistic_cols=["cycles", "instructions", "ipc"],
        )

        # Should have mean and std for all statistics including IPC
        assert "ipc" in after_seeds.columns
        assert "ipc.sd" in after_seeds.columns
