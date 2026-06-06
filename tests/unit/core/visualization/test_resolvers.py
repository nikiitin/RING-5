"""
Tests for the sentinel resolver — resolves -1 values via inheritance.

Covers:
  - Typography inheritance chain (y2label→ylabel, yticks→ticks, legend3→legend)
  - Legend spacing inheritance (secondary/tertiary inherit from primary)
  - Axis inheritance (y2 inherits from y)
  - Immutability (input not modified)
  - Edge cases (empty legends, no y2 axis)
"""

from dataclasses import FrozenInstanceError

import pytest

from src.core.models.visualization.axis_config import AxesConfig, AxisConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.legend_config import (
    LegendConfig,
    LegendSpacingConfig,
)
from src.core.models.visualization.typography_config import TypographyConfig
from src.core.services.visualization.config_resolver import (
    _resolve_float,
    _resolve_int,
    resolve_config,
)


class TestResolveInt:
    """Test integer sentinel resolution."""

    def test_sentinel_inherits(self) -> None:
        assert _resolve_int(-1, 42) == 42

    def test_explicit_value_preserved(self) -> None:
        assert _resolve_int(10, 42) == 10

    def test_zero_is_not_sentinel(self) -> None:
        assert _resolve_int(0, 42) == 0


class TestResolveFloat:
    """Test float sentinel resolution."""

    def test_sentinel_inherits(self) -> None:
        assert _resolve_float(-1.0, 5.5) == 5.5

    def test_explicit_value_preserved(self) -> None:
        assert _resolve_float(3.0, 5.5) == 3.0

    def test_zero_is_not_sentinel(self) -> None:
        assert _resolve_float(0.0, 5.5) == 0.0


class TestTypographyResolution:
    """Test full typography inheritance chain."""

    def test_y2label_inherits_ylabel(self) -> None:
        """font_size_y2label=-1 should become font_size_ylabel."""
        spec = FigureConfig(
            typography=TypographyConfig(
                font_size_ylabel=12,
                font_size_y2label=-1,
            )
        )
        resolved = resolve_config(spec)
        assert resolved.typography.font_size_y2label == 12

    def test_y2label_explicit(self) -> None:
        """Explicit font_size_y2label should not be overridden."""
        spec = FigureConfig(
            typography=TypographyConfig(
                font_size_ylabel=12,
                font_size_y2label=14,
            )
        )
        resolved = resolve_config(spec)
        assert resolved.typography.font_size_y2label == 14

    def test_yticks_inherits_ticks(self) -> None:
        spec = FigureConfig(
            typography=TypographyConfig(
                font_size_ticks=8,
                font_size_yticks=8,
                font_size_y2ticks=-1,
            )
        )
        resolved = resolve_config(spec)
        assert resolved.typography.font_size_y2ticks == 8

    def test_legend2_inherits_legend(self) -> None:
        spec = FigureConfig(
            typography=TypographyConfig(
                font_size_legend=10,
                font_size_legend2=-1,
            )
        )
        resolved = resolve_config(spec)
        assert resolved.typography.font_size_legend2 == 10

    def test_legend3_inherits_legend(self) -> None:
        spec = FigureConfig(
            typography=TypographyConfig(
                font_size_legend=10,
                font_size_legend3=-1,
            )
        )
        resolved = resolve_config(spec)
        assert resolved.typography.font_size_legend3 == 10

    def test_legend3_sub_fields_inherit_legend3(self) -> None:
        """legend3_number_fontsize and legend3_text_fontsize inherit legend3."""
        spec = FigureConfig(
            typography=TypographyConfig(
                font_size_legend=10,
                font_size_legend3=-1,  # resolves to 10
                legend3_number_fontsize=-1,  # resolves to 10
                legend3_text_fontsize=-1,  # resolves to 10
            )
        )
        resolved = resolve_config(spec)
        assert resolved.typography.font_size_legend3 == 10
        assert resolved.typography.legend3_number_fontsize == 10
        assert resolved.typography.legend3_text_fontsize == 10

    def test_legend3_sub_fields_explicit(self) -> None:
        """Explicit sub-field values override inheritance."""
        spec = FigureConfig(
            typography=TypographyConfig(
                font_size_legend=10,
                font_size_legend3=12,
                legend3_number_fontsize=8,
                legend3_text_fontsize=14,
            )
        )
        resolved = resolve_config(spec)
        assert resolved.typography.legend3_number_fontsize == 8
        assert resolved.typography.legend3_text_fontsize == 14

    def test_full_default_chain(self) -> None:
        """All default sentinels should resolve via the chain."""
        spec = FigureConfig()
        resolved = resolve_config(spec)

        # y2label inherits ylabel (9)
        assert resolved.typography.font_size_y2label == 9
        # y2ticks inherits yticks (7)
        assert resolved.typography.font_size_y2ticks == 7
        # legend2 inherits legend (8)
        assert resolved.typography.font_size_legend2 == 8
        # legend3 inherits legend (8)
        assert resolved.typography.font_size_legend3 == 8
        # legend3 sub-fields inherit legend3 (8)
        assert resolved.typography.legend3_number_fontsize == 8
        assert resolved.typography.legend3_text_fontsize == 8


