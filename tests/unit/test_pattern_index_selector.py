"""
Unit Tests for Pattern Index Selector
Tests pattern detection and index filtering logic.
"""

import time

from src.web.ui.components.pattern_index_selector import PatternIndexSelector


class TestPatternDetection:
    """Test pattern variable detection."""

    def test_is_pattern_variable_with_pattern(self) -> None:
        """Test detection of pattern variables."""
        assert PatternIndexSelector.is_pattern_variable(r"system.cpu\d+.stat")
        assert PatternIndexSelector.is_pattern_variable(r"system.ruby.l\d+_cntrl\d+.hits")

    def test_is_pattern_variable_without_pattern(self) -> None:
        """Test non-pattern variables return False."""
        assert not PatternIndexSelector.is_pattern_variable("system.total_cycles")
        assert not PatternIndexSelector.is_pattern_variable("global.time")


class TestIndexExtraction:
    """Test extraction of index positions from pattern names."""

    def test_extract_single_position(self) -> None:
        """Test extraction of single index position."""
        positions = PatternIndexSelector.extract_index_positions(r"system.cpu\d+.stat")
        assert positions == ["cpu"]

    def test_extract_multiple_positions(self) -> None:
        """Test extraction of multiple index positions."""
        positions = PatternIndexSelector.extract_index_positions(r"system.ruby.l\d+_cntrl\d+.hits")
        assert positions == ["l", "cntrl"]

    def test_extract_complex_pattern(self) -> None:
        """Test extraction from complex patterns."""
        positions = PatternIndexSelector.extract_index_positions(
            r"system.board\d+.xid\d+.bank\d+.value"
        )
        assert positions == ["board", "xid", "bank"]

    def test_extract_no_pattern(self) -> None:
        """Test extraction returns empty for non-pattern variables."""
        positions = PatternIndexSelector.extract_index_positions("system.total")
        assert positions == []


class TestEntryParsing:
    """Test parsing of entry indices."""

    def test_parse_single_index_entries(self) -> None:
        """Test parsing entries with single index."""
        entries = ["0", "1", "2", "15"]
        result = PatternIndexSelector.parse_entry_indices(entries)

        assert 0 in result
        assert result[0] == {"0", "1", "2", "15"}

    def test_parse_double_index_entries(self) -> None:
        """Test parsing entries with two indices."""
        entries = ["0_0", "0_1", "1_0", "1_1", "2_0"]
        result = PatternIndexSelector.parse_entry_indices(entries)

        assert 0 in result
        assert 1 in result
        assert result[0] == {"0", "1", "2"}
        assert result[1] == {"0", "1"}

    def test_parse_triple_index_entries(self) -> None:
        """Test parsing entries with three indices."""
        entries = ["0_0_0", "0_0_1", "1_2_3"]
        result = PatternIndexSelector.parse_entry_indices(entries)

        assert len(result) == 3
        assert result[0] == {"0", "1"}
        assert result[1] == {"0", "2"}
        assert result[2] == {"0", "1", "3"}

    def test_parse_empty_entries(self) -> None:
        """Test parsing empty entry list."""
        result = PatternIndexSelector.parse_entry_indices([])
        assert result == {}


class TestEntryFiltering:
    """Test filtering of entries based on index selection."""

    def test_filter_single_position_all(self) -> None:
        """Test filtering with all indices selected for single position."""
        entries = ["0", "1", "2", "15"]
        selections = {0: ["0", "1", "2", "15"]}

        filtered = PatternIndexSelector._filter_entries(entries, selections)
        assert filtered == entries

    def test_filter_single_position_subset(self) -> None:
        """Test filtering with subset of indices."""
        entries = ["0", "1", "2", "15"]
        selections = {0: ["0", "2"]}

        filtered = PatternIndexSelector._filter_entries(entries, selections)
        assert filtered == ["0", "2"]

    def test_filter_double_position_first_only(self) -> None:
        """Test filtering on first position only."""
        entries = ["0_0", "0_1", "1_0", "1_1", "2_0"]
        selections = {0: ["0"], 1: ["0", "1"]}  # l{0}_cntrl{all}

        filtered = PatternIndexSelector._filter_entries(entries, selections)
        assert filtered == ["0_0", "0_1"]

    def test_filter_double_position_second_only(self) -> None:
        """Test filtering on second position only."""
        entries = ["0_0", "0_1", "1_0", "1_1", "2_0"]
        selections = {0: ["0", "1", "2"], 1: ["0"]}  # l{all}_cntrl{0}

        filtered = PatternIndexSelector._filter_entries(entries, selections)
        assert filtered == ["0_0", "1_0", "2_0"]

    def test_filter_double_position_both(self) -> None:
        """Test filtering on both positions."""
        entries = ["0_0", "0_1", "1_0", "1_1", "2_0"]
        selections = {0: ["1"], 1: ["0", "1"]}  # l{1}_cntrl{0,1}

        filtered = PatternIndexSelector._filter_entries(entries, selections)
        assert filtered == ["1_0", "1_1"]

    def test_filter_cache_levels(self) -> None:
        """Test realistic cache level filtering scenario."""
        # Entries like: l{0,1,2}_cntrl{0,1,...,15}
        entries = []
        for level in [0, 1, 2]:
            for c in range(16):
                entries.append(f"{level}_{c}")

        # Select only L0 caches, controllers 0-3
        selections = {0: ["0"], 1: ["0", "1", "2", "3"]}

        filtered = PatternIndexSelector._filter_entries(entries, selections)
        assert len(filtered) == 4
        assert filtered == ["0_0", "0_1", "0_2", "0_3"]

    def test_filter_empty_selection(self) -> None:
        """Test that empty selection excludes all."""
        entries = ["0_0", "0_1", "1_0"]
        selections = {0: [], 1: ["0", "1"]}  # Empty first position

        filtered = PatternIndexSelector._filter_entries(entries, selections)
        assert filtered == []

    def test_filter_no_match(self) -> None:
        """Test filtering with non-matching selection."""
        entries = ["0_0", "0_1", "1_0"]
        selections = {0: ["2"], 1: ["0"]}  # l{2} doesn't exist

        filtered = PatternIndexSelector._filter_entries(entries, selections)
        assert filtered == []


