"""
Backward compatibility tests for CLI usage with AnalyzerInfo.
Ensures DataManager classes work with both old and new parameter types.
"""
import pytest
import pandas as pd
from pathlib import Path
import tempfile

from argumentParser import AnalyzerInfo
from src.data_management.impl.seedsReducer import SeedsReducer
from src.data_management.impl.outlierRemover import OutlierRemover
from src.data_management.impl.preprocessor import Preprocessor
from src.data_management.dataManager import DataManager


@pytest.fixture
def sample_csv_with_seeds(tmp_path):
    """Create a sample CSV file with seeds for testing."""
    data = pd.DataFrame({
        'benchmark': ['bench1', 'bench1', 'bench1', 'bench2', 'bench2', 'bench2'],
        'config': ['cfg1', 'cfg1', 'cfg1', 'cfg2', 'cfg2', 'cfg2'],
        'random_seed': [1, 2, 3, 1, 2, 3],
        'cycles': [100, 110, 105, 200, 190, 210],
        'instructions': [1000, 1100, 1050, 2000, 1900, 2100]
    })
    
    csv_file = tmp_path / "test_data.csv"
    data.to_csv(csv_file, index=False)
    return str(csv_file)


class MockAnalyzerInfo:
    """Mock AnalyzerInfo that mimics real CLI usage."""
    
    def __init__(self, csv_path, categorical_cols):
        self._csv_path = csv_path
        self._categorical_cols = categorical_cols
    
    def getWorkCsv(self):
        return self._csv_path
    
    def getCategoricalColumns(self):
        return self._categorical_cols


class TestCLIBackwardCompatibility:
    """Test that original CLI usage patterns still work."""
    
    def test_seeds_reducer_with_analyzer_info(self, sample_csv_with_seeds):
        """Test SeedsReducer works with AnalyzerInfo (old CLI pattern)."""
        # Reset DataManager state
        DataManager._df_data = None
        DataManager._categorical_columns_data = None
        DataManager._statistic_columns_data = None
        DataManager._csvPath_data = None
        
        # Create AnalyzerInfo like CLI does
        analyzer_info = MockAnalyzerInfo(
            csv_path=sample_csv_with_seeds,
            categorical_cols=['benchmark', 'config']
        )
        
        config = {'seedsReducer': True}
        
        # Create and execute reducer
        reducer = SeedsReducer(analyzer_info, config)
        reducer.manage()
        
        # Verify results
        result = DataManager._df
        assert len(result) == 2  # Two groups
        assert 'cycles.sd' in result.columns
        assert 'instructions.sd' in result.columns
        assert 'random_seed' not in result.columns
    
    def test_outlier_remover_with_analyzer_info(self, tmp_path):
        """Test OutlierRemover works with AnalyzerInfo."""
        # Create test data with outlier
        data = pd.DataFrame({
            'benchmark': ['bench1'] * 5,
            'cycles': [100, 105, 102, 500, 103]  # 500 is outlier
        })
        
        csv_file = tmp_path / "test_outliers.csv"
        data.to_csv(csv_file, index=False)
        
        # Reset state
        DataManager._df_data = None
        DataManager._categorical_columns_data = None
        DataManager._statistic_columns_data = None
        DataManager._csvPath_data = None
        
        # Use AnalyzerInfo
        analyzer_info = MockAnalyzerInfo(
            csv_path=str(csv_file),
            categorical_cols=['benchmark']
        )
        
        config = {'outlierStat': 'cycles'}
        
        # Execute
        remover = OutlierRemover(analyzer_info, config)
        remover.manage()
        
        # Verify outlier was removed
        result = DataManager._df
        assert 500 not in result['cycles'].values
    
    def test_preprocessor_with_analyzer_info(self, tmp_path):
        """Test Preprocessor works with AnalyzerInfo."""
        # Create test data
        data = pd.DataFrame({
            'benchmark': ['bench1', 'bench2'],
            'cycles': [100, 200],
            'instructions': [1000, 2000]
        })
        
        csv_file = tmp_path / "test_preprocess.csv"
        data.to_csv(csv_file, index=False)
        
        # Reset state
        DataManager._df_data = None
        DataManager._categorical_columns_data = None
        DataManager._statistic_columns_data = None
        DataManager._csvPath_data = None
        
        # Use AnalyzerInfo
        analyzer_info = MockAnalyzerInfo(
            csv_path=str(csv_file),
            categorical_cols=['benchmark']
        )
        
        config = {
            'preprocessor': {
                'ipc': {
                    'operator': 'divide',
                    'src1': 'instructions',
                    'src2': 'cycles'
                }
            }
        }
        
        # Execute
        processor = Preprocessor(analyzer_info, config)
        processor.manage()
        
        # Verify new column was created
        result = DataManager._df
        assert 'ipc' in result.columns
        assert result.iloc[0]['ipc'] == 10.0  # 1000/100
        assert result.iloc[1]['ipc'] == 10.0  # 2000/200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
