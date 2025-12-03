"""
Unit tests for data manager modules.
Tests seedsReducer, outlierRemover, and preprocessor integration.
Based on existing pytest infrastructure with proper mocking.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import tempfile
import os
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from argumentParser import AnalyzerInfo
from src.data_management.dataManager import DataManager
from src.data_management.impl.seedsReducer import SeedsReducer
from src.data_management.impl.outlierRemover import OutlierRemover
from src.data_management.impl.preprocessor import Preprocessor


class MockAnalyzerInfo:
    """Mock AnalyzerInfo for testing data managers."""
    
    def __init__(self, config_json):
        self.json = config_json
        self._workCsv = "test_results.csv"
        
    def getWorkCsv(self):
        return os.path.join(tempfile.gettempdir(), self._workCsv)
    
    def getTmpDir(self):
        return tempfile.gettempdir()


class TestSeedsReducer:
    """Test the SeedsReducer data manager."""
    
    def test_reduces_seeds_and_calculates_statistics(self, tmp_path):
        """Test that seeds are reduced and statistics calculated."""
        # Create test CSV with seeds
        csv_data = pd.DataFrame({
            'benchmark': ['bzip2', 'bzip2', 'bzip2', 'gcc', 'gcc', 'gcc'],
            'config': ['baseline', 'baseline', 'baseline', 'baseline', 'baseline', 'baseline'],
            'random_seed': [1, 2, 3, 1, 2, 3],
            'simTicks': [1000, 1010, 990, 2000, 2020, 1980],
            'ipc': [1.5, 1.52, 1.48, 2.0, 2.02, 1.98]
        })
        
        csv_file = tmp_path / "test.csv"
        csv_data.to_csv(csv_file, index=False)
        
        # Set up DataManager static state
        DataManager._df = csv_data
        DataManager._categorical_columns = ['benchmark', 'config']
        DataManager._statistic_columns = ['simTicks', 'ipc']
        DataManager._csvPath = str(csv_file)
        
        # Create config and mock params
        config = {'seedsReducer': True}
        params = MockAnalyzerInfo(config)
        
        # Execute reducer
        reducer = SeedsReducer(params, config)
        reducer()
        
        # Verify results
        result = DataManager._df
        assert len(result) == 2  # Two groups (bzip2 and gcc)
        assert 'random_seed' not in result.columns
        assert 'simTicks.sd' in result.columns
        assert 'ipc.sd' in result.columns
        
        # Check mean values
        bzip2_row = result[result['benchmark'] == 'bzip2'].iloc[0]
        assert abs(bzip2_row['simTicks'] - 1000) < 1
        
        gcc_row = result[result['benchmark'] == 'gcc'].iloc[0]
        assert abs(gcc_row['simTicks'] - 2000) < 1
    
    def test_handles_missing_random_seed_gracefully(self, tmp_path):
        """Test error handling when random_seed column is missing."""
        # Setup test data without random_seed
        test_df = pd.DataFrame({
            'benchmark': ['bzip2', 'gcc'],
            'simTicks': [1000, 2000]
        })
        
        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)
        
        DataManager._df = test_df
        DataManager._categorical_columns = ['benchmark']
        DataManager._statistic_columns = ['simTicks']
        DataManager._csvPath = str(csv_file)
        
        config = {'seedsReducer': True}
        params = MockAnalyzerInfo(config)
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="random_seed"):
            reducer = SeedsReducer(params, config)
            reducer()


class TestOutlierRemover:
    """Test the OutlierRemover data manager."""
    
    def test_removes_outliers_above_q3(self, tmp_path):
        """Test that outliers above Q3 are removed."""
        # Create data with one clear outlier
        test_df = pd.DataFrame({
            'benchmark': ['bzip2'] * 10,
            'config': ['baseline'] * 10,
            'simTicks': [100, 105, 102, 98, 101, 103, 99, 104, 500, 97]  # 500 is outlier
        })
        
        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)
        
        DataManager._df = test_df
        DataManager._categorical_columns = ['benchmark', 'config']
        DataManager._statistic_columns = ['simTicks']
        DataManager._csvPath = str(csv_file)
        
        config = {
            'outlierRemover': {
                'outlierStat': 'simTicks'
            }
        }
        params = MockAnalyzerInfo(config)
        
        # Execute remover
        remover = OutlierRemover(params, config)
        remover()
        
        # Verify outlier was removed
        result = DataManager._df
        assert len(result) < 10
        assert result['simTicks'].max() <= 105  # Should not include 500
    
    def test_preserves_data_within_q3(self, tmp_path):
        """Test that data within Q3 is preserved."""
        # Create data without outliers
        test_df = pd.DataFrame({
            'benchmark': ['bzip2'] * 5,
            'config': ['baseline'] * 5,
            'simTicks': [100, 101, 102, 103, 104]
        })
        
        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)
        
        DataManager._df = test_df
        DataManager._categorical_columns = ['benchmark', 'config']
        DataManager._statistic_columns = ['simTicks']
        DataManager._csvPath = str(csv_file)
        
        config = {
            'outlierRemover': {
                'outlierStat': 'simTicks'
            }
        }
        params = MockAnalyzerInfo(config)
        
        # Execute remover
        remover = OutlierRemover(params, config)
        remover()
        
        # Should preserve most or all data
        result = DataManager._df
        assert len(result) >= 3  # At least some data preserved


class TestPreprocessor:
    """Test the Preprocessor data manager."""
    
    def test_divide_operator(self, tmp_path):
        """Test divide operation."""
        test_df = pd.DataFrame({
            'benchmark': ['bzip2', 'gcc'],
            'simTicks': [1000, 2000],
            'instructions': [500, 1000]
        })
        
        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)
        
        DataManager._df = test_df
        DataManager._categorical_columns = ['benchmark']
        DataManager._statistic_columns = ['simTicks', 'instructions']
        DataManager._csvPath = str(csv_file)
        
        config = {
            'preprocessor': {
                'cpi': {
                    'operator': 'divide',
                    'src1': 'simTicks',
                    'src2': 'instructions'
                }
            }
        }
        params = MockAnalyzerInfo(config)
        
        # Execute preprocessor
        preprocessor = Preprocessor(params, config)
        preprocessor()
        
        # Verify new column was created
        result = DataManager._df
        assert 'cpi' in result.columns
        assert result.iloc[0]['cpi'] == 2.0  # 1000/500
        assert result.iloc[1]['cpi'] == 2.0  # 2000/1000
    
    def test_sum_operator(self, tmp_path):
        """Test sum operation."""
        test_df = pd.DataFrame({
            'benchmark': ['bzip2'],
            'value1': [100],
            'value2': [50]
        })
        
        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)
        
        DataManager._df = test_df
        DataManager._categorical_columns = ['benchmark']
        DataManager._statistic_columns = ['value1', 'value2']
        DataManager._csvPath = str(csv_file)
        
        config = {
            'preprocessor': {
                'total': {
                    'operator': 'sum',
                    'src1': 'value1',
                    'src2': 'value2'
                }
            }
        }
        params = MockAnalyzerInfo(config)
        
        # Execute preprocessor
        preprocessor = Preprocessor(params, config)
        preprocessor()
        
        # Verify sum was calculated
        result = DataManager._df
        assert 'total' in result.columns
        assert result.iloc[0]['total'] == 150


class TestDataManagerPipeline:
    """Integration tests for chaining multiple data managers."""
    
    def test_complete_pipeline(self, tmp_path):
        """Test a complete data processing pipeline."""
        # Create realistic test data
        test_df = pd.DataFrame({
            'benchmark': ['bzip2'] * 6 + ['gcc'] * 6,
            'config': ['baseline'] * 3 + ['optimized'] * 3 + ['baseline'] * 3 + ['optimized'] * 3,
            'random_seed': [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3],
            'simTicks': [1000, 1010, 990, 800, 810, 790, 2000, 2020, 1980, 1600, 1620, 1580],
            'instructions': [500, 505, 495, 500, 505, 495, 1000, 1010, 990, 1000, 1010, 990]
        })
        
        csv_file = tmp_path / "test.csv"
        test_df.to_csv(csv_file, index=False)
        
        DataManager._df = test_df
        DataManager._categorical_columns = ['benchmark', 'config']
        DataManager._statistic_columns = ['simTicks', 'instructions']
        DataManager._csvPath = str(csv_file)
        
        # Step 1: Add CPI column via preprocessor
        preprocess_config = {
            'preprocessor': {
                'cpi': {
                    'operator': 'divide',
                    'src1': 'simTicks',
                    'src2': 'instructions'
                }
            }
        }
        params = MockAnalyzerInfo(preprocess_config)
        preprocessor = Preprocessor(params, preprocess_config)
        preprocessor()
        
        # Verify CPI was added
        assert 'cpi' in DataManager._df.columns
        
        # Step 2: Reduce seeds
        seeds_config = {'seedsReducer': True}
        params = MockAnalyzerInfo(seeds_config)
        reducer = SeedsReducer(params, seeds_config)
        reducer()
        
        # Verify seeds were reduced
        result = DataManager._df
        assert len(result) == 4  # 2 benchmarks × 2 configs
        assert 'random_seed' not in result.columns
        assert 'simTicks.sd' in result.columns
        
        # Verify data integrity
        assert not result.isnull().any().any()
        assert all(col in result.columns for col in ['benchmark', 'config', 'simTicks', 'cpi'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
