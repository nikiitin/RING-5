from src.core.models.portfolio_contract import (
    CURRENT_PORTFOLIO_SCHEMA_VERSION,
    CURRENT_PORTFOLIO_VERSION,
)
from src.core.common.typed_table_codec import TypedTableCodec
from typing import Any, cast

import pandas as pd
import pytest

from src.core.common.stat_config_codec import StatConfigCodec
from src.core.models.data_models import ParseVariableConfig
from src.core.models.semantic_metadata_models import ColumnSemantics, DatasetSemantics
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.services.managers.semantic_metadata_service import SemanticMetadataService
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.fixture
def state_manager() -> RepositoryStateManager:
    """Create an independent in-memory state boundary."""
    return RepositoryStateManager()


@pytest.fixture
def portfolio_service(state_manager: Any, portfolios_dir: Any) -> PortfolioService:
    """Create PortfolioService instance."""
    return PortfolioService(state_manager)


def test_save_and_load_portfolio(
    portfolio_service: Any, tmp_path: Any, portfolios_dir: Any, state_manager: Any
) -> None:
    # [test->req~ring5.portfolio.save~1]
    # [test->req~ring5.portfolio.environment-metadata~1]
    """Test saving a portfolio and then loading it back to verify data integrity."""

    # Setup Test Data
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    plot_config = {"x": "A", "y": "B"}

    # Create a dummy plot
    plot = PlotFactory.create_plot("bar", 1, "Test Plot")
    plot.processed_data = df
    plot.config = plot_config

    config_state = {"theme": "dark"}
    parse_variables: list[ParseVariableConfig] = [
        {"name": "ipc", "type": "scalar", "_id": "ipc-1", "params": {"source_type": "scalar"}}
    ]
    state_manager.set_use_parser(True)
    state_manager.set_stats_path(str(tmp_path / "stats"))
    state_manager.set_stats_pattern("stats*.txt")
    state_manager.set_scanned_variables(
        [
            {
                "name": "ipc",
                "type": "scalar",
                "entries": [],
                "source_type": "scalar",
                "instances": [{"source_name": "ipc", "indices": []}],
            }
        ]
    )
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
    assert loaded_data["schema_version"] == CURRENT_PORTFOLIO_SCHEMA_VERSION
    assert loaded_data["version"] == CURRENT_PORTFOLIO_VERSION
    environment = loaded_data["environment_metadata"]
    assert environment is not None
    assert environment["format_version"] == 1
    assert environment["ring5_version"]
    assert environment["python_version"]
    assert set(environment["renderers"]) == {"matplotlib", "plotly"}
    assert set(environment["external_tools"]) == {
        "chrome",
        "perl",
        "xelatex",
        "pdflatex",
        "lualatex",
    }
    assert loaded_data["csv_path"] == str(tmp_path / "original.csv")
    assert loaded_data["plot_counter"] == 1
    assert loaded_data["config"] == config_state
    assert loaded_data["parse_variables"] == [
        StatConfigCodec.to_snapshot(v) for v in parse_variables
    ]
    assert loaded_data["use_parser"] is True
    assert loaded_data["stats_path"] == str(tmp_path / "stats")
    assert loaded_data["stats_pattern"] == "stats*.txt"
    assert loaded_data["scanned_variables"] == [
        {
            "name": "ipc",
            "type": "scalar",
            "entries": [],
            "source_type": "scalar",
            "instances": [{"source_name": "ipc", "indices": []}],
        }
    ]
    assert loaded_data["manager_history"][0]["operation"] == "derive B"

    loaded_df = TypedTableCodec.decode(loaded_data["data"])
    assert loaded_df is not None
    pd.testing.assert_frame_equal(df, loaded_df)

    # Verify Plots
    assert len(loaded_data["plots"]) == 1
    loaded_plot = loaded_data["plots"][0]
    assert loaded_plot["name"] == "Test Plot"
    assert loaded_plot["id"] == 1
    assert loaded_plot["plot_type"] == "bar"
    assert loaded_plot["config"] == plot_config
    plot_data = TypedTableCodec.decode(loaded_plot["processed_data"])
    assert plot_data is not None and plot_data.equals(df)
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
    decoded = TypedTableCodec.decode(loaded["data"])
    restored_data = restored.get_data()
    assert decoded is not None and restored_data is not None
    pd.testing.assert_frame_equal(decoded, data)
    assert SemanticMetadataService.inspect(restored_data).for_column("latency") == ColumnSemantics(
        "latency", "Mean latency", "ms"
    )
    restored_plot = restored.get_plots()[0]
    assert restored_plot.processed_data is not None
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


@pytest.mark.parametrize("name", ["../alias", "path/alias", ".hidden", "bad\nname"])
def test_portfolio_names_cannot_alias_after_sanitization(
    portfolio_service: Any,
    name: str,
) -> None:
    """Reject names that would share a storage path or create unsafe filenames."""
    with pytest.raises(ValueError, match="Portfolio name"):
        portfolio_service.save_portfolio(name, pd.DataFrame(), [], {}, 0)


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
    """Malformed variable entries are reported without changing retained measurements."""
    manager = RepositoryStateManager()
    report = manager.restore_session(
        {
            "parser_strategy": "simple",
            "loaded_origin": None,
            "simulator": "gem5",
            "parse_variables": cast(
                list[dict[str, Any]], ["system.cpu.ipc", "system.cpu.numCycles"]
            ),
            "data": TypedTableCodec.encode(pd.DataFrame({"a": [1], "b": [2]})),
            "plots": [],
            "config": {},
        }
    )

    assert report.parse_variables_skipped == 2
    assert report.data_restored is True
    assert manager.get_parse_variables() == []
