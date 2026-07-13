"""
Tests for FigureConfig — construction, serialization, round-trip.

Covers:
  - Default construction with sensible defaults
  - Custom construction with all sub-specs
  - to_dict() → from_dict() round-trip fidelity
  - Sub-spec isolation (modifying one spec doesn't affect another)
"""

from dataclasses import FrozenInstanceError

import pytest

from src.core.models.visualization.annotation_config import (
    AnnotationConfig,
    ReferenceLineConfig,
)
from src.core.models.visualization.axis_config import AxesConfig, AxisConfig
from src.core.models.visualization.data_label_config import DataLabelConfig
from src.core.models.visualization.figure_config import (
    DimensionConfig,
    FigureConfig,
    MarginsConfig,
)
from src.core.models.visualization.legend_config import (
    LegendConfig,
    LegendSpacingConfig,
)
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.models.visualization.typography_config import TypographyConfig


class TestFigureSpecConstruction:
    """Test FigureConfig default and custom construction."""

    def test_default_construction(self) -> None:
        """Default FigureConfig should have sensible defaults."""
        spec = FigureConfig()

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
        spec = FigureConfig()
        dims = spec.dimensions

        assert dims.width == 7.0
        assert dims.height == 4.0
        assert dims.dpi == 300
        assert dims.bar_width_scale == 1.0
        assert dims.bargap == 0.15
        assert dims.bargroupgap == 0.1

    def test_default_margins(self) -> None:
        """Default margins should be reasonable."""
        spec = FigureConfig()
        m = spec.dimensions.margins

        assert m.top == 40.0
        assert m.bottom == 80.0
        assert m.left == 60.0
        assert m.right == 30.0
        assert m.pad == 0.0

    def test_default_typography(self) -> None:
        """Default typography should have base sizes set."""
        spec = FigureConfig()
        typo = spec.typography

        assert isinstance(typo, TypographyConfig)
        assert typo.font_size_title == 10
        assert typo.font_size_xlabel == 9
        assert typo.font_size_ylabel == 9
        assert typo.font_size_ticks == 7
        assert typo.font_size_legend == 8

    def test_default_axes(self) -> None:
        """Default axes should exist with default AxisConfig."""
        spec = FigureConfig()
        axes = spec.axes

        assert isinstance(axes, AxesConfig)
        assert isinstance(axes.x, AxisConfig)
        assert isinstance(axes.y, AxisConfig)
        assert axes.y2 is None

    def test_custom_construction(self) -> None:
        """FigureConfig with explicit sub-specs."""
        dims = DimensionConfig(width=3.5, height=2.5, dpi=600)
        typo = TypographyConfig(font_size_title=12)
        legend = LegendConfig(role="primary", font_size=10, bold=True)

        spec = FigureConfig(
            dimensions=dims,
            typography=typo,
            legends=[legend],
            title="Test Plot",
            paper_bgcolor="#F0F0F0",
        )

        assert spec.dimensions.width == 3.5
        assert spec.dimensions.dpi == 600
        assert spec.typography is not None
        assert spec.typography.font_size_title == 12
        assert len(spec.legends) == 1
        assert spec.legends[0].bold is True
        assert spec.title == "Test Plot"
        assert spec.paper_bgcolor == "#F0F0F0"


