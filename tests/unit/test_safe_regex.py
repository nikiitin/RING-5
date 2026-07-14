"""Tests for bounded user-supplied regular expressions."""

import pytest

from src.core.common.safe_regex import (
    MAX_INPUT_LENGTH,
    MAX_PATTERN_LENGTH,
    SafeRegexError,
    compile_bounded_regex,
    escape_perl_stat_filter,
    fullmatch_bounded_regex,
    search_bounded_regex,
)


def test_bounded_regex_matches_capture_groups() -> None:
    pattern = compile_bounded_regex(r"cpu(\d+)\.ipc")

    match = search_bounded_regex(pattern, "cpu12.ipc")

    assert match is not None
    assert match.group(1) == "12"


def test_bounded_regex_rejects_invalid_syntax() -> None:
    with pytest.raises(SafeRegexError, match="Invalid regular expression"):
        compile_bounded_regex("[unterminated")


def test_bounded_regex_rejects_long_pattern() -> None:
    with pytest.raises(SafeRegexError, match="character limit"):
        compile_bounded_regex("a" * (MAX_PATTERN_LENGTH + 1))


def test_bounded_regex_rejects_long_input() -> None:
    pattern = compile_bounded_regex("a")

    with pytest.raises(SafeRegexError, match="Regex input exceeds"):
        search_bounded_regex(pattern, "a" * (MAX_INPUT_LENGTH + 1))


def test_bounded_regex_times_out_catastrophic_backtracking() -> None:
    pattern = compile_bounded_regex(r"(a+)+$")

    with pytest.raises(SafeRegexError, match="matching exceeded"):
        search_bounded_regex(pattern, "a" * (MAX_INPUT_LENGTH - 1) + "!")


def test_bounded_fullmatch_times_out_catastrophic_backtracking() -> None:
    pattern = compile_bounded_regex(r"(a+)+$")

    with pytest.raises(SafeRegexError, match="matching exceeded"):
        fullmatch_bounded_regex(pattern, "a" * (MAX_INPUT_LENGTH - 1) + "!")


def test_perl_stat_filter_allows_only_literals_and_numeric_placeholder() -> None:
    assert escape_perl_stat_filter(r"system.cpu\d+.ipc") == r"system\.cpu\d+\.ipc"

    with pytest.raises(SafeRegexError, match="Unsupported character"):
        escape_perl_stat_filter(r"(a+)+$")
