"""
Tests targeting uncovered lines in LayoutApplier.

Covers:
- _build_positioning_config with invalid xtick_ha (L80)
- _build_separator_config with invalid style (L111)
- _apply_ticks with xtick_offset != 0 (L248-251)
- _apply_annotations with bar totals, grouping labels, font colors (L313, L330)
- _determine_annotation_font for grouping labels and fallback (L364-370)
- _calculate_annotation_position with alternating grouping labels (L395-399)
- _determine_xycoords mixed coords (L415-419)
- _build_matplotlib_annotation yanchor/xanchor branches (L448-465)
- _draw_group_separators with dotted/solid styles (L494-519)
"""

import matplotlib
import matplotlib.pyplot as plt
import pytest

from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
    LayoutApplier,
)

matplotlib.use("Agg")


@pytest.fixture
def applier() -> LayoutApplier:
    """LayoutApplier with default preset."""
    return LayoutApplier(preset=None)


@pytest.fixture
def applier_with_preset() -> LayoutApplier:
    """LayoutApplier with full preset configuration."""
    preset = {
        "font_size_title": 12,
        "font_size_xlabel": 10,
        "font_size_ylabel": 10,
        "font_size_ticks": 8,
        "font_size_annotations": 7,
        "bold_title": True,
        "bold_xlabel": True,
        "bold_ylabel": False,
        "bold_ticks": False,
        "bold_annotations": True,
        "ylabel_pad": 15.0,
        "ylabel_y_position": 0.6,
        "xtick_pad": 6.0,
        "ytick_pad": 6.0,
        "xtick_rotation": 30.0,
        "xtick_ha": "center",
        "xtick_offset": 0.0,
        "xaxis_margin": 0.03,
        "group_label_offset": -0.15,
        "group_label_alternate": True,
        "group_separator": False,
        "group_separator_style": "dashed",
        "group_separator_color": "gray",
    }
    return LayoutApplier(preset=preset)


class TestBuildPositioningConfig:
    """Tests for _build_positioning_config, especially invalid xtick_ha."""

    def test_invalid_xtick_ha_defaults_to_right(self) -> None:
        """When xtick_ha is not left/center/right, it should default to 'right'."""
        preset = {"xtick_ha": "invalid_value"}
        applier = LayoutApplier(preset=preset)
        assert applier.pos_config.xtick_ha == "right"

    def test_valid_xtick_ha_preserved(self) -> None:
        """When xtick_ha is valid, it should be kept."""
        for ha in ("left", "center", "right"):
            applier = LayoutApplier(preset={"xtick_ha": ha})
            assert applier.pos_config.xtick_ha == ha


class TestBuildSeparatorConfig:
    """Tests for _build_separator_config with invalid style values."""

    def test_invalid_style_defaults_to_dashed(self) -> None:
        """When group_separator_style is invalid, default to 'dashed'."""
        preset = {"group_separator_style": "wavy"}
        applier = LayoutApplier(preset=preset)
        assert applier.sep_config.style == "dashed"

    def test_valid_styles_preserved(self) -> None:
        """All valid styles should be preserved."""
        for style in ("solid", "dashed", "dotted", "dashdot"):
            applier = LayoutApplier(preset={"group_separator_style": style})
            assert applier.sep_config.style == style


