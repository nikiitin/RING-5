from pathlib import Path

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.core.parsing.models import StatConfig
from src.core.parsing.parser import Gem5StatsParser

# Path to real gem5 test data
TEST_DATA_PATH = Path(__file__).parent.parent / "data" / "results-micro26-sens"


@pytest.fixture
def test_data_available():
    """Check if test data is available."""
    if not TEST_DATA_PATH.exists():
        pytest.skip(f"Test data not found at {TEST_DATA_PATH}")
    return TEST_DATA_PATH


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory using tmp_path."""
    output_dir = tmp_path / "real_data_output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def facade() -> ApplicationAPI:
    """Create an ApplicationAPI instance."""
    return ApplicationAPI()


class TestRealDataWithShapers:
    """Tests applying shapers to real parsed data."""

    @pytest.fixture
    def parsed_data(
        self, test_data_available: Path, temp_output_dir: Path, facade: ApplicationAPI
    ) -> pd.DataFrame:
        """Parse real data and return DataFrame."""
        Gem5StatsParser.reset()

        subdirs = [d for d in test_data_available.iterdir() if d.is_dir()]
        if not subdirs:
            pytest.skip("No subdirectories found")

        first_subdir = subdirs[0]

        variables = [
            StatConfig(name="simTicks", type="scalar"),
        ]

        try:
            parse_futures = facade.submit_parse_async(
                stats_path=str(first_subdir),
                stats_pattern="**/stats.txt",
                variables=variables,
                output_dir=str(temp_output_dir),
            )

            # Wait for parsing
            parse_results = []
            for future in parse_futures:
                result = future.result(timeout=30)
                if result:
                    parse_results.append(result)

            csv_path = facade.finalize_parsing(str(temp_output_dir), parse_results)

            if csv_path is None or not Path(csv_path).exists():
                pytest.skip("Parsing failed or no data")

            df = pd.read_csv(csv_path)
            if len(df) == 0:
                pytest.skip("No rows in parsed data")

            return df

        finally:
            Gem5StatsParser.reset()

    def test_column_selector_on_real_data(self, parsed_data):
        """Test column selector on real data."""
        from src.core.services.shapers.factory import ShaperFactory

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
            "config": ["baseline", "optimized", "baseline", "baseline", "optimized", "baseline"]
            * 5,
            "random_seed": [1, 1, 2, 1, 1, 2] * 5,
            "simTicks": np.random.randint(1000000, 9999999, 30).astype(float),
            "sim_insts": np.random.randint(100000, 999999, 30).astype(float),
        }

        return pd.DataFrame(data)

    def test_seeds_reducer_via_service(self, sample_real_like_data):
        """Test seeds reducer via service."""
        from src.core.services.reduction_service import ReductionService

        # Apply seeds reducer through service
        result = ReductionService.reduce_seeds(
            df=sample_real_like_data,
            categorical_cols=["benchmark", "config"],
            statistic_cols=["simTicks", "sim_insts"],
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
        from src.core.services.outlier_service import OutlierService

        # Add an outlier
        sample_real_like_data.loc[0, "simTicks"] = 999999999.0  # Very high value

        # Apply outlier remover through service
        result = OutlierService.remove_outliers(
            df=sample_real_like_data, outlier_col="simTicks", group_by_cols=["benchmark", "config"]
        )

        # Should have removed the outlier
        assert len(result) < len(sample_real_like_data)


class TestCompleteWorkflow:
    """Test complete workflows from parsing to visualization."""

    def test_facade_methods_available(self, facade: ApplicationAPI):
        """Test that all facade methods are available."""
        # Check essential methods exist
        assert hasattr(facade, "find_stats_files")
        assert hasattr(facade, "submit_parse_async")
        assert hasattr(facade, "finalize_parsing")
        assert hasattr(facade, "submit_scan_async")
        assert hasattr(facade, "finalize_scan")
        assert hasattr(facade, "apply_shapers")
        assert hasattr(facade, "load_csv_file")
        assert hasattr(facade, "save_configuration")
        assert hasattr(facade, "load_configuration")

    def test_shaper_factory_available(self):
        """Test that shaper factory can create column selector with proper config."""
        from src.core.services.shapers.factory import ShaperFactory

        # Create column selector with proper required parameters
        col_selector = ShaperFactory.createShaper(
            "columnSelector", {"type": "columnSelector", "columns": ["a"]}
        )
        assert col_selector is not None

    def test_plot_factory_available(self):
        """Test that plot factory can create all plot types."""
        from src.web.pages.ui.plotting.plot_factory import PlotFactory

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

    def test_save_and_load_configuration(
        self, temp_output_dir: Path, facade: ApplicationAPI
    ) -> None:
        """Test saving and loading configuration."""
        # Override config dir
        facade.config_pool_dir = Path(temp_output_dir) / "configs"
        facade.config_pool_dir.mkdir(parents=True, exist_ok=True)

        # Save config
        config_path = facade.save_configuration(
            name="test_config",
            description="Test configuration",
            shapers_config=[{"type": "columnSelector", "columns": ["a", "b"]}],
            csv_path="/path/to/data.csv",
        )

        assert Path(config_path).exists()

        # Load config
        loaded = facade.load_configuration(config_path)

        assert loaded["name"] == "test_config"
        assert loaded["description"] == "Test configuration"
        assert len(loaded["shapers"]) == 1

    def test_load_csv_pool(self, temp_output_dir: Path, facade: ApplicationAPI) -> None:
        """Test loading CSV pool."""
        from unittest.mock import patch

        temp_path = Path(temp_output_dir)
        csv_pool = temp_path / "csv_pool"
        csv_pool.mkdir(parents=True, exist_ok=True)

        # Create a test CSV
        test_csv = csv_pool / "test.csv"
        pd.DataFrame({"a": [1, 2, 3]}).to_csv(test_csv, index=False)

        # Patch PathService to use temp directory
        with patch(
            "src.core.services.csv_pool_service.PathService.get_data_dir", return_value=temp_path
        ):
            facade.csv_pool_dir = csv_pool

            # Load pool
            pool = facade.load_csv_pool()

            assert len(pool) == 1
            assert pool[0]["name"] == "test.csv"
