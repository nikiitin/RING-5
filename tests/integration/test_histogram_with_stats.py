"""
Integration test for histogram variables with vector-style statistics.

This test specifically addresses the case where gem5 outputs histogram data
with statistical summary lines (::samples, ::mean, ::gmean, ::stdev, ::total)
that look like vector entries but should be treated as part of the histogram.

Example from gem5 output:
    system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles::samples     256
    system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles::mean        8521.972656
    system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles::2048-4095   6
    system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles::4096-6143   49
    ...
"""

from collections.abc import Generator
from pathlib import Path

import pytest

from src.core.application_api import ApplicationAPI
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.data_models import ParseVariableConfig


class TestHistogramWithStatistics:
    """Test histogram parsing when statistics lines are present."""

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
    def facade(self) -> Generator[ApplicationAPI, None, None]:
        """Create facade instance."""
        api = ApplicationAPI()
        try:
            yield api
        finally:
            api.close(wait=True)

    def test_scan_htm_transaction_commit_cycles(
        self, facade: ApplicationAPI, stats_dir: Path
    ) -> None:
        """Test scanning detects htm_transaction_commit_cycles as histogram."""
        # Scan
        scan_futures = facade.submit_scan_async(str(stats_dir), "stats.txt", limit=-1)
        scan_results = [f.result() for f in scan_futures]
        vars_found = facade.finalize_scan(scan_results).variables

        # Find the variable
        htm_var = next(
            (v for v in vars_found if "htm_transaction_commit_cycles" in v.name),
            None,
        )

        assert htm_var is not None, "htm_transaction_commit_cycles not found in scan"
        assert htm_var.type == "histogram", f"Expected histogram type, got {htm_var.type}"

        # Check that both bucket entries and statistics are present
        entries = htm_var.entries or []
        assert len(entries) > 0, "No entries found"

        # Should have histogram buckets (ranges)
        bucket_entries = [e for e in entries if "-" in e and e[0].isdigit()]
        assert len(bucket_entries) > 0, "No bucket entries found"

        # Should have statistics
        stat_entries = [e for e in entries if e in ("samples", "mean", "gmean", "stdev", "total")]
        assert len(stat_entries) > 0, "No statistics entries found"

    def test_parse_htm_transaction_commit_cycles_as_histogram(
        self, facade: ApplicationAPI, stats_dir: Path, tmp_path: Path
    ) -> None:
        """
        Test parsing htm_transaction_commit_cycles configured as histogram.

        This test ensures that when a histogram variable has vector-style
        statistics (::samples, ::mean, etc.), it doesn't raise a type mismatch
        error during parsing.
        """
        # Scan
        scan_futures = facade.submit_scan_async(str(stats_dir), "stats.txt", limit=-1)
        scan_results = [f.result() for f in scan_futures]
        vars_found = facade.finalize_scan(scan_results).variables

        # Parse with histogram configuration
        output_dir = tmp_path / "hist_stats_output"
        output_dir.mkdir()

        variables: list[ParseVariableConfig] = [
            {
                "name": "system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles",
                "type": "histogram",
                "params": {"source_type": "histogram", "statistics": ["samples", "mean", "total"]},
            }
        ]

        parse_batch = facade.submit_parse_async(
            str(stats_dir),
            "stats.txt",
            facade.compile_parse_variables(variables),
            str(output_dir),
            scanned_vars=vars_found,
        )

        parse_results = [f.result() for f in parse_batch.futures]
        parsed_output = facade.finalize_parsing(parse_batch, parse_results)
        csv_path = parsed_output.csv_path

        assert csv_path is not None, "Parsing failed"
        assert Path(csv_path).exists(), f"CSV file not created: {csv_path}"

    def test_parse_htm_transaction_commit_cycles_with_regex(
        self, facade: ApplicationAPI, stats_dir: Path, tmp_path: Path
    ) -> None:
        r"""
        Test parsing htm_transaction_commit_cycles using regex pattern.

        This is the exact scenario from the bug report:
        Pattern: system.ruby.l\d+_cntrl\d+.xact_mgr.htm_transaction_commit_cycles
        Type: histogram
        Error: "Variable type mismatch - Expected: histogram Found: vector"
        """
        # Scan
        scan_futures = facade.submit_scan_async(str(stats_dir), "stats.txt", limit=-1)
        scan_results = [f.result() for f in scan_futures]
        vars_found = facade.finalize_scan(scan_results).variables

        # Parse with regex pattern
        output_dir = tmp_path / "hist_regex_output"
        output_dir.mkdir()

        pattern = r"system.ruby.l\d+_cntrl\d+.xact_mgr.htm_transaction_commit_cycles"
        variables: list[ParseVariableConfig] = [
            {
                "name": pattern,
                "type": "histogram",
                "params": {"source_type": "histogram", "statistics": ["samples", "mean", "total"]},
            }
        ]

        parse_batch = facade.submit_parse_async(
            str(stats_dir),
            "stats.txt",
            facade.compile_parse_variables(variables),
            str(output_dir),
            scanned_vars=vars_found,
        )

        parse_results = [f.result() for f in parse_batch.futures]
        parsed_output = facade.finalize_parsing(parse_batch, parse_results)
        csv_path = parsed_output.csv_path

        assert csv_path is not None, "Parsing with regex pattern failed"
        assert Path(csv_path).exists(), f"CSV file not created: {csv_path}"

        # Verify data was parsed
        df = ParsedOutputIO.to_frame(parsed_output)
        assert len(df) > 0, "No data in parsed CSV"

        # Check that columns were created for the histogram
        histogram_cols = [c for c in df.columns if "htm_transaction_commit_cycles" in c]
        assert len(histogram_cols) > 0, "No histogram columns in output"

    def test_histogram_buckets_and_statistics_both_parsed(
        self, facade: ApplicationAPI, stats_dir: Path, tmp_path: Path
    ) -> None:
        """
        Test that both histogram buckets and statistics are correctly parsed.

        When additional statistics are selected, those statistics
        should appear as columns in the output CSV.
        """
        # Scan
        scan_futures = facade.submit_scan_async(str(stats_dir), "stats.txt", limit=-1)
        scan_results = [f.result() for f in scan_futures]
        vars_found = facade.finalize_scan(scan_results).variables

        # Parse with explicit statistics
        output_dir = tmp_path / "hist_explicit_stats_output"
        output_dir.mkdir()

        variables: list[ParseVariableConfig] = [
            {
                "name": "system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles",
                "type": "histogram",
                "params": {"source_type": "histogram", "statistics": ["samples", "mean"]},
            }
        ]

        parse_batch = facade.submit_parse_async(
            str(stats_dir),
            "stats.txt",
            facade.compile_parse_variables(variables),
            str(output_dir),
            scanned_vars=vars_found,
        )

        parse_results = [f.result() for f in parse_batch.futures]
        parsed_output = facade.finalize_parsing(parse_batch, parse_results)
        csv_path = parsed_output.csv_path

        assert csv_path is not None

        # Read and verify
        df = ParsedOutputIO.to_frame(parsed_output)

        # Should have columns for the requested statistics
        expected_stats = [
            "system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles..samples",
            "system.ruby.l0_cntrl0.xact_mgr.htm_transaction_commit_cycles..mean",
        ]

        for stat_col in expected_stats:
            assert stat_col in df.columns, f"Missing expected column: {stat_col}"
            assert not bool(df[stat_col].isna().all()), f"Column has no data: {stat_col}"
