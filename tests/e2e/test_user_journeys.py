import shutil
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.parsers.parser import Gem5StatsParser
from src.web.facade import BackendFacade
from src.web.services.plot_service import PlotService
from src.web.services.portfolio_service import PortfolioService
from src.web.state_manager import StateManager

# Constants
TEST_DATA_PATH = Path(__file__).parent.parent / "data" / "results-micro26-sens"


@pytest.fixture
def test_data_available():
    """Check if test data is available."""
    if not TEST_DATA_PATH.exists():
        pytest.skip(f"Test data not found at {TEST_DATA_PATH}")
    return TEST_DATA_PATH


@pytest.fixture
def temp_env(tmp_path):
    """Setup a temporary environment for facade and services."""
    # Create temp structure
    ring5_dir = tmp_path / ".ring5"
    ring5_dir.mkdir()

    # Initialize facade
    facade = BackendFacade()

    # Override paths to use temp dir
    facade.ring5_data_dir = ring5_dir
    facade.csv_pool_dir = ring5_dir / "csv_pool"
    facade.config_pool_dir = ring5_dir / "saved_configs"
    facade.csv_pool_dir.mkdir()
    facade.config_pool_dir.mkdir()

    # Mock PathService for PortfolioService
    # PortfolioService uses PathService.get_portfolios_dir()
    # We need to patch it.
    portfolios_dir = ring5_dir / "portfolios"
    portfolios_dir.mkdir()

    from unittest.mock import patch

    patcher = patch(
        "src.web.services.paths.PathService.get_portfolios_dir", return_value=portfolios_dir
    )
    patcher.start()

    yield facade

    patcher.stop()
    # Cleanup logic if needed (tmp_path handles it)


def test_workflow_stats_to_portfolio(test_data_available, temp_env):
    """
    E2E Journey:
    1. Parse raw Gem5 stats.
    2. Load data.
    3. Create a Plot and configure a pipeline.
    4. Save the Portfolio.
    5. Load and Verify.
    """
    facade = temp_env

    # 1. Parse Stats
    # Use a small subset of variables
    variables = [
        {"name": "simTicks", "type": "scalar"},
        {"name": "sim_insts", "type": "scalar"},
    ]

    # Find a subdir
    subdirs = [d for d in test_data_available.iterdir() if d.is_dir()]
    if not subdirs:
        pytest.skip("No stats subdirectories found")

    output_dir = tempfile.mkdtemp()
    try:
        Gem5StatsParser.reset()
        parse_futures = facade.submit_parse_async(
            stats_path=str(subdirs[0]),
            stats_pattern="**/stats.txt",
            variables=variables,
            output_dir=output_dir,
        )

        # Wait for parsing
        parse_results = []
        for future in parse_futures:
            result = future.result(timeout=30)
            if result:
                parse_results.append(result)

        csv_path = facade.finalize_parsing(output_dir, parse_results)

        assert csv_path is not None, "Parsing failed"

        # 2. Load Data into State
        df = pd.read_csv(csv_path)
        StateManager.set_data(df)

        # 3. Create Plot
        StateManager.initialize()  # Init plots list
        plot = PlotService.create_plot("E2E Plot", "bar")

        # Configure Pipeline (e.g. simple column selection)
        # We simulate what UI does: append to pipeline list
        plot.pipeline.append(
            {
                "id": 0,
                "type": "columnSelector",
                "config": {"type": "columnSelector", "columns": ["simTicks", "sim_insts"]},
            }
        )
        plot.pipeline_counter = 1

        # Apply Pipeline (simulate 'Finalize' button).
        # Manually apply shapers as PlotService doesn't do it automatically.
        # Configure shaper manually as the UI would.

        processed_data = facade.apply_shapers(df, [s["config"] for s in plot.pipeline])
        plot.processed_data = processed_data

        assert "simTicks" in processed_data.columns
        assert "sim_insts" in processed_data.columns
        # ColumnSelector with columns=["simTicks", "sim_insts"] will keep only them.
        assert len(processed_data.columns) == 2

        # 4. Save Portfolio
        PortfolioService.save_portfolio(
            name="MyE2EPortfolio",
            data=df,
            plots=[plot],
            config={"theme": "light"},
            plot_counter=StateManager.get_plot_counter(),
            csv_path=csv_path,
        )

        # 5. Load and Verify
        loaded_portfolio = PortfolioService.load_portfolio("MyE2EPortfolio")

        assert loaded_portfolio["plots"][0]["name"] == "E2E Plot"
        assert len(loaded_portfolio["plots"][0]["pipeline"]) == 1

        # Verify CSV path persistence
        assert loaded_portfolio["csv_path"] == csv_path

    finally:
        shutil.rmtree(output_dir)


def test_workflow_failed_parsing_recovery(temp_env):
    """Test system resilience when parsing fails (e.g. empty variables)."""
    facade = temp_env

    empty_dir = tempfile.mkdtemp()
    try:
        # Empty variables should raise ValueError during parse
        with pytest.raises((ValueError, FileNotFoundError)):
            facade.submit_parse_async(
                stats_path=empty_dir,
                stats_pattern="**/stats.txt",
                variables=[],
                output_dir=empty_dir,
            )

    finally:
        shutil.rmtree(empty_dir)