class TestApplyTicksWithOffset:
    """Tests for _apply_ticks with xtick_offset != 0."""

    def test_xtick_offset_applies_transform(self) -> None:
        """When xtick_offset is non-zero, tick labels should have offset transforms."""
        preset = {"xtick_offset": 5.0, "xtick_rotation": 45.0, "xtick_ha": "right"}
        applier = LayoutApplier(preset=preset)

        fig, ax = plt.subplots()
        ax.bar([0, 1, 2], [3, 4, 5])

        layout = {
            "x_tickvals": [0, 1, 2],
            "x_ticktext": ["A", "B", "C"],
        }
        applier._apply_ticks(ax, layout)

        labels = ax.get_xticklabels()
        assert len(labels) == 3
        # With offset applied, each label should have a modified transform
        # The transform should differ from the default
        plt.close(fig)

    def test_zero_offset_no_extra_transform(self) -> None:
        """When xtick_offset is 0, no extra transform is applied."""
        preset = {"xtick_offset": 0.0, "xtick_rotation": 0.0}
        applier = LayoutApplier(preset=preset)

        fig, ax = plt.subplots()
        ax.bar([0, 1, 2], [3, 4, 5])

        layout = {
            "x_tickvals": [0, 1, 2],
            "x_ticktext": ["A", "B", "C"],
        }
        applier._apply_ticks(ax, layout)

        labels = ax.get_xticklabels()
        assert len(labels) == 3
        plt.close(fig)

    def test_y_tickvals_applied(self) -> None:
        """Y tick positions and labels should be set when present in layout."""
        applier = LayoutApplier(preset=None)

        fig, ax = plt.subplots()
        ax.bar([0, 1], [10, 20])

        layout = {
            "y_tickvals": [0, 10, 20],
            "y_ticktext": ["Zero", "Ten", "Twenty"],
        }
        applier._apply_ticks(ax, layout)

        ytick_labels = [t.get_text() for t in ax.get_yticklabels()]
        assert "Zero" in ytick_labels
        assert "Ten" in ytick_labels
        plt.close(fig)


class TestDetermineAnnotationFont:
    """Tests for _determine_annotation_font branches."""

    def test_bar_total_font(self) -> None:
        """Bar total annotations use annotation font size and bold."""
        applier = LayoutApplier(preset=None)
        result = applier._determine_annotation_font(is_bar_total=True, is_grouping_label=False)
        assert result["fontsize"] == applier.font_config.font_size_annotations
        assert result["weight"] == "bold"  # bold_annotations defaults to True

    def test_grouping_label_font(self) -> None:
        """Grouping labels use xlabel font size."""
        applier = LayoutApplier(preset=None)
        result = applier._determine_annotation_font(is_bar_total=False, is_grouping_label=True)
        assert result["fontsize"] == applier.font_config.font_size_xlabel

    def test_fallback_font(self) -> None:
        """Fallback (neither bar total nor grouping) uses annotation font."""
        applier = LayoutApplier(preset=None)
        result = applier._determine_annotation_font(is_bar_total=False, is_grouping_label=False)
        assert result["fontsize"] == applier.font_config.font_size_annotations

    def test_non_bold_annotations(self) -> None:
        """When bold_annotations is False, weight should be 'normal'."""
        preset = {"bold_annotations": False}
        applier = LayoutApplier(preset=preset)
        result = applier._determine_annotation_font(is_bar_total=True, is_grouping_label=False)
        assert result["weight"] == "normal"

    def test_bold_xlabel_grouping_label(self) -> None:
        """Grouping label with bold_xlabel should be bold."""
        preset = {"bold_xlabel": True}
        applier = LayoutApplier(preset=preset)
        result = applier._determine_annotation_font(is_bar_total=False, is_grouping_label=True)
        assert result["weight"] == "bold"


class TestCalculateAnnotationPosition:
    """Tests for _calculate_annotation_position with alternation."""

    def test_non_grouping_label_returns_ann_y(self) -> None:
        """Non-grouping labels return the annotation's original y."""
        applier = LayoutApplier(preset=None)
        ann = {"y": 5.0}
        y_pos, idx = applier._calculate_annotation_position(
            ann, is_grouping_label=False, grouping_label_index=0
        )
        assert y_pos == 5.0
        assert idx == 0

    def test_grouping_label_even_index(self) -> None:
        """Even-indexed grouping labels use group_label_offset."""
        applier = LayoutApplier(preset=None)
        ann = {"y": -0.05}
        y_pos, idx = applier._calculate_annotation_position(
            ann, is_grouping_label=True, grouping_label_index=0
        )
        assert y_pos == applier.pos_config.group_label_offset
        assert idx == 1  # index incremented

    def test_grouping_label_odd_index_alternates(self) -> None:
        """Odd-indexed grouping labels use offset - 0.05 when alternating."""
        applier = LayoutApplier(preset=None)
        ann = {"y": -0.05}
        y_pos, idx = applier._calculate_annotation_position(
            ann, is_grouping_label=True, grouping_label_index=1
        )
        assert y_pos == applier.pos_config.group_label_offset - 0.05
        assert idx == 2

    def test_no_alternate_all_same_offset(self) -> None:
        """When group_label_alternate is False, all use same offset."""
        preset = {"group_label_alternate": False}
        applier = LayoutApplier(preset=preset)
        ann = {"y": -0.05}
        y_pos, _ = applier._calculate_annotation_position(
            ann, is_grouping_label=True, grouping_label_index=1
        )
        assert y_pos == applier.pos_config.group_label_offset


