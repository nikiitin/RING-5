"""Contract tests for the complete supported analysis workflow."""

from __future__ import annotations

import json
from concurrent.futures import Future
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

import ring5
from ring5._parse import ParseJob
from ring5._scan import ScanJob
from src.core.models import ScanFileResult, ScannedVariable, ScanResult

pytestmark = pytest.mark.public_api


def _write_stats_run(root: Path, body: str, config: str | None = None) -> Path:
    run = root / "run"
    run.mkdir(parents=True)
    (run / "stats.txt").write_text(body)
    if config is not None:
        (run / "config.ini").write_text(config)
    return run


def test_scan_parse_and_config_aware_workflow(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.async-parse~1]
    # [test->req~ring5.ingestion.async-scan~1]
    run = _write_stats_run(
        tmp_path / "inputs",
        "simTicks 123 # ticks\n",
        "[system]\nnum_cpus = 4\ncpu_type = O3CPU\n",
    )

    with ring5.Session() as session:
        job = session.scan_submit(str(run), limit=0)
        scan = job.finalize()
        assert scan.complete
        assert [(variable.name, variable.type) for variable in scan.variables] == [
            ("simTicks", "scalar")
        ]

        parsed = session.parse(
            str(run),
            ["simTicks"],
            strategy="config_aware",
            output_dir=str(tmp_path / "output"),
        )

    frame = pd.read_csv(parsed.csv_path)
    assert frame.loc[0, "simTicks"] == 123
    assert frame.loc[0, "sim_path"] == str(run / "stats.txt")
    assert json.loads(frame.loc[0, "config_json"])["system"]["num_cpus"] == "4"


def test_config_aware_missing_config_is_typed(tmp_path: Path) -> None:
    run = _write_stats_run(tmp_path / "inputs", "simTicks 123 # ticks\n")
    with ring5.Session() as session:
        with pytest.raises(ring5.ParseError, match="config.ini not found"):
            session.parse(
                str(run),
                ["simTicks"],
                strategy="config_aware",
                output_dir=str(tmp_path / "output"),
            )


def test_gem5_oneline_histogram_is_scanned_and_parsed(tmp_path: Path) -> None:
    run = _write_stats_run(
        tmp_path / "inputs",
        "\n".join(
            [
                "system.delay::bucket_size 10 # geometry",
                "system.delay::max_bucket 19 # geometry",
                "system.delay::samples 5 # summary",
                "system.delay | 3 60.00% 60.00% | 2 40.00% 100.00% # buckets",
                "system.delay::total 5 # summary",
            ]
        )
        + "\n",
    )

    with ring5.Session() as session:
        scanned = session.scan(str(run), limit=0)
        variable = next(value for value in scanned.variables if value.name == "system.delay")
        assert variable.type == "histogram"
        assert {"0-9", "10-19"} <= set(variable.entries)
        parsed = session.parse(
            str(run), [variable.name], output_dir=str(tmp_path / "output"), scan_limit=0
        )

    frame = pd.read_csv(parsed.csv_path)
    assert frame.loc[0, "system.delay..0-9"] == 3
    assert frame.loc[0, "system.delay..10-19"] == 2


def test_scan_job_partial_and_timeout_are_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    # [test->req~ring5.ingestion.async-scan~1]
    good: Future[ScanFileResult] = Future()
    good.set_result(ScanFileResult("good/stats.txt", [ScannedVariable(name="x", type="scalar")]))
    bad_result = ScanFileResult("bad/stats.txt", error="scanner failed")
    bad: Future[ScanFileResult] = Future()
    bad.set_result(bad_result)
    api = MagicMock()
    api.finalize_scan.return_value = ScanResult(
        variables=[ScannedVariable(name="x", type="scalar")],
        failures=[bad_result],
        scanned_files=2,
    )
    job = ScanJob(api, [good, bad], "runs", "stats.txt")

    with pytest.raises(ring5.ScanError, match="1 of 2"):
        job.finalize()
    partial = job.finalize(strict=False)
    assert not partial.complete
    api.state_manager.set_scanned_variables.assert_called()

    pending: Future[ScanFileResult] = Future()
    monkeypatch.setattr("ring5._scan.SCAN_BATCH_TIMEOUT_SECONDS", 0)
    with pytest.raises(ring5.ScanError, match="cancellation succeeded for 1"):
        ScanJob(api, [pending], "runs", "stats.txt").finalize()
    assert pending.cancelled()


def test_session_close_defers_cleanup_for_running_parse(tmp_path: Path) -> None:
    # [test->req~ring5.api.session~1]
    # [test->req~ring5.ingestion.async-parse~1]
    # [test->req~ring5.quality.async-ownership~1]
    output = tmp_path / "owned"
    output.mkdir()
    running: Future[dict[str, Any]] = Future()
    assert running.set_running_or_notify_cancel()
    session = ring5.Session()
    session._owned_tmpdirs.append(str(output))
    session._parse_jobs.append(
        ParseJob(
            api=session.api,
            futures=[running],
            var_names=["x"],
            output_dir=str(output),
            strategy="simple",
            stats_path="runs",
            stats_pattern="stats.txt",
        )
    )

    session.close()
    assert output.exists()
    running.set_result({})
    assert not output.exists()
    session.close()  # idempotent


