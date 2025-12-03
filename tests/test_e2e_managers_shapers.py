"""End-to-end tests for data managers and shapers using real gem5 data."""
import pytest
import pandas as pd
import shutil
import os
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.data_management.impl.seedsReducer import SeedsReducer
from src.data_management.impl.outlierRemover import OutlierRemover
from src.data_management.impl.preprocessor import Preprocessor
from src.data_management.dataManager import DataManager
from data_plotter.src.shaper.impl.selector_algorithms.columnSelector import ColumnSelector
from data_plotter.src.shaper.impl.mean import Mean
from data_plotter.src.shaper.impl.normalize import Normalize
from data_plotter.src.shaper.impl.sort import Sort

# Import test utilities
sys.path.insert(0, str(Path(__file__).parent / 'pytests'))
from common.csvComparer import CsvComparer


class MockAnalyzerInfo:
    """Mock AnalyzerInfo for testing."""
    def __init__(self, config_json):
        self.json = config_json
        self._workCsv = None
        self._tmpDir = None
        self._categoricalColumns = []
        self._statisticColumns = []
    
    def getWorkCsv(self):
        return self._workCsv
    
    def getTmpDir(self):
        return self._tmpDir or os.getcwd()
    
    def getCategoricalColumns(self):
        return self._categoricalColumns
    
    def getStatisticColumns(self):
        return self._statisticColumns
    
    def setWorkCsv(self, csv_path):
        self._workCsv = csv_path
    
    def setTmpDir(self, tmpDir):
        self._tmpDir = tmpDir
    
    def setCategoricalColumns(self, cols):
        self._categoricalColumns = cols
    
    def setStatisticColumns(self, cols):
        self._statisticColumns = cols


class TestE2EManagers:
    """End-to-end tests for data managers using real gem5 data."""
    
    inputsDir = os.path.relpath("tests/pytests/mock/inputs")
    expectsDir = os.path.relpath("tests/pytests/mock/expects")
    
    def test_e2e_preprocessor_divide_with_gem5_data(self, tmp_path):
        """Test Preprocessor divide operation with real gem5 data."""
        # Copy input CSV
        input_csv = os.path.join(self.inputsDir, "csv/configurer/configurer_test_case01.csv")
        test_csv = tmp_path / "test_divide.csv"
        shutil.copyfile(input_csv, test_csv)
        
        # Load data
        data = pd.read_csv(test_csv, sep=r'\s+')
        
        # Set up DataManager globals
        DataManager._df = data.copy()
        DataManager._categorical_columns = ['benchmark_name', 'config_description_abbrev']
        DataManager._statistic_columns = data.select_dtypes(include=['number']).columns.tolist()
        DataManager._csvPath = str(test_csv)
        
        # Create mock AnalyzerInfo with divide operation
        mock_info = MockAnalyzerInfo({})
        mock_info.setWorkCsv(str(test_csv))
        mock_info.setTmpDir(str(tmp_path))
        
        # JSON config for divide operation
        json_config = {
            "operation": "divide",
            "column1": "flits_injected__get_summary",
            "column2": "simTicks"
        }
        
        # Execute Preprocessor
        preprocessor = Preprocessor(mock_info, json_config)
        preprocessor.manage()
        
        # Verify results
        result_df = DataManager._df
        
        # Should have new column with divide result
        assert result_df is not None
        new_col = "flits_injected__get_summary/simTicks"
        assert new_col in result_df.columns
        
        # Verify calculation is correct for first row
        if len(result_df) > 0:
            expected = result_df['flits_injected__get_summary'].iloc[0] / result_df['simTicks'].iloc[0]
            actual = result_df[new_col].iloc[0]
            assert abs(expected - actual) < 0.0001
    
    def test_e2e_manager_pipeline(self, tmp_path):
        """Test complete manager pipeline: Preprocessor -> Outlier Remover."""
        # Copy input CSV
        input_csv = os.path.join(self.inputsDir, "csv/configurer/configurer_test_case01.csv")
        test_csv = tmp_path / "test_pipeline.csv"
        shutil.copyfile(input_csv, test_csv)
        
        # Load data
        data = pd.read_csv(test_csv, sep=r'\s+')
        
        # Set up DataManager globals
        DataManager._df = data.copy()
        DataManager._categorical_columns = ['benchmark_name', 'config_description_abbrev']
        DataManager._statistic_columns = data.select_dtypes(include=['number']).columns.tolist()
        DataManager._csvPath = str(test_csv)
        
        # Step 1: Preprocessor - create efficiency metric
        preprocess_info = MockAnalyzerInfo({})
        preprocess_info.setWorkCsv(str(test_csv))
        preprocess_info.setTmpDir(str(tmp_path))
        
        preprocessor = Preprocessor(preprocess_info, {
            "operation": "divide",
            "column1": "flits_injected__get_summary",
            "column2": "simTicks"
        })
        preprocessor.manage()
        
        # Verify preprocessing worked
        assert "flits_injected__get_summary/simTicks" in DataManager._df.columns
        
        # Step 2: OutlierRemover - remove outliers
        outlier_info = MockAnalyzerInfo({})
        outlier_info.setWorkCsv(str(test_csv))
        outlier_info.setTmpDir(str(tmp_path))
        
        original_len = len(DataManager._df)
        remover = OutlierRemover(outlier_info, {})
        remover.manage()
        
        # Final verification
        final_df = DataManager._df
        assert final_df is not None
        assert len(final_df) > 0
        
        # All transformations should be preserved
        assert "flits_injected__get_summary/simTicks" in final_df.columns
        assert "benchmark_name" in final_df.columns