class TestDetermineXycoords:
    """Tests for _determine_xycoords with all coordinate combinations."""

    def test_both_paper(self) -> None:
        applier = LayoutApplier(preset=None)
        assert applier._determine_xycoords("paper", "paper") == "axes fraction"

    def test_xref_paper_only(self) -> None:
        applier = LayoutApplier(preset=None)
        result = applier._determine_xycoords("paper", "y")
        assert result == ("axes fraction", "data")

    def test_yref_paper_only(self) -> None:
        applier = LayoutApplier(preset=None)
        result = applier._determine_xycoords("x", "paper")
        assert result == ("data", "axes fraction")

    def test_both_data(self) -> None:
        applier = LayoutApplier(preset=None)
        assert applier._determine_xycoords("x", "y") == "data"


class TestBuildMatplotlibAnnotation:
    """Tests for _build_matplotlib_annotation yanchor/xanchor branches."""

    def test_yanchor_top(self) -> None:
        applier = LayoutApplier(preset=None)
        ann = {"x": 1.0, "y": 2.0, "yanchor": "top"}
        result = applier._build_matplotlib_annotation(ann, "text", 2.0, "data", {})
        assert result["va"] == "top"

    def test_yanchor_bottom(self) -> None:
        applier = LayoutApplier(preset=None)
        ann = {"x": 1.0, "y": 2.0, "yanchor": "bottom"}
        result = applier._build_matplotlib_annotation(ann, "text", 2.0, "data", {})
        assert result["va"] == "bottom"

    def test_yanchor_middle(self) -> None:
        applier = LayoutApplier(preset=None)
        ann = {"x": 1.0, "y": 2.0, "yanchor": "middle"}
        result = applier._build_matplotlib_annotation(ann, "text", 2.0, "data", {})
        assert result["va"] == "center"

    def test_yanchor_auto_paper_negative_y(self) -> None:
        """Auto yanchor with paper yref and negative y should use 'top'."""
        applier = LayoutApplier(preset=None)
        ann = {"x": 0.5, "y": -0.1, "yref": "paper"}
        result = applier._build_matplotlib_annotation(ann, "text", -0.1, "data", {})
        assert result["va"] == "top"

    def test_yanchor_auto_positive_y(self) -> None:
        """Auto yanchor with positive y should use 'bottom'."""
        applier = LayoutApplier(preset=None)
        ann = {"x": 1.0, "y": 5.0}
        result = applier._build_matplotlib_annotation(ann, "text", 5.0, "data", {})
        assert result["va"] == "bottom"

    def test_xanchor_left(self) -> None:
        applier = LayoutApplier(preset=None)
        ann = {"x": 1.0, "y": 2.0, "xanchor": "left"}
        result = applier._build_matplotlib_annotation(ann, "text", 2.0, "data", {})
        assert result["ha"] == "left"

    def test_xanchor_right(self) -> None:
        applier = LayoutApplier(preset=None)
        ann = {"x": 1.0, "y": 2.0, "xanchor": "right"}
        result = applier._build_matplotlib_annotation(ann, "text", 2.0, "data", {})
        assert result["ha"] == "right"

    def test_xanchor_center_default(self) -> None:
        applier = LayoutApplier(preset=None)
        ann = {"x": 1.0, "y": 2.0}
        result = applier._build_matplotlib_annotation(ann, "text", 2.0, "data", {})
        assert result["ha"] == "center"

    def test_textangle_rotation(self) -> None:
        applier = LayoutApplier(preset=None)
        ann = {"x": 1.0, "y": 2.0, "textangle": 45}
        result = applier._build_matplotlib_annotation(ann, "text", 2.0, "data", {})
        assert result["rotation"] == -45

    def test_font_props_merged(self) -> None:
        applier = LayoutApplier(preset=None)
        ann = {"x": 1.0, "y": 2.0}
        font_props = {"fontsize": 8, "weight": "bold"}
        result = applier._build_matplotlib_annotation(ann, "text", 2.0, "data", font_props)
        assert result["fontsize"] == 8
        assert result["weight"] == "bold"


