"""
Tests for the sentinel resolver — resolves -1 values via inheritance.

Covers:
  - Typography inheritance chain (y2label→ylabel, yticks→ticks, legend3→legend)
  - Legend spacing inheritance (secondary/boxed inherit from primary)
  - Axis inheritance (y2 inherits from y)
  - Immutability (input not modified)
  - Edge cases (empty legends, no y2 axis)
"""

from src.core.visualization.axis_spec import AxesSpec, AxisSpec
from src.core.visualization.figure_spec import FigureSpec
from src.core.visualization.legend_spec import LegendSpacingSpec, LegendSpec
from src.core.visualization.resolvers import (
    _resolve_float,
    _resolve_int,
    resolve_spec,
)
from src.core.visualization.typography_spec import TypographySpec


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
        spec = FigureSpec(
            typography=TypographySpec(
                font_size_ylabel=12,
                font_size_y2label=-1,
            )
        )
        resolved = resolve_spec(spec)
        assert resolved.typography.font_size_y2label == 12

    def test_y2label_explicit(self) -> None:
        """Explicit font_size_y2label should not be overridden."""
        spec = FigureSpec(
            typography=TypographySpec(
                font_size_ylabel=12,
                font_size_y2label=14,
            )
        )
        resolved = resolve_spec(spec)
        assert resolved.typography.font_size_y2label == 14

    def test_yticks_inherits_ticks(self) -> None:
        spec = FigureSpec(
            typography=TypographySpec(
                font_size_ticks=8,
                font_size_yticks=8,
                font_size_y2ticks=-1,
            )
        )
        resolved = resolve_spec(spec)
        assert resolved.typography.font_size_y2ticks == 8

    def test_legend2_inherits_legend(self) -> None:
        spec = FigureSpec(
            typography=TypographySpec(
                font_size_legend=10,
                font_size_legend2=-1,
            )
        )
        resolved = resolve_spec(spec)
        assert resolved.typography.font_size_legend2 == 10

    def test_legend3_inherits_legend(self) -> None:
        spec = FigureSpec(
            typography=TypographySpec(
                font_size_legend=10,
                font_size_legend3=-1,
            )
        )
        resolved = resolve_spec(spec)
        assert resolved.typography.font_size_legend3 == 10

    def test_legend3_sub_fields_inherit_legend3(self) -> None:
        """legend3_number_fontsize and legend3_text_fontsize inherit legend3."""
        spec = FigureSpec(
            typography=TypographySpec(
                font_size_legend=10,
                font_size_legend3=-1,  # resolves to 10
                legend3_number_fontsize=-1,  # resolves to 10
                legend3_text_fontsize=-1,  # resolves to 10
            )
        )
        resolved = resolve_spec(spec)
        assert resolved.typography.font_size_legend3 == 10
        assert resolved.typography.legend3_number_fontsize == 10
        assert resolved.typography.legend3_text_fontsize == 10

    def test_legend3_sub_fields_explicit(self) -> None:
        """Explicit sub-field values override inheritance."""
        spec = FigureSpec(
            typography=TypographySpec(
                font_size_legend=10,
                font_size_legend3=12,
                legend3_number_fontsize=8,
                legend3_text_fontsize=14,
            )
        )
        resolved = resolve_spec(spec)
        assert resolved.typography.legend3_number_fontsize == 8
        assert resolved.typography.legend3_text_fontsize == 14

    def test_full_default_chain(self) -> None:
        """All default sentinels should resolve via the chain."""
        spec = FigureSpec()
        resolved = resolve_spec(spec)

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
        primary = LegendSpec(role="primary", font_size=12)
        secondary = LegendSpec(role="secondary", font_size=-1)

        spec = FigureSpec(legends=[primary, secondary])
        resolved = resolve_spec(spec)

        assert resolved.legends[1].font_size == 12

    def test_secondary_font_explicit(self) -> None:
        """Explicit secondary font_size is preserved."""
        primary = LegendSpec(role="primary", font_size=12)
        secondary = LegendSpec(role="secondary", font_size=10)

        spec = FigureSpec(legends=[primary, secondary])
        resolved = resolve_spec(spec)

        assert resolved.legends[1].font_size == 10

    def test_spacing_inheritance(self) -> None:
        """Secondary spacing sentinels (-1.0) inherit from primary."""
        primary_spacing = LegendSpacingSpec(columnspacing=2.0, borderpad=0.5)
        secondary_spacing = LegendSpacingSpec(
            columnspacing=-1.0,  # should inherit 2.0
            borderpad=1.0,  # explicit, stays 1.0
        )

        primary = LegendSpec(role="primary", spacing=primary_spacing)
        secondary = LegendSpec(role="secondary", spacing=secondary_spacing)

        spec = FigureSpec(legends=[primary, secondary])
        resolved = resolve_spec(spec)

        assert resolved.legends[1].spacing.columnspacing == 2.0
        assert resolved.legends[1].spacing.borderpad == 1.0

    def test_boxed_legend_inherits(self) -> None:
        """Boxed (legend3) number_fontsize/text_fontsize inherit font_size."""
        primary = LegendSpec(role="primary", font_size=10)
        boxed = LegendSpec(
            role="boxed",
            font_size=-1,  # inherits 10 from primary
            number_fontsize=-1,  # inherits own font_size (resolved to 10)
            text_fontsize=-1,
        )

        spec = FigureSpec(legends=[primary, boxed])
        resolved = resolve_spec(spec)

        assert resolved.legends[1].font_size == 10
        assert resolved.legends[1].number_fontsize == 10
        assert resolved.legends[1].text_fontsize == 10

    def test_title_font_inherits_own_font_size(self) -> None:
        """title_font_size=-1 inherits own font_size."""
        legend = LegendSpec(
            role="primary",
            font_size=12,
            title_font_size=-1,
        )

        spec = FigureSpec(legends=[legend])
        resolved = resolve_spec(spec)

        assert resolved.legends[0].title_font_size == 12

    def test_empty_legends(self) -> None:
        """Empty legend list should not crash resolver."""
        spec = FigureSpec(legends=[])
        resolved = resolve_spec(spec)
        assert resolved.legends == []

    def test_single_legend(self) -> None:
        """Single legend should resolve title_font_size."""
        spec = FigureSpec(legends=[LegendSpec(font_size=9, title_font_size=-1)])
        resolved = resolve_spec(spec)
        assert resolved.legends[0].title_font_size == 9

    def test_three_legends(self) -> None:
        """Three legends: secondary and boxed both inherit from primary."""
        primary = LegendSpec(role="primary", font_size=10)
        secondary = LegendSpec(role="secondary", font_size=-1)
        boxed = LegendSpec(role="boxed", font_size=-1)

        spec = FigureSpec(legends=[primary, secondary, boxed])
        resolved = resolve_spec(spec)

        assert resolved.legends[1].font_size == 10
        assert resolved.legends[2].font_size == 10


