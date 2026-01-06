
import tempfile
import os
import pytest
import pandas as pd
import numpy as np
from src.processing.managers.mixer import Mixer
from src.processing.managers.params import DataManagerParams
from src.processing.managers.base_manager import DataManager

class TestMixerExtended:
    """Extended tests for Mixer."""

    def setup_method(self):
        DataManager._df_data = None
        DataManager._statistic_columns = []
        # Create a dummy element so validation passes
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        self.tmp_file.close()

    def teardown_method(self):
        if os.path.exists(self.tmp_file.name):
            os.remove(self.tmp_file.name)

    def test_sum_columns(self):
        """Test simple sum of columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        DataManager._df = df
        DataManager._statistic_columns = ["A", "B"]
        
        # params is needed but unused in logic except for parent verify?
        # DataManagerParams expects csv_path etc.
        params = DataManagerParams(
            csv_path=self.tmp_file.name,
            categorical_columns=[],
            statistic_columns=["A", "B"]
        )
        
        config = {
            "mixer": {
                "C": ["A", "B"]
            }
        }
        
        mixer = Mixer(params, config)
        mixer() # Invoke __call__
        
        result = DataManager._df
        assert "C" in result.columns
        assert np.array_equal(result["C"].values, [4, 6])

    def test_sum_columns_with_sd_propagation(self):
        """Test sum of columns propagates SD."""
        # A=10, sd=1; B=20, sd=2. Sum=30. SD=sqrt(1^2 + 2^2)=sqrt(5)=2.236
        df = pd.DataFrame({
            "A": [10.0], "A.sd": [1.0],
            "B": [20.0], "B.sd": [2.0]
        })
        DataManager._df = df
        DataManager._statistic_columns = ["A", "B"]
        
        params = DataManagerParams(
            csv_path=self.tmp_file.name, 
            categorical_columns=[], 
            statistic_columns=["A", "B"]
        )
        config = {
            "mixer": {
                "C": ["A", "B"]
            }
        }
        
        mixer = Mixer(params, config)
        mixer()
        
        result = DataManager._df
        assert "C" in result.columns
        assert result["C"].iloc[0] == 30.0
        
        # This is the critical check
        if "C.sd" in result.columns:
            print("SD Propagation implemented!")
            expected_sd = np.sqrt(1.0**2 + 2.0**2)
            assert np.isclose(result["C.sd"].iloc[0], expected_sd)
        else:
            pytest.fail("Mixer did NOT propagate Standard Deviation (C.sd missing)")