class TestE2EShapers:
    """End-to-end tests for shapers using real gem5 data."""
    
    inputsDir = os.path.relpath("tests/pytests/mock/inputs")
    expectsDir = os.path.relpath("tests/pytests/mock/expects")
    configDir = os.path.relpath("tests/pytests/mock/config_files/json_components/config")
    
    def test_e2e_column_selector_with_gem5_data(self, tmp_path):
        """Test ColumnSelector shaper with real gem5 data."""
        # Copy input CSV
        input_csv = os.path.join(self.inputsDir, "csv/configurer/configurer_test_case01.csv")
        test_csv = tmp_path / "test_selector.csv"
        shutil.copyfile(input_csv, test_csv)
        
        # Load data
        data = pd.read_csv(test_csv, sep=r'\s+')
        
        # Create ColumnSelector to select specific columns
        selected_cols = ['benchmark_name', 'config_description_abbrev', 'simTicks']
        selector = ColumnSelector({
            "columns": selected_cols
        })
        
        # Execute selector
        result_df = selector(data)
        
        # Verify results
        assert result_df is not None
        assert len(result_df) == len(data)  # Same number of rows
        assert list(result_df.columns) == selected_cols  # Only selected columns
        
        # Data should be preserved
        assert result_df['benchmark_name'].equals(data['benchmark_name'])
        assert result_df['simTicks'].equals(data['simTicks'])
    
    def test_e2e_sort_with_gem5_data(self, tmp_path):
        """Test Sort shaper with real gem5 data."""
        # Copy input CSV
        input_csv = os.path.join(self.inputsDir, "csv/configurer/configurer_test_case01.csv")
        test_csv = tmp_path / "test_sort.csv"
        shutil.copyfile(input_csv, test_csv)
        
        # Load data
        data = pd.read_csv(test_csv, sep=r'\s+')
        
        # Create custom sort order
        benchmark_order = [
            'llb-l', 'llb-h', 'cadd', 'bayes', 'genome',
            'intruder', 'intruder-qs', 'kmeans-l', 'kmeans-h',
            'labyrinth', 'ssca2', 'vacation-l', 'vacation-h', 'yada'
        ]
        
        sorter = Sort({
            "order_dict": {
                "benchmark_name": benchmark_order
            }
        })
        
        # Execute sort
        result_df = sorter(data)
        
        # Verify results
        assert result_df is not None
        assert len(result_df) == len(data)
        
        # Check that benchmarks appear in order (at least the ones that exist)
        unique_benchmarks = result_df['benchmark_name'].unique()
        prev_idx = -1
        for benchmark in unique_benchmarks:
            if benchmark in benchmark_order:
                curr_idx = benchmark_order.index(benchmark)
                assert curr_idx >= prev_idx, f"Benchmarks not in order: {benchmark} at {curr_idx}, prev was {prev_idx}"
                prev_idx = curr_idx
    
    def test_e2e_mean_with_gem5_data(self, tmp_path):
        """Test Mean shaper with real gem5 data."""
        # Copy input CSV
        input_csv = os.path.join(self.inputsDir, "csv/configurer/configurer_test_case01.csv")
        test_csv = tmp_path / "test_mean.csv"
        shutil.copyfile(input_csv, test_csv)
        
        # Load data
        data = pd.read_csv(test_csv, sep=r'\s+')
        
        # Select only the columns we need
        data = data[['benchmark_name', 'config_description_abbrev', 'simTicks']]
        
        # Create Mean shaper
        mean_shaper = Mean({
            "meanAlgorithm": "arithmean",
            "meanVars": ["simTicks"],
            "groupingColumn": "config_description_abbrev",
            "replacingColumn": "benchmark_name"
        })
        
        # Execute mean
        result_df = mean_shaper(data)
        
        # Verify results
        assert result_df is not None
        assert len(result_df) > len(data)  # Should have added mean rows
        
        # Should have 'arithmean' in benchmark_name
        assert 'arithmean' in result_df['benchmark_name'].values
    
    def test_e2e_normalize_with_gem5_data(self, tmp_path):
        """Test Normalize shaper with real gem5 data."""
        # Copy input CSV
        input_csv = os.path.join(self.inputsDir, "csv/configurer/configurer_test_case01.csv")
        test_csv = tmp_path / "test_normalize.csv"
        shutil.copyfile(input_csv, test_csv)
        
        # Load data
        data = pd.read_csv(test_csv, sep=r'\s+')
        
        # Select only the columns we need
        data = data[['benchmark_name', 'config_description_abbrev', 'simTicks']]
        
        # Create Normalize shaper
        normalize_shaper = Normalize({
            "normalizeVars": ["simTicks"],
            "normalizerColumn": "config_description_abbrev",
            "normalizerValue": "CPUtest_BinSfx.htm.fallbacklock_LV_ED_CRrw_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_Rtry6_Pflt",
            "groupBy": ["benchmark_name"]
        })
        
        # Execute normalize
        result_df = normalize_shaper(data)
        
        # Verify results
        assert result_df is not None
        assert len(result_df) == len(data)  # Should have same number of rows
        
        # Check that baseline configuration exists for each benchmark
        baseline_rows = result_df[
            result_df['config_description_abbrev'] == 
            "CPUtest_BinSfx.htm.fallbacklock_LV_ED_CRrw_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_Rtry6_Pflt"
        ]
        assert len(baseline_rows) > 0, "No baseline rows found"
        
        # For single variable normalization, each baseline value should be 1.0
        # (since there's only one variable, dividing by sum equals dividing by itself)
        assert all(baseline_rows['simTicks'] == 1.0), "With single variable, baseline rows should all be 1.0"
        
        # Check that other configurations are normalized (not 1.0 unless they match baseline)
        # At least some non-baseline rows should exist
        non_baseline_rows = result_df[
            result_df['config_description_abbrev'] != 
            "CPUtest_BinSfx.htm.fallbacklock_LV_ED_CRrw_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_Rtry6_Pflt"
        ]
        assert len(non_baseline_rows) > 0, "Should have non-baseline rows"
    
    def test_e2e_shaper_pipeline(self, tmp_path):
        """Test complete shaper pipeline: ColumnSelector -> Mean -> Sort."""
        # Copy input CSV
        input_csv = os.path.join(self.inputsDir, "csv/configurer/configurer_test_case01.csv")
        test_csv = tmp_path / "test_shaper_pipeline.csv"
        shutil.copyfile(input_csv, test_csv)
        
        # Load data
        data = pd.read_csv(test_csv, sep=r'\s+')
        
        # Step 1: ColumnSelector - select columns
        selected_cols = ['benchmark_name', 'config_description_abbrev', 'simTicks']
        selector = ColumnSelector({"columns": selected_cols})
        data = selector(data)
        
        assert list(data.columns) == selected_cols
        
        # Step 2: Mean - calculate mean grouped by config
        mean_shaper = Mean({
            "meanAlgorithm": "arithmean",
            "meanVars": ["simTicks"],
            "groupingColumn": "config_description_abbrev",
            "replacingColumn": "benchmark_name"
        })
        data = mean_shaper(data)
        
        # Should have mean row added
        assert 'arithmean' in data['benchmark_name'].values
        
        # Step 3: Sort - sort by benchmark name
        benchmark_order = [
            'llb-l', 'llb-h', 'cadd', 'bayes', 'genome',
            'intruder', 'intruder-qs', 'kmeans-l', 'kmeans-h',
            'labyrinth', 'ssca2', 'vacation-l', 'vacation-h', 'yada',
            'arithmean'
        ]
        sorter = Sort({
            "order_dict": {
                "benchmark_name": benchmark_order
            }
        })
        data = sorter(data)
        
        # Final verification
        assert data is not None
        assert len(data) > 0
        assert 'arithmean' in data['benchmark_name'].values
        assert list(data.columns) == selected_cols


