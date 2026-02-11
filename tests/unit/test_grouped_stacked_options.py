"""Tests for GroupedStackedBarPlot UI branch coverage.

Covers _render_stack_total_options and render_theme_options.
"""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

from src.web.pages.ui.plotting.types.grouped_stacked_bar_plot import (
    GroupedStackedBarPlot,
)


def _make_col_mock() -> MagicMock:
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=m)
    m.__exit__ = MagicMock(return_value=False)
    return m


def _columns_side_effect(n: "int | list[int]") -> "list[MagicMock]":
    count = len(n) if isinstance(n, list) else n
    return [_make_col_mock() for _ in range(count)]


class TestRenderStackTotalOptions:
    """Test _render_stack_total_options branches."""

    @patch("src.web.pages.ui.plotting.types.grouped_stacked_bar_plot.st")
    def test_totals_disabled(self, mock_st: MagicMock) -> None:
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.checkbox.return_value = False

        plot = GroupedStackedBarPlot(1, "test")
        config: Dict[str, Any] = {}
        plot._render_stack_total_options({}, config)

        assert config["show_totals"] is False
        # When disabled, font size / format etc. should NOT be set
        assert "total_font_size" not in config

    @patch("src.web.pages.ui.plotting.types.grouped_stacked_bar_plot.st")
    def test_totals_enabled_outside(self, mock_st: MagicMock) -> None:
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.checkbox.return_value = True
        mock_st.text_input.return_value = ".3f"
        mock_st.number_input.side_effect = [14, 0, 0, 0.0]  # font_size, offset, rotation, threshold
        mock_st.color_picker.return_value = "#FF0000"
        mock_st.selectbox.return_value = "Outside"

        plot = GroupedStackedBarPlot(1, "test")
        config: Dict[str, Any] = {}
        plot._render_stack_total_options({}, config)

        assert config["show_totals"] is True
        assert config["net_total_format"] == ".3f"
        assert config["total_position"] == "Outside"
        assert "total_anchor" not in config  # Only for Inside

    @patch("src.web.pages.ui.plotting.types.grouped_stacked_bar_plot.st")
    def test_totals_enabled_inside_with_anchor(self, mock_st: MagicMock) -> None:
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.checkbox.return_value = True
        mock_st.text_input.return_value = ".2f"
        mock_st.number_input.side_effect = [
            12,
            5,
            90,
            1.0,
        ]  # font_size, offset, rotation, threshold
        mock_st.color_picker.return_value = "#000000"
        mock_st.selectbox.side_effect = ["Inside", "Middle"]

        plot = GroupedStackedBarPlot(1, "test")
        config: Dict[str, Any] = {}
        plot._render_stack_total_options({}, config)

        assert config["total_position"] == "Inside"
        assert config["total_anchor"] == "Middle"


class TestRenderThemeOptions:
    """Test render_theme_options for grouped stacked bar."""

    @patch("src.web.pages.ui.plotting.types.grouped_stacked_bar_plot.st")
    @patch.object(
        GroupedStackedBarPlot,
        "_render_stack_total_options",
    )
    @patch(
        "src.web.pages.ui.plotting.base_plot.BasePlot.render_theme_options",
        return_value={"some_base": True},
    )
    def test_adds_major_group_styling(
        self,
        mock_base_theme: MagicMock,
        mock_stack_totals: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.number_input.side_effect = [16, -0.10]  # major_label_size, major_label_offset
        mock_st.color_picker.side_effect = [
            "#111111",  # major_label_color
            "#E0E0E0",  # separator_color
            "#F5F5F5",  # shade_color
        ]
        mock_st.checkbox.side_effect = [
            True,  # show_separators
            False,  # shade_alternate
            False,  # isolate_last_group
        ]

        plot = GroupedStackedBarPlot(1, "test")
        config = plot.render_theme_options({"y_columns": ["ipc", "cycles"]})

        assert config["major_label_size"] == 16
        assert config["show_separators"] is True
        assert config["isolate_last_group"] is False

    @patch("src.web.pages.ui.plotting.types.grouped_stacked_bar_plot.st")
    @patch.object(
        GroupedStackedBarPlot,
        "_render_stack_total_options",
    )
    @patch(
        "src.web.pages.ui.plotting.base_plot.BasePlot.render_theme_options",
        return_value={},
    )
    def test_isolate_last_with_gap(
        self,
        mock_base_theme: MagicMock,
        mock_stack_totals: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.number_input.side_effect = [
            14,
            -0.15,
            0.8,
        ]  # major_label_size, offset, isolation_gap
        mock_st.color_picker.side_effect = ["#000", "#E0E0E0", "#F5F5F5"]
        mock_st.checkbox.side_effect = [
            True,  # show_separators
            False,  # shade_alternate
            True,  # isolate_last_group
        ]

        plot = GroupedStackedBarPlot(1, "test")
        config = plot.render_theme_options({})

        assert config["isolate_last_group"] is True
        assert config["isolation_gap"] == 0.8
