"""Tests for publication quality validator (Step 36)."""

from __future__ import annotations

import dataclasses

from src.core.visualization.figure_spec import DimensionsSpec, FigureSpec
from src.core.visualization.publication_validator import (
    VENUE_REQUIREMENTS,
    validate_for_publication,
)
from src.core.visualization.typography_spec import TypographySpec


def _spec_with(
    tick_font: int = 10,
    label_font: int = 10,
    legend_font: int = 10,
    dpi: int = 300,
    width: float = 800.0,
    height: float = 500.0,
) -> FigureSpec:
    """Create a FigureSpec with specified values."""
    return dataclasses.replace(
        FigureSpec(),
        typography=TypographySpec(
            font_size_ticks=tick_font,
            font_size_xlabel=label_font,
            font_size_legend=legend_font,
        ),
        dimensions=DimensionsSpec(width=width, height=height, dpi=dpi),
    )


class TestFontSizeWarnings:
    """Verify warnings for undersized fonts."""

    def test_small_tick_font_warns(self) -> None:
        spec = _spec_with(tick_font=5)
        warnings = validate_for_publication(spec, "isca")
        assert any("Tick font size" in w for w in warnings)

    def test_acceptable_tick_font_no_warn(self) -> None:
        spec = _spec_with(tick_font=8)
        warnings = validate_for_publication(spec, "isca")
        assert not any("Tick font size" in w for w in warnings)

    def test_small_label_font_warns(self) -> None:
        spec = _spec_with(label_font=4)
        warnings = validate_for_publication(spec, "nature")
        assert any("Axis label font size" in w for w in warnings)

    def test_small_legend_font_warns(self) -> None:
        spec = _spec_with(legend_font=3)
        warnings = validate_for_publication(spec, "micro")
        assert any("Legend font size" in w for w in warnings)


class TestDpiWarnings:
    """Verify warnings for low DPI."""

    def test_low_dpi_warns(self) -> None:
        spec = _spec_with(dpi=150)
        warnings = validate_for_publication(spec, "isca")
        assert any("DPI" in w for w in warnings)

    def test_adequate_dpi_no_warn(self) -> None:
        spec = _spec_with(dpi=300)
        warnings = validate_for_publication(spec, "isca")
        assert not any("DPI" in w for w in warnings)

    def test_nature_requires_600_dpi(self) -> None:
        spec = _spec_with(dpi=300)
        warnings = validate_for_publication(spec, "nature")
        assert any("DPI" in w for w in warnings)

    def test_nature_600_dpi_ok(self) -> None:
        spec = _spec_with(dpi=600)
        warnings = validate_for_publication(spec, "nature")
        assert not any("DPI" in w for w in warnings)


class TestDimensionWarnings:
    """Verify warnings for oversized figures."""

    def test_oversized_width_warns(self) -> None:
        # 4 inches wide at 300 DPI = 1200 px, exceeds 3.5 in
        spec = _spec_with(dpi=300, width=1200)
        warnings = validate_for_publication(spec, "isca")
        assert any("width" in w for w in warnings)

    def test_oversized_height_warns(self) -> None:
        # 6 inches tall at 300 DPI = 1800 px, exceeds 5.0 in
        spec = _spec_with(dpi=300, height=1800)
        warnings = validate_for_publication(spec, "isca")
        assert any("height" in w for w in warnings)

    def test_within_limits_no_warn(self) -> None:
        # 3 inches wide at 300 DPI = 900 px
        spec = _spec_with(dpi=300, width=900, height=1200)
        warnings = validate_for_publication(spec, "isca")
        assert not any("width" in w for w in warnings)
        assert not any("height" in w for w in warnings)


class TestUnknownVenue:
    """Unknown venue returns a warning."""

    def test_unknown_venue_warns(self) -> None:
        spec = _spec_with()
        warnings = validate_for_publication(spec, "nonexistent")
        assert len(warnings) == 1
        assert "Unknown venue" in warnings[0]


class TestAllVenuesCovered:
    """Verify all expected venues are in VENUE_REQUIREMENTS."""

    def test_key_venues_present(self) -> None:
        expected = {"isca", "micro", "asplos", "hpca", "nature", "science", "poster", "slides"}
        assert expected <= set(VENUE_REQUIREMENTS.keys())

    def test_all_venues_return_clean_for_good_spec(self) -> None:
        """A well-configured spec passes all venue checks."""
        good_spec = _spec_with(tick_font=20, label_font=20, legend_font=20, dpi=600)
        for venue in VENUE_REQUIREMENTS:
            warnings = validate_for_publication(good_spec, venue)
            # Only dimension warnings might trigger since dpi=600 with px dims
            font_warns = [w for w in warnings if "font" in w.lower() or "DPI" in w]
            assert len(font_warns) == 0, f"Unexpected warning for {venue}: {font_warns}"
