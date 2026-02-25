"""Unit tests for PresetApplicator.

Validates that preset values are correctly overlaid onto an existing
FigureConfig while preserving data-derived fields (traces, colors, etc.).
"""

from __future__ import annotations

from typing import Any

from src.core.models.visualization.axis_config import AxesConfig, AxisConfig
from src.core.models.visualization.figure_config import (
    DimensionConfig,
    FigureConfig,
    SeparatorConfig,
)
from src.core.models.visualization.legend_config import LegendConfig
from src.core.models.visualization.trace_config import TraceConfig
from src.core.models.visualization.typography_config import TypographyConfig
from src.web.rendering.preset_applicator import PresetApplicator

# ── Fixtures ─────────────────────────────────────────────────────


def _make_config_spec() -> FigureConfig:
    """Build a FigureConfig that simulates a user's plot config.

    Uses non-default values for data-derived fields so we can verify
    they survive the preset overlay.
    """
    return FigureConfig(
        dimensions=DimensionConfig(
            width=800.0,
            height=600.0,
            dpi=1,  # pixel passthrough
            bar_width_scale=0.85,
        ),
        typography=TypographyConfig(
            font_size_base=14,
            font_size_title=18,
        ),
        axes=AxesConfig(
            x=AxisConfig(tick_angle=90.0),
        ),
        legends=[
            LegendConfig(role="primary", font_size=12, ncol=2),
        ],
        traces=[
            TraceConfig(name="trace_A", trace_type="bar"),
            TraceConfig(name="trace_B", trace_type="scatter"),
        ],
        annotations=[],
        separator=SeparatorConfig(enabled=False),
        color_palette=["#FF0000", "#00FF00", "#0000FF"],
        title="My Custom Title",
        font_family="sans-serif",
        metadata={"benchmark": "parsec"},
    )


def _isca_preset() -> dict[str, Any]:
    """Return an ISCA-style preset dictionary."""
    return {
        "width_inches": 3.5,
        "height_inches": 2.5,
        "dpi": 300,
        "font_family": "serif",
        "font_size_base": 10,
        "font_size_title": 10,
        "font_size_xlabel": 9,
        "font_size_ylabel": 9,
        "font_size_ticks": 8,
        "font_size_legend": 8,
        "legend_columnspacing": 1.0,
        "legend_handletextpad": 0.5,
        "legend_labelspacing": 0.3,
        "legend_handlelength": 1.5,
        "legend_handleheight": 0.7,
        "legend_borderpad": 0.3,
        "legend_borderaxespad": 0.3,
        "xtick_rotation": 45.0,
        "xtick_pad": 5.0,
        "ytick_pad": 5.0,
        "group_separator": True,
        "group_separator_style": "dot",
        "group_separator_color": "#888888",
        "latex_extra_preamble": "\\usepackage{times}",
    }


def _poster_preset() -> dict[str, Any]:
    """Return a poster-style preset dictionary."""
    return {
        "width_inches": 10.0,
        "height_inches": 7.0,
        "dpi": 150,
        "font_family": "sans-serif",
        "font_size_base": 24,
        "font_size_title": 28,
        "font_size_xlabel": 20,
        "font_size_ylabel": 20,
        "font_size_ticks": 16,
        "font_size_legend": 18,
        "bold_title": True,
        "bold_xlabel": True,
        "bold_ylabel": True,
    }


# ── Test: apply() full overlay ───────────────────────────────────


