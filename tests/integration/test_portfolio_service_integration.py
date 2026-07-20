import io
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

from src.core.models import ColumnSemantics, DatasetSemantics
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.services.managers.semantic_metadata_service import SemanticMetadataService
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.fixture
def mock_session_state() -> Generator[Any, None, None]:
    """Mock streamlit.session_state as a dictionary."""
    with patch("streamlit.session_state", new_callable=dict) as mock_state:
        yield mock_state


@pytest.fixture
def state_manager(mock_session_state: Any) -> RepositoryStateManager:
    """Initialize RepositoryStateManager with mocked session state."""
    return RepositoryStateManager()


@pytest.fixture
def portfolio_service(state_manager: Any, portfolios_dir: Any) -> PortfolioService:
    """Create PortfolioService instance."""
    return PortfolioService(state_manager)


def test_save_and_load_portfolio(
    portfolio_service: Any, tmp_path: Any, portfolios_dir: Any, state_manager: Any
) -> None:
    # [test->req~ring5.portfolio.save~1]
    """Test saving a portfolio and then loading it back to verify data integrity."""

    # Setup Test Data
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    plot_config = {"x": "A", "y": "B"}

    # Create a dummy plot
    plot = PlotFactory.create_plot("bar", 1, "Test Plot")
    plot.processed_data = df
    plot.config = plot_config

    config_state = {"theme": "dark"}
    parse_variables = [{"name": "ipc", "type": "scalar", "_id": "ipc-1"}]
    state_manager.set_use_parser(True)
    state_manager.set_stats_path(str(tmp_path / "stats"))
    state_manager.set_stats_pattern("stats*.txt")
    state_manager.set_scanned_variables([{"name": "ipc", "type": "scalar"}])
    state_manager.add_manager_history_record(
        {
            "source_columns": ["A"],
            "dest_columns": ["B"],
            "operation": "derive B",
            "timestamp": "2026-07-19T12:00:00",
        }
    )

    # Save Portfolio (using instance method)
    portfolio_service.save_portfolio(
        name="test_portfolio",
        data=df,
        plots=[plot],
        config=config_state,
        plot_counter=1,
        csv_path=str(tmp_path / "original.csv"),
        parse_variables=parse_variables,
    )

    # Verify File Exists
    expected_file = portfolios_dir / "test_portfolio.json"
    assert expected_file.exists()

    # Load Portfolio (using instance method)
    loaded_data = portfolio_service.load_portfolio("test_portfolio")

    # Verify Content
    assert loaded_data["version"] == "2.0"
    assert loaded_data["csv_path"] == str(tmp_path / "original.csv")
    assert loaded_data["plot_counter"] == 1
    assert loaded_data["config"] == config_state
    assert loaded_data["parse_variables"] == parse_variables
    assert loaded_data["use_parser"] is True
    assert loaded_data["stats_path"] == str(tmp_path / "stats")
    assert loaded_data["stats_pattern"] == "stats*.txt"
    assert loaded_data["scanned_variables"] == [{"name": "ipc", "type": "scalar"}]
    assert loaded_data["manager_history"][0]["operation"] == "derive B"

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
    assert pd.read_csv(io.StringIO(loaded_plot["processed_data"])).equals(df)
    assert loaded_plot["pipeline"] == []
    assert loaded_plot["pipeline_counter"] == 0


def test_portfolio_retains_data_and_plot_semantics(
    portfolio_service: PortfolioService,
    state_manager: RepositoryStateManager,
    portfolios_dir: Any,
) -> None:
    # [test->req~ring5.data.semantic-units~1]
    semantics = DatasetSemantics((ColumnSemantics("latency", "Mean latency", "ms"),))
    data = SemanticMetadataService.attach(pd.DataFrame({"latency": [1.0]}), semantics)
    plot = PlotFactory.create_plot("line", 3, "Latency")
    plot.processed_data = data
    plot.config = {"x": "latency", "y": "latency"}

    portfolio_service.save_portfolio(
        "semantic_portfolio",
        data,
        [plot],
        {},
        4,
    )
    loaded = portfolio_service.load_portfolio("semantic_portfolio")
    restored = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    report = restored.restore_session(loaded)

    assert report.complete
    assert loaded["data_semantics"]["latency"] == {
        "label": "Mean latency",
        "unit": "ms",
    }
    assert SemanticMetadataService.inspect(restored.get_data()).for_column(
        "latency"
    ) == ColumnSemantics("latency", "Mean latency", "ms")
    restored_plot = restored.get_plots()[0]
    assert SemanticMetadataService.inspect(restored_plot.processed_data) == semantics


