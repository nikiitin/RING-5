from pathlib import Path

import pytest

from src.core.models.parsing_models import StatConfig
from src.core.common.parsed_output import ParsedOutputIO
from src.parsing.gem5.impl.gem5_parser import Gem5Parser


class TestStatisticsOnlyIntegration:
    """Test statistics-only mode with real gem5 stats files."""

    # [test->req~ring5.ingestion.statistics-only~1]

    @pytest.fixture
    def stats_file(self, tmp_path: Path) -> Path:
        """Create a sample stats.txt file with distribution data."""
        stats_content = """
---------- Begin Simulation Statistics ----------
simTicks                                  1000000
system.cpu.numCycles                           100
system.mem.latency_dist::samples               500
system.mem.latency_dist::mean             10.5
system.mem.latency_dist::stdev             2.3
system.mem.latency_dist::underflows            5
system.mem.latency_dist::0                    10
system.mem.latency_dist::1                    20
system.mem.latency_dist::2                    30
system.mem.latency_dist::3                    40
system.mem.latency_dist::4                    50
system.mem.latency_dist::5                    60
system.mem.latency_dist::6                    70
system.mem.latency_dist::7                    80
system.mem.latency_dist::8                    90
system.mem.latency_dist::9                   100
system.mem.latency_dist::10                   45
system.mem.latency_dist::overflows             5
system.mem.latency_dist::total               500
---------- End Simulation Statistics   ----------
"""
        stats_path = tmp_path / "stats.txt"
        stats_path.write_text(stats_content)
        return stats_path

    def test_distribution_statistics_only_parsing(self, stats_file: Path, tmp_path: Path) -> None:
        """Test parsing distribution with only statistics (no buckets)."""
        # Configure variable with statistics_only=True
        variables = [
            StatConfig(
                name="system.mem.latency_dist",
                type="distribution",
                statistics_only=True,
                params={
                    "minimum": 0,
                    "maximum": 10,
                    "statistics": ["samples", "mean", "stdev", "total"],
                    "source_type": "distribution",
                },
            )
        ]

        output_dir = str(tmp_path / "stats_only_output_1")
        Path(output_dir).mkdir()

        # Parse with statistics-only mode
        batch = Gem5Parser.submit_parse_async(
            stats_path=str(stats_file.parent),
            stats_pattern="stats.txt",
            variables=variables,
            output_dir=output_dir,
        )
        parse_results = [f.result() for f in batch.futures]
        parsed_output = Gem5Parser.finalize_parsing(batch, parse_results)
        csv_path = parsed_output.csv_path

        # Load and verify CSV
        assert csv_path is not None
        df = ParsedOutputIO.to_frame(parsed_output)

        # Should have 1 row (1 simpoint)
        assert len(df) == 1

        # Should have only statistics columns, no bucket columns
        # Column names use ".." separator for distribution statistics
        assert "system.mem.latency_dist..samples" in df.columns
        assert "system.mem.latency_dist..mean" in df.columns
        assert "system.mem.latency_dist..stdev" in df.columns
        assert "system.mem.latency_dist..total" in df.columns

        # Statistics-only output contains the four aggregates and parser metadata.
        assert len(df.columns) <= 7  # simpoint + 4 stats + maybe 1-2 extras

        # Verify values
        assert df["system.mem.latency_dist..samples"].iloc[0] == 500
        assert df["system.mem.latency_dist..mean"].iloc[0] == 10.5
        assert df["system.mem.latency_dist..stdev"].iloc[0] == 2.3
        assert df["system.mem.latency_dist..total"].iloc[0] == 500

    def test_distribution_full_mode_parsing(self, stats_file: Path, tmp_path: Path) -> None:
        """Test parsing distribution with full buckets (statistics_only=False)."""
        # Configure variable with statistics_only=False
        variables = [
            StatConfig(
                name="system.mem.latency_dist",
                type="distribution",
                statistics_only=False,
                params={
                    "minimum": 0,
                    "maximum": 10,
                    "statistics": ["samples", "mean", "stdev", "total"],
                    "source_type": "distribution",
                },
            )
        ]

        output_dir = str(tmp_path / "stats_only_output_2")
        Path(output_dir).mkdir()

        # Parse with full mode
        batch = Gem5Parser.submit_parse_async(
            stats_path=str(stats_file.parent),
            stats_pattern="stats.txt",
            variables=variables,
            output_dir=output_dir,
        )
        parse_results = [f.result() for f in batch.futures]
        parsed_output = Gem5Parser.finalize_parsing(batch, parse_results)
        csv_path = parsed_output.csv_path

        # Load and verify CSV
        assert csv_path is not None
        df = ParsedOutputIO.to_frame(parsed_output)

        # Should have 1 row (1 simpoint)
        assert len(df) == 1

        # Should have statistics columns
        assert "system.mem.latency_dist..samples" in df.columns
        assert "system.mem.latency_dist..mean" in df.columns

        # Full mode includes the distribution buckets in addition to aggregates.
        assert len(df.columns) > 10

    def test_statistics_only_reduces_column_count(self, stats_file: Path, tmp_path: Path) -> None:
        """Verify that statistics-only mode significantly reduces column count."""
        variables_full = [
            StatConfig(
                name="system.mem.latency_dist",
                type="distribution",
                statistics_only=False,
                params={
                    "minimum": 0,
                    "maximum": 10,
                    "statistics": ["samples", "mean", "stdev", "total"],
                    "source_type": "distribution",
                },
            )
        ]

        variables_stats_only = [
            StatConfig(
                name="system.mem.latency_dist",
                type="distribution",
                statistics_only=True,
                params={
                    "minimum": 0,
                    "maximum": 10,
                    "statistics": ["samples", "mean", "stdev", "total"],
                    "source_type": "distribution",
                },
            )
        ]

        output_dir_full = str(tmp_path / "stats_only_full")
        Path(output_dir_full).mkdir()

        # Parse full mode
        batch_full = Gem5Parser.submit_parse_async(
            stats_path=str(stats_file.parent),
            stats_pattern="stats.txt",
            variables=variables_full,
            output_dir=output_dir_full,
        )
        results_full = [f.result() for f in batch_full.futures]
        output_full = Gem5Parser.finalize_parsing(batch_full, results_full)
        csv_full = output_full.csv_path
        assert csv_full is not None
        df_full = ParsedOutputIO.to_frame(output_full)

        output_dir_stats = str(tmp_path / "stats_only_stats")
        Path(output_dir_stats).mkdir()

        # Parse statistics-only mode
        batch_stats = Gem5Parser.submit_parse_async(
            stats_path=str(stats_file.parent),
            stats_pattern="stats.txt",
            variables=variables_stats_only,
            output_dir=output_dir_stats,
        )
        results_stats = [f.result() for f in batch_stats.futures]
        output_stats = Gem5Parser.finalize_parsing(batch_stats, results_stats)
        csv_stats = output_stats.csv_path
        assert csv_stats is not None
        df_stats = ParsedOutputIO.to_frame(output_stats)

        # Statistics-only should have fewer columns
        # Full mode will have all bucket columns (underflows, 0-10, overflows)
        # Statistics-only should only have the 4 statistics
        assert len(df_stats.columns) < len(df_full.columns)
        # Stats-only: simpoint + 4 statistics = 5 columns (or close to it)
        # Full: simpoint + 4 stats + 13 buckets (underflows, 0-10, overflows) = 18+
        assert len(df_stats.columns) <= 7  # Allow some extras
        assert len(df_full.columns) >= 15  # Should have many bucket columns
