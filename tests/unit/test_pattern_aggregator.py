"""
Unit Tests for Pattern Aggregator
Tests the pattern detection and aggregation logic for repeated gem5 variables.
"""

from src.parsers.pattern_aggregator import PatternAggregator


class TestPatternExtraction:
    """Test pattern extraction from variable names."""

    def test_extract_single_numeric_pattern(self) -> None:
        """Test extraction of single numeric index (e.g., cpu0, cpu1)."""
        result = PatternAggregator._extract_pattern("system.cpu0.numCycles")
        assert result is not None
        pattern, numeric_id = result
        assert pattern == "system.cpu{}.numCycles"
        assert numeric_id == "0"

    def test_extract_multiple_numeric_patterns(self) -> None:
        """Test extraction of multiple numeric indices (e.g., l0_cntrl1)."""
        result = PatternAggregator._extract_pattern("system.ruby.l0_cntrl1.stat")
        assert result is not None
        pattern, numeric_id = result
        assert pattern == "system.ruby.l{}_cntrl{}.stat"
        assert numeric_id == "0_1"

    def test_extract_no_pattern(self) -> None:
        """Test that non-numeric variables return None."""
        result = PatternAggregator._extract_pattern("system.total_cycles")
        assert result is None

    def test_extract_with_trailing_numbers(self) -> None:
        """Test handling of numbers in various positions."""
        result = PatternAggregator._extract_pattern("board.xid2.value")
        assert result is not None
        pattern, numeric_id = result
        assert pattern == "board.xid{}.value"
        assert numeric_id == "2"

    def test_extract_multiple_consecutive_numbers(self) -> None:
        """Test handling cpu10, cpu11 (multi-digit numbers)."""
        result = PatternAggregator._extract_pattern("system.cpu10.stat")
        assert result is not None
        pattern, numeric_id = result
        assert pattern == "system.cpu{}.stat"
        assert numeric_id == "10"