class TestFigureSpecSerialization:
    """Test to_dict/from_dict round-trip fidelity."""

    def test_default_round_trip(self) -> None:
        """Default FigureConfig should round-trip through dict."""
        spec = FigureConfig()
        data = spec.to_dict()
        restored = FigureConfig.from_dict(data)

        assert restored.title == spec.title
        assert restored.dimensions.width == spec.dimensions.width
        assert restored.dimensions.height == spec.dimensions.height
        assert restored.typography is not None
        assert spec.typography is not None
        assert restored.typography.font_size_title == spec.typography.font_size_title

    def test_custom_round_trip(self) -> None:
        """Custom FigureConfig should preserve all values through round-trip."""
        legend = LegendConfig(
            role="primary",
            font_size=12,
            bold=True,
            ncol=3,
            orientation="horizontal",
            spacing=LegendSpacingConfig(columnspacing=1.5, borderpad=0.8),
        )
        annotation = AnnotationConfig(
            text="Threshold",
            x=0.5,
            y=100.0,
            xref="paper",
            yref="data",
            font_size=14,
        )
        spec = FigureConfig(
            dimensions=DimensionConfig(width=3.5, height=2.5, dpi=600),
            typography=TypographyConfig(font_size_title=8),
            axes=AxesConfig(
                x=AxisConfig(label="Benchmark", tick_angle=45.0),
                y=AxisConfig(label="Speedup", dtick=0.5),
                y2=AxisConfig(label="IPC"),
            ),
            legends=[legend],
            annotations=[annotation],
            title="Performance Results",
            paper_bgcolor="#FAFAFA",
            font_family="sans-serif",
        )

        data = spec.to_dict()
        restored = FigureConfig.from_dict(data)

        assert restored.dimensions.width == 3.5
        assert restored.dimensions.dpi == 600
        assert restored.typography is not None
        assert restored.typography.font_size_title == 8
        assert restored.axes is not None
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
        assert restored.title == "Performance Results"

    def test_to_dict_is_plain_dict(self) -> None:
        """to_dict() should produce only plain Python types."""
        spec = FigureConfig(
            legends=[LegendConfig(role="primary")],
            annotations=[AnnotationConfig(text="test")],
        )
        data = spec.to_dict()

        assert isinstance(data, dict)
        assert isinstance(data["dimensions"], dict)
        assert isinstance(data["typography"], dict)
        assert isinstance(data["legends"], list)
        if data["legends"]:
            assert isinstance(data["legends"][0], dict)


class TestSubSpecIsolation:
    """Test that sub-specs are independent instances.

    The FigureConfig tree is frozen, so values cannot bleed across specs by
    mutation; isolation is guaranteed by each spec getting its own (distinct)
    default-factory instances.
    """

    def test_margins_isolation(self) -> None:
        """Two FigureSpecs should have independent (distinct) margins instances."""
        spec1 = FigureConfig()
        spec2 = FigureConfig()

        assert spec1.dimensions.margins is not spec2.dimensions.margins
        # Frozen: a margin cannot be mutated to bleed into the other spec.
        with pytest.raises(FrozenInstanceError):
            spec1.dimensions.margins.top = 100.0  # type: ignore[misc]

    def test_axes_isolation(self) -> None:
        """Two FigureSpecs should have independent (distinct) axes instances."""
        spec1 = FigureConfig()
        spec2 = FigureConfig()

        assert spec1.axes is not None
        assert spec2.axes is not None
        assert spec1.axes is not spec2.axes
        assert spec1.axes.x is not spec2.axes.x
        # Frozen: axis fields cannot be mutated post-construction.
        with pytest.raises(FrozenInstanceError):
            spec1.axes.x.label = "Modified"  # type: ignore[misc]

    def test_legend_list_isolation(self) -> None:
        """Legend lists should be independent."""
        spec1 = FigureConfig(legends=[LegendConfig()])
        spec2 = FigureConfig()

        assert len(spec1.legends) == 1
        assert len(spec2.legends) == 0


class TestDimensionsSpec:
    """Test DimensionConfig independently."""

    def test_default_values(self) -> None:
        dims = DimensionConfig()
        assert dims.width == 7.0
        assert dims.height == 4.0
        assert dims.dpi == 300

    def test_custom_values(self) -> None:
        dims = DimensionConfig(width=3.5, height=2.5, dpi=600)
        assert dims.width == 3.5
        assert dims.height == 2.5
        assert dims.dpi == 600


class TestMarginsSpec:
    """Test MarginsConfig independently."""

    def test_to_dict(self) -> None:
        m = MarginsConfig(top=10, bottom=20, left=30, right=40, pad=5)
        d = m.to_dict()

        assert d == {"top": 10, "bottom": 20, "left": 30, "right": 40, "pad": 5}


# ────────────────────────────────────────────────────────────────────
# Step 6 — scalar fields, color palette, hatching, reference lines
# ────────────────────────────────────────────────────────────────────