class TestE2EIntegration:
    """Integration tests combining managers and shapers."""
    
    inputsDir = os.path.relpath("tests/pytests/mock/inputs")
    
    def test_e2e_simple_workflow_with_gem5_data(self, tmp_path):
        """Test simple end-to-end workflow with real gem5 data: load → select → sort."""
        # Copy input CSV
        input_csv = os.path.join(self.inputsDir, "csv/configurer/configurer_test_case01.csv")
        test_csv = tmp_path / "test_simple_e2e.csv"
        shutil.copyfile(input_csv, test_csv)
        
        # Load real gem5 benchmark data
        data = pd.read_csv(test_csv, sep=r'\s+')
        
        print(f"\n✅ Loaded gem5 data: {len(data)} rows × {len(data.columns)} columns")
        print(f"   Benchmarks: {data['benchmark_name'].unique()[:5]}...")
        print(f"   Configs: {len(data['config_description_abbrev'].unique())} unique configurations")
        
        # Step 1: ColumnSelector - select key metrics
        selector = ColumnSelector({
            "columns": ['benchmark_name', 'config_description_abbrev', 'simTicks', 'branchMispredicts']
        })
        shaped_data = selector(data)
        
        assert shaped_data is not None
        assert len(shaped_data) == len(data)
        assert len(shaped_data.columns) == 4
        print(f"\n✅ Column selection: reduced from {len(data.columns)} to {len(shaped_data.columns)} columns")
        
        # Step 2: Sort - order by benchmark
        benchmark_order = [
            'llb-l', 'llb-h', 'cadd', 'bayes', 'genome',
            'intruder', 'intruder-qs', 'kmeans-l', 'kmeans-h',
            'labyrinth', 'ssca2', 'vacation-l', 'vacation-h', 'yada'
        ]
        sorter = Sort({
            "order_dict": {
                "benchmark_name": benchmark_order
            }
        })
        final_data = sorter(shaped_data)
        
        assert final_data is not None
        assert len(final_data) > 0
        print(f"\n✅ Sorting: data ordered by benchmark")
        
        # Verify benchmarks are in order
        unique_benchmarks = final_data['benchmark_name'].unique()
        prev_idx = -1
        for benchmark in unique_benchmarks:
            if benchmark in benchmark_order:
                curr_idx = benchmark_order.index(benchmark)
                assert curr_idx >= prev_idx
                prev_idx = curr_idx
        
        # Save result
        result_csv = tmp_path / "e2e_result.csv"
        final_data.to_csv(result_csv, index=False)
        
        print(f"\n✅ COMPLETE E2E TEST SUCCESSFUL!")
        print(f"   - Input: Real gem5 configurer_test_case01.csv with {len(data)} rows")
        print(f"   - Applied: ColumnSelector → Sort")
        print(f"   - Output: {len(final_data)} rows × {len(final_data.columns)} columns")
        print(f"   - Result saved to: {result_csv}")
        print(f"   - Data properly filtered and ordered for gem5 HTM analysis")
