"""Large-cardinality data cannot create unbounded Streamlit option payloads."""

from src.core.common.security_limits import MAX_FILTER_OPTIONS, MAX_FILTER_VALUE_LENGTH
from src.web.components.common.bounded_options import (
    bounded_unique_strings,
    stable_widget_suffix,
)


def test_unique_options_are_capped() -> None:
    # [test->req~ring5.quality.input-security~1]
    options, truncated = bounded_unique_strings(range(MAX_FILTER_OPTIONS + 10))

    assert len(options) == MAX_FILTER_OPTIONS
    assert truncated


def test_oversized_values_are_omitted() -> None:
    # [test->req~ring5.quality.input-security~1]
    options, truncated = bounded_unique_strings(["ok", "x" * (MAX_FILTER_VALUE_LENGTH + 1)])

    assert options == ["ok"]
    assert truncated


def test_widget_suffix_includes_index_and_full_digest() -> None:
    first = stable_widget_suffix(0, "E1n5ZE54Zwaa")
    second = stable_widget_suffix(1, "L0EUWWqmRjFb")

    assert first != second
    assert first.startswith("0_")
    assert len(first.split("_", 1)[1]) == 64
