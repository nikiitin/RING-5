import numpy as np
import pandas as pd
import pytest

from src.core.services.arithmetic_service import ArithmeticService
from src.core.services.outlier_service import OutlierService
from src.core.services.reduction_service import ReductionService
from src.core.services.shapers.factory import ShaperFactory


class TestDataPipeline:

    @pytest.fixture
    def sample_data(self):
        return pd.DataFrame(
            {
                "group": ["A", "A", "B", "B", "C", "C"],
                "value": [10, 12, 20, 22, 100, 102],
                "noise": [0.1, 0.2, 0.1, 0.2, 10.0, 10.1],
                "category": ["x", "y", "x", "y", "x", "y"],
            }
        )

    def test_seeds_reduction(self, sample_data):
        # Add seed column
        df = sample_data.copy()
        df["random_seed"] = [1, 2, 1, 2, 1, 2]

        # Reduce
        reduced = ReductionService.reduce_seeds(
            df, categorical_cols=["group"], statistic_cols=["value"]
        )

        # Expect 3 rows (A, B, C)
        assert len(reduced) == 3
        assert "value" in reduced.columns
        assert "value.sd" in reduced.columns
        assert reduced[reduced["group"] == "A"]["value"].iloc[0] == 11.0  # (10+12)/2

    def test_outlier_removal(self, sample_data):
        # Outlier logic works on IQR.
        # Create a clear outlier case within a group.
        df = pd.DataFrame(
            {
                "group": ["A"] * 10,
                "value": [10, 10, 10, 10, 10, 10, 10, 10, 10, 1000],  # 1000 is outlier
            }
        )

        cleaned = OutlierService.remove_outliers(df, outlier_col="value", group_by_cols=["group"])

        assert len(cleaned) == 9
        assert 1000 not in cleaned["value"].values

    def test_shaper_pipeline_execution(self, sample_data):
        # Configure a pipeline: Filter > Sort

        # To strictly test the factory and execution
        # 1. Column Selector
        col_selector = ShaperFactory.createShaper("columnSelector", {"columns": ["group", "value"]})
        df_cols = col_selector(sample_data)
        assert "noise" not in df_cols.columns

        # 2. Condition Selector (Filter)
        filter_shaper = ShaperFactory.createShaper(
            "conditionSelector", {"column": "value", "mode": "less_than", "threshold": 50}
        )
        df_filtered = filter_shaper(sample_data)
        assert "C" not in df_filtered["group"].values  # C has values 100+

    def test_mixer_operations(self, sample_data):
        df = sample_data.copy()
        # Add implicit SD cols
        df["value.sd"] = [1] * 6
        df["noise.sd"] = [0.1] * 6

        # Sum
        result = ArithmeticService.merge_columns(
            df, source_cols=["value", "noise"], operation="Sum", dest_col="mixed"
        )

        assert "mixed" in result.columns
        # Check Value
        assert result["mixed"].iloc[0] == 10.1
        # Check SD propagation: sqrt(1^2 + 0.1^2) ~= 1.005
        assert "mixed.sd" in result.columns
        expected_sd = np.sqrt(1**2 + 0.1**2)
        assert np.isclose(result["mixed.sd"].iloc[0], expected_sd)