class TestFigureSpecColorPalette:
    """Test color_palette default and custom values."""

    def test_default_is_wong_palette(self) -> None:
        """Default color palette is the 8-color Wong colorblind-safe set."""
        spec = FigureConfig()
        assert len(spec.color_palette) == 8
        assert spec.color_palette[0] == "#000000"
        assert spec.color_palette[1] == "#E69F00"
        assert spec.color_palette[-1] == "#CC79A7"

    def test_custom_palette(self) -> None:
        spec = FigureConfig(color_palette=["#FF0000", "#00FF00"])
        assert spec.color_palette == ["#FF0000", "#00FF00"]

    def test_palette_isolation(self) -> None:
        """Two specs should have independent palette lists."""
        spec1 = FigureConfig()
        spec2 = FigureConfig()
        spec1.color_palette.append("#AABBCC")
        assert "#AABBCC" not in spec2.color_palette

    def test_palette_round_trip(self) -> None:
        custom = ["#AAA", "#BBB", "#CCC"]
        spec = FigureConfig(color_palette=custom)
        restored = FigureConfig.from_dict(spec.to_dict())
        assert restored.color_palette == custom

    def test_palette_default_round_trip(self) -> None:
        """Default palette survives serialization."""
        spec = FigureConfig()
        restored = FigureConfig.from_dict(spec.to_dict())
        assert restored.color_palette == spec.color_palette


class TestFigureSpecHatchingSequence:
    """Test hatching_sequence default and custom values."""

    def test_default_hatching_sequence(self) -> None:
        spec = FigureConfig()
        assert len(spec.hatching_sequence) == 8
        assert spec.hatching_sequence[0] == "/"
        assert spec.hatching_sequence[-1] == "O"

    def test_custom_hatching(self) -> None:
        spec = FigureConfig(hatching_sequence=["x", "o"])
        assert spec.hatching_sequence == ["x", "o"]

    def test_hatching_round_trip(self) -> None:
        custom = ["+", "-"]
        spec = FigureConfig(hatching_sequence=custom)
        restored = FigureConfig.from_dict(spec.to_dict())
        assert restored.hatching_sequence == custom


class TestFigureSpecReferenceLines:
    """Test reference_lines list field."""

    def test_default_empty(self) -> None:
        spec = FigureConfig()
        assert spec.reference_lines == []

    def test_custom_reference_line(self) -> None:
        rl = ReferenceLineConfig(
            enabled=True,
            axis="y",
            value=1.0,
            color="blue",
            width=2.0,
            style="solid",
            label="Baseline",
        )
        spec = FigureConfig(reference_lines=[rl])
        assert len(spec.reference_lines) == 1
        assert spec.reference_lines[0].value == 1.0
        assert spec.reference_lines[0].label == "Baseline"

    def test_reference_lines_round_trip(self) -> None:
        rl = ReferenceLineConfig(
            enabled=True,
            axis="x",
            value=50.0,
            color="green",
            width=1.0,
            style="dash",
            label="Mean",
        )
        spec = FigureConfig(reference_lines=[rl])
        data = spec.to_dict()
        restored = FigureConfig.from_dict(data)

        assert len(restored.reference_lines) == 1
        assert restored.reference_lines[0].enabled is True
        assert restored.reference_lines[0].axis == "x"
        assert restored.reference_lines[0].value == 50.0
        assert restored.reference_lines[0].color == "green"
        assert restored.reference_lines[0].label == "Mean"

    def test_multiple_reference_lines(self) -> None:
        lines = [
            ReferenceLineConfig(enabled=True, axis="y", value=1.0, label="Baseline"),
            ReferenceLineConfig(enabled=True, axis="y", value=2.0, label="Target"),
        ]
        spec = FigureConfig(reference_lines=lines)
        assert len(spec.reference_lines) == 2

    def test_reference_lines_isolation(self) -> None:
        spec1 = FigureConfig()
        spec2 = FigureConfig()
        spec1.reference_lines.append(ReferenceLineConfig(enabled=True))
        assert len(spec2.reference_lines) == 0


