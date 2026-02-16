"""
Tests for FigureSpec — construction, serialization, round-trip.

Covers:
  - Default construction with sensible defaults
  - Custom construction with all sub-specs
  - to_dict() → from_dict() round-trip fidelity
  - Sub-spec isolation (modifying one spec doesn't affect another)
"""

import pytest

from src.core.visualization.figure_spec import (
    DimensionsSpec,
    FigureSpec,
    MarginsSpec,
    SeparatorSpec,
)
from src.core.visualization.typography_spec import TypographySpec
from src.core.visualization.axis_spec import AxesSpec, AxisSpec
from src.core.visualization.legend_spec import LegendSpec, LegendSpacingSpec
from src.core.visualization.annotation_spec import AnnotationSpec


class TestFigureSpecConstruction:
    """Test FigureSpec default and custom construction."""

    def test_default_construction(self) -> None:
        """Default FigureSpec should have sensible defaults."""
        spec = FigureSpec()

        assert spec.title == ""
        assert spec.paper_bgcolor == "white"
        assert spec.plot_bgcolor == "white"
        assert spec.font_family == "serif"
        assert spec.latex_extra_preamble == ""
        assert spec.metadata == {}
        assert spec.legends == []
        assert spec.traces == []
        assert spec.annotations == []

    def test_default_dimensions(self) -> None:
        """Default dimensions should be publication-quality."""
        spec = FigureSpec()
        dims = spec.dimensions

        assert dims.width == 7.0
        assert dims.height == 4.0
        assert dims.dpi == 300
        assert dims.bar_width_scale == 1.0
        assert dims.bargap == 0.15
        assert dims.bargroupgap == 0.1

    def test_default_margins(self) -> None:
        """Default margins should be reasonable."""
        spec = FigureSpec()
        m = spec.dimensions.margins

        assert m.top == 40.0
        assert m.bottom == 80.0
        assert m.left == 60.0
        assert m.right == 30.0
        assert m.pad == 0.0

    def test_default_typography(self) -> None:
        """Default typography should have base sizes set."""
        spec = FigureSpec()
        typo = spec.typography

        assert isinstance(typo, TypographySpec)
        assert typo.font_size_base == 10
        assert typo.font_size_title == 10
        assert typo.font_size_xlabel == 9
        assert typo.font_size_ylabel == 9
        assert typo.font_size_ticks == 7
        assert typo.font_size_legend == 8

    def test_default_axes(self) -> None:
        """Default axes should exist with default AxisSpec."""
        spec = FigureSpec()
        axes = spec.axes

        assert isinstance(axes, AxesSpec)
        assert isinstance(axes.x, AxisSpec)
        assert isinstance(axes.y, AxisSpec)
        assert axes.y2 is None

    def test_custom_construction(self) -> None:
        """FigureSpec with explicit sub-specs."""
        dims = DimensionsSpec(width=3.5, height=2.5, dpi=600)
        typo = TypographySpec(font_size_base=8, font_size_title=12)
        legend = LegendSpec(role="primary", font_size=10, bold=True)

        spec = FigureSpec(
            dimensions=dims,
            typography=typo,
            legends=[legend],
            title="Test Plot",
            paper_bgcolor="#F0F0F0",
        )

        assert spec.dimensions.width == 3.5
        assert spec.dimensions.dpi == 600
        assert spec.typography.font_size_title == 12
        assert len(spec.legends) == 1
        assert spec.legends[0].bold is True
        assert spec.title == "Test Plot"
        assert spec.paper_bgcolor == "#F0F0F0"

    def test_default_separator(self) -> None:
        """Default separator should be disabled."""
        spec = FigureSpec()
        assert spec.separator.enabled is False
        assert spec.separator.style == "dashed"
        assert spec.separator.color == "gray"


