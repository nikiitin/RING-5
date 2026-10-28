"""Scientific and persistence checks for the canonical synthetic tutorial."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import pandas as pd
import pytest
import plotly.graph_objects as go
from matplotlib.figure import Figure

from ring5 import RenderError, Session
from scripts.generate_example_portfolio import (
    BENCHMARK_ORDER,
    CACHE_CAPACITIES,
    CONFIGURATION_ORDER,
    HISTOGRAM_COLUMNS,
    build_example_data,
    build_example_plots,
    build_example_portfolio,
    generate_example_portfolio,
    main,
)
from src.core.models.portfolio_contract import CURRENT_PORTFOLIO_SCHEMA_VERSION
from src.core.models.visualization.trace_config import ScatterTraceConfig
from src.core.services.data_services.path_service import PathService
from src.core.services.data_services.portfolio_validation_service import (
    validate_portfolio_document,
)
from src.core.services.environment_metadata_service import EnvironmentMetadataService
from src.core.services.portfolio_integrity_service import PortfolioIntegrityService
from src.core.services.shapers.pipeline_service import PipelineService
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.rendering.figure_preparation import PreparedFigure


@pytest.fixture(scope="module")
def catalog() -> tuple[pd.DataFrame, list[BasePlot]]:
    """Share a validated catalog while all tests treat its domain inputs as read-only."""
    data = build_example_data()
    return data, build_example_plots(data)


def test_example_data_is_deterministic_and_scenarios_are_explicit() -> None:
    """Keep unrelated illustrative scenarios distinguishable in one shared source."""
    first = build_example_data()
    pd.testing.assert_frame_equal(first, build_example_data())
    assert len(first) == 83
    assert first["scenario"].value_counts().to_dict() == {
        "repeated_runs": 36,
        "traffic_series": 15,
        "summary": 12,
        "cache_sweep": 12,
        "request_flow": 5,
        "energy_waterfall": 3,
    }
    summary = first[first["scenario"] == "summary"]
    assert set(summary["benchmark"]) == set(BENCHMARK_ORDER)
    assert set(summary["configuration"]) == set(CONFIGURATION_ORDER)
    assert summary["cache_kib"].isna().all()
    assert summary["traffic_requests"].isna().all()
    assert summary["memory_latency_ns"].isna().all()
    assert first[first["scenario"] == "request_flow"]["ipc"].isna().all()


def test_each_example_replays_from_the_full_shared_source(
    catalog: tuple[pd.DataFrame, list[BasePlot]],
) -> None:
    """Let the web pipeline reproduce every plot from its actual workspace input."""
    # [test->req~ring5.portfolio.example-catalog~1]
    data, plots = catalog
    original = data.copy(deep=True)
    assert {plot.plot_type for plot in plots} == set(PlotFactory.get_available_plot_types())
    assert len(plots) == len(PlotFactory.get_available_plot_types()) == 17
    assert [plot.plot_id for plot in plots] == list(range(1, 18))
    assert len({plot.name for plot in plots}) == 17
    for plot in plots:
        assert plot.source_data is not None
        pd.testing.assert_frame_equal(plot.source_data, data)
        assert plot.pipeline[0]["config"]["type"] == "itemSelector"
        assert plot.pipeline[0]["config"]["column"] == "scenario"
        replay = PipelineService.process_pipeline(data, [step["config"] for step in plot.pipeline])
        assert plot.processed_data is not None
        assert not replay.isna().any().any()
        pd.testing.assert_frame_equal(replay, plot.processed_data)
    pd.testing.assert_frame_equal(data, original)


def test_catalog_uses_meaningful_numeric_examples(
    catalog: tuple[pd.DataFrame, list[BasePlot]],
) -> None:
    """Check the tutorial's baseline, conservation, units and distribution claims."""
    data, plots = catalog
    by_type = {plot.plot_type: plot for plot in plots}
    normalized = by_type["bar"].processed_data
    assert normalized is not None
    for configuration, ratio in zip(CONFIGURATION_ORDER, (1.0, 1.12, 1.21), strict=True):
        assert normalized.loc[
            normalized["configuration"] == configuration, "ipc"
        ].tolist() == pytest.approx([ratio] * 4)

    sweep = by_type["line"].processed_data
    assert sweep is not None
    workload = sweep[sweep["benchmark"] == "blackscholes"]
    assert workload["cache_kib"].tolist() == CACHE_CAPACITIES
    assert workload["ipc"].tolist() == pytest.approx([1.55, 1.674, 1.798])
    assert by_type["line"].config["line_shape"] == "linear"

    summary = data[data["scenario"] == "summary"]
    pd.testing.assert_series_equal(
        summary[["front_end_cycles", "execution_cycles", "memory_cycles"]].sum(axis=1),
        summary["cycles"],
        check_names=False,
    )
    assert summary[HISTOGRAM_COLUMNS].sum(axis=1).tolist() == [1000] * 12
    assert summary["latency_sample_count"].tolist() == [1000] * 12
    histogram_data = by_type["histogram"].processed_data
    assert histogram_data is not None
    assert "memory_latency_ns" not in histogram_data.columns
    assert by_type["heatmap"].config["metric_columns"] == ["l1_miss_rate", "l2_miss_rate"]

    observations = by_type["box"].processed_data
    assert observations is not None
    assert observations["benchmark"].unique().tolist() == ["blackscholes"]
    assert observations.groupby("configuration").size().to_dict() == dict.fromkeys(
        CONFIGURATION_ORDER, 12
    )
    assert observations.groupby("configuration")["ipc"].mean().reindex(
        CONFIGURATION_ORDER
    ).tolist() == pytest.approx([1.55, 1.736, 1.8755])

    traffic = by_type["area"].processed_data
    assert traffic is not None
    assert traffic.groupby("epoch")["traffic_requests"].sum().tolist() == [15, 20, 26, 23, 18]
    assert not traffic.duplicated(["epoch", "traffic_class"]).any()
    flow = by_type["sankey"].processed_data
    assert flow is not None
    for intermediate in ("L1", "L2"):
        incoming = flow.loc[flow["target"] == intermediate, "traffic_requests"].sum()
        outgoing = flow.loc[flow["source"] == intermediate, "traffic_requests"].sum()
        assert incoming == outgoing
    assert flow.loc[flow["target"] == "Memory", "traffic_requests"].sum() == 180
    waterfall = by_type["waterfall"].processed_data
    assert waterfall is not None
    assert waterfall["energy_delta"].tolist() == [10.0, -1.6, -1.2]
    assert waterfall["energy_delta"].sum() == pytest.approx(7.2)