class TestLegendResolution:
    """Test legend list sentinel resolution."""

    def test_secondary_font_inherits_primary(self) -> None:
        """Secondary legend font_size=-1 inherits from primary."""
        primary = LegendConfig(role="primary", font_size=12)
        secondary = LegendConfig(role="secondary", font_size=-1)

        spec = FigureConfig(legends=[primary, secondary])
        resolved = resolve_config(spec)

        assert resolved.legends[1].font_size == 12

    def test_secondary_font_explicit(self) -> None:
        """Explicit secondary font_size is preserved."""
        primary = LegendConfig(role="primary", font_size=12)
        secondary = LegendConfig(role="secondary", font_size=10)

        spec = FigureConfig(legends=[primary, secondary])
        resolved = resolve_config(spec)

        assert resolved.legends[1].font_size == 10

    def test_spacing_inheritance(self) -> None:
        """Secondary spacing sentinels (-1.0) inherit from primary."""
        primary_spacing = LegendSpacingConfig(columnspacing=2.0, borderpad=0.5)
        secondary_spacing = LegendSpacingConfig(
            columnspacing=-1.0,  # should inherit 2.0
            borderpad=1.0,  # explicit, stays 1.0
        )

        primary = LegendConfig(role="primary", spacing=primary_spacing)
        secondary = LegendConfig(role="secondary", spacing=secondary_spacing)

        spec = FigureConfig(legends=[primary, secondary])
        resolved = resolve_config(spec)

        assert resolved.legends[1].spacing.columnspacing == 2.0
        assert resolved.legends[1].spacing.borderpad == 1.0

    def test_tertiary_legend_inherits(self) -> None:
        """Tertiary (legend3) number_fontsize/text_fontsize inherit font_size."""
        primary = LegendConfig(role="primary", font_size=10)
        tertiary = LegendConfig(
            role="tertiary",
            font_size=-1,  # inherits 10 from primary
            number_fontsize=-1,  # inherits own font_size (resolved to 10)
            text_fontsize=-1,
        )

        spec = FigureConfig(legends=[primary, tertiary])
        resolved = resolve_config(spec)

        assert resolved.legends[1].font_size == 10
        assert resolved.legends[1].number_fontsize == 10
        assert resolved.legends[1].text_fontsize == 10

    def test_title_font_inherits_own_font_size(self) -> None:
        """title_font_size=-1 inherits own font_size."""
        legend = LegendConfig(
            role="primary",
            font_size=12,
            title_font_size=-1,
        )

        spec = FigureConfig(legends=[legend])
        resolved = resolve_config(spec)

        assert resolved.legends[0].title_font_size == 12

    def test_empty_legends(self) -> None:
        """Empty legend list should not crash resolver."""
        spec = FigureConfig(legends=[])
        resolved = resolve_config(spec)
        assert resolved.legends == []

    def test_single_legend(self) -> None:
        """Single legend should resolve title_font_size."""
        spec = FigureConfig(legends=[LegendConfig(font_size=9, title_font_size=-1)])
        resolved = resolve_config(spec)
        assert resolved.legends[0].title_font_size == 9

    def test_three_legends(self) -> None:
        """Three legends: secondary and tertiary both inherit from primary."""
        primary = LegendConfig(role="primary", font_size=10)
        secondary = LegendConfig(role="secondary", font_size=-1)
        tertiary = LegendConfig(role="tertiary", font_size=-1)

        spec = FigureConfig(legends=[primary, secondary, tertiary])
        resolved = resolve_config(spec)

        assert resolved.legends[1].font_size == 10
        assert resolved.legends[2].font_size == 10


