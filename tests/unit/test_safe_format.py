"""Security bounds for user-controlled numeric formats."""

from src.core.common.safe_format import (
    normalize_numeric_format,
    plotly_numeric_template,
    safe_format_number,
)


def test_normal_formats_are_preserved() -> None:
    assert safe_format_number(12.345, ".2f") == "12.35"
    assert plotly_numeric_template(".1%") == "%{y:.1%}"


def test_huge_width_falls_back_without_allocating() -> None:
    assert normalize_numeric_format("1000000000f") == ".2f"
    assert safe_format_number(12.0, "1000000000f") == "12.00"


def test_huge_plotly_template_falls_back() -> None:
    assert plotly_numeric_template("%{y:1000000000f}") == "%{y:.2f}"


def test_arbitrary_template_is_not_forwarded() -> None:
    assert plotly_numeric_template("%{customdata}") == "%{y:.2f}"