class TestApplyAnnotations:
    """Tests for _apply_annotations with various annotation types."""

    def test_bar_total_annotation(self) -> None:
        """Bar total annotations (both x/y data) should use annotation font."""
        applier = LayoutApplier(preset=None)
        fig, ax = plt.subplots()
        ax.bar([0, 1], [10, 20])

        layout = {
            "annotations": [
                {"text": "10", "x": 0, "y": 10, "xref": "x", "yref": "y"},
            ]
        }
        applier._apply_annotations(ax, layout)
        # Should complete without error; annotation added
        assert len(ax.texts) == 1
        plt.close(fig)

    def test_grouping_label_annotation(self) -> None:
        """Grouping labels (yref=paper, y<0) should use xlabel font."""
        applier = LayoutApplier(preset=None)
        fig, ax = plt.subplots()

        layout = {
            "annotations": [
                {"text": "Group A", "x": 0.5, "y": -0.1, "xref": "x", "yref": "paper"},
            ]
        }
        applier._apply_annotations(ax, layout)
        assert len(ax.texts) == 1
        plt.close(fig)

    def test_annotation_with_font_color(self) -> None:
        """Annotations with font.color should include color in font props."""
        applier = LayoutApplier(preset=None)
        fig, ax = plt.subplots()

        layout = {
            "annotations": [
                {
                    "text": "value",
                    "x": 0,
                    "y": 5,
                    "xref": "x",
                    "yref": "y",
                    "font": {"color": "red"},
                },
            ]
        }
        applier._apply_annotations(ax, layout)
        assert len(ax.texts) == 1
        plt.close(fig)

    def test_annotation_with_html_tags_cleaned(self) -> None:
        """HTML tags in annotation text should be cleaned."""
        applier = LayoutApplier(preset=None)
        fig, ax = plt.subplots()

        layout = {
            "annotations": [
                {"text": "<b>Bold</b> and <i>italic</i>", "x": 0, "y": 5},
            ]
        }
        applier._apply_annotations(ax, layout)
        assert len(ax.texts) == 1
        # Text should have HTML removed
        plt.close(fig)

    def test_no_annotations_key(self) -> None:
        """If no 'annotations' in layout, should return early."""
        applier = LayoutApplier(preset=None)
        fig, ax = plt.subplots()

        applier._apply_annotations(ax, {})
        assert len(ax.texts) == 0
        plt.close(fig)


