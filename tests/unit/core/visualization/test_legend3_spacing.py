"""
Tests for legend3 (boxed annotation) spacing resolution.

Verifies that _render_boxed_annotation correctly uses legend3-specific
overrides when set, and falls back to primary legend spacing when not set.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Any, Dict

from src.web.pages.ui.plotting.export.converters.impl.layout_config import (
    FontStyleConfig,
    LegendSpacingConfig,
    PositioningConfig,
    SeparatorConfig,
)
from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
    LayoutApplier,
)


def _make_applier(
    legend_spacing: LegendSpacingConfig,
    font_config: FontStyleConfig | None = None,
) -> LayoutApplier:
    """Create a LayoutApplier with specific config for testing."""
    applier = LayoutApplier.__new__(LayoutApplier)
    applier.legend_spacing = legend_spacing
    applier.font_config = font_config or FontStyleConfig(
        font_size_title=10,
        font_size_xlabel=8,
        font_size_ylabel=8,
        font_size_y2label=8,
        font_size_ticks=6,
        font_size_yticks=6,
        font_size_y2ticks=6,
        font_size_annotations=5,
        font_size_legend=7,
        font_size_legend2=7,
        font_size_legend3=7,
        legend3_number_fontsize=7,
        legend3_text_fontsize=7,
        bold_title=False,
        bold_xlabel=False,
        bold_ylabel=False,
        bold_y2label=False,
        bold_ticks=False,
        bold_annotations=False,
        bold_group_labels=False,
        bold_legend=False,
        bold_legend2=False,
        bold_legend3=False,
    )
    applier.pos_config = PositioningConfig()
    applier.sep_config = SeparatorConfig()
    return applier


class TestLegend3SpacingResolution:
    """Validate that legend3-specific spacing overrides work correctly."""

    @patch("matplotlib.pyplot.rcParams", {"text.usetex": False})
    def test_legend3_borderpad_override(self) -> None:
        """When legend3_borderpad is set, boxed annotation uses it."""
        spacing = LegendSpacingConfig(
            borderpad=0.3,
            labelspacing=0.2,
            legend3_borderpad=0.8,
            legend3_labelspacing=-1.0,
        )
        applier = _make_applier(spacing)

        mock_ax = MagicMock()
        ann: Dict[str, Any] = {
            "x": 0.5,
            "y": 0.5,
            "xref": "paper",
            "yref": "paper",
            "borderwidth": 1,
            "bordercolor": "black",
            "bgcolor": "white",
        }

        applier._render_boxed_annotation(mock_ax, ann, "1. foo\n2. bar")

        # Check the bbox_props passed to annotate
        call_kwargs = mock_ax.annotate.call_args[1]
        assert "pad=0.800" in call_kwargs["bbox"]["boxstyle"]

    @patch("matplotlib.pyplot.rcParams", {"text.usetex": False})
    def test_legend3_labelspacing_override(self) -> None:
        """When legend3_labelspacing is set, boxed annotation uses it."""
        spacing = LegendSpacingConfig(
            borderpad=0.3,
            labelspacing=0.2,
            legend3_borderpad=-1.0,
            legend3_labelspacing=0.6,
        )
        applier = _make_applier(spacing)

        mock_ax = MagicMock()
        ann: Dict[str, Any] = {
            "x": 0.5,
            "y": 0.5,
            "xref": "paper",
            "yref": "paper",
            "borderwidth": 1,
            "bordercolor": "black",
            "bgcolor": "white",
        }

        applier._render_boxed_annotation(mock_ax, ann, "1. foo\n2. bar")

        call_kwargs = mock_ax.annotate.call_args[1]
        # linespacing = 1.0 + 0.6 * 2.0 = 2.2
        assert abs(call_kwargs["linespacing"] - 2.2) < 0.01

    @patch("matplotlib.pyplot.rcParams", {"text.usetex": False})
    def test_legend3_fallback_to_primary(self) -> None:
        """When legend3 overrides are -1, falls back to primary legend."""
        spacing = LegendSpacingConfig(
            borderpad=0.3,
            labelspacing=0.2,
            legend3_borderpad=-1.0,
            legend3_labelspacing=-1.0,
        )
        applier = _make_applier(spacing)

        mock_ax = MagicMock()
        ann: Dict[str, Any] = {
            "x": 0.5,
            "y": 0.5,
            "xref": "paper",
            "yref": "paper",
            "borderwidth": 1,
            "bordercolor": "black",
            "bgcolor": "white",
        }

        applier._render_boxed_annotation(mock_ax, ann, "1. foo")

        call_kwargs = mock_ax.annotate.call_args[1]
        # Falls back to primary: borderpad=0.3
        assert "pad=0.300" in call_kwargs["bbox"]["boxstyle"]
        # linespacing = 1.0 + 0.2 * 2.0 = 1.4
        assert abs(call_kwargs["linespacing"] - 1.4) < 0.01
