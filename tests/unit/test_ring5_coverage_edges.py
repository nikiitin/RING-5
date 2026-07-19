"""Edge contracts that keep the public API's exact coverage gate honest."""

from __future__ import annotations

import builtins
import importlib
import runpy
import sys
import warnings
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import pytest
from kaleido.errors import ChromeNotFoundError
from matplotlib.figure import Figure

import ring5
import ring5.cli as ring5_cli
from ring5 import _doctor, _export, _parse, _plot_validation, _portfolio
from ring5._session import Session, _remove_directory_when_settled
from ring5.errors import Ring5Error
from ring5.figure_spec import DualAxisOpts, FigureSpec, FigureSpecBuilder, LegendOpts
from src.core.models import RestoreReport, ScanFileResult, ScanResult, StatConfig
from src.parsing.gem5.models import Gem5ScannedVariable

pytestmark = pytest.mark.public_api


def _future(value: Any = None, error: Exception | None = None) -> Future[Any]:
    future: Future[Any] = Future()
    if error is not None:
        future.set_exception(error)
    else:
        future.set_result(value)
    return future


def test_lazy_module_fallback_directory_and_shutdown() -> None:
    assert "Session" in dir(ring5)
    assert ring5.__getattr__("Session") is Session
    ring5.shutdown()

    with patch("importlib.metadata.version", side_effect=ring5.PackageNotFoundError):
        reloaded = importlib.reload(ring5)
        assert reloaded.__version__ == "0.0.0"
    importlib.reload(ring5)


def test_doctor_report_and_browser_fallbacks() -> None:
    found = _doctor.DependencyStatus("x", True, "/x", "tests", "install")
    missing = _doctor.DependencyStatus("y", False, None, "tests", "install y")
    all_found = _doctor.DoctorReport(found, found, found)
    partial = _doctor.DoctorReport(found, missing, missing)
    assert all_found.all_found
    assert not partial.all_found
    assert "install y" in str(partial)

    real_import = builtins.__import__

    def fail_choreographer(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "choreographer.browsers.chromium":
            raise ImportError("moved")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fail_choreographer):
        with patch("ring5._doctor.shutil.which", side_effect=lambda name: f"/{name}"):
            assert _doctor._find_chrome() == "/chrome"
        with patch("ring5._doctor.shutil.which", return_value=None):
            assert _doctor._find_chrome() is None


def test_export_error_normalization(tmp_path: Path) -> None:
    # [test->req~ring5.export.public-boundary~1]
    plotly = go.Figure()
    mpl = Figure()

    with patch("ring5._export.plotly_download_bytes", side_effect=ChromeNotFoundError("chrome")):
        with pytest.raises(ring5.DependencyMissingError):
            _export.export_bytes(plotly, "png")
    with patch("ring5._export.plotly_download_bytes", side_effect=ValueError("bad image")):
        with pytest.raises(ring5.ExportError, match="bad image"):
            _export.export_bytes(plotly, "png")
    with patch("ring5._export.matplotlib_download_bytes", side_effect=RuntimeError("xelatex gone")):
        with pytest.raises(ring5.DependencyMissingError):
            _export.export_bytes(mpl, "pgf")
    with patch("ring5._export.matplotlib_download_bytes", side_effect=ValueError("bad figure")):
        with pytest.raises(ring5.ExportError, match="bad figure"):
            _export.export_bytes(mpl, "pdf")
    with pytest.raises(ring5.ExportError, match="Cannot export object"):
        _export.export_bytes(object(), "pdf")  # type: ignore[arg-type]

    with patch("pathlib.Path.write_bytes", side_effect=OSError("read only")):
        with pytest.raises(ring5.ExportError, match="read only"):
            _export.export_file(mpl, str(tmp_path / "out.pdf"))


def _parse_job(api: MagicMock, futures: list[Future[Any]]) -> _parse.ParseJob:
    return _parse.ParseJob(api, futures, ["x"], "out", "simple", "runs", "stats.txt")


