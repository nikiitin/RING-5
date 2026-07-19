"""Integration tests for the complete headless ``ring5`` workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, get_args

import pandas as pd
import pytest

import ring5

DATA_ROOT = Path(__file__).parent.parent / "data" / "results-micro26-sens"

pytestmark = [pytest.mark.xdist_group("ring5_portfolios"), pytest.mark.public_api]


def _first_stats_subtree() -> Path:
    """The directory for one real gem5 run from the test dataset."""
    if not DATA_ROOT.exists():
        pytest.skip("test data not downloaded (make test-data)")
    for stats_file in sorted(DATA_ROOT.rglob("stats.txt")):
        return stats_file.parent
    pytest.skip("no stats.txt under test data")


class TestFullWorkflow:
    """stats.txt → figure file, entirely through ring5."""

    def test_parse_to_figure_files(self, tmp_path: Path) -> None:
        # [test->req~ring5.ingestion.csv-load~1]
        subtree = _first_stats_subtree()

        with ring5.Session() as s:
            # parse (the scan resolves each variable's type)
            result = s.parse(
                str(subtree),
                variables=["simTicks", "hostSeconds"],
                output_dir=str(tmp_path / "parse_out"),
            )
            assert result.missing_stats == []
            assert Path(result.csv_path).exists()

            # load + shape
            df = s.load(result.csv_path)
            assert "simTicks" in df.columns
            assert len(df) > 0
            shaped = s.shape(df, [{"type": "columnSelector", "columns": ["simTicks"]}])
            assert list(shaped.columns) == ["simTicks"]

            # plot on a small slice
            plot_df = df.head(5).copy()
            plot_df["run"] = [f"r{i}" for i in range(len(plot_df))]
            plot = s.create_plot(
                "bar",
                data=plot_df,
                config={"x": "run", "y": "simTicks", "title": "simTicks"},
            )

            # render both engines + export zero-dependency formats
            mpl_fig = s.render(plot, engine="matplotlib")
            pdf_path = s.export(mpl_fig, str(tmp_path / "fig.pdf"))
            assert open(pdf_path, "rb").read(5) == b"%PDF-"

            plotly_fig = s.render(plot, engine="plotly")
            html_path = s.export(plotly_fig, str(tmp_path / "fig.html"))
            assert b"<html" in open(html_path, "rb").read(200).lower()

    def test_typoed_stat_raises_missing_stat_error(self, tmp_path: Path) -> None:
        """strict mode turns the all-NaN-column trap into a loud error."""
        subtree = _first_stats_subtree()
        with ring5.Session() as s:
            with pytest.raises(ring5.ScanError, match="not found by the scan"):
                s.parse(
                    str(subtree),
                    variables=["totally.bogus.stat"],
                    output_dir=str(tmp_path / "parse_out"),
                )

    def test_vector_and_pattern_variables_parse(self, tmp_path: Path) -> None:
        """Scan metadata (entries, pattern flag) must reach the parser:
        a bare name+type config crashed vectors and never expanded
        pattern variables (regression)."""
        subtree = _first_stats_subtree()
        with ring5.Session() as s:
            # Full scan: a sampled scan can report a type that later files
            # contradict (gem5 type evolution), which is a parser error by
            # design — this test targets the metadata plumbing, not that.
            futures = s.api.submit_scan_async(str(subtree), "stats.txt", limit=0)
            scan = s.api.finalize_scan([f.result() for f in futures])
            by_name_order = sorted(scan.variables, key=lambda v: v.name)
            # A plain (non-pattern) vector — per-core vectors get aggregated
            # into pattern variables, so one may not exist in every dataset.
            vector = next(
                (
                    v
                    for v in by_name_order
                    if v.type == "vector" and v.entries and "\\d+" not in v.name
                ),
                None,
            )
            pattern = next(
                (v for v in by_name_order if "\\d+" in v.name and v.type == "vector" and v.entries),
                None,
            )
            names = [v.name for v in (vector, pattern) if v is not None]
            if not names:
                pytest.skip("no vector/pattern variables in sampled files")

            result = s.parse(
                str(subtree),
                variables=names,
                output_dir=str(tmp_path / "parse_out"),
                scan_limit=0,
                strict=False,
            )

            # The vector's entries metadata reached TypeMapper (a bare
            # name+type config raised 'entries parameter is required') and
            # real values were parsed for it.
            if vector is not None:
                assert vector.name not in result.missing_stats

            # The pattern variable expanded (is_regex was enabled), produced
            # its per-index entry columns, and retained real values.
            if pattern is not None:
                df = pd.read_csv(result.csv_path)
                pattern_cols = [c for c in df.columns if c.startswith(f"{pattern.name}.")]
                assert pattern_cols, (
                    "pattern variable produced no columns — is_regex was "
                    "not enabled on the way to the parser"
                )
                assert bool(df[pattern_cols].notna().any().any())

    def test_parse_empty_dir_raises_typed(self, tmp_path: Path) -> None:
        """The boundary normalizes the core FileNotFoundError to ScanError."""
        empty = tmp_path / "empty"
        empty.mkdir()
        with ring5.Session() as s:
            with pytest.raises(ring5.ScanError, match="No files matching"):
                s.parse(str(empty), variables=["simTicks"])


class TestPortfolioReplay:
    """Save a session, regenerate every figure from the snapshot."""

    def test_save_then_render_portfolio(self, tmp_path: Path, portfolios_dir: Path) -> None:
        df = pd.DataFrame({"bench": ["a", "b", "c"], "ipc": [1.0, 2.0, 3.0]})
        with ring5.Session() as s:
            s.api.state_manager.set_data(df)
            s.create_plot(
                "bar",
                data=df,
                config={"x": "bench", "y": "ipc", "title": "Replay"},
                name="replay_plot",
            )
            s.save_portfolio("replay_probe")

            # overwrite protection is the script-side default (typed error)
            with pytest.raises(ring5.PortfolioError, match="already exists"):
                s.save_portfolio("replay_probe")
            s.save_portfolio("replay_probe", overwrite=True)

        written = ring5.render_portfolio(
            "replay_probe", str(tmp_path / "figs"), engine="matplotlib", fmt="pdf"
        )
        assert len(written) == 1
        assert written[0].endswith("replay_plot.pdf")
        assert open(written[0], "rb").read(5) == b"%PDF-"

    def test_v1_portfolio_replays(self, tmp_path: Path, portfolios_dir: Path) -> None:
        """The long-horizon reproducibility contract: V1 files keep working."""
        v1: dict[str, Any] = {
            # V1: no schema_version key, export_* keys, no engine field
            "version": "2.0",
            "data_csv": "bench,ipc\na,1.0\nb,2.0\n",
            "csv_path": None,
            "plots": [
                {
                    "id": 0,
                    "name": "v1_plot",
                    "plot_type": "bar",
                    "config": {
                        "x": "bench",
                        "y": "ipc",
                        "title": "V1",
                        "export_format": "png",
                        "export_dpi": 300,
                    },
                    "processed_data": "bench,ipc\na,1.0\nb,2.0\n",
                    "pipeline": [],
                    "pipeline_counter": 0,
                    "legend_mappings_by_column": {},
                    "legend_mappings": {},
                }
            ],
            "plot_counter": 1,
            "config": {},
            "parse_variables": [],
        }
        (portfolios_dir / "v1_probe.json").write_text(json.dumps(v1))

        written = ring5.render_portfolio(
            "v1_probe", str(tmp_path / "figs"), engine="matplotlib", fmt="pdf"
        )
        assert len(written) == 1
        assert open(written[0], "rb").read(5) == b"%PDF-"

    def test_future_portfolio_refused(self, tmp_path: Path, portfolios_dir: Path) -> None:
        """Forward-version files are refused, never silently downgraded."""
        (portfolios_dir / "future.json").write_text(json.dumps({"schema_version": 3}))
        with pytest.raises(ring5.PortfolioVersionError, match="newer than this RING-5"):
            ring5.render_portfolio("future", str(tmp_path / "figs"))

    def test_missing_portfolio_typed_error(self, tmp_path: Path, portfolios_dir: Path) -> None:
        with pytest.raises(ring5.PortfolioError, match="not found"):
            ring5.render_portfolio("does_not_exist", str(tmp_path / "figs"))


class TestDeterminism:
    """The CI-regression contract for the zero-dependency formats."""

    def test_fig_json_and_exports_stable(self) -> None:
        df = pd.DataFrame({"x": ["a", "b"], "y": [1.0, 2.0]})

        def build() -> tuple[bytes, bytes, str]:
            with ring5.Session() as s:
                plot = s.create_plot("bar", data=df, config={"x": "x", "y": "y"})
                mpl_fig = s.render(plot, engine="matplotlib")
                plotly_fig = s.render(plot, engine="plotly")
                return (
                    s.export_bytes(mpl_fig, "pdf", deterministic=True),
                    s.export_bytes(plotly_fig, "html", deterministic=True),
                    plotly_fig.to_json(),
                )

        pdf_a, html_a, json_a = build()
        pdf_b, html_b, json_b = build()
        assert pdf_a == pdf_b
        assert html_a == html_b
        assert json_a == json_b


class TestErrorSurface:
    """The typed error hierarchy behaves as documented."""

    def test_pipeline_error_carries_step(self) -> None:
        df = pd.DataFrame({"x": [1.0]})
        with ring5.Session() as s:
            with pytest.raises(ring5.PipelineError) as exc_info:
                s.shape(df, [{"columns": ["x"]}])  # type: ignore[list-item]
        assert exc_info.value.step_index == 0

    def test_missing_column_typed(self) -> None:
        df = pd.DataFrame({"x": [1.0]})
        with ring5.Session() as s:
            with pytest.raises(ring5.ColumnNotFoundError) as exc_info:
                s.remove_outliers(df, "nope")
        assert exc_info.value.column == "nope"
        assert "x" in exc_info.value.available

    def test_all_errors_are_ring5_errors(self) -> None:
        for err in (
            ring5.ScanError,
            ring5.ParseError,
            ring5.MissingStatError,
            ring5.PipelineError,
            ring5.ColumnNotFoundError,
            ring5.DataLoadError,
            ring5.DataValidationError,
            ring5.RenderError,
            ring5.PortfolioError,
            ring5.PortfolioVersionError,
            ring5.ExportError,
            ring5.DependencyMissingError,
        ):
            assert issubclass(err, ring5.Ring5Error)

    def test_missing_csv_raises_typed_error_with_cause(self, tmp_path: Path) -> None:
        """Input-file failures do not leak ``FileNotFoundError``."""
        missing = tmp_path / "missing.csv"
        with ring5.Session() as session:
            with pytest.raises(ring5.DataLoadError) as exc_info:
                session.load(str(missing))
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    def test_invalid_engine_lists_choices(self) -> None:
        """Invalid render configuration uses the public error hierarchy."""
        data = pd.DataFrame({"x": ["a"], "y": [1.0]})
        with ring5.Session() as session:
            plot = session.create_plot("bar", data=data, config={"x": "x", "y": "y"})
            with pytest.raises(ring5.RenderError, match="matplotlib.*plotly"):
                session.render(plot, engine="invalid")  # type: ignore[arg-type]

    def test_plot_without_data_raises_render_error(self) -> None:
        """A restored or manually cleared plot fails with an actionable error."""
        data = pd.DataFrame({"x": ["a"], "y": [1.0]})
        with ring5.Session() as session:
            plot = session.create_plot("bar", data=data, config={"x": "x", "y": "y"})
            plot.replace_processed_data(None)
            with pytest.raises(ring5.RenderError, match="no processed data"):
                session.render(plot)

    def test_table_missing_column_uses_typed_error(self) -> None:
        """Convenience-table operations share the same column error contract."""
        table = ring5.Table.from_rows([{"x": 1}])
        with pytest.raises(ring5.ColumnNotFoundError) as exc_info:
            table.sort(["missing"])
        assert exc_info.value.column == "missing"


class TestApiErgonomics:
    """Common plotting workflows remain concise and discoverable."""

    def test_plot_accepts_typed_spec_and_display_name(self) -> None:
        data = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 1.5]})
        spec = ring5.FigureSpec(x="benchmark", y_columns=["ipc"], title="IPC")

        with ring5.Session() as session:
            figure = session.plot("Bar Chart", data=data, config=spec, engine="plotly")

            assert figure.layout.title.text == "IPC"
            assert session.plots[0].plot_type == "bar"

    def test_available_plot_types_are_public(self) -> None:
        assert "bar" in ring5.available_plot_types()
        assert "grouped_stacked_bar" in ring5.available_plot_types()
        assert set(get_args(ring5.PlotType)) == set(ring5.available_plot_types())

    def test_unknown_plot_type_lists_valid_choices(self) -> None:
        data = pd.DataFrame({"x": ["a"], "y": [1.0]})

        with ring5.Session() as session:
            with pytest.raises(ring5.DataValidationError, match="Available types:.*bar"):
                session.create_plot("not-a-plot", data=data, config={"x": "x", "y": "y"})
