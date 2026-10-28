"""
Tests for PatternIndexService — pure business logic for pattern variable operations.

Extracted from UI layer (pattern_index_selector.py) to Layer B.
"""

from src.core.models.pattern_index_service import PatternIndexService


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
        r"""Ensure partial \d does not match."""
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


def test_label_extraction_handles_long_nonpattern_names_without_regex_matching():
    assert PatternIndexService.extract_index_positions("A" + "a" * 3000) == []
    assert PatternIndexService.extract_index_positions("_" * 2000 + "a" * 2000) == []
