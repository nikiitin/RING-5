"""
Unit Tests for Pattern Aggregator
Tests the pattern detection and aggregation logic for repeated gem5 variables.
"""

from src.core.models.source_evidence import ResolvedSourceKind


from src.core.models.parsing_models import SourceInstance
from typing import cast

from src.core.models.parsing_models import ScannedVariable
from src.parsing.gem5.impl.scanning.pattern_aggregator import PatternAggregator


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
            ScannedVariable(
                name="system.cpu0.numCycles",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.numCycles", ()),),
            ),
            ScannedVariable(
                name="system.cpu1.numCycles",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu1.numCycles", ()),),
            ),
            ScannedVariable(
                name="system.cpu2.numCycles",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu2.numCycles", ()),),
            ),
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0].name == r"system.cpu\d+.numCycles"
        assert result[0].type == "vector"
        assert result[0].entries == []
        assert result[0].source_evidence == ResolvedSourceKind("scalar", "backend_metadata")
        assert result[0].instances == (
            SourceInstance("system.cpu0.numCycles", ("0",)),
            SourceInstance("system.cpu1.numCycles", ("1",)),
            SourceInstance("system.cpu2.numCycles", ("2",)),
        )

    def test_aggregate_mixed_patterns_and_non_patterns(self) -> None:
        """Test that non-pattern variables are preserved."""
        variables = [
            ScannedVariable(
                name="system.cpu0.numCycles",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.numCycles", ()),),
            ),
            ScannedVariable(
                name="system.cpu1.numCycles",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu1.numCycles", ()),),
            ),
            ScannedVariable(
                name="system.total_cycles",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.total_cycles", ()),),
            ),  # No pattern
            ScannedVariable(
                name="global.simulation_time",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("global.simulation_time", ()),),
            ),  # No pattern
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        # Should have: cpu pattern + 2 non-patterns
        assert len(result) == 3

        names = [v.name for v in result]
        assert "global.simulation_time" in names
        assert "system.total_cycles" in names
        assert r"system.cpu\d+.numCycles" in names

    def test_aggregate_single_instance_not_aggregated(self) -> None:
        """Test that single instances are not converted to patterns."""
        variables = [
            ScannedVariable(
                name="system.cpu0.numCycles",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.numCycles", ()),),
            ),
            ScannedVariable(
                name="system.memory.accesses",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.memory.accesses", ()),),
            ),
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        # Both should be kept as-is (no pattern detected)
        assert len(result) == 2
        names = [v.name for v in result]
        assert "system.cpu0.numCycles" in names
        assert "system.memory.accesses" in names

    def test_aggregate_multiple_different_patterns(self) -> None:
        """Test multiple distinct patterns in same scan."""
        variables = [
            ScannedVariable(
                name="system.cpu0.ipc",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.ipc", ()),),
            ),
            ScannedVariable(
                name="system.cpu1.ipc",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu1.ipc", ()),),
            ),
            ScannedVariable(
                name="system.ruby.l0_cntrl0.hits",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.ruby.l0_cntrl0.hits", ()),),
            ),
            ScannedVariable(
                name="system.ruby.l0_cntrl1.hits",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.ruby.l0_cntrl1.hits", ()),),
            ),
            ScannedVariable(
                name="system.ruby.l1_cntrl0.misses",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.ruby.l1_cntrl0.misses", ()),),
            ),
            ScannedVariable(
                name="system.ruby.l1_cntrl1.misses",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.ruby.l1_cntrl1.misses", ()),),
            ),
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        # Should have 3 patterns: cpu, l0_cntrl, l1_cntrl
        assert len(result) == 3

        names = [v.name for v in result]
        assert r"system.cpu\d+.ipc" in names
        assert r"system.ruby.l\d+_cntrl\d+.hits" in names
        assert r"system.ruby.l\d+_cntrl\d+.misses" in names

    def test_aggregate_vector_variables(self) -> None:
        """Test aggregating variables that are already vectors."""
        variables = [
            ScannedVariable(
                name="system.cpu0.instsIssued",
                type="vector",
                entries=["0", "1", "2"],
                source_evidence=ResolvedSourceKind("vector", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.instsIssued", ()),),
            ),
            ScannedVariable(
                name="system.cpu1.instsIssued",
                type="vector",
                entries=["0", "1", "2"],
                source_evidence=ResolvedSourceKind("vector", "backend_metadata"),
                instances=(SourceInstance("system.cpu1.instsIssued", ()),),
            ),
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0].name == r"system.cpu\d+.instsIssued"
        assert result[0].type == "vector"
        # Should merge entries from both instances
        assert "0" in result[0].entries
        assert "1" in result[0].entries
        assert "2" in result[0].entries

    def test_aggregate_distribution_variables(self) -> None:
        """Retain declared backend evidence and observed numeric labels."""
        variables = [
            ScannedVariable(
                name="system.cpu0.latency",
                type="distribution",
                entries=["10", "100", "samples", "mean"],
                source_evidence=ResolvedSourceKind("distribution", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.latency", ()),),
            ),
            ScannedVariable(
                name="system.cpu1.latency",
                type="distribution",
                entries=["5", "120", "samples", "mean"],
                source_evidence=ResolvedSourceKind("distribution", "backend_metadata"),
                instances=(SourceInstance("system.cpu1.latency", ()),),
            ),
        ]

        result = PatternAggregator.aggregate_patterns(cast(list[ScannedVariable], variables))

        assert len(result) == 1
        res0 = cast(ScannedVariable, result[0])
        assert res0.name == r"system.cpu\d+.latency"
        assert res0.type == "distribution"
        assert set(res0.entries) == {"5", "10", "100", "120", "samples", "mean"}
        assert res0.source_evidence == ResolvedSourceKind("distribution", "backend_metadata")
        assert "minimum" not in res0.to_dict() and "maximum" not in res0.to_dict()

    def test_aggregate_histogram_variables(self) -> None:
        """Test aggregating histogram variables."""
        variables = [
            ScannedVariable(
                name="system.cpu0.histogram",
                type="histogram",
                entries=["0", "10", "20", "samples", "mean"],
                source_evidence=ResolvedSourceKind("histogram", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.histogram", ()),),
            ),
            ScannedVariable(
                name="system.cpu1.histogram",
                type="histogram",
                entries=["0", "10", "20", "samples", "mean"],
                source_evidence=ResolvedSourceKind("histogram", "backend_metadata"),
                instances=(SourceInstance("system.cpu1.histogram", ()),),
            ),
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0].name == r"system.cpu\d+.histogram"
        assert result[0].type == "histogram"
        assert "samples" in result[0].entries
        assert "mean" in result[0].entries

    def test_aggregate_preserves_sorting(self) -> None:
        """Test that result is sorted alphabetically by name."""
        variables = [
            ScannedVariable(
                name="system.zeta.value",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.zeta.value", ()),),
            ),
            ScannedVariable(
                name="system.cpu1.ipc",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu1.ipc", ()),),
            ),
            ScannedVariable(
                name="system.cpu0.ipc",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.ipc", ()),),
            ),
            ScannedVariable(
                name="system.alpha.stat",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.alpha.stat", ()),),
            ),
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        names = [v.name for v in result]
        assert names == sorted(names)

    def test_aggregate_large_number_range(self) -> None:
        """Test aggregating 16 CPUs (cpu0-cpu15)."""
        variables = [
            ScannedVariable(
                name=f"system.cpu{i}.numCycles",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance(f"system.cpu{i}.numCycles", ()),),
            )
            for i in range(16)
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0].name == r"system.cpu\d+.numCycles"
        assert result[0].type == "vector"
        assert result[0].entries == []
        assert len(result[0].instances) == 16
        assert {record.indices for record in result[0].instances} == {(str(i),) for i in range(16)}

    def test_aggregate_mixed_numeric_widths(self) -> None:
        """Test handling both single and double-digit indices (cpu0-cpu15)."""
        variables = [
            ScannedVariable(
                name="system.cpu0.stat",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.stat", ()),),
            ),
            ScannedVariable(
                name="system.cpu9.stat",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu9.stat", ()),),
            ),
            ScannedVariable(
                name="system.cpu10.stat",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu10.stat", ()),),
            ),
            ScannedVariable(
                name="system.cpu15.stat",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu15.stat", ()),),
            ),
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0].name == r"system.cpu\d+.stat"
        assert result[0].entries == []
        assert [record.indices for record in result[0].instances] == [
            ("0",),
            ("9",),
            ("10",),
            ("15",),
        ]

    def test_aggregate_empty_list(self) -> None:
        """Test handling empty variable list."""
        result = PatternAggregator.aggregate_patterns([])
        assert result == []

    def test_aggregate_complex_multi_index_pattern(self) -> None:
        """Test complex patterns like l0_cntrl0, l1_cntrl1, etc."""
        variables = [
            ScannedVariable(
                name="system.ruby.l0_cntrl0.hits",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.ruby.l0_cntrl0.hits", ()),),
            ),
            ScannedVariable(
                name="system.ruby.l0_cntrl1.hits",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.ruby.l0_cntrl1.hits", ()),),
            ),
            ScannedVariable(
                name="system.ruby.l1_cntrl0.hits",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.ruby.l1_cntrl0.hits", ()),),
            ),
            ScannedVariable(
                name="system.ruby.l1_cntrl1.hits",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.ruby.l1_cntrl1.hits", ()),),
            ),
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0].name == r"system.ruby.l\d+_cntrl\d+.hits"
        assert result[0].entries == []
        assert [record.indices for record in result[0].instances] == [
            ("0", "0"),
            ("0", "1"),
            ("1", "0"),
            ("1", "1"),
        ]


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_variables_with_special_characters(self) -> None:
        """Test variables with dots, underscores, etc."""
        variables = [
            ScannedVariable(
                name="system.cpu0.dcache.overall_hits",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.dcache.overall_hits", ()),),
            ),
            ScannedVariable(
                name="system.cpu1.dcache.overall_hits",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu1.dcache.overall_hits", ()),),
            ),
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 1
        assert result[0].name == r"system.cpu\d+.dcache.overall_hits"

    def test_no_aggregation_for_different_stat_names(self) -> None:
        """Test that different stats don't get aggregated even with same index."""
        variables = [
            ScannedVariable(
                name="system.cpu0.ipc",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.ipc", ()),),
            ),
            ScannedVariable(
                name="system.cpu0.numCycles",
                type="scalar",
                source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
                instances=(SourceInstance("system.cpu0.numCycles", ()),),
            ),
        ]

        result = PatternAggregator.aggregate_patterns(variables)

        # Should remain separate (no repeated pattern)
        assert len(result) == 2
        names = [v.name for v in result]
        assert "system.cpu0.ipc" in names
        assert "system.cpu0.numCycles" in names