def test_parse_job_failure_edges(tmp_path: Path) -> None:
    api = MagicMock()
    with pytest.raises(ring5.ParseError, match="worker failed"):
        _parse_job(api, [_future(error=RuntimeError("boom"))]).finalize()

    api.finalize_parsing.return_value = None
    with pytest.raises(ring5.ParseError, match="produced no CSV"):
        _parse_job(api, [_future({})]).finalize()

    api.finalize_parsing.side_effect = None
    api.finalize_parsing.return_value = str(tmp_path / "result.csv")
    with patch("ring5._parse.pd.read_csv", side_effect=UnicodeError("encoding")):
        with pytest.raises(ring5.ParseError, match="validate parser output"):
            _parse_job(api, [_future({})]).finalize()

    csv_path = tmp_path / "missing.csv"
    pd.DataFrame({"x": [float("nan")]}).to_csv(csv_path, index=False)
    api.finalize_parsing.return_value = str(csv_path)
    with pytest.raises(ring5.MissingStatError) as error:
        _parse_job(api, [_future({})]).finalize()
    assert error.value.missing == ["x"]
    assert _parse._find_missing_stats(str(csv_path), ["x", "absent"]) == ["x", "absent"]


def test_build_stat_configs_explicit_and_distribution_metadata() -> None:
    api = MagicMock()
    api.submit_scan_async.side_effect = OSError("cannot scan")
    with pytest.raises(ring5.ScanError, match="cannot scan"):
        _parse.build_stat_configs(api, "runs", ["x"])

    distribution = Gem5ScannedVariable(
        name="dist", type="distribution", entries=["0"], minimum=0, maximum=4
    )
    api.submit_scan_async.side_effect = None
    api.submit_scan_async.return_value = [_future(ScanFileResult("stats", [distribution]))]
    api.finalize_scan.return_value = ScanResult([distribution], scanned_files=1)
    configs, _ = _parse.build_stat_configs(
        api,
        "runs",
        [
            StatConfig(name=r"cpu\d+", type="scalar"),
            StatConfig(name="plain", type="scalar"),
            "dist",
        ],
    )
    assert configs[0].is_regex  # type: ignore[union-attr]
    assert not configs[1].is_regex  # type: ignore[union-attr]
    assert configs[2] == {
        "name": "dist",
        "type": "distribution",
        "entries": ["0"],
        "minimum": 0,
        "maximum": 4,
    }


def test_plot_validation_rejects_each_invalid_shape() -> None:
    frame = pd.DataFrame({"x": ["a"], "y": [1.0], "latency..0-9.sd": [1.0]})
    with pytest.raises(ring5.DataValidationError, match="non-empty string"):
        _plot_validation.validate_plot_config("bar", frame, {"x": 1, "y": "y"})
    with pytest.raises(ring5.DataValidationError, match="non-empty list"):
        _plot_validation.validate_plot_config("stacked_bar", frame, {"x": "x", "y_columns": []})
    with pytest.raises(ring5.ColumnNotFoundError):
        _plot_validation.validate_plot_config(
            "stacked_bar", frame, {"x": "x", "y_columns": ["missing"]}
        )
    with pytest.raises(ring5.DataValidationError, match="histogram_variable"):
        _plot_validation.validate_plot_config("histogram", frame, {"histogram_variable": 1})
    with pytest.raises(ring5.DataValidationError, match="No histogram bucket"):
        _plot_validation.validate_plot_config("histogram", frame, {"histogram_variable": "latency"})
    with pytest.raises(ring5.DataValidationError, match="optional"):
        _plot_validation.validate_plot_config(
            "grouped_bar", frame, {"x": "x", "y": "y", "group": 1}
        )
    with pytest.raises(ring5.DataValidationError, match="optional non-empty"):
        _plot_validation.validate_plot_config(
            "grouped_stacked_bar",
            frame,
            {"x": "x", "y_columns": ["y"], "y_columns_right": []},
        )