class TestAxisResolution:
    """Test axis inheritance: y2 inherits from y."""

    def test_y2_label_pad_inherits(self) -> None:
        """y2.label_pad=-1 inherits from y.label_pad."""
        spec = FigureConfig(
            axes=AxesConfig(
                y=AxisConfig(label_pad=15.0),
                y2=AxisConfig(label_pad=-1.0),
            )
        )
        resolved = resolve_config(spec)
        assert resolved.axes.y2 is not None
        assert resolved.axes.y2.label_pad == 15.0

    def test_y2_tick_pad_inherits(self) -> None:
        """y2.tick_pad=-1 inherits from y.tick_pad."""
        spec = FigureConfig(
            axes=AxesConfig(
                y=AxisConfig(tick_pad=8.0),
                y2=AxisConfig(tick_pad=-1.0),
            )
        )
        resolved = resolve_config(spec)
        assert resolved.axes.y2 is not None
        assert resolved.axes.y2.tick_pad == 8.0

    def test_y2_explicit_preserved(self) -> None:
        """Explicit y2 values are preserved."""
        spec = FigureConfig(
            axes=AxesConfig(
                y=AxisConfig(label_pad=15.0),
                y2=AxisConfig(label_pad=20.0),
            )
        )
        resolved = resolve_config(spec)
        assert resolved.axes.y2 is not None
        assert resolved.axes.y2.label_pad == 20.0

    def test_no_y2_axis(self) -> None:
        """No y2 axis should not crash resolver."""
        spec = FigureConfig(axes=AxesConfig(y2=None))
        resolved = resolve_config(spec)
        assert resolved.axes.y2 is None


class TestResolverImmutability:
    """Test that resolve_config does not modify the input."""

    def test_input_preserved(self) -> None:
        """Original spec should be unchanged after resolution."""
        spec = FigureConfig(
            typography=TypographyConfig(
                font_size_legend=10,
                font_size_legend3=-1,
            ),
            legends=[
                LegendConfig(role="primary", font_size=10),
                LegendConfig(role="secondary", font_size=-1),
            ],
        )

        # Preserve original values
        original_legend3 = spec.typography.font_size_legend3
        original_secondary_font = spec.legends[1].font_size

        resolved = resolve_config(spec)

        # Original should be untouched
        assert spec.typography.font_size_legend3 == original_legend3
        assert spec.legends[1].font_size == original_secondary_font

        # Resolved should have concrete values
        assert resolved.typography.font_size_legend3 == 10
        assert resolved.legends[1].font_size == 10

    def test_deep_copy(self) -> None:
        """resolve_config returns an independent, immutable copy of the input."""
        spec = FigureConfig()
        resolved = resolve_config(spec)

        # Distinct objects all the way down — not aliased to the input.
        assert resolved is not spec
        assert resolved.dimensions is not spec.dimensions
        assert resolved.typography is not spec.typography

        # Both input and output are frozen: the resolver cannot have mutated
        # the caller's spec, and callers cannot mutate the resolved result.
        with pytest.raises(FrozenInstanceError):
            resolved.title = "Modified"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            resolved.dimensions.width = 99.0  # type: ignore[misc]
