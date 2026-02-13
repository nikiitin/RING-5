"""
Tests for PatternIndexService — pure business logic for pattern variable operations.

Extracted from UI layer (pattern_index_selector.py) to Layer B.
"""

from src.core.services.data_services.pattern_index_service import (
    PatternIndexService,
)


class TestIsPatternVariable:
    """Tests for is_pattern_variable detection."""

    def test_pattern_with_single_digit_group(self) -> None:
        assert PatternIndexService.is_pattern_variable(r"system.cpu\d+.ipc") is True

    def test_pattern_with_multiple_digit_groups(self) -> None:
        assert PatternIndexService.is_pattern_variable(r"system.ruby.l\d+_cntrl\d+.stat") is True

    def test_non_pattern_variable(self) -> None:
        assert PatternIndexService.is_pattern_variable("system.cpu.ipc") is False

    def test_empty_string(self) -> None:
        assert PatternIndexService.is_pattern_variable("") is False

    def test_partial_match(self) -> None:
        """Ensure partial \\d does not match."""
        assert PatternIndexService.is_pattern_variable(r"system.\d.stat") is False

    def test_escaped_d_plus(self) -> None:
        assert PatternIndexService.is_pattern_variable(r"a\d+b") is True


class TestExtractIndexPositions:
    """Tests for extracting position labels from pattern names."""

    def test_single_position(self) -> None:
        result = PatternIndexService.extract_index_positions(r"system.cpu\d+.ipc")
        assert result == ["cpu"]

    def test_two_positions(self) -> None:
        result = PatternIndexService.extract_index_positions(r"system.ruby.l\d+_cntrl\d+.stat")
        assert result == ["l", "cntrl"]

    def test_three_positions(self) -> None:
        result = PatternIndexService.extract_index_positions(
            r"system.chip\d+.core\d+.thread\d+.ipc"
        )
        assert result == ["chip", "core", "thread"]

    def test_no_pattern(self) -> None:
        result = PatternIndexService.extract_index_positions("system.cpu.ipc")
        assert result == []

    def test_empty_string(self) -> None:
        result = PatternIndexService.extract_index_positions("")
        assert result == []

    def test_leading_underscore_stripped(self) -> None:
        """Labels like _cntrl should become cntrl."""
        result = PatternIndexService.extract_index_positions(r"system.ruby.l\d+_cntrl\d+.stat")
        assert "cntrl" in result
        assert "_cntrl" not in result

    def test_numeric_prefix_label(self) -> None:
        """When label contains digits at start, only alpha tail is extracted."""
        result = PatternIndexService.extract_index_positions(r"sys.abc123xyz\d+.stat")
        assert result == ["xyz"]


class TestParseEntryIndices:
    """Tests for parsing entries into position-value mappings."""

    def test_two_positions(self) -> None:
        entries = ["0_0", "0_1", "1_0", "1_1"]
        result = PatternIndexService.parse_entry_indices(entries)
        assert result[0] == {"0", "1"}
        assert result[1] == {"0", "1"}

    def test_single_position(self) -> None:
        entries = ["0", "1", "2", "3"]
        result = PatternIndexService.parse_entry_indices(entries)
        assert len(result) == 1
        assert result[0] == {"0", "1", "2", "3"}

    def test_three_positions(self) -> None:
        entries = ["0_0_0", "0_0_1", "1_0_0"]
        result = PatternIndexService.parse_entry_indices(entries)
        assert result[0] == {"0", "1"}
        assert result[1] == {"0"}
        assert result[2] == {"0", "1"}

    def test_empty_entries(self) -> None:
        result = PatternIndexService.parse_entry_indices([])
        assert result == {}

    def test_uneven_entries(self) -> None:
        """Entries with different part counts should still parse."""
        entries = ["0_0", "1_0_extra"]
        result = PatternIndexService.parse_entry_indices(entries)
        assert 0 in result
        assert 1 in result
        assert 2 in result  # Extra position from second entry


class TestFilterEntries:
    """Tests for filtering entries based on selections."""

    def test_filter_single_position(self) -> None:
        entries = ["0_0", "0_1", "1_0", "1_1"]
        result = PatternIndexService.filter_entries(entries, {0: ["0"]})
        assert result == ["0_0", "0_1"]

    def test_filter_two_positions(self) -> None:
        entries = ["0_0", "0_1", "1_0", "1_1"]
        result = PatternIndexService.filter_entries(entries, {0: ["0"], 1: ["1"]})
        assert result == ["0_1"]

    def test_filter_all_selected(self) -> None:
        entries = ["0_0", "0_1", "1_0", "1_1"]
        result = PatternIndexService.filter_entries(entries, {0: ["0", "1"], 1: ["0", "1"]})
        assert result == entries

    def test_filter_empty_selection_excludes_all(self) -> None:
        entries = ["0_0", "0_1"]
        result = PatternIndexService.filter_entries(entries, {0: []})
        assert result == []

    def test_filter_no_selections(self) -> None:
        entries = ["0_0", "0_1"]
        result = PatternIndexService.filter_entries(entries, {})
        assert result == entries

    def test_filter_preserves_order(self) -> None:
        entries = ["2_1", "0_0", "1_0"]
        result = PatternIndexService.filter_entries(entries, {0: ["0", "2"]})
        assert result == ["2_1", "0_0"]


class TestFormatEntryDisplay:
    """Tests for formatting entries for display."""

    def test_two_positions(self) -> None:
        result = PatternIndexService.format_entry_display("0_1", ["l", "cntrl"])
        assert result == "l{0}_cntrl{1}"

    def test_single_position(self) -> None:
        result = PatternIndexService.format_entry_display("2", ["cpu"])
        assert result == "cpu{2}"

    def test_more_parts_than_positions(self) -> None:
        result = PatternIndexService.format_entry_display("0_1_2", ["l", "cntrl"])
        assert result == "l{0}_cntrl{1}_2"

    def test_more_positions_than_parts(self) -> None:
        result = PatternIndexService.format_entry_display("0", ["l", "cntrl"])
        assert result == "l{0}"

    def test_empty_entry(self) -> None:
        result = PatternIndexService.format_entry_display("", [])
        assert result == ""