class TestFormatting:
    """Test entry display formatting."""

    def test_format_single_index(self) -> None:
        """Test formatting single index entry."""
        result = PatternIndexSelector._format_entry_display("0", ["cpu"])
        assert result == "cpu{0}"

    def test_format_double_index(self) -> None:
        """Test formatting double index entry."""
        result = PatternIndexSelector._format_entry_display("1_2", ["l", "cntrl"])
        assert result == "l{1}_cntrl{2}"

    def test_format_triple_index(self) -> None:
        """Test formatting triple index entry."""
        result = PatternIndexSelector._format_entry_display("0_1_2", ["board", "xid", "bank"])
        assert result == "board{0}_xid{1}_bank{2}"

    def test_format_more_parts_than_positions(self) -> None:
        """Test formatting when entry has more parts than position labels."""
        result = PatternIndexSelector._format_entry_display("0_1_2", ["l", "cntrl"])
        assert result == "l{0}_cntrl{1}_2"


class TestRealisticScenarios:
    """Test realistic usage scenarios."""

    def test_cpu_pattern(self) -> None:
        """Test CPU pattern filtering."""
        var_name = r"system.cpu\d+.numCycles"
        entries = [str(i) for i in range(16)]  # cpu0-cpu15

        positions = PatternIndexSelector.extract_index_positions(var_name)
        assert positions == ["cpu"]

        position_values = PatternIndexSelector.parse_entry_indices(entries)
        assert len(position_values[0]) == 16

        # Select only CPUs 0, 1, 2, 3
        selections = {0: ["0", "1", "2", "3"]}
        filtered = PatternIndexSelector._filter_entries(entries, selections)
        assert filtered == ["0", "1", "2", "3"]

    def test_cache_controller_pattern(self) -> None:
        """Test cache controller pattern filtering."""
        var_name = r"system.ruby.l\d+_cntrl\d+.hits"

        # Generate entries: l{0,1,2}_cntrl{0-15}
        entries = []
        for level in [0, 1, 2]:
            for ctrl in range(16):
                entries.append(f"{level}_{ctrl}")

        positions = PatternIndexSelector.extract_index_positions(var_name)
        assert positions == ["l", "cntrl"]

        position_values = PatternIndexSelector.parse_entry_indices(entries)
        assert position_values[0] == {"0", "1", "2"}  # Cache levels
        assert len(position_values[1]) == 16  # Controllers

        # Select L1 caches, all controllers
        selections = {0: ["1"], 1: [str(i) for i in range(16)]}
        filtered = PatternIndexSelector._filter_entries(entries, selections)
        assert len(filtered) == 16
        assert all(e.startswith("1_") for e in filtered)

    def test_multiple_cache_levels(self) -> None:
        """Test selecting multiple cache levels."""
        entries = []
        for level in [0, 1, 2]:
            for ctrl in range(4):
                entries.append(f"{level}_{ctrl}")

        # Select L0 and L2, controllers 0 and 1
        selections = {0: ["0", "2"], 1: ["0", "1"]}
        filtered = PatternIndexSelector._filter_entries(entries, selections)

        expected = ["0_0", "0_1", "2_0", "2_1"]
        assert filtered == expected


class TestReDoSSecurity:
    """Test that the regex pattern doesn't have ReDoS vulnerabilities."""

    def test_no_redos_with_pathological_input(self) -> None:
        """Test that pathological inputs don't cause exponential backtracking."""
        # Pathological case: many repeating characters that could cause
        # catastrophic backtracking with overlapping character classes
        pathological_input = "A" + "a" * 30

        # Measure time to ensure it completes quickly (< 0.1 seconds)
        start = time.time()
        result = PatternIndexSelector.extract_index_positions(pathological_input)
        elapsed = time.time() - start

        # Should return empty list since input doesn't contain \d+ pattern
        assert result == []
        # Should complete very quickly (< 100ms indicates no exponential backtracking)
        assert elapsed < 0.1, f"Pattern matching took too long: {elapsed}s"

    def test_no_redos_with_complex_input(self) -> None:
        """Test that complex inputs with many underscores complete quickly."""
        # Input with many underscores and letters that could trigger backtracking
        complex_input = "_" * 20 + "a" * 20 + "A" * 20

        start = time.time()
        result = PatternIndexSelector.extract_index_positions(complex_input)
        elapsed = time.time() - start

        assert result == []
        assert elapsed < 0.1, f"Pattern matching took too long: {elapsed}s"
