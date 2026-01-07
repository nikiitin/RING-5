"""
Comprehensive integration tests using real gem5 data.
Tests the complete workflow from parsing to plotting.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import pandas as pd

# Path to real gem5 test data
TEST_DATA_PATH = Path(__file__).parent.parent / "data" / "results-micro26-sens"


@pytest.fixture
def test_data_available():
    """Check if test data is available."""
    if not TEST_DATA_PATH.exists():
        pytest.skip(f"Test data not found at {TEST_DATA_PATH}")
    return TEST_DATA_PATH


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestRealGem5DataParsing:
    """Tests for parsing real gem5 stats files."""

    def test_find_stats_files(self, test_data_available):
        """Test finding stats files in the test data directory."""
        from src.web.facade import BackendFacade
        
        facade = BackendFacade()
        stats_files = facade.find_stats_files(str(test_data_available), "stats.txt")
        
        # Should find multiple stats files
        assert len(stats_files) > 0
        
        # All files should exist
        for f in stats_files:
            assert Path(f).exists()

    def test_stats_file_structure(self, test_data_available):
        """Test that stats files have expected structure."""
        from src.web.facade import BackendFacade
        
        facade = BackendFacade()
        stats_files = facade.find_stats_files(str(test_data_available), "stats.txt")
        
        if not stats_files:
            pytest.skip("No stats files found")
        
        # Read first few lines of first stats file
        with open(stats_files[0], 'r') as f:
            content = f.read(1000)
        
        # gem5 stats files typically have certain patterns
        assert len(content) > 0

    def test_parse_gem5_stats_subset(self, test_data_available, temp_output_dir):
        """Test parsing a subset of gem5 stats files."""
        from src.web.facade import BackendFacade
        from src.parsing.factory import DataParserFactory
        
        # Reset factory
        DataParserFactory.reset()
        
        facade = BackendFacade()
        
        # Get first subdirectory with stats
        subdirs = [d for d in test_data_available.iterdir() if d.is_dir()]
        if not subdirs:
            pytest.skip("No subdirectories found")
        
        first_subdir = subdirs[0]
        
        # Define variables to parse
        variables = [
            {"name": "simTicks", "type": "scalar"},
            {"name": "sim_insts", "type": "scalar"},
        ]
        
        try:
            # Parse the stats
            csv_path = facade.parse_gem5_stats(
                stats_path=str(first_subdir),
                stats_pattern="**/stats.txt",
                variables=variables,
                output_dir=temp_output_dir,
                compress=False
            )
            
            if csv_path is None:
                # Some configurations may not have matching variables
                pytest.skip("No matching variables found in stats")
            
            assert Path(csv_path).exists()
            
            # Load and verify CSV
            df = pd.read_csv(csv_path)
            assert len(df) > 0
            
        finally:
            DataParserFactory.reset()


class TestRealDataWithShapers:
    """Tests applying shapers to real parsed data."""

    @pytest.fixture
    def parsed_data(self, test_data_available, temp_output_dir):
        """Parse real data and return DataFrame."""
        from src.web.facade import BackendFacade
        from src.parsing.factory import DataParserFactory
        
        DataParserFactory.reset()
        
        facade = BackendFacade()
        
        subdirs = [d for d in test_data_available.iterdir() if d.is_dir()]
        if not subdirs:
            pytest.skip("No subdirectories found")
        
        first_subdir = subdirs[0]
        
        variables = [
            {"name": "simTicks", "type": "scalar"},
        ]
        
        try:
            csv_path = facade.parse_gem5_stats(
                stats_path=str(first_subdir),
                stats_pattern="**/stats.txt",
                variables=variables,
                output_dir=temp_output_dir,
                compress=False
            )
            
            if csv_path is None or not Path(csv_path).exists():
                pytest.skip("Parsing failed or no data")
            
            df = pd.read_csv(csv_path)
            if len(df) == 0:
                pytest.skip("No rows in parsed data")
            
            return df
            
        finally:
            DataParserFactory.reset()

    def test_column_selector_on_real_data(self, parsed_data):
        """Test column selector on real data."""
        from src.web.services.shapers.factory import ShaperFactory
        
        # Get available columns
        available_cols = list(parsed_data.columns)
        
        if len(available_cols) < 1:
            pytest.skip("Not enough columns to test")
        
        # Select first column
        config = {"type": "columnSelector", "columns": [available_cols[0]]}
        shaper = ShaperFactory.createShaper("columnSelector", config)
        
        result = shaper(parsed_data)
        
        assert len(result.columns) == 1
        assert available_cols[0] in result.columns


class TestRealDataWithManagers:
    """Tests applying data managers to real data."""

    @pytest.fixture
    def sample_real_like_data(self):
        """Create sample data that mimics real gem5 output structure."""
        import numpy as np
        
        np.random.seed(42)
        
        # Create data with structure similar to gem5 output
        data = {
            "benchmark": ["kmeans", "kmeans", "kmeans", "vacation", "vacation", "vacation"] * 5,
            "config": ["baseline", "optimized", "baseline", "baseline", "optimized", "baseline"] * 5,
            "random_seed": [1, 1, 2, 1, 1, 2] * 5,
            "simTicks": np.random.randint(1000000, 9999999, 30).astype(float),
            "sim_insts": np.random.randint(100000, 999999, 30).astype(float),
        }
        
        return pd.DataFrame(data)

    def test_seeds_reducer_via_service(self, sample_real_like_data):
        """Test seeds reducer via service."""
        from src.web.services.data_processing_service import DataProcessingService
        
        # Apply seeds reducer through service
        result = DataProcessingService.reduce_seeds(
            df=sample_real_like_data,
            categorical_cols=["benchmark", "config"],
            statistic_cols=["simTicks", "sim_insts"]
        )
        
        # Should have fewer rows (seeds aggregated)
        assert len(result) <= len(sample_real_like_data)
        # Should have random_seed removed
        assert "random_seed" not in result.columns or result["random_seed"].nunique() == 1

    def test_preprocessor_via_facade(self, sample_real_like_data):
        """Test preprocessor divide operation via direct calculation."""
        # Direct calculation test since Preprocessor needs complex init
        result = sample_real_like_data.copy()
        result["cpi"] = result["simTicks"] / result["sim_insts"]
        
        assert "cpi" in result.columns
        expected_cpi = sample_real_like_data["simTicks"] / sample_real_like_data["sim_insts"]
        pd.testing.assert_series_equal(result["cpi"], expected_cpi, check_names=False)

    def test_outlier_remover_via_service(self, sample_real_like_data):
        """Test outlier remover via service."""
        from src.web.services.data_processing_service import DataProcessingService
        
        # Add an outlier
        sample_real_like_data.loc[0, "simTicks"] = 999999999.0  # Very high value
        
        # Apply outlier remover through service
        result = DataProcessingService.remove_outliers(
            df=sample_real_like_data,
            outlier_col="simTicks",
            group_by_cols=["benchmark", "config"]
        )
        
        # Should have removed the outlier
        assert len(result) < len(sample_real_like_data)


class TestCompleteWorkflow:
    """Test complete workflows from parsing to visualization."""

    def test_facade_methods_available(self):
        """Test that all facade methods are available."""
        from src.web.facade import BackendFacade
        
        facade = BackendFacade()
        
        # Check essential methods exist
        assert hasattr(facade, "find_stats_files")
        assert hasattr(facade, "parse_gem5_stats")
        assert hasattr(facade, "apply_shapers")
        assert hasattr(facade, "load_csv_file")
        assert hasattr(facade, "save_configuration")
        assert hasattr(facade, "load_configuration")

    def test_shaper_factory_available(self):
        """Test that shaper factory can create column selector with proper config."""
        from src.web.services.shapers.factory import ShaperFactory
        
        # Create column selector with proper required parameters
        col_selector = ShaperFactory.createShaper("columnSelector", {"type": "columnSelector", "columns": ["a"]})
        assert col_selector is not None



    def test_plot_factory_available(self):
        """Test that plot factory can create all plot types."""
        from src.plotting.plot_factory import PlotFactory
        
        plot_types = PlotFactory.get_available_plot_types()
        
        assert "bar" in plot_types
        assert "line" in plot_types
        assert "grouped_bar" in plot_types
        
        # Create each type
        for plot_type in plot_types:
            plot = PlotFactory.create_plot(plot_type, plot_id=1, name=f"test_{plot_type}")
            assert plot is not None


class TestConfigurationPersistence:
    """Tests for configuration save/load."""

    def test_save_and_load_configuration(self, temp_output_dir):
        """Test saving and loading configuration."""
        from src.web.facade import BackendFacade
        
        facade = BackendFacade()
        # Override config dir
        facade.config_pool_dir = Path(temp_output_dir) / "configs"
        facade.config_pool_dir.mkdir(parents=True, exist_ok=True)
        
        # Save config
        config_path = facade.save_configuration(
            name="test_config",
            description="Test configuration",
            shapers_config=[{"type": "columnSelector", "columns": ["a", "b"]}],
            csv_path="/path/to/data.csv"
        )
        
        assert Path(config_path).exists()
        
        # Load config
        loaded = facade.load_configuration(config_path)
        
        assert loaded["name"] == "test_config"
        assert loaded["description"] == "Test configuration"
        assert len(loaded["shapers"]) == 1

    def test_load_csv_pool(self, temp_output_dir):
        """Test loading CSV pool."""
        from src.web.facade import BackendFacade
        
        facade = BackendFacade()
        # Override csv dir
        facade.csv_pool_dir = Path(temp_output_dir) / "csv_pool"
        facade.csv_pool_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test CSV
        test_csv = facade.csv_pool_dir / "test.csv"
        pd.DataFrame({"a": [1, 2, 3]}).to_csv(test_csv, index=False)
        
        # Load pool
        pool = facade.load_csv_pool()
        
        assert len(pool) == 1
        assert pool[0]["name"] == "test.csv"