class TestFigureSpecSerialization:
    """Test to_dict/from_dict round-trip fidelity."""

    def test_default_round_trip(self) -> None:
        """Default FigureSpec should round-trip through dict."""
        spec = FigureSpec()
        data = spec.to_dict()
        restored = FigureSpec.from_dict(data)

        assert restored.title == spec.title
        assert restored.dimensions.width == spec.dimensions.width
        assert restored.dimensions.height == spec.dimensions.height
        assert restored.typography.font_size_base == spec.typography.font_size_base

    def test_custom_round_trip(self) -> None:
        """Custom FigureSpec should preserve all values through round-trip."""
        legend = LegendSpec(
            role="primary",
            font_size=12,
            bold=True,
            ncol=3,
            orientation="horizontal",
            spacing=LegendSpacingSpec(columnspacing=1.5, borderpad=0.8),
        )
        annotation = AnnotationSpec(
            text="Threshold",
            x=0.5,
            y=100.0,
            xref="paper",
            yref="data",
            font_size=14,
        )
        spec = FigureSpec(
            dimensions=DimensionsSpec(width=3.5, height=2.5, dpi=600),
            typography=TypographySpec(font_size_base=8),
            axes=AxesSpec(
                x=AxisSpec(label="Benchmark", tick_angle=45.0),
                y=AxisSpec(label="Speedup", dtick=0.5),
                y2=AxisSpec(label="IPC"),
            ),
            legends=[legend],
            annotations=[annotation],
            separator=SeparatorSpec(enabled=True, style="dotted", color="blue"),
            title="Performance Results",
            paper_bgcolor="#FAFAFA",
            font_family="sans-serif",
        )

        data = spec.to_dict()
        restored = FigureSpec.from_dict(data)

        assert restored.dimensions.width == 3.5
        assert restored.dimensions.dpi == 600
        assert restored.typography.font_size_base == 8
        assert restored.axes.x.label == "Benchmark"
        assert restored.axes.x.tick_angle == 45.0
        assert restored.axes.y.label == "Speedup"
        assert restored.axes.y.dtick == 0.5
        assert restored.axes.y2 is not None
        assert restored.axes.y2.label == "IPC"
        assert len(restored.legends) == 1
        assert restored.legends[0].font_size == 12
        assert restored.legends[0].bold is True
        assert restored.legends[0].spacing.columnspacing == 1.5
        assert len(restored.annotations) == 1
        assert restored.annotations[0].text == "Threshold"
        assert restored.separator.enabled is True
        assert restored.separator.style == "dotted"
        assert restored.title == "Performance Results"

    def test_to_dict_is_plain_dict(self) -> None:
        """to_dict() should produce only plain Python types."""
        spec = FigureSpec(
            legends=[LegendSpec(role="primary")],
            annotations=[AnnotationSpec(text="test")],
        )
        data = spec.to_dict()

        assert isinstance(data, dict)
        assert isinstance(data["dimensions"], dict)
        assert isinstance(data["typography"], dict)
        assert isinstance(data["legends"], list)
        if data["legends"]:
            assert isinstance(data["legends"][0], dict)


class TestSubSpecIsolation:
    """Test that sub-specs are independent instances."""

    def test_margins_isolation(self) -> None:
        """Two FigureSpecs should have independent margins."""
        spec1 = FigureSpec()
        spec2 = FigureSpec()

        spec1.dimensions.margins.top = 100.0
        assert spec2.dimensions.margins.top == 40.0

    def test_axes_isolation(self) -> None:
        """Two FigureSpecs should have independent axes."""
        spec1 = FigureSpec()
        spec2 = FigureSpec()

        spec1.axes.x.label = "Modified"
        assert spec2.axes.x.label == ""

    def test_legend_list_isolation(self) -> None:
        """Legend lists should be independent."""
        spec1 = FigureSpec(legends=[LegendSpec()])
        spec2 = FigureSpec()

        assert len(spec1.legends) == 1
        assert len(spec2.legends) == 0


class TestDimensionsSpec:
    """Test DimensionsSpec independently."""

    def test_default_values(self) -> None:
        dims = DimensionsSpec()
        assert dims.width == 7.0
        assert dims.height == 4.0
        assert dims.dpi == 300

    def test_custom_values(self) -> None:
        dims = DimensionsSpec(width=3.5, height=2.5, dpi=600)
        assert dims.width == 3.5
        assert dims.height == 2.5
        assert dims.dpi == 600


class TestMarginsSpec:
    """Test MarginsSpec independently."""

    def test_to_dict(self) -> None:
        m = MarginsSpec(top=10, bottom=20, left=30, right=40, pad=5)
        d = m.to_dict()

        assert d == {"top": 10, "bottom": 20, "left": 30, "right": 40, "pad": 5}