def test_manager_operations_preserve_dataframe_and_table() -> None:
    # [test->req~ring5.api.session~1]
    # [test->req~ring5.quality.immutable-data~1]
    frame = pd.DataFrame({"a": [2.0, 4.0], "b": [1.0, 2.0], "a.sd": [0.3, 0.4], "b.sd": [0.4, 0.3]})
    original = frame.copy(deep=True)
    with ring5.Session() as session:
        divided = session.apply_operation(frame, "Division", "a", "b", "ratio")
        assert isinstance(divided, pd.DataFrame)
        assert divided["ratio"].tolist() == [2.0, 2.0]

        mixed = session.mix_columns(ring5.Table(frame), "total", ["a", "b"])
        assert isinstance(mixed, ring5.Table)
        assert mixed.rows()[0]["total"] == 3.0
        assert mixed.rows()[0]["total.sd"] == pytest.approx(0.5)

        with pytest.raises(ring5.ColumnNotFoundError):
            session.apply_operation(frame, "Sum", "missing", "b", "total")
        with pytest.raises(ring5.DataValidationError, match="Invalid operation"):
            session.mix_columns(frame, "total", ["a", "b"], operation="Nope")

    pd.testing.assert_frame_equal(frame, original)


def test_public_registries_are_complete() -> None:
    # [test->req~ring5.api.registry-discovery~1]
    assert set(ring5.available_shaper_types()) == {
        "mean",
        "columnSelector",
        "conditionSelector",
        "itemSelector",
        "normalize",
        "pivotLonger",
        "pivotWider",
        "sort",
        "splitApply",
        "transformer",
        "deriveColumn",
        "groupCardinalitySelector",
        "groupPredicateSelector",
    }
    assert ring5.ScanJob is ScanJob
    assert ring5.ScanResult is ScanResult
    assert ring5.ScannedVariable is ScannedVariable
    assert ring5.ShaperStepConfig is not None


@pytest.mark.parametrize(
    ("plot_type", "config"),
    [
        ("area", {"x": "x", "y": "y", "color": "group", "area_mode": "stack"}),
        ("bar", {"x": "x", "y": "y", "color": "group"}),
        ("box", {"x": "x", "y": "y", "color": "group", "point_mode": "all"}),
        ("violin", {"x": "x", "y": "y", "color": "group", "point_mode": "all"}),
        ("dual_axis_bar_dot", {"x": "x", "y_bar": "y", "y_dot": "z"}),
        ("ecdf", {"x": "y", "color": "group", "ecdf_complementary": True}),
        ("grouped_bar", {"x": "x", "y": "y", "group": "group"}),
        ("grouped_stacked_bar", {"x": "x", "y_columns": ["y", "z"], "group": "group"}),
        ("heatmap", {"x": "x", "metric_columns": ["y", "z"], "facet_col": "group"}),
        ("histogram", {"histogram_variable": "latency", "group_by": "group"}),
        ("line", {"x": "x", "y": "y", "color": "group"}),
        ("radar", {"x": "x", "y": "y", "color": "group", "radar_fill": True}),
        ("scatter", {"x": "x", "y": "y", "color": "group"}),
        ("stacked_bar", {"x": "x", "y_columns": ["y", "z"]}),
    ],
)
def test_every_registered_plot_accepts_validated_config(
    plot_type: str, config: dict[str, Any]
) -> None:
    # [test->req~ring5.api.plot-validation~1]
    frame = pd.DataFrame(
        {
            "x": ["a", "b", "c"],
            "group": ["one", "two", "three"],
            "y": [1.0, 2.0, 3.0],
            "z": [2.0, 3.0, 4.0],
            "latency..0-9": [2.0, 3.0, 4.0],
            "latency..10-19": [1.0, 4.0, 2.0],
        }
    )
    with ring5.Session() as session:
        plot = session.create_plot(plot_type, data=frame, config=config)
        assert plot.plot_type == plot_type
        assert session.render(plot, engine="plotly") is not None
        assert session.render(plot, engine="matplotlib") is not None


def test_invalid_plot_config_does_not_register_and_render_errors_are_typed() -> None:
    # [test->req~ring5.api.plot-validation~1]
    frame = pd.DataFrame({"x": ["a"], "y": [1.0]})
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="field 'y'"):
            session.create_plot("bar", data=frame, config={"x": "x"})
        assert session.plots == []

        with pytest.raises(ring5.ColumnNotFoundError):
            session.create_plot("bar", data=frame, config={"x": "x", "y": "missing"})
        assert session.plots == []

        plot = session.create_plot("bar", data=frame, config={"x": "x", "y": "y"})
        plot.config = {"x": "x"}
        with pytest.raises(ring5.RenderError, match="Could not render plot") as error:
            session.render(plot, engine="plotly")
        assert isinstance(error.value.__cause__, KeyError)
