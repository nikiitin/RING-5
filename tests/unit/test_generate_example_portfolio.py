"""Tests for the example portfolio generator."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.generate_example_portfolio import (
    BENCHMARK_ORDER,
    CONFIGURATION_ORDER,
    build_example_data,
    build_example_plots,
    generate_example_portfolio,
    main,
)
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory


def test_example_data_is_deterministic_and_complete() -> None:
    first = build_example_data()
    second = build_example_data()

    pd.testing.assert_frame_equal(first, second)
    assert len(first) == len(BENCHMARK_ORDER) * len(CONFIGURATION_ORDER)
    assert set(first["benchmark"]) == set(BENCHMARK_ORDER)
    assert set(first["configuration"]) == set(CONFIGURATION_ORDER)
    assert len([column for column in first if column.startswith("memory_latency..")]) == 5
    assert {"ipc.sd", "energy_j.sd", "l2_miss_rate.sd"}.issubset(first.columns)


def test_every_registered_plot_example_renders() -> None:
    data = build_example_data()
    plots = build_example_plots(data)

    assert {plot.plot_type for plot in plots} == set(PlotFactory.get_available_plot_types())
    assert all(plot.last_generated_fig is not None for plot in plots)
    assert all(plot.processed_data is not None for plot in plots)
    assert any(plot.pipeline for plot in plots)


def test_generated_portfolio_round_trips(tmp_path: Path) -> None:
    output = generate_example_portfolio("Example Cases", output_dir=tmp_path)

    assert output == tmp_path / "Example Cases.json"
    assert output.is_file()
    raw = json.loads(output.read_text())
    assert raw["schema_version"] == 2
    assert len(raw["plots"]) == len(PlotFactory.get_available_plot_types())
    assert all("figure_spec" in plot for plot in raw["plots"])

    state_manager = RepositoryStateManager(plot_deserializer=BasePlot.from_dict)
    loaded = PortfolioService(state_manager, portfolios_dir=tmp_path).load_portfolio(
        "Example Cases"
    )
    state_manager.restore_session(loaded)
    assert state_manager.get_data() is not None
    assert len(state_manager.get_plots()) == len(PlotFactory.get_available_plot_types())


def test_generator_refuses_overwrite_without_force(tmp_path: Path) -> None:
    first = generate_example_portfolio("Protected", output_dir=tmp_path)

    with pytest.raises(FileExistsError, match="--force"):
        generate_example_portfolio("Protected", output_dir=tmp_path)

    replaced = generate_example_portfolio("Protected", output_dir=tmp_path, force=True)
    assert replaced == first


def test_cli_reports_success_and_existing_file_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = ["--name", "CLI Example", "--output-dir", str(tmp_path)]

    assert main(args) == 0
    assert "Generated portfolio:" in capsys.readouterr().out
    assert main(args) == 1
    assert "--force" in capsys.readouterr().err