class TestFigureSpecScalarFields:
    """Test hovermode, enable_stripes, show_error_bars defaults and overrides."""

    def test_default_hovermode(self) -> None:
        spec = FigureConfig()
        assert spec.hovermode == "x unified"

    def test_custom_hovermode(self) -> None:
        spec = FigureConfig(hovermode="closest")
        assert spec.hovermode == "closest"

    def test_hovermode_round_trip(self) -> None:
        spec = FigureConfig(hovermode="y")
        restored = FigureConfig.from_dict(spec.to_dict())
        assert restored.hovermode == "y"

    def test_default_enable_stripes(self) -> None:
        spec = FigureConfig()
        assert spec.enable_stripes is False

    def test_custom_enable_stripes(self) -> None:
        spec = FigureConfig(enable_stripes=True)
        assert spec.enable_stripes is True

    def test_enable_stripes_round_trip(self) -> None:
        spec = FigureConfig(enable_stripes=True)
        restored = FigureConfig.from_dict(spec.to_dict())
        assert restored.enable_stripes is True

    def test_default_show_error_bars(self) -> None:
        spec = FigureConfig()
        assert spec.show_error_bars is False

    def test_custom_show_error_bars(self) -> None:
        spec = FigureConfig(show_error_bars=True)
        assert spec.show_error_bars is True

    def test_show_error_bars_round_trip(self) -> None:
        spec = FigureConfig(show_error_bars=True)
        restored = FigureConfig.from_dict(spec.to_dict())
        assert restored.show_error_bars is True


class TestFigureSpecFullRoundTrip:
    """Verify extended figure fields survive a complete round trip."""

    def test_full_round_trip_with_all_new_fields(self) -> None:
        rl = ReferenceLineConfig(enabled=True, axis="y", value=42.0, color="red", label="Threshold")
        spec = FigureConfig(
            color_palette=["#111", "#222"],
            hatching_sequence=["x", "|"],
            reference_lines=[rl],
            hovermode="closest",
            enable_stripes=True,
            show_error_bars=True,
            data_labels=DataLabelConfig(enabled=True, font_size=14),
            series_styles=[SeriesStyleConfig(line_width=3.0, opacity=0.8)],
        )

        data = spec.to_dict()
        restored = FigureConfig.from_dict(data)

        assert restored.color_palette == ["#111", "#222"]
        assert restored.hatching_sequence == ["x", "|"]
        assert len(restored.reference_lines) == 1
        assert restored.reference_lines[0].value == 42.0
        assert restored.hovermode == "closest"
        assert restored.enable_stripes is True
        assert restored.show_error_bars is True
        assert restored.data_labels is not None
        assert restored.data_labels.enabled is True
        assert restored.data_labels.font_size == 14
        assert len(restored.series_styles) == 1
        assert restored.series_styles[0].line_width == 3.0


class TestFigureSpecImmutability:
    """The whole FigureConfig styling tree is frozen for reproducibility.

    Connectors and the resolver treat a resolved spec as read-only; these
    guards lock in that contract so a future field assignment can't silently
    mutate shared styling state.
    """

    def test_figure_config_is_frozen(self) -> None:
        spec = FigureConfig()
        with pytest.raises(FrozenInstanceError):
            spec.title = "nope"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            spec.barmode = "stack"  # type: ignore[misc]

    def test_nested_specs_are_frozen(self) -> None:
        spec = FigureConfig(legends=[LegendConfig()])
        with pytest.raises(FrozenInstanceError):
            spec.dimensions.width = 1.0  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            spec.typography.font_size_title = 1  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            spec.axes.y.label = "x"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            spec.legends[0].font_size = 99  # type: ignore[misc]

    def test_list_fields_remain_replaceable_by_construction(self) -> None:
        """Frozen blocks field rebinding, not building a fresh spec with new lists."""
        spec = FigureConfig(legends=[LegendConfig(role="primary")])
        # Construction (not mutation) is how you get a changed spec.
        spec2 = FigureConfig(legends=[*spec.legends, LegendConfig(role="secondary")])
        assert len(spec.legends) == 1
        assert len(spec2.legends) == 2