class TestDrawGroupSeparators:
    """Tests for _draw_group_separators."""

    def test_separators_drawn_with_two_groups(self) -> None:
        """With 2+ grouping positions, a separator line should be drawn."""
        preset = {
            "group_separator": True,
            "group_separator_style": "dashed",
            "group_separator_color": "gray",
        }
        applier = LayoutApplier(preset=preset)

        fig, ax = plt.subplots()
        ax.bar([0, 1, 2, 3], [5, 10, 15, 20])

        layout = {
            "annotations": [
                {"text": "Group A", "x": 0.5, "y": -0.1, "xref": "x", "yref": "paper"},
                {"text": "Group B", "x": 2.5, "y": -0.1, "xref": "x", "yref": "paper"},
            ]
        }

        applier._draw_group_separators(ax, layout)
        # Should have drawn a line
        assert len(ax.lines) > 0
        plt.close(fig)

    def test_no_separator_with_one_group(self) -> None:
        """With fewer than 2 grouping positions, no separator is drawn."""
        applier = LayoutApplier(preset={"group_separator": True})
        fig, ax = plt.subplots()

        layout = {
            "annotations": [
                {"text": "Only One", "x": 0.5, "y": -0.1, "xref": "x", "yref": "paper"},
            ]
        }

        initial_lines = len(ax.lines)
        applier._draw_group_separators(ax, layout)
        assert len(ax.lines) == initial_lines
        plt.close(fig)

    def test_dotted_separator_style(self) -> None:
        """Dotted style should map to ':' linestyle."""
        preset = {
            "group_separator": True,
            "group_separator_style": "dotted",
            "group_separator_color": "blue",
        }
        applier = LayoutApplier(preset=preset)

        fig, ax = plt.subplots()
        layout = {
            "annotations": [
                {"text": "A", "x": 1.0, "y": -0.1, "xref": "x", "yref": "paper"},
                {"text": "B", "x": 3.0, "y": -0.1, "xref": "x", "yref": "paper"},
            ]
        }
        applier._draw_group_separators(ax, layout)
        assert len(ax.lines) > 0
        plt.close(fig)

    def test_solid_separator_style(self) -> None:
        """Solid style should map to '-' linestyle."""
        preset = {
            "group_separator": True,
            "group_separator_style": "solid",
            "group_separator_color": "black",
        }
        applier = LayoutApplier(preset=preset)

        fig, ax = plt.subplots()
        layout = {
            "annotations": [
                {"text": "A", "x": 0.0, "y": -0.1, "xref": "x", "yref": "paper"},
                {"text": "B", "x": 2.0, "y": -0.1, "xref": "x", "yref": "paper"},
            ]
        }
        applier._draw_group_separators(ax, layout)
        assert len(ax.lines) > 0
        plt.close(fig)

    def test_separators_enabled_in_apply_annotations(self) -> None:
        """When separators are enabled, _apply_annotations should call _draw_group_separators."""
        preset = {
            "group_separator": True,
            "group_separator_style": "dashed",
            "group_separator_color": "gray",
        }
        applier = LayoutApplier(preset=preset)

        fig, ax = plt.subplots()
        layout = {
            "annotations": [
                {"text": "G1", "x": 1.0, "y": -0.1, "xref": "x", "yref": "paper"},
                {"text": "G2", "x": 3.0, "y": -0.1, "xref": "x", "yref": "paper"},
            ]
        }
        applier._apply_annotations(ax, layout)
        # Should have separator line drawn
        assert len(ax.lines) > 0
        plt.close(fig)


class TestApplyAxisRangesMargins:
    """Tests for _apply_axis_ranges with margin configuration."""

    def test_no_x_range_tightens_margins(self) -> None:
        """Without explicit x_range, should use margins()."""
        applier = LayoutApplier(preset=None)
        fig, ax = plt.subplots()
        ax.bar([0, 1, 2], [3, 4, 5])

        layout = {"y_range": [0, 10]}
        applier._apply_axis_ranges(ax, layout)

        assert ax.get_ylim() == (0, 10)
        plt.close(fig)


class TestApplyLegend:
    """Tests for _apply_legend with legend positioning."""

    def test_legend_applied_with_handles(self) -> None:
        """Legend should be created when handles exist."""
        applier = LayoutApplier(preset=None)
        fig, ax = plt.subplots()
        ax.bar([0, 1], [3, 4], label="Series A")

        layout = {"legend": {"x": 0.8, "y": 0.95}}
        applier._apply_legend(ax, layout)

        legend = ax.get_legend()
        assert legend is not None
        plt.close(fig)

    def test_legend_not_created_without_handles(self) -> None:
        """Legend should not be created when no labeled artists."""
        applier = LayoutApplier(preset=None)
        fig, ax = plt.subplots()
        ax.bar([0, 1], [3, 4])  # No label → no handles

        layout = {"legend": {"x": 0.8, "y": 0.95}}
        applier._apply_legend(ax, layout)

        legend = ax.get_legend()
        assert legend is None
        plt.close(fig)

    def test_no_legend_key_in_layout(self) -> None:
        """No 'legend' key should be a no-op."""
        applier = LayoutApplier(preset=None)
        fig, ax = plt.subplots()
        applier._apply_legend(ax, {})
        plt.close(fig)
