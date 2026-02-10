"""Integration test for histogram plot with real gem5 data."""

import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

from src.plotting.plot_factory import PlotFactory
from src.web.facade import BackendFacade


class TestHistogramPlotIntegration:
    """Integration tests for histogram plot with real data."""

    @pytest.fixture
    def stats_dir(self) -> Path:
        """Get test data directory with histogram variables."""
        return Path(
            "tests/data/results-micro26-sens/"
            "CPUtest_BinSfx.htm.fallbacklock_LV_ED_CRHighwayResolutionPolicy"
            "_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_FCSabort_Rtry16_Pflt/"
            "stamp.vacation-l/0"
        )

    @pytest.fixture
    def facade(self) -> BackendFacade:
        """Create facade instance."""
        return BackendFacade()

    def test_histogram_plot_creation_from_factory(self) -> None:
        """Test creating histogram plot from factory."""
        plot = PlotFactory.create_plot("histogram", plot_id=1, name="Test Histogram")

        assert plot is not None
        assert plot.plot_type == "histogram"
        assert plot.name == "Test Histogram"

    def test_histogram_with_parsed_gem5_data(
        self, facade: BackendFacade, stats_dir: Path
    ) -> None:
        """Test histogram plot with parsed gem5 histogram data."""
        # 1. Scan for histogram variables
        scan_futures = facade.submit_scan_async(str(stats_dir), "stats.txt", limit=-1)
        scan_results = [f.result() for f in scan_futures]
        vars_found = facade.finalize_scan(scan_results)

        # Find htm_transaction_commit_cycles (histogram variable)
        htm_var = next(
            (
                v
                for v in vars_found
                if "htm_transaction_commit_cycles" in v["name"]
                and v["type"] == "histogram"
            ),
            None,
        )

        assert htm_var is not None, "Histogram variable not found"

        # 2. Parse histogram data
        with tempfile.TemporaryDirectory() as tmpdir:
            variables: List[Dict[str, Any]] = [
                {
                    "name": "system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles",
                    "type": "histogram",
                    "entries": htm_var["entries"][:5],  # Use first 5 buckets
                }
            ]

            parse_futures = facade.submit_parse_async(
                str(stats_dir),
                "stats.txt",
                variables,
                tmpdir,
                scanned_vars=vars_found,
            )

            parse_results = [f.result() for f in parse_futures]
            csv_path = facade.finalize_parsing(tmpdir, parse_results)

            assert csv_path is not None

            # 3. Load data
            data = pd.read_csv(csv_path)

            # 4. Create histogram plot
            plot = PlotFactory.create_plot("histogram", plot_id=1, name="Transaction Cycles")

            # 5. Configure plot
            config = {
                "histogram_variable": "system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles",
                "title": "Transaction Commit Cycles Distribution",
                "xlabel": "Cycles",
                "ylabel": "Count",
                "bucket_size": 2048,
                "normalization": "count",
                "group_by": None,
                "cumulative": False,
            }

            # 6. Generate figure
            fig = plot.create_figure(data, config)

            assert fig is not None
            assert len(fig.data) > 0
            assert fig.layout.title.text == "Transaction Commit Cycles Distribution"

    def test_histogram_with_grouping(
        self, facade: BackendFacade, stats_dir: Path
    ) -> None:
        """Test histogram plot with categorical grouping."""
        # Parse with configuration variable for grouping
        with tempfile.TemporaryDirectory() as tmpdir:
            scan_futures = facade.submit_scan_async(
                str(stats_dir), "stats.txt", limit=-1
            )
            scan_results = [f.result() for f in scan_futures]
            vars_found = facade.finalize_scan(scan_results)

            # Get a histogram variable
            htm_var = next(
                (
                    v
                    for v in vars_found
                    if "htm_transaction_commit_cycles" in v["name"]
                    and v["type"] == "histogram"
                ),
                None,
            )

            assert htm_var is not None

            variables: List[Dict[str, Any]] = [
                {
                    "name": "benchmark_name",
                    "type": "configuration",
                },
                {
                    "name": "system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles",
                    "type": "histogram",
                    "entries": htm_var["entries"][:5],
                },
            ]

            parse_futures = facade.submit_parse_async(
                str(stats_dir),
                "stats.txt",
                variables,
                tmpdir,
                scanned_vars=vars_found,
            )

            parse_results = [f.result() for f in parse_futures]
            csv_path = facade.finalize_parsing(tmpdir, parse_results)

            assert csv_path is not None

            data = pd.read_csv(csv_path)

            # Create histogram with grouping
            plot = PlotFactory.create_plot("histogram", plot_id=1, name="Grouped Histogram")

            config = {
                "histogram_variable": "system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles",
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
            assert len(fig.data) >= 1

    def test_histogram_normalization_modes(self) -> None:
        """Test different normalization modes."""
        # Create synthetic histogram data
        data = pd.DataFrame(
            {
                "hist_var..0-10": [10],
                "hist_var..10-20": [20],
                "hist_var..20-30": [30],
                "hist_var..30-40": [40],
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
        data = pd.DataFrame(
            {
                "hist_var..0-10": [10],
                "hist_var..10-20": [20],
                "hist_var..20-30": [30],
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
        assert len(fig.data) > 0
