"""Integration test for histogram plot with real gem5 data."""

import tempfile
from pathlib import Path
from typing import cast

import pandas as pd
import pytest
import matplotlib.pyplot as plt

import ring5

from src.core.application_api import ApplicationAPI
from src.core.models.data_models import ParseVariableConfig
from src.web.pages.ui.plotting.plot_factory import PlotFactory


class TestHistogramPlotIntegration:
    """Integration tests for histogram plot with real data."""

    @pytest.fixture
    def stats_dir(self) -> Path:
        """Get test data directory with histogram variables."""
        path = Path(
            "tests/data/results-micro26-sens/"
            "CPUtest_BinSfx.htm.fallbacklock_LV_ED_CRHighwayResolutionPolicy"
            "_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_FCSabort_Rtry16_Pflt/"
            "stamp.vacation-l/0"
        )
        if not path.exists():
            pytest.skip(f"Test data not found at {path}")
        return path

    @pytest.fixture
    def facade(self) -> ApplicationAPI:
        """Create facade instance."""
        return ApplicationAPI()

    def test_histogram_plot_creation_from_factory(self) -> None:
        """Test creating histogram plot from factory."""
        plot = PlotFactory.create_plot("histogram", plot_id=1, name="Test Histogram")

        assert plot is not None
        assert plot.plot_type == "histogram"
        assert plot.name == "Test Histogram"

    def test_histogram_with_parsed_gem5_data(self, facade: ApplicationAPI, stats_dir: Path) -> None:
        """Test histogram plot with parsed gem5 histogram data."""
        # Scan for histogram variables
        scan_futures = facade.submit_scan_async(str(stats_dir), "stats.txt", limit=-1)
        scan_results = [f.result() for f in scan_futures]
        vars_found = facade.finalize_scan(scan_results).variables

        # Find htm_transaction_commit_cycles (histogram variable)
        htm_var = next(
            (
                v
                for v in vars_found
                if "htm_transaction_commit_cycles" in v.name and v.type == "histogram"
            ),
            None,
        )

        assert htm_var is not None, "Histogram variable not found"

        # Parse histogram data
        with tempfile.TemporaryDirectory() as tmpdir:
            variables: list[ParseVariableConfig] = [
                cast(
                    ParseVariableConfig,
                    {
                        "name": "system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles",
                        "type": "histogram",
                        "params": {
                            "entries": (htm_var.entries or [])[:5],
                            "source_type": htm_var.source_type,
                        },
                    },
                )
            ]

            parse_batch = facade.submit_parse_async(
                str(stats_dir),
                "stats.txt",
                facade.compile_parse_variables(variables),
                tmpdir,
                scanned_vars=vars_found,
            )

            parse_results = [f.result() for f in parse_batch.futures]
            csv_path = facade.finalize_parsing(
                tmpdir, parse_results, var_names=parse_batch.var_names
            )

            assert csv_path is not None

            # Load data
            data = pd.read_csv(csv_path)

            # Create histogram plot
            plot = PlotFactory.create_plot("histogram", plot_id=1, name="Transaction Cycles")

            # Configure plot
            config = {
                "histogram_variable": (
                    "system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles"
                ),
                "title": "Transaction Commit Cycles Distribution",
                "xlabel": "Cycles",
                "ylabel": "Count",
                "bucket_size": 2048,
                "normalization": "count",
                "group_by": None,
                "cumulative": False,
            }

            # Generate figure
            fig = plot.create_figure(data, config)

            assert fig is not None
            assert len(list(fig.data)) > 0
            # Title is applied by the style chain, not create_figure()

    def test_histogram_with_grouping(
        self, facade: ApplicationAPI, stats_dir: Path, tmp_path: Path
    ) -> None:
        """Test histogram plot with categorical grouping."""
        # Parse with configuration variable for grouping
        output_dir = tmp_path / "hist_grouping_output"
        output_dir.mkdir()

        scan_futures = facade.submit_scan_async(str(stats_dir), "stats.txt", limit=-1)
        scan_results = [f.result() for f in scan_futures]
        vars_found = facade.finalize_scan(scan_results).variables

        # Get a histogram variable
        htm_var = next(
            (
                v
                for v in vars_found
                if "htm_transaction_commit_cycles" in v.name and v.type == "histogram"
            ),
            None,
        )

        assert htm_var is not None

        variables: list[ParseVariableConfig] = [
            cast(
                ParseVariableConfig,
                {
                    "name": "benchmark_name",
                    "type": "configuration",
                    "params": {"source_type": "configuration"},
                },
            ),
            cast(
                ParseVariableConfig,
                {
                    "name": "system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles",
                    "type": "histogram",
                    "params": {
                        "entries": (htm_var.entries or [])[:5],
                        "source_type": htm_var.source_type,
                    },
                },
            ),
        ]

        parse_batch = facade.submit_parse_async(
            str(stats_dir),
            "stats.txt",
            facade.compile_parse_variables(variables),
            str(output_dir),
            scanned_vars=vars_found,
        )

        parse_results = [f.result() for f in parse_batch.futures]
        csv_path = facade.finalize_parsing(
            str(output_dir), parse_results, var_names=parse_batch.var_names
        )

        assert csv_path is not None

        data = pd.read_csv(csv_path)

        # Create histogram with grouping
        plot = PlotFactory.create_plot("histogram", plot_id=1, name="Grouped Histogram")

        config = {
            "histogram_variable": ("system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles"),
            "title": "Cycles by Benchmark",
            "xlabel": "Cycles",
            "ylabel": "Count",
            "bucket_size": 2048,
            "normalization": "count",
            "group_by": "benchmark_name",
            "cumulative": False,
        }

        fig = plot.create_figure(data, config)

        assert fig is not None
        # Should have at least one trace
        assert len(list(fig.data)) >= 1

    def test_histogram_normalization_modes(self) -> None:
        """Test different normalization modes."""
        # Create synthetic histogram data
        data = pd.DataFrame(
            {
                "hist_var..0-9": [10],
                "hist_var..10-19": [20],
                "hist_var..20-29": [30],
                "hist_var..30-39": [40],
            }
        )

        plot = PlotFactory.create_plot("histogram", plot_id=1, name="Test Histogram")

        # Test count normalization
        config_count = {
            "histogram_variable": "hist_var",
            "title": "Count",
            "xlabel": "X",
            "ylabel": "Count",
            "bucket_size": 10,
            "normalization": "count",
            "group_by": None,
            "cumulative": False,
        }

        fig_count = plot.create_figure(data, config_count)
        assert fig_count is not None

        # Test probability normalization
        config_prob = {
            **config_count,
            "normalization": "probability",
            "ylabel": "Probability",
        }

        fig_prob = plot.create_figure(data, config_prob)
        assert fig_prob is not None

        # Test percent normalization
        config_pct = {
            **config_count,
            "normalization": "percent",
            "ylabel": "Percent",
        }

        fig_pct = plot.create_figure(data, config_pct)
        assert fig_pct is not None

    def test_histogram_cumulative_distribution(self) -> None:
        """Test cumulative histogram."""
        # [test->req~ring5.figure.histogram-cumulative~1]
        data = pd.DataFrame(
            {
                "hist_var..0-9": [10],
                "hist_var..10-19": [20],
                "hist_var..20-29": [30],
            }
        )

        plot = PlotFactory.create_plot("histogram", plot_id=1, name="Test Histogram")

        config = {
            "histogram_variable": "hist_var",
            "title": "Cumulative Distribution",
            "xlabel": "X",
            "ylabel": "CDF",
            "bucket_size": 10,
            "normalization": "probability",
            "group_by": None,
            "cumulative": True,
        }

        fig = plot.create_figure(data, config)

        assert fig is not None
        assert len(list(fig.data)) > 0