def _portfolio_session(plots: list[Any], report: RestoreReport | None = None) -> MagicMock:
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    session.load_portfolio.return_value = report or RestoreReport(data_restored=True)
    session.plots = plots
    session.render.return_value = object()
    session.export.side_effect = lambda _fig, path, **_kwargs: path
    return session


def test_portfolio_replay_edges(tmp_path: Path) -> None:
    with pytest.raises(ring5.PortfolioError, match="Unknown engine"):
        _portfolio.render_portfolio("p", str(tmp_path), engine="bad")  # type: ignore[arg-type]

    for report in (RestoreReport(), RestoreReport(plots_skipped=["broken plot"])):
        session = _portfolio_session([], report)
        with patch("ring5._portfolio.Session", return_value=session):
            with pytest.raises(ring5.PortfolioError, match="No plots restored"):
                _portfolio.render_portfolio("p", str(tmp_path))

    plots = [
        SimpleNamespace(name="same/name", plot_id=1),
        SimpleNamespace(name="same_name", plot_id=2),
    ]
    session = _portfolio_session(plots)
    with patch("ring5._portfolio.Session", return_value=session):
        written = _portfolio.render_portfolio("p", str(tmp_path))
    assert written[0] != written[1]
    assert written[1].endswith("_2.pdf")

    session = _portfolio_session([SimpleNamespace(name="bad", plot_id=1)])
    session.render.side_effect = Ring5Error("render failed")
    with patch("ring5._portfolio.Session", return_value=session):
        with pytest.raises(ring5.PortfolioError, match="Rendering plot 'bad'"):
            _portfolio.render_portfolio("p", str(tmp_path))


def test_scan_cancel_and_worker_error() -> None:
    pending: Future[ScanFileResult] = Future()
    api = MagicMock()
    ring5.ScanJob(api, [pending], "runs", "stats.txt").cancel()
    assert pending.cancelled()
    ring5.ScanJob(api, [], "runs", "stats.txt").cancel()

    with pytest.raises(ring5.ScanError, match="worker failed"):
        ring5.ScanJob(
            api, [_future(error=RuntimeError("scan boom"))], "runs", "stats.txt"
        ).finalize()


def test_session_lifecycle_and_submission_edges(tmp_path: Path) -> None:
    done = _future({})
    running: Future[dict[str, Any]] = Future()
    assert running.set_running_or_notify_cancel()
    output = tmp_path / "deferred"
    output.mkdir()
    _remove_directory_when_settled(str(output), [done, running])
    assert output.exists()
    running.set_result({})
    assert not output.exists()

    first: Future[dict[str, Any]] = Future()
    second: Future[dict[str, Any]] = Future()
    assert first.set_running_or_notify_cancel()
    assert second.set_running_or_notify_cancel()
    two_step = tmp_path / "two-step"
    two_step.mkdir()
    _remove_directory_when_settled(str(two_step), [first, second])
    first.set_result({})
    assert two_step.exists()
    second.set_result({})
    assert not two_step.exists()

    session = Session()
    with patch.object(session.api, "submit_scan_async", side_effect=OSError("scan submit")):
        with pytest.raises(ring5.ScanError, match="scan submit"):
            session.scan_submit("runs")

    with patch("ring5._session._parse.build_stat_configs", return_value=([], [])):
        with patch.object(
            session.api, "submit_parse_async", side_effect=ValueError("parse submit")
        ):
            with pytest.raises(ring5.ParseError, match="parse submit"):
                session.parse_submit("runs", [])
            user_output = tmp_path / "user-output"
            with pytest.raises(ring5.ParseError, match="parse submit"):
                session.parse_submit("runs", [], output_dir=str(user_output))

    with patch.object(session.api, "load_data", return_value=None):
        with patch.object(session.api.state_manager, "get_data", return_value=None):
            with pytest.raises(ring5.DataLoadError, match="produced no data"):
                session.load("empty.csv")

    with patch.object(session.api, "apply_shapers", side_effect=ValueError("bad pipeline")):
        with pytest.raises(ring5.PipelineError, match="bad pipeline"):
            session.shape(pd.DataFrame({"x": [1]}), [])
    session.close()


