"""Tests for pivot column-pattern detection."""

from src.web.components.shapers.pivot_config import detect_common_pattern


def test_detect_common_pattern_escapes_literal_segments() -> None:
    pattern, template = detect_common_pattern(["cpu0.ipc", "cpu1.ipc", "cpu12.ipc"])

    assert pattern == r"cpu(\d+)\.ipc"
    assert template == "cpu{}.ipc"


def test_detect_common_pattern_supports_multiple_numeric_fields() -> None:
    pattern, template = detect_common_pattern(["l0_cntrl1", "l2_cntrl14"])

    assert pattern == r"l(\d+)_cntrl(\d+)"
    assert template == "l{}_cntrl{}"


def test_detect_common_pattern_rejects_different_structures() -> None:
    assert detect_common_pattern(["cpu0.ipc", "gpu1.ipc"]) == ("", "")


def test_detect_common_pattern_requires_numeric_fields() -> None:
    assert detect_common_pattern(["simTicks", "hostSeconds"]) == ("", "")


def test_detect_common_pattern_handles_empty_input() -> None:
    assert detect_common_pattern([]) == ("", "")