class TestPatternAggregation:
    """Test aggregation of repeated variables into patterns."""

    def test_aggregate_simple_scalar_pattern(self) -> None:
        """Test aggregating scalar variables with numeric indices."""
        variables = [
            {"name": "system.cpu0.numCycles", "type": "scalar"},
            {"name": "system.cpu1.numCycles", "type": "scalar"},
            {"name": "system.cpu2.numCycles", "type": "scalar"},
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0]["name"] == r"system.cpu\d+.numCycles"
        assert result[0]["type"] == "vector"
        assert result[0]["entries"] == ["0", "1", "2"]

    def test_aggregate_mixed_patterns_and_non_patterns(self) -> None:
        """Test that non-pattern variables are preserved."""
        variables = [
            {"name": "system.cpu0.numCycles", "type": "scalar"},
            {"name": "system.cpu1.numCycles", "type": "scalar"},
            {"name": "system.total_cycles", "type": "scalar"},  # No pattern
            {"name": "global.simulation_time", "type": "scalar"},  # No pattern
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        # Should have: cpu pattern + 2 non-patterns
        assert len(result) == 3

        names = [v["name"] for v in result]
        assert "global.simulation_time" in names
        assert "system.total_cycles" in names
        assert r"system.cpu\d+.numCycles" in names

    def test_aggregate_single_instance_not_aggregated(self) -> None:
        """Test that single instances are not converted to patterns."""
        variables = [
            {"name": "system.cpu0.numCycles", "type": "scalar"},
            {"name": "system.memory.accesses", "type": "scalar"},
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        # Both should be kept as-is (no pattern detected)
        assert len(result) == 2
        names = [v["name"] for v in result]
        assert "system.cpu0.numCycles" in names
        assert "system.memory.accesses" in names

    def test_aggregate_multiple_different_patterns(self) -> None:
        """Test multiple distinct patterns in same scan."""
        variables = [
            {"name": "system.cpu0.ipc", "type": "scalar"},
            {"name": "system.cpu1.ipc", "type": "scalar"},
            {"name": "system.ruby.l0_cntrl0.hits", "type": "scalar"},
            {"name": "system.ruby.l0_cntrl1.hits", "type": "scalar"},
            {"name": "system.ruby.l1_cntrl0.misses", "type": "scalar"},
            {"name": "system.ruby.l1_cntrl1.misses", "type": "scalar"},
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        # Should have 3 patterns: cpu, l0_cntrl, l1_cntrl
        assert len(result) == 3

        names = [v["name"] for v in result]
        assert r"system.cpu\d+.ipc" in names
        assert r"system.ruby.l\d+_cntrl\d+.hits" in names
        assert r"system.ruby.l\d+_cntrl\d+.misses" in names

    def test_aggregate_vector_variables(self) -> None:
        """Test aggregating variables that are already vectors."""
        variables = [
            {"name": "system.cpu0.instsIssued", "type": "vector", "entries": ["0", "1", "2"]},
            {"name": "system.cpu1.instsIssued", "type": "vector", "entries": ["0", "1", "2"]},
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0]["name"] == r"system.cpu\d+.instsIssued"
        assert result[0]["type"] == "vector"
        # Should merge entries from both instances
        assert "0" in result[0]["entries"]
        assert "1" in result[0]["entries"]
        assert "2" in result[0]["entries"]

    def test_aggregate_distribution_variables(self) -> None:
        """Test aggregating distribution variables with min/max."""
        variables = [
            {
                "name": "system.cpu0.latency",
                "type": "distribution",
                "entries": ["samples", "mean"],
                "minimum": 10.0,
                "maximum": 100.0,
            },
            {
                "name": "system.cpu1.latency",
                "type": "distribution",
                "entries": ["samples", "mean"],
                "minimum": 5.0,
                "maximum": 120.0,
            },
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0]["name"] == r"system.cpu\d+.latency"
        assert result[0]["type"] == "distribution"
        assert result[0]["minimum"] == 5.0  # Min of all minimums
        assert result[0]["maximum"] == 120.0  # Max of all maximums

    def test_aggregate_histogram_variables(self) -> None:
        """Test aggregating histogram variables."""
        variables = [
            {
                "name": "system.cpu0.histogram",
                "type": "histogram",
                "entries": ["0", "10", "20", "samples", "mean"],
            },
            {
                "name": "system.cpu1.histogram",
                "type": "histogram",
                "entries": ["0", "10", "20", "samples", "mean"],
            },
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0]["name"] == r"system.cpu\d+.histogram"
        assert result[0]["type"] == "histogram"
        assert "samples" in result[0]["entries"]
        assert "mean" in result[0]["entries"]

    def test_aggregate_preserves_sorting(self) -> None:
        """Test that result is sorted alphabetically by name."""
        variables = [
            {"name": "system.zeta.value", "type": "scalar"},
            {"name": "system.cpu1.ipc", "type": "scalar"},
            {"name": "system.cpu0.ipc", "type": "scalar"},
            {"name": "system.alpha.stat", "type": "scalar"},
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        names = [v["name"] for v in result]
        assert names == sorted(names)

    def test_aggregate_large_number_range(self) -> None:
        """Test aggregating 16 CPUs (cpu0-cpu15)."""
        variables = [{"name": f"system.cpu{i}.numCycles", "type": "scalar"} for i in range(16)]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0]["name"] == r"system.cpu\d+.numCycles"
        assert result[0]["type"] == "vector"
        assert len(result[0]["entries"]) == 16
        assert "0" in result[0]["entries"]
        assert "15" in result[0]["entries"]

    def test_aggregate_mixed_numeric_widths(self) -> None:
        """Test handling both single and double-digit indices (cpu0-cpu15)."""
        variables = [
            {"name": "system.cpu0.stat", "type": "scalar"},
            {"name": "system.cpu9.stat", "type": "scalar"},
            {"name": "system.cpu10.stat", "type": "scalar"},
            {"name": "system.cpu15.stat", "type": "scalar"},
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0]["name"] == r"system.cpu\d+.stat"
        assert result[0]["entries"] == ["0", "10", "15", "9"]  # Sorted lexically

    def test_aggregate_empty_list(self) -> None:
        """Test handling empty variable list."""
        result = PatternAggregator.aggregate_patterns([])
        assert result == []

    def test_aggregate_complex_multi_index_pattern(self) -> None:
        """Test complex patterns like l0_cntrl0, l1_cntrl1, etc."""
        variables = [
            {"name": "system.ruby.l0_cntrl0.hits", "type": "scalar"},
            {"name": "system.ruby.l0_cntrl1.hits", "type": "scalar"},
            {"name": "system.ruby.l1_cntrl0.hits", "type": "scalar"},
            {"name": "system.ruby.l1_cntrl1.hits", "type": "scalar"},
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0]["name"] == r"system.ruby.l\d+_cntrl\d+.hits"
        assert result[0]["entries"] == ["0_0", "0_1", "1_0", "1_1"]


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_variables_without_type(self) -> None:
        """Test handling variables missing 'type' field."""
        variables = [
            {"name": "system.cpu0.stat"},  # Missing type
            {"name": "system.cpu1.stat"},  # Missing type
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        # Should still aggregate, defaulting to scalar -> vector
        assert len(result) == 1
        assert result[0]["type"] == "vector"

    def test_variables_with_special_characters(self) -> None:
        """Test variables with dots, underscores, etc."""
        variables = [
            {"name": "system.cpu0.dcache.overall_hits", "type": "scalar"},
            {"name": "system.cpu1.dcache.overall_hits", "type": "scalar"},
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0]["name"] == r"system.cpu\d+.dcache.overall_hits"

    def test_no_aggregation_for_different_stat_names(self) -> None:
        """Test that different stats don't get aggregated even with same index."""
        variables = [
            {"name": "system.cpu0.ipc", "type": "scalar"},
            {"name": "system.cpu0.numCycles", "type": "scalar"},
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        # Should remain separate (no repeated pattern)
        assert len(result) == 2
        names = [v["name"] for v in result]
        assert "system.cpu0.ipc" in names
        assert "system.cpu0.numCycles" in names
