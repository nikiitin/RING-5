import io
from unittest.mock import patch

import pandas as pd
import pytest

from src.core.services.portfolio_service import PortfolioService
from src.core.state.state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.plot_factory import PlotFactory


# Fixture to mock the portfolios directory
@pytest.fixture
def mock_portfolios_dir(tmp_path):
    # Create a temporary directory for portfolios
    portfolios_dir = tmp_path / "portfolios"
    portfolios_dir.mkdir()

    # Mock PathService to return this directory
    with patch(
        "src.core.services.paths.PathService.get_portfolios_dir", return_value=portfolios_dir
    ):
        yield portfolios_dir


@pytest.fixture
def mock_session_state():
    """Mock streamlit.session_state as a dictionary."""
    with patch("streamlit.session_state", new_callable=dict) as mock_state:
        yield mock_state


@pytest.fixture
def state_manager(mock_session_state):
    """Initialize RepositoryStateManager with mocked session state."""
    return RepositoryStateManager()


@pytest.fixture
def portfolio_service(state_manager, mock_portfolios_dir):
    """Create PortfolioService instance."""
    return PortfolioService(state_manager)


def test_save_and_load_portfolio(portfolio_service, tmp_path, mock_portfolios_dir, state_manager):
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

    # Setup state manager mocks to return expected values for stats config
    # Since RepositoryStateManager reads from session_state repositories,
    # passed via mock_session_state
    # Or we can just let it read defaults which are fine.

    # 2. Save Portfolio (using instance method)
    portfolio_service.save_portfolio(
        name="test_portfolio",
        data=df,
        plots=[plot],
        config=config_state,
        plot_counter=1,
        csv_path=str(tmp_path / "original.csv"),
        parse_variables=parse_variables,
    )

    # 3. Verify File Exists
    expected_file = mock_portfolios_dir / "test_portfolio.json"
    assert expected_file.exists()

    # 4. Load Portfolio (using instance method)
    loaded_data = portfolio_service.load_portfolio("test_portfolio")

    # 5. Verify Content
    assert loaded_data["version"] == "2.0"
    assert loaded_data["csv_path"] == str(tmp_path / "original.csv")
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


def test_list_portfolios(portfolio_service, mock_portfolios_dir):
    """Test listing available portfolios."""
    # Create two dummy portfolio files
    (mock_portfolios_dir / "p1.json").touch()
    (mock_portfolios_dir / "p2.json").touch()
    (mock_portfolios_dir / "not_a_portfolio.txt").touch()

    portfolios = portfolio_service.list_portfolios()
    assert set(portfolios) == {"p1", "p2"}


def test_delete_portfolio(portfolio_service, mock_portfolios_dir):
    """Test deleting a portfolio."""
    # Create a dummy portfolio file
    p_path = mock_portfolios_dir / "to_delete.json"
    p_path.touch()

    assert p_path.exists()
    portfolio_service.delete_portfolio("to_delete")
    assert not p_path.exists()


def test_save_portfolio_empty_name(portfolio_service):
    """Test error handling for empty name."""
    with pytest.raises(ValueError, match="Portfolio name cannot be empty"):
        portfolio_service.save_portfolio("", pd.DataFrame(), [], {}, 0)


def test_load_nonexistent_portfolio(portfolio_service):
    """Test error handling for loading missing portfolio."""
    with pytest.raises(FileNotFoundError):
        portfolio_service.load_portfolio("ghost")
