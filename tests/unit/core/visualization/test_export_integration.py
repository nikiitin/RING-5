"""
Integration tests — FigureSpec ↔ MatplotlibConverter legend kwargs.

Verifies that the resolved FigureSpec produces the same legend kwargs
that the old manual preset-lookup logic produced.
"""

import pytest
from typing import Any, Dict

from src.core.visualization.connectors.builders import PresetSpecBuilder
from src.core.visualization.legend_spec import LegendSpec, LegendSpacingSpec
from src.core.visualization.resolvers import resolve_spec
from src.web.pages.ui.plotting.export.converters.impl.matplotlib_converter import (
    MatplotlibConverter,
)
from src.web.pages.ui.plotting.export.presets.preset_schema import LaTeXPreset


def _minimal_preset(**overrides: Any) -> LaTeXPreset:
    """Create a minimal valid LaTeXPreset with optional overrides."""
    base: Dict[str, Any] = {
        "width_inches": 3.5,
        "height_inches": 2.5,
        "dpi": 300,
        "font_family": "serif",
        "font_size_base": 8,
        "font_size_title": 10,
        "font_size_xlabel": 8,
        "font_size_ylabel": 8,
        "font_size_y2label": -1,
        "font_size_legend": 7,
        "font_size_legend2": -1,
        "font_size_legend3": -1,
        "font_size_ticks": 6,
        "font_size_yticks": 6,
        "font_size_y2ticks": -1,
        "font_size_annotations": 5,
        "bold_title": True,
        "bold_xlabel": False,
        "bold_ylabel": False,
        "bold_y2label": False,
        "bold_ticks": False,
        "bold_annotations": True,
        "bold_group_labels": True,
        "bold_legend": False,
        "bold_legend2": False,
        "bold_legend3": False,
        "line_width": 1.5,
        "marker_size": 6,
        "legend_ncol": 2,
        "legend_columnspacing": 1.0,
        "legend_handletextpad": 0.4,
        "legend_labelspacing": 0.3,
        "legend_handlelength": 1.5,
        "legend_handleheight": 0.8,
        "legend_borderpad": 0.3,
        "legend_borderaxespad": 0.6,
        "legend2_columnspacing": -1.0,
        "legend2_handletextpad": -1.0,
        "legend2_labelspacing": -1.0,
        "legend2_handlelength": -1.0,
        "legend2_handleheight": -1.0,
        "legend2_borderpad": -1.0,
        "legend2_borderaxespad": -1.0,
        "legend2_ncol": 0,
        "legend3_borderpad": -1.0,
        "legend3_labelspacing": -1.0,
        "legend3_number_fontsize": -1,
        "legend3_text_fontsize": -1,
        "legend_custom_pos": True,
        "legend_x": 0.5,
        "legend_y": 1.05,
        "xtick_rotation": 30.0,
        "xtick_pad": 4.0,
        "xtick_ha": "right",
        "xtick_offset": 0.0,
        "ytick_pad": 4.0,
        "ylabel_pad": 12.0,
        "ylabel_y_position": 0.5,
        "y2label_pad": 12.0,
        "y2tick_pad": 4.0,
        "xaxis_margin": 0.03,
        "bar_width_scale": 0.9,
        "group_separator": True,
        "group_separator_style": "dotted",
        "group_separator_color": "blue",
        "group_label_offset": -0.15,
        "group_label_alternate": False,
        "group_label_alt_spacing": 0.05,
        "latex_extra_preamble": "",
    }
    base.update(overrides)
    return base  # type: ignore[return-value]


