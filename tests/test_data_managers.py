"""
Unit tests for data manager modules.
Tests seedsReducer, outlierRemover, and preprocessor integration.
Uses proper DataManagerParams classes instead of mocks.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_management.dataManager import DataManager
from src.data_management.impl.outlierRemover import OutlierRemover
from src.data_management.impl.preprocessor import Preprocessor
from src.data_management.impl.seedsReducer import SeedsReducer
from src.data_management.manager_params import (OutlierRemoverParams,
                                                PreprocessorParams,
                                                SeedsReducerParams)


class TestSeedsReducer:
    """Test the SeedsReducer data manager."""

    def test_reduces_seeds_and_calculates_statistics(self, tmp_path):
        """Test that seeds are reduced and statistics calculated."""
        # Create test CSV with seeds
        csv_data = pd.DataFrame(
            {
                "benchmark": ["bzip2", "bzip2", "bzip2", "gcc", "gcc", "gcc"],
                "config": ["baseline", "baseline", "baseline", "baseline", "baseline", "baseline"],
                "random_seed": [1, 2, 3, 1, 2, 3],
                "simTicks": [1000, 1010, 990, 2000, 2020, 1980],
                "ipc": [1.5, 1.52, 1.48, 2.0, 2.02, 1.98],
            }
        )

        csv_file = tmp_path / "test.csv"
        csv_data.to_csv(csv_file, index=False)

        # Create proper params using SeedsReducerParams
        params = SeedsReducerParams(
            csv_path=str(csv_file),
            categorical_columns=["benchmark", "config"],
            statistic_columns=["simTicks", "ipc"],
            enable_reduction=True,
        )

        config = {"seedsReducer": True}

        # Execute reducer
        reducer = SeedsReducer(params, config)
        reducer.manage()

        # Verify results
        result = DataManager._df
        assert len(result) == 2  # Two groups (bzip2 and gcc)
        assert "random_seed" not in result.columns
        assert "simTicks.sd" in result.columns
        assert "ipc.sd" in result.columns

        # Check mean values
        bzip2_row = result[result["benchmark"] == "bzip2"].iloc[0]
        assert abs(bzip2_row["simTicks"] - 1000) < 1

        gcc_row = result[result["benchmark"] == "gcc"].iloc[0]
        assert abs(gcc_row["simTicks"] - 2000) < 1

    def test_handles_missing_random_seed_gracefully(self, tmp_path):
        """Test error handling when random_seed column is missing."""
        # Setup test data without random_seed
        test_df = pd.DataFrame({"benchmark": ["bzip2", "gcc"], "simTicks": [1000, 2000]})

        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)

        params = SeedsReducerParams(
            csv_path=str(csv_file),
            categorical_columns=["benchmark"],
            statistic_columns=["simTicks"],
            enable_reduction=True,
        )

        config = {"seedsReducer": True}

        # Should raise ValueError
        with pytest.raises(ValueError, match="random_seed"):
            reducer = SeedsReducer(params, config)
            reducer.manage()


class TestOutlierRemover:
    """Test the OutlierRemover data manager."""

    def test_removes_outliers_above_q3(self, tmp_path):
        """Test that outliers above Q3 are removed."""
        # Create data with one clear outlier
        test_df = pd.DataFrame(
            {
                "benchmark": ["bzip2"] * 10,
                "config": ["baseline"] * 10,
                "simTicks": [100, 105, 102, 98, 101, 103, 99, 104, 500, 97],  # 500 is outlier
            }
        )

        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)

        # Create proper params using OutlierRemoverParams
        params = OutlierRemoverParams(
            csv_path=str(csv_file),
            categorical_columns=["benchmark", "config"],
            statistic_columns=["simTicks"],
            outlier_column="simTicks",
        )

        config = {"outlierRemover": {"outlierStat": "simTicks"}}

        # Execute remover
        remover = OutlierRemover(params, config)
        remover()

        # Verify outlier was removed
        result = DataManager._df
        assert len(result) < 10
        assert result["simTicks"].max() <= 105  # Should not include 500

    def test_preserves_data_within_q3(self, tmp_path):
        """Test that data within Q3 is preserved."""
        # Create data without outliers
        test_df = pd.DataFrame(
            {
                "benchmark": ["bzip2"] * 5,
                "config": ["baseline"] * 5,
                "simTicks": [100, 101, 102, 103, 104],
            }
        )

        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)

        params = OutlierRemoverParams(
            csv_path=str(csv_file),
            categorical_columns=["benchmark", "config"],
            outlier_column="simTicks",
            group_by_columns=["benchmark", "config"],
        )

        config = {"outlierRemover": {"outlierStat": "simTicks"}}

        # Execute remover
        remover = OutlierRemover(params, config)
        remover.manage()

        # Should preserve most or all data
        result = DataManager._df
        assert len(result) >= 3  # At least some data preserved


class TestPreprocessor:
    """Test the Preprocessor data manager."""

    def test_divide_operator(self, tmp_path):
        """Test divide operation."""
        test_df = pd.DataFrame(
            {"benchmark": ["bzip2", "gcc"], "simTicks": [1000, 2000], "instructions": [500, 1000]}
        )

        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)

        params = PreprocessorParams(
            csv_path=str(csv_file),
            categorical_columns=["benchmark"],
            operations={"cpi": {"operator": "divide", "src1": "simTicks", "src2": "instructions"}},
        )

        config = {
            "preprocessor": {
                "cpi": {"operator": "divide", "src1": "simTicks", "src2": "instructions"}
            }
        }

        # Execute preprocessor
        preprocessor = Preprocessor(params, config)
        preprocessor.manage()

        # Verify new column was created
        result = DataManager._df
        assert "cpi" in result.columns
        assert result.iloc[0]["cpi"] == 2.0  # 1000/500
        assert result.iloc[1]["cpi"] == 2.0  # 2000/1000

    def test_sum_operator(self, tmp_path):
        """Test sum operation."""
        test_df = pd.DataFrame({"benchmark": ["bzip2"], "value1": [100], "value2": [50]})

        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)

        params = PreprocessorParams(
            csv_path=str(csv_file),
            categorical_columns=["benchmark"],
            operations={"total": {"operator": "sum", "src1": "value1", "src2": "value2"}},
        )

        config = {
            "preprocessor": {"total": {"operator": "sum", "src1": "value1", "src2": "value2"}}
        }

        # Execute preprocessor
        preprocessor = Preprocessor(params, config)
        preprocessor.manage()

        # Verify sum was calculated
        result = DataManager._df
        assert "total" in result.columns
        assert result.iloc[0]["total"] == 150


class TestDataManagerPipeline:
    """Integration tests for chaining multiple data managers."""

    def test_complete_pipeline(self, tmp_path):
        """Test a complete data processing pipeline."""
        # Create realistic test data
        test_df = pd.DataFrame(
            {
                "benchmark": ["bzip2"] * 6 + ["gcc"] * 6,
                "config": ["baseline"] * 3
                + ["optimized"] * 3
                + ["baseline"] * 3
                + ["optimized"] * 3,
                "random_seed": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3],
                "simTicks": [1000, 1010, 990, 800, 810, 790, 2000, 2020, 1980, 1600, 1620, 1580],
                "instructions": [500, 505, 495, 500, 505, 495, 1000, 1010, 990, 1000, 1010, 990],
            }
        )

        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)

        # Step 1: Add CPI column via preprocessor
        preprocess_config = {
            "preprocessor": {
                "cpi": {"operator": "divide", "src1": "simTicks", "src2": "instructions"}
            }
        }
        preprocess_params = PreprocessorParams(
            csv_path=str(csv_file),
            categorical_columns=["benchmark", "config"],
            operations={"cpi": {"operator": "divide", "src1": "simTicks", "src2": "instructions"}},
        )
        preprocessor = Preprocessor(preprocess_params, preprocess_config)
        preprocessor.manage()

        # Verify CPI was added
        assert "cpi" in DataManager._df.columns

        # Save intermediate result
        intermediate_file = tmp_path / "after_preprocess.csv"
        DataManager._df.to_csv(intermediate_file, index=False)

        # Step 2: Reduce seeds
        seeds_config = {"seedsReducer": True}
        seeds_params = SeedsReducerParams(
            csv_path=str(intermediate_file),
            categorical_columns=["benchmark", "config"],
            statistic_columns=["simTicks", "instructions", "cpi"],
            enable_reduction=True,
        )
        reducer = SeedsReducer(seeds_params, seeds_config)
        reducer.manage()

        # Verify seeds were reduced
        result = DataManager._df
        assert len(result) == 4  # 2 benchmarks × 2 configs
        assert "random_seed" not in result.columns
        assert "simTicks.sd" in result.columns

        # Verify data integrity
        assert not result.isnull().any().any()
        assert all(col in result.columns for col in ["benchmark", "config", "simTicks", "cpi"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