def test_list_portfolios(portfolio_service: Any, portfolios_dir: Any) -> None:
    # [test->req~ring5.portfolio.manage~1]
    """Test listing available portfolios."""
    # Create two dummy portfolio files
    (portfolios_dir / "p1.json").touch()
    (portfolios_dir / "p2.json").touch()
    (portfolios_dir / "not_a_portfolio.txt").touch()

    portfolios = portfolio_service.list_portfolios()
    assert set(portfolios) == {"p1", "p2"}


def test_delete_portfolio(portfolio_service: Any, portfolios_dir: Any) -> None:
    # [test->req~ring5.portfolio.manage~1]
    """Test deleting a portfolio."""
    # Create a dummy portfolio file
    p_path = portfolios_dir / "to_delete.json"
    p_path.touch()

    assert p_path.exists()
    portfolio_service.delete_portfolio("to_delete")
    assert not p_path.exists()


def test_save_portfolio_empty_name(portfolio_service: Any) -> None:
    """Test error handling for empty name."""
    with pytest.raises(ValueError, match="Portfolio name cannot be empty"):
        portfolio_service.save_portfolio("", pd.DataFrame(), [], {}, 0)


def test_load_nonexistent_portfolio(portfolio_service: Any) -> None:
    """Test error handling for loading missing portfolio."""
    with pytest.raises(FileNotFoundError):
        portfolio_service.load_portfolio("ghost")


def test_save_portfolio_overwrite_false_raises(portfolio_service: Any, portfolios_dir: Any) -> None:
    # [test->req~ring5.portfolio.safe-overwrite~1]
    """Portfolios are keyed by name alone; overwrite=False must protect existing files."""
    df = pd.DataFrame({"A": [1, 2]})
    portfolio_service.save_portfolio("dup", df, [], {}, 0)

    with pytest.raises(FileExistsError, match="already exists"):
        portfolio_service.save_portfolio("dup", df, [], {}, 0, overwrite=False)

    # The default (overwrite=True) keeps the historical replace-by-name behavior.
    portfolio_service.save_portfolio("dup", df, [], {}, 0)


def test_restore_returns_report_with_skipped_plots_when_no_deserializer(
    portfolio_service: Any, portfolios_dir: Any, state_manager: Any
) -> None:
    # [test->req~ring5.portfolio.partial-report~1]
    """Without a plot deserializer the plots are skipped — the report must
    say so explicitly (previously only a logger.warning, invisible to scripts)."""
    df = pd.DataFrame({"A": [1, 2]})
    plot = PlotFactory.create_plot("bar", 1, "Report Plot")
    plot.processed_data = df
    plot.config = {"x": "A", "y": "A"}
    portfolio_service.save_portfolio("report_probe", df, [plot], {}, 1)

    fresh_manager = RepositoryStateManager()  # no plot_deserializer
    loaded = portfolio_service.load_portfolio("report_probe")
    report = fresh_manager.restore_session(loaded)

    assert report.data_restored is True
    assert report.plots_restored == 0
    assert len(report.plots_skipped) == 1
    assert "no plot_deserializer" in report.plots_skipped[0]
    assert report.complete is False


def test_restore_report_complete_with_deserializer(
    portfolio_service: Any, portfolios_dir: Any
) -> None:
    # [test->req~ring5.portfolio.restore~1]
    df = pd.DataFrame({"A": [1, 2]})
    plot = PlotFactory.create_plot("bar", 2, "OK Plot")
    plot.processed_data = df
    plot.config = {"x": "A", "y": "A"}
    portfolio_service.save_portfolio("report_ok", df, [plot], {}, 1)

    fresh_manager = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    loaded = portfolio_service.load_portfolio("report_ok")
    report = fresh_manager.restore_session(loaded)

    assert report.complete is True
    assert report.plots_restored == 1
    assert fresh_manager.get_plots()[0].name == "OK Plot"


def test_restore_survives_malformed_parse_variables(
    portfolio_service: Any, portfolios_dir: Any
) -> None:
    # [test->req~ring5.portfolio.partial-report~1]
    """Portfolio JSON is untrusted: a plain-string parse_variables list
    (the old documented save signature produced exactly this) must not
    crash restore — entries are skipped and counted in the report."""
    manager = RepositoryStateManager()
    report = manager.restore_session(
        {
            "parse_variables": ["system.cpu.ipc", "system.cpu.numCycles"],
            "data_csv": "a,b\n1,2\n",
            "plots": [],
            "config": {},
        }  # type: ignore[typeddict-item]
    )

    assert report.parse_variables_skipped == 2
    assert report.data_restored is True
    assert manager.get_parse_variables() == []
