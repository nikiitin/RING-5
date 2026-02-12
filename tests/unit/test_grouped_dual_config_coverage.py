"""Tests for DualAxisBarDotPlot render_config_ui — branch coverage."""

from typing import Any, List
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

_TITLE_LABELS_PATCH = (
    "src.web.pages.ui.components.plot_config_components"
    ".PlotConfigComponents.render_title_labels_section"
)


def _make_col_mock() -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _columns_side_effect(n: Any) -> List[MagicMock]:
    count = len(n) if isinstance(n, list) else n
    return [_make_col_mock() for _ in range(count)]


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "benchmark": ["a", "b", "c"],
            "config": ["x", "y", "z"],
            "cycles": [100.0, 200.0, 300.0],
            "ipc": [0.5, 0.6, 0.7],
        }
    )


class TestDualAxisRenderConfigUI:
    """Cover DualAxisBarDotPlot.render_config_ui branches."""

    @patch(_TITLE_LABELS_PATCH)
    @patch("src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot.st")
    def test_no_saved_config(
        self, mock_st: MagicMock, mock_labels: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot import DualAxisBarDotPlot

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = [
            "benchmark",  # x
            None,  # color
            "cycles",  # y_bar
            "ipc",  # y_dot
            "circle",  # dot_symbol
        ]
        mock_st.text_input.return_value = "IPC"
        mock_st.checkbox.return_value = True  # show_lines
        mock_st.number_input.side_effect = [10, 2]  # dot_size, line_width
        mock_st.color_picker.return_value = "#EF553B"
        mock_labels.return_value = {
            "title": "Test",
            "xlabel": "benchmark",
            "ylabel": "cycles",
            "legend_title": "",
        }

        plot = DualAxisBarDotPlot(1, "test")
        result = plot.render_config_ui(sample_df, {})

        assert result["x"] == "benchmark"
        assert result["y_bar"] == "cycles"
        assert result["y_dot"] == "ipc"

    @patch(_TITLE_LABELS_PATCH)
    @patch("src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot.st")
    def test_with_saved_config(
        self, mock_st: MagicMock, mock_labels: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot import DualAxisBarDotPlot

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = [
            "benchmark",  # x
            "config",  # color (non-None)
            "cycles",  # y_bar
            "ipc",  # y_dot
            "diamond",  # dot_symbol
        ]
        mock_st.text_input.return_value = "IPC"
        mock_st.checkbox.return_value = False  # show_lines
        mock_st.number_input.side_effect = [12, 3]
        mock_labels.return_value = {
            "title": "Saved",
            "xlabel": "benchmark",
            "ylabel": "cycles",
            "legend_title": "Legend",
        }

        saved = {
            "x": "benchmark",
            "color": "config",
            "y_bar": "cycles",
            "y_dot": "ipc",
            "dot_symbol": "diamond",
            "show_lines": False,
            "title": "Saved",
            "xlabel": "benchmark",
            "ylabel_bar": "cycles",
            "ylabel_dot": "IPC",
            "legend_title": "Legend",
        }

        plot = DualAxisBarDotPlot(1, "test")
        result = plot.render_config_ui(sample_df, saved)

        assert result["color"] == "config"
        assert result["show_lines"] is False

    @patch(_TITLE_LABELS_PATCH)
    @patch("src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot.st")
    def test_no_color_shows_dot_color_picker(
        self, mock_st: MagicMock, mock_labels: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot import DualAxisBarDotPlot

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = [
            "benchmark",
            None,
            "cycles",
            "ipc",
            "circle",
        ]
        mock_st.text_input.return_value = "IPC"
        mock_st.checkbox.return_value = True
        mock_st.number_input.side_effect = [10, 2]
        mock_st.color_picker.return_value = "#FF0000"
        mock_labels.return_value = {
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "legend_title": "",
        }

        plot = DualAxisBarDotPlot(1, "test")
        result = plot.render_config_ui(sample_df, {})
        assert result["dot_color"] == "#FF0000"
        mock_st.color_picker.assert_called()

    @patch(_TITLE_LABELS_PATCH)
    @patch("src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot.st")
    def test_with_color_no_dot_color_picker(
        self, mock_st: MagicMock, mock_labels: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot import DualAxisBarDotPlot

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = [
            "benchmark",
            "config",
            "cycles",
            "ipc",
            "square",
        ]
        mock_st.text_input.return_value = "IPC"
        mock_st.checkbox.return_value = True
        mock_st.number_input.side_effect = [10, 2]
        mock_labels.return_value = {
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "legend_title": "",
        }

        plot = DualAxisBarDotPlot(1, "test")
        result = plot.render_config_ui(sample_df, {"color": "config"})
        assert result["dot_color"] is None


class TestGroupedBarRenderConfigUI:
    """Cover GroupedBarPlot.render_config_ui branches."""

    @patch("src.web.pages.ui.plotting.types.grouped_bar_plot.PlotConfigComponents")
    @patch("src.web.pages.ui.plotting.types.grouped_bar_plot.st")
    def test_no_saved_config(
        self, mock_st: MagicMock, mock_pcc: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.plotting.types.grouped_bar_plot import GroupedBarPlot

        plot = GroupedBarPlot(1, "test")
        plot.render_common_config = MagicMock(
            return_value={
                "categorical_cols": ["benchmark", "config"],
                "x": "benchmark",
                "y": "cycles",
                "title": "Test",
                "xlabel": "X",
                "ylabel": "Y",
            }
        )
        mock_st.selectbox.return_value = "config"
        mock_pcc.render_filter_multiselects.return_value = (["a", "b"], ["x", "y"])

        result = plot.render_config_ui(sample_df, {})
        assert result["group"] == "config"
        assert result["_needs_advanced"] is True

    @patch("src.web.pages.ui.plotting.types.grouped_bar_plot.PlotConfigComponents")
    @patch("src.web.pages.ui.plotting.types.grouped_bar_plot.st")
    def test_with_saved_group(
        self, mock_st: MagicMock, mock_pcc: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.plotting.types.grouped_bar_plot import GroupedBarPlot

        plot = GroupedBarPlot(1, "test")
        plot.render_common_config = MagicMock(
            return_value={
                "categorical_cols": ["benchmark", "config"],
                "x": "benchmark",
                "y": "cycles",
                "title": "Test",
                "xlabel": "X",
                "ylabel": "Y",
            }
        )
        mock_st.selectbox.return_value = "benchmark"
        mock_pcc.render_filter_multiselects.return_value = (["a"], ["x"])

        result = plot.render_config_ui(sample_df, {"group": "benchmark"})
        assert result["group"] == "benchmark"


class TestGroupedBarThemeOptions:
    """Cover GroupedBarPlot.render_theme_options branches."""

    @patch("src.web.pages.ui.plotting.types.grouped_bar_plot.st")
    def test_isolate_last_disabled(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.plotting.types.grouped_bar_plot import GroupedBarPlot

        plot = GroupedBarPlot(1, "test")
        # Mock parent's render_theme_options to return empty dict
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.checkbox.side_effect = [False, False, False]  # show_sep, shade_alt, isolate_last
        mock_st.color_picker.side_effect = ["#E0E0E0", "#F5F5F5"]

        with patch.object(type(plot).__bases__[0], "render_theme_options", return_value={}):
            result = plot.render_theme_options({})
        assert result.get("isolate_last_group") is False

    @patch("src.web.pages.ui.plotting.types.grouped_bar_plot.st")
    def test_isolate_last_enabled(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.plotting.types.grouped_bar_plot import GroupedBarPlot

        plot = GroupedBarPlot(1, "test")
        mock_st.columns.side_effect = _columns_side_effect
        # show_sep, shade_alt, isolate_last (True)
        mock_st.checkbox.side_effect = [True, False, True]
        mock_st.color_picker.side_effect = ["#E0E0E0", "#F5F5F5"]
        mock_st.number_input.return_value = 0.5

        with patch.object(type(plot).__bases__[0], "render_theme_options", return_value={}):
            result = plot.render_theme_options({})
        assert result["isolate_last_group"] is True
        assert result["isolation_gap"] == 0.5


class TestGroupedBarAdvancedOptions:
    """Cover GroupedBarPlot.render_advanced_options filter branches."""

    @patch("src.web.pages.ui.plotting.types.grouped_bar_plot.st")
    def test_with_x_and_group_filter(self, mock_st: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.grouped_bar_plot import GroupedBarPlot

        plot = GroupedBarPlot(1, "test")
        saved = {
            "x": "benchmark",
            "group": "config",
            "x_filter": ["a", "b"],
            "group_filter": ["x"],
        }
        # Mock the parent's render_advanced_options
        with patch.object(type(plot).__bases__[0], "render_advanced_options", return_value={}):
            result = plot.render_advanced_options(saved, sample_df)
        assert isinstance(result, dict)

    @patch("src.web.pages.ui.plotting.types.grouped_bar_plot.st")
    def test_without_filters(self, mock_st: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.grouped_bar_plot import GroupedBarPlot

        plot = GroupedBarPlot(1, "test")
        saved = {"x": "benchmark", "group": "config"}

        with patch.object(type(plot).__bases__[0], "render_advanced_options", return_value={}):
            result = plot.render_advanced_options(saved, sample_df)
        assert isinstance(result, dict)
