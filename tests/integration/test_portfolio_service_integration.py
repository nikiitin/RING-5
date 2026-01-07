
import pytest
import pandas as pd
import io
import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.web.services.portfolio_service import PortfolioService
from src.plotting.plot_factory import PlotFactory
from src.web.services.paths import PathService

# Fixture to mock the portfolios directory
@pytest.fixture
def mock_portfolios_dir(tmp_path):
    # Create a temporary directory for portfolios
    portfolios_dir = tmp_path / "portfolios"
    portfolios_dir.mkdir()
    
    # Mock PathService to return this directory
    with patch("src.web.services.paths.PathService.get_portfolios_dir", return_value=portfolios_dir):
        yield portfolios_dir

def test_save_and_load_portfolio(mock_portfolios_dir):
    """Test saving a portfolio and then loading it back to verify data integrity."""
    
    # 1. Setup Test Data
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    plot_config = {"x": "A", "y": "B"}
    
    # Create a dummy plot
    plot = PlotFactory.create_plot("bar", 1, "Test Plot")
    plot.result = df
    plot.config = plot_config
    
    config_state = {"theme": "dark"}
    parse_variables = ["var1", "var2"]
    
    # 2. Save Portfolio
    PortfolioService.save_portfolio(
        name="test_portfolio",
        data=df,
        plots=[plot],
        config=config_state,
        plot_counter=1,
        csv_path="/tmp/original.csv",
        parse_variables=parse_variables
    )
    
    # 3. Verify File Exists
    expected_file = mock_portfolios_dir / "test_portfolio.json"
    assert expected_file.exists()
    
    # 4. Load Portfolio
    loaded_data = PortfolioService.load_portfolio("test_portfolio")
    
    # 5. Verify Content
    assert loaded_data["version"] == "2.0"
    assert loaded_data["csv_path"] == "/tmp/original.csv"
    assert loaded_data["plot_counter"] == 1
    assert loaded_data["config"] == config_state
    assert loaded_data["parse_variables"] == parse_variables
    
    # Verify Data CSV reconstruction
    loaded_df_csv = loaded_data["data_csv"]
    loaded_df = pd.read_csv(io.StringIO(loaded_df_csv))
    pd.testing.assert_frame_equal(df, loaded_df)
    
    # Verify Plots
    assert len(loaded_data["plots"]) == 1
    loaded_plot = loaded_data["plots"][0]
    assert loaded_plot["name"] == "Test Plot"
    assert loaded_plot["id"] == 1
    assert loaded_plot["plot_type"] == "bar"
    assert loaded_plot["config"] == plot_config

def test_list_portfolios(mock_portfolios_dir):
    """Test listing available portfolios."""
    # Create two dummy portfolio files
    (mock_portfolios_dir / "p1.json").touch()
    (mock_portfolios_dir / "p2.json").touch()
    (mock_portfolios_dir / "not_a_portfolio.txt").touch()
    
    portfolios = PortfolioService.list_portfolios()
    assert set(portfolios) == {"p1", "p2"}

def test_delete_portfolio(mock_portfolios_dir):
    """Test deleting a portfolio."""
    # Create a dummy portfolio file
    p_path = mock_portfolios_dir / "to_delete.json"
    p_path.touch()
    
    assert p_path.exists()
    PortfolioService.delete_portfolio("to_delete")
    assert not p_path.exists()

def test_save_portfolio_empty_name(mock_portfolios_dir):
    """Test error handling for empty name."""
    with pytest.raises(ValueError, match="Portfolio name cannot be empty"):
        PortfolioService.save_portfolio("", pd.DataFrame(), [], {}, 0)

def test_load_nonexistent_portfolio(mock_portfolios_dir):
    """Test error handling for loading missing portfolio."""
    with pytest.raises(FileNotFoundError):
        PortfolioService.load_portfolio("ghost")
