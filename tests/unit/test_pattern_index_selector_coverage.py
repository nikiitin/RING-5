"""Tests for PatternIndexSelector — pure logic methods (no Streamlit)."""

from src.web.pages.ui.components.pattern_index_selector import PatternIndexSelector


class TestIsPatternVariable:
    """Test is_pattern_variable static method."""

    def test_with_digit_pattern(self) -> None:
        assert PatternIndexSelector.is_pattern_variable(r"system.cpu\d+.ipc") is True

    def test_without_digit_pattern(self) -> None:
        assert PatternIndexSelector.is_pattern_variable("system.cpu0.ipc") is False

    def test_multiple_patterns(self) -> None:
        assert PatternIndexSelector.is_pattern_variable(r"system.ruby.l\d+_cntrl\d+.stat") is True

    def test_empty_string(self) -> None:
        assert PatternIndexSelector.is_pattern_variable("") is False


class TestExtractIndexPositions:
    """Test extract_index_positions static method."""

    def test_single_position(self) -> None:
        result = PatternIndexSelector.extract_index_positions(r"system.cpu\d+.ipc")
        assert result == ["cpu"]

    def test_two_positions(self) -> None:
        result = PatternIndexSelector.extract_index_positions(r"system.ruby.l\d+_cntrl\d+.stat")
        assert result == ["l", "cntrl"]

    def test_no_positions(self) -> None:
        result = PatternIndexSelector.extract_index_positions("system.cpu0.ipc")
        assert result == []

    def test_trailing_underscore_stripped(self) -> None:
        result = PatternIndexSelector.extract_index_positions(r"system._foo\d+.stat")
        assert result == ["foo"]


class TestParseEntryIndices:
    """Test parse_entry_indices static method."""

    def test_basic_entries(self) -> None:
        entries = ["0_0", "0_1", "1_0", "1_1"]
        result = PatternIndexSelector.parse_entry_indices(entries)
        assert result[0] == {"0", "1"}
        assert result[1] == {"0", "1"}

    def test_single_index(self) -> None:
        entries = ["0", "1", "2"]
        result = PatternIndexSelector.parse_entry_indices(entries)
        assert result[0] == {"0", "1", "2"}

    def test_empty_entries(self) -> None:
        result = PatternIndexSelector.parse_entry_indices([])
        assert result == {}

    def test_asymmetric_entries(self) -> None:
        entries = ["0_0", "0_1", "2_0"]
        result = PatternIndexSelector.parse_entry_indices(entries)
        assert result[0] == {"0", "2"}
        assert result[1] == {"0", "1"}

    def test_three_positions(self) -> None:
        entries = ["0_0_0", "0_0_1", "1_0_0"]
        result = PatternIndexSelector.parse_entry_indices(entries)
        assert result[0] == {"0", "1"}
        assert result[1] == {"0"}
        assert result[2] == {"0", "1"}


class TestFilterEntries:
    """Test _filter_entries static method."""

    def test_filter_first_position(self) -> None:
        entries = ["0_0", "0_1", "1_0", "1_1"]
        sel = {0: ["0"], 1: ["0", "1"]}
        result = PatternIndexSelector._filter_entries(entries, sel)
        assert result == ["0_0", "0_1"]

    def test_filter_second_position(self) -> None:
        entries = ["0_0", "0_1", "1_0", "1_1"]
        sel = {0: ["0", "1"], 1: ["1"]}
        result = PatternIndexSelector._filter_entries(entries, sel)
        assert result == ["0_1", "1_1"]

    def test_empty_selection_excludes_all(self) -> None:
        entries = ["0_0", "0_1"]
        sel = {0: []}
        result = PatternIndexSelector._filter_entries(entries, sel)
        assert result == []

    def test_all_selected(self) -> None:
        entries = ["0_0", "0_1", "1_0", "1_1"]
        sel = {0: ["0", "1"], 1: ["0", "1"]}
        result = PatternIndexSelector._filter_entries(entries, sel)
        assert result == entries


class TestFormatEntryDisplay:
    """Test _format_entry_display static method."""

    def test_two_positions(self) -> None:
        result = PatternIndexSelector._format_entry_display("0_1", ["l", "cntrl"])
        assert result == "l{0}_cntrl{1}"

    def test_single_position(self) -> None:
        result = PatternIndexSelector._format_entry_display("3", ["cpu"])
        assert result == "cpu{3}"

    def test_more_parts_than_positions(self) -> None:
        result = PatternIndexSelector._format_entry_display("0_1_2", ["l", "cntrl"])
        assert result == "l{0}_cntrl{1}_2"

    def test_no_positions(self) -> None:
        result = PatternIndexSelector._format_entry_display("0_1", [])
        assert result == "0_1"