@pytest.mark.parametrize("bucket_size", [None, 1, 5])
def test_parser_histogram_union_geometry_renders_observed_mass(
    tmp_path: Path,
    bucket_size: float | None,
) -> None:
    """Different observed bucket geometries survive the async parse/render boundary."""
    from src.core.models.parsing_models import StatConfig
    from src.parsing.gem5.impl.gem5_parser import Gem5Parser
    from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

    inputs = tmp_path / "inputs"
    for name, bucket, count in [("a", "0-0", 1), ("b", "0-9", 2)]:
        directory = inputs / name
        directory.mkdir(parents=True)
        (directory / "stats.txt").write_text(f"h::{bucket} {count} 100% 100%\n")
    output = tmp_path / "parsed"
    batch = Gem5Parser.submit_parse_async(
        str(inputs),
        "stats.txt",
        [StatConfig("h", "histogram", params={"source_type": "histogram"})],
        str(output),
    )
    results = [future.result() for future in batch.futures]
    csv_path = Gem5Parser.finalize_parsing(str(output), results, var_names=batch.var_names)
    assert csv_path is not None
    data = pd.read_csv(csv_path)
    assert data[["h..0-0", "h..0-9"]].notna().sum().tolist() == [1, 1]
    trace = (
        HistogramPlot(1, "Observed histogram")
        .create_traces(
            data,
            {"histogram_variable": "h", "bucket_size": bucket_size},
        )
        .traces[0]
    )
    assert sum(trace.y) == pytest.approx(3)
    assert len(trace.x_positions) == len(trace.y) == len(trace.bar_width)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_public_histogram_renders_explicit_geometry_and_rejects_overlapping_observations(
    engine: str,
) -> None:
    """Both engines use the same label grammar without mutating the input table."""
    data = ring5.Table(pd.DataFrame({"h..0-9": [3], "h..[10,20)": [7]}))
    config = {"histogram_variable": "h", "normalization": "probability"}
    with ring5.Session() as session:
        figure = session.plot("histogram", data=data, config=config, engine=engine)
        try:
            if engine == "plotly":
                assert list(figure.data[0].y) == [0.3, 0.7]
                assert list(figure.data[0].x) == [5, 15]
                assert list(figure.data[0].width) == [10, 10]
            else:
                patches = figure.axes[0].patches
                assert [patch.get_height() for patch in patches] == [0.3, 0.7]
                assert [patch.get_x() + patch.get_width() / 2 for patch in patches] == [5, 15]
                assert [patch.get_width() for patch in patches] == [10, 10]
        finally:
            if engine == "matplotlib":
                plt.close(figure)
        invalid = ring5.Table(pd.DataFrame({"h..0-10": [3], "h..10-20": [7]}))
        with pytest.raises(ring5.RenderError, match="Overlapping histogram buckets"):
            session.plot("histogram", data=invalid, config=config, engine=engine)
    assert data.frame.to_dict("list") == {"h..0-9": [3], "h..[10,20)": [7]}