class TestPresetApplicatorApply:
    """Tests for PresetApplicator.apply() — full overlay."""

    def test_dimensions_overridden(self) -> None:
        """Preset dimensions replace config dimensions."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _isca_preset())

        assert result.dimensions.width == 3.5
        assert result.dimensions.height == 2.5
        assert result.dimensions.dpi == 300

    def test_typography_overridden(self) -> None:
        """Preset font sizes replace config font sizes."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _isca_preset())

        assert result.typography is not None
        assert result.typography.font_size_base == 10
        assert result.typography.font_size_title == 10
        assert result.typography.font_size_ticks == 8

    def test_axes_overridden(self) -> None:
        """Preset axes styling replaces config axes."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _isca_preset())

        assert result.axes is not None
        assert result.axes.x.tick_angle == 45.0
        assert result.axes.x.tick_pad == 5.0

    def test_legends_overridden(self) -> None:
        """Preset legends replace config legends."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _isca_preset())

        # PresetSpecBuilder generates 3 legends (primary, secondary, tertiary)
        assert len(result.legends) == 3
        primary = result.legends[0]
        assert primary.role == "primary"
        assert primary.font_size == 8
        assert primary.spacing is not None
        assert primary.spacing.columnspacing == 1.0

    def test_separator_overridden(self) -> None:
        """Preset separator settings replace config separator."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _isca_preset())

        assert result.separator.enabled is True
        assert result.separator.style == "dot"
        assert result.separator.color == "#888888"

    def test_font_family_overridden(self) -> None:
        """Preset font family replaces config font family."""
        spec = _make_config_spec()
        assert spec.font_family == "sans-serif"

        result = PresetApplicator.apply(spec, _isca_preset())
        assert result.font_family == "serif"

    def test_latex_preamble_overridden(self) -> None:
        """Preset LaTeX preamble replaces config preamble."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _isca_preset())

        assert result.latex_extra_preamble == "\\usepackage{times}"

    def test_traces_preserved(self) -> None:
        """Traces from the config spec survive the preset overlay."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _isca_preset())

        assert len(result.traces) == 2
        assert result.traces[0].name == "trace_A"
        assert result.traces[1].name == "trace_B"

    def test_color_palette_preserved(self) -> None:
        """Color palette from config spec is not overridden by preset."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _isca_preset())

        assert result.color_palette == ["#FF0000", "#00FF00", "#0000FF"]

    def test_title_preserved(self) -> None:
        """Title from config spec is not overridden by preset."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _isca_preset())

        assert result.title == "My Custom Title"

    def test_metadata_preserved(self) -> None:
        """Metadata from config spec is not overridden by preset."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _isca_preset())

        assert result.metadata == {"benchmark": "parsec"}

    def test_immutability(self) -> None:
        """apply() returns a new spec — original is unchanged."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _isca_preset())

        assert result is not spec
        # Original spec still has its own dimensions
        assert spec.dimensions.width == 800.0
        assert spec.dimensions.dpi == 1

    def test_same_preset_both_engines_identical_spec(self) -> None:
        """Same preset applied to same config produces identical FigureConfig.

        This validates engine-agnosticism: the spec is the same
        regardless of which engine will consume it.
        """
        spec = _make_config_spec()
        result_a = PresetApplicator.apply(spec, _isca_preset())
        result_b = PresetApplicator.apply(spec, _isca_preset())

        assert result_a == result_b


# ── Test: apply_partial() selective overlay ──────────────────────


class TestPresetApplicatorPartial:
    """Tests for PresetApplicator.apply_partial() — selective overlay."""

    def test_only_dimensions_when_only_dim_keys(self) -> None:
        """Only dimensions are overridden when only dim keys present."""
        spec = _make_config_spec()
        partial_preset: dict[str, Any] = {
            "width_inches": 5.0,
            "height_inches": 3.0,
        }
        result = PresetApplicator.apply_partial(spec, partial_preset)

        # Dimensions changed
        assert result.dimensions.width == 5.0
        assert result.dimensions.height == 3.0
        # Typography unchanged
        assert result.typography is not None
        assert result.typography.font_size_base == 14

    def test_only_typography_when_only_typo_keys(self) -> None:
        """Only typography is overridden when only font keys present."""
        spec = _make_config_spec()
        partial_preset: dict[str, Any] = {
            "font_size_base": 12,
            "bold_title": True,
        }
        result = PresetApplicator.apply_partial(spec, partial_preset)

        # Typography changed
        assert result.typography is not None
        assert result.typography.font_size_base == 12
        assert result.typography.bold_title is True
        # Dimensions unchanged
        assert result.dimensions.width == 800.0
        assert result.dimensions.dpi == 1

    def test_empty_preset_returns_original(self) -> None:
        """Empty preset dict returns spec unchanged."""
        spec = _make_config_spec()
        result = PresetApplicator.apply_partial(spec, {})

        assert result is spec

    def test_font_family_only(self) -> None:
        """Single scalar key overrides just that field."""
        spec = _make_config_spec()
        result = PresetApplicator.apply_partial(spec, {"font_family": "monospace"})

        assert result.font_family == "monospace"
        # Everything else unchanged
        assert result.dimensions.width == 800.0
        assert result.typography is not None
        assert result.typography.font_size_base == 14

    def test_separator_keys_override_separator(self) -> None:
        """Separator keys trigger separator override."""
        spec = _make_config_spec()
        partial_preset: dict[str, Any] = {
            "group_separator": True,
            "group_separator_style": "solid",
        }
        result = PresetApplicator.apply_partial(spec, partial_preset)

        assert result.separator.enabled is True
        assert result.separator.style == "solid"

    def test_mixed_groups(self) -> None:
        """Multiple groups can be overridden simultaneously."""
        spec = _make_config_spec()
        partial_preset: dict[str, Any] = {
            "width_inches": 7.0,
            "font_size_base": 20,
            "xtick_rotation": 0.0,
        }
        result = PresetApplicator.apply_partial(spec, partial_preset)

        assert result.dimensions.width == 7.0
        assert result.typography is not None
        assert result.typography.font_size_base == 20
        assert result.axes is not None
        assert result.axes.x.tick_angle == 0.0


# ── Test: different presets produce different specs ───────────────


class TestPresetVariety:
    """Verify different presets produce meaningfully different specs."""

    def test_isca_vs_poster(self) -> None:
        """ISCA and poster presets produce different dimensions and fonts."""
        spec = _make_config_spec()
        isca = PresetApplicator.apply(spec, _isca_preset())
        poster = PresetApplicator.apply(spec, _poster_preset())

        # Dimensions differ
        assert isca.dimensions.width < poster.dimensions.width
        assert isca.dimensions.dpi > poster.dimensions.dpi

        # Fonts differ
        assert isca.typography is not None
        assert poster.typography is not None
        assert isca.typography.font_size_base < poster.typography.font_size_base
        assert isca.typography.font_size_title < poster.typography.font_size_title

        # Both preserved traces
        assert isca.traces == poster.traces
        assert len(isca.traces) == 2

    def test_poster_bold_flags(self) -> None:
        """Poster preset applies bold flags correctly."""
        spec = _make_config_spec()
        result = PresetApplicator.apply(spec, _poster_preset())

        assert result.typography is not None
        assert result.typography.bold_title is True
        assert result.typography.bold_xlabel is True
        assert result.typography.bold_ylabel is True