class TestAxisResolution:
    """Test axis inheritance: y2 inherits from y."""

    def test_y2_label_pad_inherits(self) -> None:
        """y2.label_pad=-1 inherits from y.label_pad."""
        spec = FigureSpec(
            axes=AxesSpec(
                y=AxisSpec(label_pad=15.0),
                y2=AxisSpec(label_pad=-1.0),
            )
        )
        resolved = resolve_spec(spec)
        assert resolved.axes.y2 is not None
        assert resolved.axes.y2.label_pad == 15.0

    def test_y2_tick_pad_inherits(self) -> None:
        """y2.tick_pad=-1 inherits from y.tick_pad."""
        spec = FigureSpec(
            axes=AxesSpec(
                y=AxisSpec(tick_pad=8.0),
                y2=AxisSpec(tick_pad=-1.0),
            )
        )
        resolved = resolve_spec(spec)
        assert resolved.axes.y2 is not None
        assert resolved.axes.y2.tick_pad == 8.0

    def test_y2_explicit_preserved(self) -> None:
        """Explicit y2 values are preserved."""
        spec = FigureSpec(
            axes=AxesSpec(
                y=AxisSpec(label_pad=15.0),
                y2=AxisSpec(label_pad=20.0),
            )
        )
        resolved = resolve_spec(spec)
        assert resolved.axes.y2 is not None
        assert resolved.axes.y2.label_pad == 20.0

    def test_no_y2_axis(self) -> None:
        """No y2 axis should not crash resolver."""
        spec = FigureSpec(axes=AxesSpec(y2=None))
        resolved = resolve_spec(spec)
        assert resolved.axes.y2 is None


class TestResolverImmutability:
    """Test that resolve_spec does not modify the input."""

    def test_input_preserved(self) -> None:
        """Original spec should be unchanged after resolution."""
        spec = FigureSpec(
            typography=TypographySpec(
                font_size_legend=10,
                font_size_legend3=-1,
            ),
            legends=[
                LegendSpec(role="primary", font_size=10),
                LegendSpec(role="secondary", font_size=-1),
            ],
        )

        # Preserve original values
        original_legend3 = spec.typography.font_size_legend3
        original_secondary_font = spec.legends[1].font_size

        resolved = resolve_spec(spec)

        # Original should be untouched
        assert spec.typography.font_size_legend3 == original_legend3
        assert spec.legends[1].font_size == original_secondary_font

        # Resolved should have concrete values
        assert resolved.typography.font_size_legend3 == 10
        assert resolved.legends[1].font_size == 10

    def test_deep_copy(self) -> None:
        """Modifying resolved spec should not affect original."""
        spec = FigureSpec()
        resolved = resolve_spec(spec)

        resolved.title = "Modified"
        resolved.dimensions.width = 99.0

        assert spec.title == ""
        assert spec.dimensions.width == 7.0
