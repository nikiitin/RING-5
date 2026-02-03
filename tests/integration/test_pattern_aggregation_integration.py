"""
Integration Tests for Pattern Aggregation in Scanner Service
Tests the full scanning workflow with pattern aggregation.
"""

import pytest
from pathlib import Path
from src.parsers.scanner_service import ScannerService


class TestScannerPatternAggregation:
    """Test pattern aggregation in full scanning workflow."""

    @pytest.fixture
    def stats_dir(self) -> Path:
        """Get path to test data directory."""
        return Path(__file__).parent.parent / "data" / "results-micro26-sens"

    def test_scan_aggregates_cpu_patterns(self, stats_dir: Path) -> None:
        """Test that scanner aggregates multiple CPU statistics into patterns."""
        # Find a stats file with multiple CPUs
        stats_pattern = "**/stats.txt"
        stats_files = list(stats_dir.rglob(stats_pattern))

        if not stats_files:
            pytest.skip("No stats files found in test data")

        # Submit scan
        futures = ScannerService.submit_scan_async(
            str(stats_dir), "stats.txt", limit=1  # Just scan one file for speed
        )

        # Get results
        scan_results = [f.result() for f in futures]
        scanned_vars = ScannerService.aggregate_scan_results(scan_results)

        # Check that we have pattern variables (not individual cpu0, cpu1, etc.)
        var_names = [v["name"] for v in scanned_vars]

        # Should have regex pattern for CPUs
        cpu_pattern_vars = [name for name in var_names if r"cpu\d+" in name]
        assert len(cpu_pattern_vars) > 0, "Should have CPU pattern variables"

        # Should NOT have individual cpu0, cpu1, etc.
        individual_cpus = [name for name in var_names if "cpu0" in name or "cpu1" in name]
        assert (
            len(individual_cpus) == 0
        ), f"Should not have individual CPU vars, found: {individual_cpus}"

    def test_scan_aggregates_controller_patterns(self, stats_dir: Path) -> None:
        """Test that scanner aggregates controller patterns (l0_cntrl, etc.)."""
        stats_files = list(stats_dir.rglob("stats.txt"))

        if not stats_files:
            pytest.skip("No stats files found in test data")

        # Submit scan
        futures = ScannerService.submit_scan_async(str(stats_dir), "stats.txt", limit=1)

        scan_results = [f.result() for f in futures]
        scanned_vars = ScannerService.aggregate_scan_results(scan_results)

        var_names = [v["name"] for v in scanned_vars]

        # Check for controller patterns
        controller_patterns = [
            name for name in var_names if r"cntrl\d+" in name or r"_cntrl\d+" in name
        ]

        # Should have pattern variables for controllers
        if any("cntrl" in name for name in var_names):
            assert len(controller_patterns) > 0, "Should have controller pattern variables"

    def test_scan_preserves_non_pattern_variables(self, stats_dir: Path) -> None:
        """Test that non-pattern variables are preserved."""
        stats_files = list(stats_dir.rglob("stats.txt"))

        if not stats_files:
            pytest.skip("No stats files found in test data")

        futures = ScannerService.submit_scan_async(str(stats_dir), "stats.txt", limit=1)

        scan_results = [f.result() for f in futures]
        scanned_vars = ScannerService.aggregate_scan_results(scan_results)

        var_names = [v["name"] for v in scanned_vars]

        # Should have some non-pattern variables (global stats, etc.)
        # These typically don't have numeric indices
        non_pattern_vars = [name for name in var_names if r"\d+" not in name]  # No regex pattern

        assert len(non_pattern_vars) > 0, "Should preserve some non-pattern variables"

    def test_scan_pattern_has_correct_entries(self, stats_dir: Path) -> None:
        """Test that pattern variables have correct entry lists."""
        stats_files = list(stats_dir.rglob("stats.txt"))

        if not stats_files:
            pytest.skip("No stats files found in test data")

        futures = ScannerService.submit_scan_async(str(stats_dir), "stats.txt", limit=1)

        scan_results = [f.result() for f in futures]
        scanned_vars = ScannerService.aggregate_scan_results(scan_results)

        # Find a CPU pattern variable
        cpu_vars = [v for v in scanned_vars if r"cpu\d+" in v["name"]]

        if cpu_vars:
            cpu_var = cpu_vars[0]

            # Should be type vector (aggregated scalars)
            assert cpu_var["type"] in ["vector", "distribution", "histogram"]

            # Should have entries list
            assert "entries" in cpu_var
            assert isinstance(cpu_var["entries"], list)
            assert len(cpu_var["entries"]) > 0

            # Entries should be numeric IDs like "0", "1", "2", etc.
            # (or could be entry names for vector types)
            assert all(isinstance(e, str) for e in cpu_var["entries"])

    def test_scan_reduces_variable_count(self, stats_dir: Path) -> None:
        """Test that aggregation reduces total variable count."""
        stats_files = list(stats_dir.rglob("stats.txt"))

        if not stats_files:
            pytest.skip("No stats files found in test data")

        # Scan WITHOUT aggregation (bypass by directly calling scanner)
        from src.parsers.scanner import Gem5StatsScanner

        scanner = Gem5StatsScanner.get_instance()
        raw_vars = scanner.scan_file(stats_files[0])

        # Scan WITH aggregation (through service)
        futures = ScannerService.submit_scan_async(str(stats_dir), "stats.txt", limit=1)
        scan_results = [f.result() for f in futures]
        aggregated_vars = ScannerService.aggregate_scan_results(scan_results)

        # Aggregation should significantly reduce variable count
        # (16 CPUs × N stats → N pattern variables)
        assert len(aggregated_vars) < len(
            raw_vars
        ), f"Aggregation should reduce count: {len(raw_vars)} → {len(aggregated_vars)}"

        # Should be at least 2x reduction for 16-CPU system
        reduction_ratio = len(raw_vars) / len(aggregated_vars)
        assert (
            reduction_ratio > 2.0
        ), f"Should have significant reduction, got {reduction_ratio:.2f}x"

    def test_scan_pattern_variable_is_parseable(self, stats_dir: Path) -> None:
        """Test that pattern variables can be parsed successfully."""
        stats_files = list(stats_dir.rglob("stats.txt"))

        if not stats_files:
            pytest.skip("No stats files found in test data")

        # Scan to get pattern variables
        futures = ScannerService.submit_scan_async(str(stats_dir), "stats.txt", limit=1)
        scan_results = [f.result() for f in futures]
        scanned_vars = ScannerService.aggregate_scan_results(scan_results)

        # Find a simple CPU scalar pattern (converted to vector)
        cpu_scalar_patterns = [
            v for v in scanned_vars if r"cpu\d+" in v["name"] and v["type"] == "vector"
        ]

        if not cpu_scalar_patterns:
            pytest.skip("No CPU scalar patterns found")

        # Pick one pattern variable
        pattern_var = cpu_scalar_patterns[0]

        # Verify it has the structure needed for parsing
        assert "name" in pattern_var
        assert "type" in pattern_var
        assert "entries" in pattern_var

        # The name should be a valid regex
        import re

        try:
            re.compile(pattern_var["name"])
        except re.error:
            pytest.fail(f"Pattern variable name is not valid regex: {pattern_var['name']}")
