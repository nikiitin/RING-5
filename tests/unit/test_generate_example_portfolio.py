"""Tests for the example portfolio generator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.figure import Figure

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
from src.core.services.portfolio_migrator import PortfolioMigrator
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_traces


def test_example_data_is_deterministic_and_complete() -> None:
    """Build stable rows with every required category and uncertainty column."""
    first = build_example_data()
    second = build_example_data()

    pd.testing.assert_frame_equal(first, second)
    assert len(first) == len(BENCHMARK_ORDER) * len(CONFIGURATION_ORDER)
    assert set(first["benchmark"]) == set(BENCHMARK_ORDER)
    assert set(first["configuration"]) == set(CONFIGURATION_ORDER)
    assert len([column for column in first if column.startswith("memory_latency..")]) == 5
    assert {"ipc.sd", "energy_j.sd", "l2_miss_rate.sd"}.issubset(first.columns)


def test_every_registered_plot_example_renders() -> None:
    """Render the complete registry through both supported figure engines."""
    # [test->req~ring5.portfolio.example-catalog~1]
    data = build_example_data()
    plots = build_example_plots(data)

    assert {plot.plot_type for plot in plots} == set(PlotFactory.get_available_plot_types())
    assert all(plot.last_generated_fig is not None for plot in plots)
    assert all(plot.processed_data is not None for plot in plots)
    assert any(plot.pipeline for plot in plots)
    for plot in plots:
        assert plot.last_traces is not None
        figure, _spec = build_matplotlib_figure_from_traces(
            plot.config,
            plot.plot_type,
            plot.last_traces,
        )
        try:
            assert isinstance(figure, Figure)
            assert figure.axes
        finally:
            plt.close(figure)


def test_generated_portfolio_round_trips(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep custom output isolated and restore its integrity-checked artifact."""
    monkeypatch.setattr(
        PathService,
        "get_portfolio_revisions_dir",
        lambda: pytest.fail("isolated generation used the global revision directory"),
    )
    output = generate_example_portfolio("Example Cases", output_dir=tmp_path)

    assert output == tmp_path / "Example Cases.json"
    assert output.is_file()
    raw = json.loads(output.read_text())
    assert raw["schema_version"] == PortfolioMigrator.CURRENT_VERSION
    assert len(raw["plots"]) == len(PlotFactory.get_available_plot_types())
    assert all("figure_spec" in plot for plot in raw["plots"])

    state_manager = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    service = PortfolioService(state_manager, portfolios_dir=tmp_path)
    loaded = service.load_portfolio("Example Cases")
    state_manager.restore_session(loaded)
    assert state_manager.get_data() is not None
    assert len(state_manager.get_plots()) == len(PlotFactory.get_available_plot_types())
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