def _assert_rendered_plot(plot: BasePlot, figure: go.Figure | Figure) -> None:
    """Check actual marks and labels through both supported native connectors."""
    prepared = plot.render_artifact.preparation
    assert isinstance(prepared, PreparedFigure)
    assert prepared.trace_result is not None
    assert prepared.trace_result.traces
    if plot.plot_type == "dual_axis_bar_dot":
        secondary = [trace for trace in prepared.trace_result.traces if trace.yaxis == "y2"]
        assert len(secondary) == 3
        assert all(isinstance(trace, ScatterTraceConfig) for trace in secondary)
        assert plot.config["show_lines"] is False
        if isinstance(figure, go.Figure):
            native_secondary = [trace for trace in figure.data if trace.yaxis == "y2"]
            assert len(native_secondary) == 3
            assert all(
                isinstance(trace, go.Scatter) and trace.mode == "markers"
                for trace in native_secondary
            )
        else:
            assert len(figure.axes) == 2
            assert all(
                line.get_linestyle() in ("None", "none", "", " ") for line in figure.axes[1].lines
            )
    if isinstance(figure, go.Figure):
        assert figure.data
        assert figure.layout.title.text == plot.config["title"]
        assert [trace.name for trace in figure.data] == [
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
def test_every_registered_plot_example_renders(
    catalog: tuple[pd.DataFrame, list[BasePlot]],
    engine: Literal["plotly", "matplotlib"],
) -> None:
    """Render the complete catalog through both connectors without external tools."""
    # [test->req~ring5.portfolio.example-catalog~1]
    with Session() as session:
        for plot in catalog[1]:
            _assert_rendered_plot(plot, session.render(plot, engine=engine))


def test_builder_uses_current_serializer_without_user_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build honest, integrity-checked bytes without choosing a user data directory."""
    for name in ("get_data_dir", "get_portfolios_dir", "get_portfolio_revisions_dir"):
        monkeypatch.setattr(PathService, name, lambda: pytest.fail("builder used user storage"))
    document = json.loads(build_example_portfolio())
    assert document["schema_version"] == CURRENT_PORTFOLIO_SCHEMA_VERSION
    assert document["timestamp"]
    assert document["csv_path"] is None
    assert document["stats_path"] == ""
    assert document["loaded_origin"] is None
    assert document["use_parser"] is False
    assert document["config"]["example_portfolio"] is True
    assert "synthetic" in document["config"]["data_provenance"].lower()
    assert document["parse_variables"] == document["scanned_variables"] == []
    assert all("figure_spec" in plot for plot in document["plots"])
    validate_portfolio_document(document)
    assert PortfolioIntegrityService.verify(document).status == "checksum-valid"
    saved_environment = EnvironmentMetadataService.from_payload(document["environment_metadata"])
    assert saved_environment == EnvironmentMetadataService.capture()


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_explicit_output_round_trips_without_revision_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    engine: Literal["plotly", "matplotlib"],
) -> None:
    """Restore the exact written asset using ordinary portfolio contracts."""
    # [test->req~ring5.portfolio.example-catalog~1]
    monkeypatch.setattr(
        PathService,
        "get_portfolio_revisions_dir",
        lambda: pytest.fail("asset generation used revisions"),
    )
    output = generate_example_portfolio(tmp_path / "assets" / "example-portfolio.json.gz")
    assert list(tmp_path.rglob("*")) == [tmp_path / "assets", output]
    compressed = output.read_bytes()
    assert compressed[:2] == b"\x1f\x8b"
    assert compressed[4:8] == b"\x00" * 4
    assert len(compressed) < 1_000_000
    document = json.loads(gzip.decompress(compressed))
    assert PortfolioIntegrityService.verify(document).safe_to_restore
    restored = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    report = restored.restore_session(document)
    assert report.complete and report.data_restored and report.plots_restored == 17
    assert restored.get_data() is not None
    pd.testing.assert_frame_equal(restored.get_data(), build_example_data())
    with Session() as session:
        for plot in restored.get_plots():
            assert isinstance(plot, BasePlot)
            _assert_rendered_plot(plot, session.render(plot, engine=engine))


def test_generator_requires_explicit_replacement(tmp_path: Path) -> None:
    """Preserve an existing artifact until the maintainer explicitly replaces it."""
    output = tmp_path / "example.json.gz"
    output.write_text("protected bytes", encoding="utf-8")
    with pytest.raises(FileExistsError, match="--force"):
        generate_example_portfolio(output)
    assert output.read_text(encoding="utf-8") == "protected bytes"
    assert generate_example_portfolio(output, force=True) == output
    assert PortfolioIntegrityService.verify(
        json.loads(gzip.decompress(output.read_bytes()))
    ).safe_to_restore


def test_generator_preserves_a_concurrently_created_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce no-overwrite at file creation after expensive render validation."""
    output = tmp_path / "contended.json.gz"

    def build_after_competitor() -> bytes:
        output.write_text("competing bytes", encoding="utf-8")
        return b"not persisted"

    monkeypatch.setattr(
        "scripts.generate_example_portfolio.build_example_portfolio", build_after_competitor
    )
    with pytest.raises(FileExistsError, match="--force"):
        generate_example_portfolio(output)
    assert output.read_text(encoding="utf-8") == "competing bytes"


def test_cli_requires_output_and_reports_success_or_collision(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Require an explicit destination and return shell-friendly diagnostics."""
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2
    capsys.readouterr()
    arguments = ["--output", str(tmp_path / "example.json.gz")]
    assert main(arguments) == 0
    assert "Generated synthetic portfolio:" in capsys.readouterr().out
    assert main(arguments) == 1
    assert "--force" in capsys.readouterr().err


def test_cli_preserves_existing_asset_when_render_validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Validate every example before opening an explicitly replaceable target."""
    output = tmp_path / "example.json.gz"
    output.write_text("previous valid asset", encoding="utf-8")

    def reject_render(_session: Session, _plot: BasePlot) -> None:
        raise RenderError("invalid example traces")

    monkeypatch.setattr(Session, "render", reject_render)
    assert main(["--output", str(output), "--force"]) == 1
    assert "invalid example traces" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "previous valid asset"


def test_failed_atomic_replacement_preserves_existing_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Leave the old artifact intact and remove staging when promotion fails."""
    output = tmp_path / "example.json.gz"
    output.write_bytes(b"previous bytes")
    monkeypatch.setattr(
        "scripts.generate_example_portfolio.build_example_portfolio", lambda: b"replacement bytes"
    )

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("destination cannot be replaced")

    monkeypatch.setattr("scripts.generate_example_portfolio.os.replace", fail_replace)
    with pytest.raises(OSError, match="destination cannot be replaced"):
        generate_example_portfolio(output, force=True)
    assert output.read_bytes() == b"previous bytes"
    assert list(tmp_path.iterdir()) == [output]
