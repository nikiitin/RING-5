"""Real numeric-pattern matching bounds and parser error propagation contracts."""

import pytest

from src.core.common.safe_regex import (
    MAX_INPUT_LENGTH,
    MAX_PATTERN_LENGTH,
    SafeRegexError,
    numeric_pattern_id,
)

_HOSTILE_PATTERN = "cpu" + r"\d+" * 50
_HOSTILE_NAME = "cpu" + "1" * 1000 + "x" + "1" * 1000


def test_numeric_capture_matching_enforces_the_real_execution_bound() -> None:
    assert len(_HOSTILE_PATTERN) < MAX_PATTERN_LENGTH
    assert len(_HOSTILE_NAME) < MAX_INPUT_LENGTH
    with pytest.raises(SafeRegexError, match="matching exceeded 50 ms"):
        numeric_pattern_id(_HOSTILE_PATTERN, _HOSTILE_NAME)


def test_derived_capture_expansion_keeps_the_original_source_length_contract() -> None:
    pattern = "cpu" + (r"\d+." * 120) + "ipc"
    name = "cpu" + "1." * 120 + "ipc"
    assert len(pattern) <= MAX_PATTERN_LENGTH
    assert numeric_pattern_id(pattern, name) == "_".join(["1"] * 120)


@pytest.mark.parametrize(
    ("pattern", "name", "expected"),
    [
        (r"system.cpu\d+.cache\d+.ipc", "system.cpu012.cache3.ipc", "012_3"),
        (r"system\.cpu\d+\.ipc", "system.cpu12.ipc", "12"),
        (r"system.cpu\d+.ipc", "system.gpu12.ipc", None),
        (r"system.cpu\d+.ipc", "system.cpu١.ipc", None),
        ("system.cpu.ipc", "system.cpu.ipc", None),
    ],
)
def test_numeric_capture_matching_preserves_valid_and_unmatched_names(
    pattern: str, name: str, expected: str | None
) -> None:
    assert numeric_pattern_id(pattern, name) == expected


def test_numeric_capture_source_and_name_bounds_still_apply() -> None:
    with pytest.raises(SafeRegexError, match="between 1 and 512"):
        numeric_pattern_id("a" * (MAX_PATTERN_LENGTH + 1), "a")
    with pytest.raises(SafeRegexError, match="Stat name exceeds"):
        numeric_pattern_id(r"cpu\d+", "a" * (MAX_INPUT_LENGTH + 1))