def test_session_manager_edge_paths() -> None:
    frame = pd.DataFrame({"group": ["a", "a", "b"], "x": [1.0, 3.0, 10.0], "y": [2, 4, 8]})
    with Session() as session:
        reduced = session.reduce_seeds(ring5.Table(frame), ["group"], ["x"])
        assert isinstance(reduced, ring5.Table)
        with pytest.raises(ring5.DataValidationError):
            session.reduce_seeds(frame, [], [])
        with patch.object(session.api.managers, "reduce_seeds", side_effect=ValueError("reduce")):
            with pytest.raises(ring5.DataValidationError, match="reduce"):
                session.reduce_seeds(frame, ["group"], ["x"])

        assert isinstance(session.remove_outliers(ring5.Table(frame), "x"), ring5.Table)
        with patch.object(
            session.api.managers, "remove_outliers", side_effect=ValueError("outliers")
        ):
            with pytest.raises(ring5.DataValidationError, match="outliers"):
                session.remove_outliers(frame, "x")

        with pytest.raises(ring5.DataValidationError, match="cannot be empty"):
            session.apply_operation(frame, "Sum", "x", "y", "")
        with pytest.raises(ring5.DataValidationError, match="Unknown operation"):
            session.apply_operation(frame, "Nope", "x", "y", "z")
        assert isinstance(
            session.apply_operation(ring5.Table(frame), "Sum", "x", "y", "z"), ring5.Table
        )

        with patch.object(session.api.managers, "apply_mixer", side_effect=ValueError("mixer")):
            with pytest.raises(ring5.DataValidationError, match="mixer"):
                session.mix_columns(frame, "z", ["x", "y"])


def test_session_plot_and_portfolio_error_edges() -> None:
    with Session() as session:
        with pytest.raises(ring5.DataValidationError, match="Plot data"):
            session.create_plot(
                "bar", data=[], config={"x": "x", "y": "y"}  # type: ignore[arg-type]
            )
        with pytest.raises(ring5.DataValidationError, match="must be a mapping"):
            session.create_plot(
                "bar", data=pd.DataFrame({"x": [1], "y": [2]}), config=1  # type: ignore[arg-type]
            )

        with patch.object(session.api.data_services, "save_portfolio", side_effect=OSError("disk")):
            with pytest.raises(ring5.PortfolioError, match="could not be saved"):
                session.save_portfolio("p")
        with patch.object(
            session.api.data_services, "load_portfolio", side_effect=ValueError("json")
        ):
            with pytest.raises(ring5.PortfolioError, match="could not be read"):
                session.load_portfolio("p")
        with patch.object(session.api.data_services, "load_portfolio", return_value={}):
            with patch.object(
                session.api.state_manager, "restore_session", side_effect=KeyError("schema")
            ):
                with pytest.raises(ring5.PortfolioError, match="could not be restored"):
                    session.load_portfolio("p")