class TestLegendKwargsFromSpec:
    """Test _legend_kwargs_from_spec produces correct kwargs."""

    def test_primary_legend_kwargs(self) -> None:
        """Primary legend kwargs should match preset values."""
        preset = _minimal_preset()
        spec = resolve_spec(PresetSpecBuilder.from_preset(dict(preset)))
        primary = spec.legends[0]

        dummy_handles = ["h1", "h2", "h3"]
        dummy_labels = ["a", "b", "c"]

        kwargs = MatplotlibConverter._legend_kwargs_from_spec(
            primary, dummy_handles, dummy_labels
        )

        assert kwargs["fontsize"] == 7
        assert kwargs["ncol"] == 2
        assert kwargs["columnspacing"] == 1.0
        assert kwargs["handletextpad"] == 0.4
        assert kwargs["labelspacing"] == 0.3
        assert kwargs["handlelength"] == 1.5
        assert kwargs["handleheight"] == 0.8
        assert kwargs["borderpad"] == 0.3
        assert kwargs["borderaxespad"] == 0.6
        assert kwargs["bbox_to_anchor"] == (0.5, 1.05)
        assert kwargs["loc"] == "upper left"

    def test_secondary_legend_inherits_from_primary(self) -> None:
        """Secondary legend with -1 sentinels should inherit from primary."""
        preset = _minimal_preset()
        spec = resolve_spec(PresetSpecBuilder.from_preset(dict(preset)))
        # legends[1] is the secondary legend
        secondary = spec.legends[1]

        dummy_handles = ["h1"]
        dummy_labels = ["x"]

        kwargs = MatplotlibConverter._legend_kwargs_from_spec(
            secondary, dummy_handles, dummy_labels
        )

        # font_size_legend2 was -1 → inherits from primary (7)
        assert kwargs["fontsize"] == 7
        # legend2_columnspacing was -1 → inherits from primary (1.0)
        assert kwargs["columnspacing"] == 1.0
        assert kwargs["handletextpad"] == 0.4
        assert kwargs["labelspacing"] == 0.3

    def test_secondary_legend_explicit_values(self) -> None:
        """Secondary legend with explicit values should NOT inherit."""
        preset = _minimal_preset(
            font_size_legend2=12,
            legend2_columnspacing=2.5,
            legend2_ncol=4,
        )
        spec = resolve_spec(PresetSpecBuilder.from_preset(dict(preset)))
        secondary = spec.legends[1]

        kwargs = MatplotlibConverter._legend_kwargs_from_spec(
            secondary, ["h1", "h2"], ["a", "b"]
        )

        assert kwargs["fontsize"] == 12
        assert kwargs["columnspacing"] == 2.5
        assert kwargs["ncol"] == 4

    def test_no_custom_position_uses_best(self) -> None:
        """Legend without custom_position should use 'best' loc."""
        preset = _minimal_preset(legend_custom_pos=False)
        spec = resolve_spec(PresetSpecBuilder.from_preset(dict(preset)))
        primary = spec.legends[0]

        kwargs = MatplotlibConverter._legend_kwargs_from_spec(
            primary, ["h1"], ["a"]
        )

        assert kwargs["loc"] == "best"
        assert "bbox_to_anchor" not in kwargs

    def test_auto_ncol_few_handles(self) -> None:
        """With ncol=0 and few handles, should use 1 column."""
        preset = _minimal_preset(legend_ncol=0)
        spec = resolve_spec(PresetSpecBuilder.from_preset(dict(preset)))
        primary = spec.legends[0]

        kwargs = MatplotlibConverter._legend_kwargs_from_spec(
            primary, ["h1", "h2"], ["a", "b"]
        )

        assert kwargs["ncol"] == 1

    def test_auto_ncol_many_handles(self) -> None:
        """With ncol=0 and many handles, should use 2 columns."""
        preset = _minimal_preset(legend_ncol=0)
        spec = resolve_spec(PresetSpecBuilder.from_preset(dict(preset)))
        primary = spec.legends[0]

        handles = [f"h{i}" for i in range(6)]
        labels = [f"l{i}" for i in range(6)]

        kwargs = MatplotlibConverter._legend_kwargs_from_spec(
            primary, handles, labels
        )

        assert kwargs["ncol"] == 2


class TestConverterSpecIntegration:
    """Test MatplotlibConverter uses its _spec attribute correctly."""

    def test_converter_has_resolved_spec(self) -> None:
        """Converter should build a resolved FigureSpec from preset."""
        preset = _minimal_preset()
        converter = MatplotlibConverter(preset)

        assert converter._spec is not None
        assert converter._spec.dimensions.width == 3.5
        assert converter._spec.dimensions.height == 2.5
        assert converter._spec.typography.font_size_legend == 7

        # Should be resolved (no -1 sentinels)
        assert converter._spec.legends[1].font_size == 7  # inherited from primary
        assert converter._spec.typography.font_size_legend2 == 7

    def test_converter_spec_updates_on_reinit(self) -> None:
        """Creating a new converter with different preset should produce different spec."""
        preset1 = _minimal_preset(font_size_legend=7)
        preset2 = _minimal_preset(font_size_legend=14)

        conv1 = MatplotlibConverter(preset1)
        conv2 = MatplotlibConverter(preset2)

        assert conv1._spec.legends[0].font_size == 7
        assert conv2._spec.legends[0].font_size == 14
