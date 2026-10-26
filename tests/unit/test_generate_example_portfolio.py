"""Tests for the example portfolio generator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import matplotlib.pyplot as plt
import pandas as pd
import pytest
import plotly.graph_objects as go
from matplotlib.figure import Figure

from ring5 import RenderError, Session
from scripts.generate_example_portfolio import (
    BENCHMARK_ORDER,
    CONFIGURATION_ORDER,
    build_example_data,
    build_example_plots,
    generate_example_portfolio,
    main,
)
from src.core.services.data_services.path_service import PathService
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.models.portfolio_contract import CURRENT_PORTFOLIO_SCHEMA_VERSION
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.rendering.figure_preparation import PreparedFigure


def test_example_data_is_deterministic_and_complete() -> None:
    """Build stable rows with every required category and uncertainty column."""
    first = build_example_data()
    second = build_example_data()

    pd.testing.assert_frame_equal(first, second)
    assert len(first) == len(BENCHMARK_ORDER) * len(CONFIGURATION_ORDER)
    assert set(first["benchmark"]) == set(BENCHMARK_ORDER)
    assert set(first["configuration"]) == set(CONFIGURATION_ORDER)
    histogram_columns = []
    for column in first:
        assert isinstance(column, str)
        if column.startswith("memory_latency.."):
            histogram_columns.append(column)
    assert len(histogram_columns) == 5
    assert {"ipc.sd", "energy_j.sd", "l2_miss_rate.sd"}.issubset(first.columns)


def _assert_rendered_plot(plot: BasePlot, figure: go.Figure | Figure) -> None:
    """Check actual marks and labels, rather than only a figure's existence."""
    prepared = plot.render_artifact.preparation
    assert isinstance(prepared, PreparedFigure)
    assert prepared.trace_result is not None
    assert prepared.trace_result.traces
    if isinstance(figure, go.Figure):
        assert figure.data
        assert figure.layout.title.text == plot.config["title"]
        names = []
        for trace in figure.data:
            assert isinstance(
                trace,
                (
                    go.Bar,
                    go.Box,
                    go.Violin,
                    go.Scatterpolar,
                    go.Waterfall,
                    go.Sankey,
                    go.Parcoords,
                    go.Scatter,
                    go.Heatmap,
                ),
            )
            names.append(trace.name)
        assert names == [
            plot.config.get("legend_labels", {}).get(trace.name, trace.name)
            for trace in prepared.trace_result.traces
        ]
    else:
        assert figure.axes
        assert any(
            axis.lines or axis.patches or axis.collections or axis.images for axis in figure.axes
        )
        assert figure.number not in plt.get_fignums()


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_every_registered_plot_example_renders(engine: Literal["plotly", "matplotlib"]) -> None:
    """Render the complete registry through both supported figure engines."""
    # [test->req~ring5.portfolio.example-catalog~1]
    data = build_example_data()
    plots = build_example_plots(data)

    assert {plot.plot_type for plot in plots} == set(PlotFactory.get_available_plot_types())
    assert all(plot.render_artifact.figure is not None for plot in plots)
    assert all(plot.processed_data is not None for plot in plots)
    assert any(plot.pipeline for plot in plots)
    with Session() as session:
        for plot in plots:
            figure = session.render(plot, engine=engine)
            _assert_rendered_plot(plot, figure)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_generated_portfolio_round_trips(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    engine: Literal["plotly", "matplotlib"],
) -> None:
    """Keep custom output isolated and restore its integrity-checked artifact."""
    # [test->req~ring5.portfolio.example-catalog~1]
    monkeypatch.setattr(
        PathService,
        "get_portfolio_revisions_dir",
        lambda: pytest.fail("isolated generation used the global revision directory"),
    )
    output = generate_example_portfolio("Example Cases", output_dir=tmp_path)

    assert output == tmp_path / "Example Cases.json"
    assert output.is_file()
    raw = json.loads(output.read_text())
    assert raw["schema_version"] == CURRENT_PORTFOLIO_SCHEMA_VERSION
    assert len(raw["plots"]) == len(PlotFactory.get_available_plot_types())
    assert all("figure_spec" in plot for plot in raw["plots"])

    state_manager = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    service = PortfolioService(state_manager, portfolios_dir=tmp_path)
    loaded = service.load_portfolio("Example Cases")
    state_manager.restore_session(loaded)
    assert state_manager.get_data() is not None
    assert len(state_manager.get_plots()) == len(PlotFactory.get_available_plot_types())
    with Session() as session:
        for plot in state_manager.get_plots():
            assert isinstance(plot, BasePlot)
            figure = session.render(plot, engine=engine)
            _assert_rendered_plot(plot, figure)
    revisions = service.list_portfolio_revisions("Example Cases")
    assert len(revisions) == 1
    assert len(list((tmp_path / ".revisions").rglob("*.json"))) == 1
    restored_revision = service.load_portfolio_revision(
        "Example Cases",
        revisions[0].revision_id,
    )
    assert len(restored_revision["plots"]) == len(PlotFactory.get_available_plot_types())
    assert not service.compare_portfolio_revisions(
        "Example Cases",
        revisions[0].revision_id,
        revisions[0].revision_id,
    ).entries

    service.delete_portfolio("Example Cases")
    assert not output.exists()
    assert not list((tmp_path / ".revisions").rglob("*.json"))


def test_generator_refuses_overwrite_without_force(tmp_path: Path) -> None:
    """Require an explicit destructive choice before replacing an example."""
    first = generate_example_portfolio("Protected", output_dir=tmp_path)

    with pytest.raises(FileExistsError, match="--force"):
        generate_example_portfolio("Protected", output_dir=tmp_path)

    replaced = generate_example_portfolio("Protected", output_dir=tmp_path, force=True)
    assert replaced == first
    assert len(list((tmp_path / ".revisions").rglob("*.json"))) == 2


def test_generator_preserves_a_concurrently_created_portfolio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce the no-overwrite choice again at the atomic persistence boundary."""
    output = tmp_path / "Contended.json"
    original_save = PortfolioService.save_portfolio

    def save_after_competitor(
        service: PortfolioService,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Create a competing artifact immediately before the real save."""
        output.write_text("competing process", encoding="utf-8")
        original_save(service, *args, **kwargs)

    monkeypatch.setattr(PortfolioService, "save_portfolio", save_after_competitor)

    with pytest.raises(FileExistsError, match="already exists"):
        generate_example_portfolio("Contended", output_dir=tmp_path)

    assert output.read_text(encoding="utf-8") == "competing process"


def test_cli_reports_success_and_existing_file_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return shell-friendly status and diagnostics for success and collision."""
    args = ["--name", "CLI Example", "--output-dir", str(tmp_path)]

    assert main(args) == 0
    assert "Generated portfolio:" in capsys.readouterr().out
    assert main(args) == 1
    assert "--force" in capsys.readouterr().err


def test_cli_reports_public_render_validation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reject an invalid example before persisting an incomplete catalog."""

    def reject_render(_session: Session, _plot: BasePlot) -> None:
        raise RenderError("invalid example traces")

    monkeypatch.setattr(Session, "render", reject_render)

    assert main(["--output-dir", str(tmp_path)]) == 1
    assert "invalid example traces" in capsys.readouterr().err
    assert not list(tmp_path.glob("*.json"))