def test_cli_warning_restore_details_file_error_and_module_entry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.csv"
    source.write_text("x\nNaN\n")
    fake_session = MagicMock()
    fake_session.__enter__.return_value = fake_session
    fake_session.__exit__.return_value = None
    fake_session.parse.return_value = _parse.ParseResult(str(source), ["x"])
    with patch("ring5._session.Session", return_value=fake_session):
        assert (
            ring5_cli.main(
                ["parse", "runs", "-v", "x", "-o", str(tmp_path / "out.csv"), "--lenient"]
            )
            == 0
        )
    assert "warning" in capsys.readouterr().out

    fake_session.load_portfolio.return_value = RestoreReport(
        data_error="bad csv", parse_variables_skipped=2
    )
    with patch("ring5._session.Session", return_value=fake_session):
        assert ring5_cli.main(["upgrade", "p"]) == 2
    error_text = capsys.readouterr().err
    assert "bad csv" in error_text and "2 malformed" in error_text

    with patch("ring5._portfolio.render_portfolio", side_effect=FileNotFoundError("gone")):
        assert ring5_cli.main(["render", "p", "-o", str(tmp_path)]) == 2

    monkeypatch.setattr(sys, "argv", ["ring5", "doctor"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with pytest.raises(SystemExit):
            runpy.run_module("ring5.cli", run_name="__main__")


def test_table_io_and_shaper_error_edges(tmp_path: Path) -> None:
    with patch("ring5.data.pd.read_csv", side_effect=ValueError("bad csv")):
        with pytest.raises(ring5.DataLoadError, match="bad csv"):
            ring5.Table.from_csv("bad.csv")
    table = ring5.Table.from_rows([{"x": 1}])
    with patch.object(pd.DataFrame, "to_csv", side_effect=OSError("disk")):
        with pytest.raises(ring5.ExportError, match="disk"):
            table.to_csv(str(tmp_path / "x.csv"))
    with pytest.raises(ring5.ColumnNotFoundError):
        table.apply(lambda frame: frame["missing"])
    with pytest.raises(ring5.PipelineError, match="transform"):
        table.apply(lambda _frame: (_ for _ in ()).throw(ValueError("transform")))


def test_error_payloads_and_complete_figure_spec() -> None:
    missing = ring5.MissingStatError(["x"])
    dependency = ring5.DependencyMissingError("tool", "install it")
    assert missing.missing == ["x"]
    assert dependency.binary == "tool" and dependency.install_hint == "install it"

    legend = LegendOpts(
        position=(0.1, 0.2),
        anchor=("left", "top"),
        ncols=2,
        font_size=9,
        item_width=4,
        bgcolor="white",
        bgalpha=0.5,
        border_color="black",
        border_width=1,
        tracegroupgap=2,
        column_spacing=0.2,
        handletextpad=0.3,
    )
    spec = FigureSpec(
        x="x",
        group="g",
        y_columns=["y"],
        x_order=["b", "a"],
        group_order=["g2", "g1"],
        legend=legend,
        dual_axis=DualAxisOpts(columns=["z"], legend=legend),
    )
    config = spec.to_config()
    assert config["xaxis_order"] == ["b", "a"]
    assert config["group_order"] == ["g2", "g1"]
    assert config["legend_handletextpad"] == 0.3
    assert config["dual_legend_handletextpad"] == 0.3

    built = FigureSpecBuilder().title("Title", 12, "serif").bars("stack", 0.1, 0.2, 1).build()
    assert built.title == "Title" and built.bar_border_width == 1


def test_decoration_optional_paths() -> None:
    fig, ax = plt.subplots()
    ax.text(0, 0, "other")
    ax.text(1, 1, "target")
    ring5.FigureDecorations.tighten_y_ticks(fig)
    ring5.FigureDecorations.tighten_y_ticks(fig, twin_pad=2)
    ring5.FigureDecorations.set_twin_ylabel_pad(fig, 3)
    ring5.FigureDecorations.log_xaxis(fig, ticks=[1, 2])
    ring5.FigureDecorations.hide_spines(fig, "missing", include_twin=False)
    ring5.FigureDecorations.hide_spines(fig, "missing", include_twin=True)
    ring5.FigureDecorations.clamp_bar_xlim(fig)
    ax.bar([1], [1])
    ring5.FigureDecorations.clamp_bar_xlim(fig)
    twin = ax.twinx()
    setattr(ax, "_ring5_twin", twin)
    ring5.FigureDecorations.hide_spines(fig, "missing", "top", include_twin=True)
    ring5.FigureDecorations.nudge_text(fig, "target", 1)
    ring5.FigureDecorations.over_cap_labels(
        fig, {}, {"below": 1.0, "missing-coordinate": 3.0}, cap=2.0
    )
    plt.close(fig)
