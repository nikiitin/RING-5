"""
Coverage tests for StackedBarPlot, HistogramPlot, PlotConfigComponents,
and BaseConverter.

Targets uncovered lines:
- stacked_bar_plot.py: 22-63 (render_config_ui), 159->163, 212-213, 253->255
- histogram_plot.py: 51-55, 145, 238->236, 244-246, 249, 364, 373-374
- plot_config_components.py: 43->59, 97-114, 165->174
- base_converter.py: 68, 77, 98, 100, 102
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _columns_side_effect(*args: Any, **kwargs: Any) -> List[MagicMock]:
    n = args[0] if args else kwargs.get("spec", 2)
    count = len(n) if isinstance(n, list) else n
    return [MagicMock() for _ in range(count)]


def _sample_stacked_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bench": ["A", "B", "C"],
            "ipc": [1.0, 2.0, 3.0],
            "cpi": [0.5, 0.3, 0.2],
            "ipc.sd": [0.1, 0.2, 0.1],
        }
    )


def _sample_histogram_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bench": ["A", "A", "B", "B"],
            "latency..0-10": [100, 200, 150, 250],
            "latency..10-20": [50, 60, 70, 80],
            "latency..0-10.sd": [5.0, 6.0, 7.0, 8.0],
            "group": ["g1", "g2", "g1", "g2"],
        }
    )


# ===========================================================================
# StackedBarPlot
# ===========================================================================


class TestStackedBarRenderConfigUI:
    """Lines 22-63: render_config_ui (calls PlotConfigComponents)."""

    @patch("src.web.pages.ui.plotting.types.stacked_bar_plot.PlotConfigComponents")
    @patch("src.web.pages.ui.plotting.types.stacked_bar_plot.st")
    def test_render_config_ui_basic(self, mock_st: MagicMock, mock_pcc: MagicMock) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        mock_st.selectbox.return_value = "bench"
        mock_pcc.render_statistics_multiselect.return_value = ["ipc", "cpi"]
        mock_pcc.render_filter_multiselects.return_value = (["A", "B"], [])
        mock_pcc.render_title_labels_section.return_value = {
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "legend_title": "L",
        }

        plot = StackedBarPlot(plot_id=1, name="test")
        df = _sample_stacked_data()
        result = plot.render_config_ui(df, {})

        assert result["x"] == "bench"
        assert result["y_columns"] == ["ipc", "cpi"]
        mock_pcc.render_title_labels_section.assert_called_once()
        # Verify include_legend_title=True was passed
        call_kwargs = mock_pcc.render_title_labels_section.call_args
        assert call_kwargs[1]["include_legend_title"] is True

    @patch("src.web.pages.ui.plotting.types.stacked_bar_plot.PlotConfigComponents")
    @patch("src.web.pages.ui.plotting.types.stacked_bar_plot.st")
    def test_render_config_ui_with_saved(self, mock_st: MagicMock, mock_pcc: MagicMock) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        mock_st.selectbox.return_value = "bench"
        mock_pcc.render_statistics_multiselect.return_value = ["ipc"]
        mock_pcc.render_filter_multiselects.return_value = (["A"], [])
        mock_pcc.render_title_labels_section.return_value = {
            "title": "Saved",
            "xlabel": "X",
            "ylabel": "Y",
        }

        plot = StackedBarPlot(plot_id=1, name="test")
        df = _sample_stacked_data()
        saved = {"x": "bench", "title": "Saved", "legend_title": "Stats"}
        result = plot.render_config_ui(df, saved)

        assert result["title"] == "Saved"


class TestStackedBarCreateFigure:
    """Lines 73-98, 134-145, 156-213, 243-258."""

    def test_empty_config_returns_placeholder(self) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        fig = plot.create_figure(_sample_stacked_data(), {"x": None, "y_columns": []})
        assert "Please select" in fig.layout.title.text

    def test_basic_stacked(self) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        config: Dict[str, Any] = {
            "x": "bench",
            "y_columns": ["ipc", "cpi"],
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "legend_title": "Stats",
        }
        fig = plot.create_figure(_sample_stacked_data(), config)

        assert len(fig.data) == 2
        assert fig.layout.barmode == "stack"

    def test_with_error_bars_and_styles(self) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        config: Dict[str, Any] = {
            "x": "bench",
            "y_columns": ["ipc"],
            "show_error_bars": True,
            "series_styles": {
                "ipc": {"name": "IPC", "color": "#ff0000", "pattern": "/"},
            },
        }
        fig = plot.create_figure(_sample_stacked_data(), config)

        assert len(fig.data) == 1
        assert fig.data[0].error_y is not None
        assert fig.data[0].marker.color == "#ff0000"

    def test_with_x_filter(self) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        config: Dict[str, Any] = {
            "x": "bench",
            "y_columns": ["ipc"],
            "x_filter": ["A"],
        }
        fig = plot.create_figure(_sample_stacked_data(), config)

        assert len(fig.data[0].x) == 1

    def test_show_totals_annotations(self) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        config: Dict[str, Any] = {
            "x": "bench",
            "y_columns": ["ipc", "cpi"],
            "show_totals": True,
            "total_threshold": 0.0,
        }
        fig = plot.create_figure(_sample_stacked_data(), config)

        assert fig.layout.annotations is not None
        assert len(fig.layout.annotations) == 3

    def test_totals_inside_end(self) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        y, anchor = plot._get_total_position(10.0, "Inside", "End")
        assert y == 10.0
        assert anchor == "top"

    def test_totals_inside_middle(self) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        y, anchor = plot._get_total_position(10.0, "Inside", "Middle")
        assert y == 5.0
        assert anchor == "middle"

    def test_totals_inside_start(self) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        y, anchor = plot._get_total_position(10.0, "Inside", "Start")
        assert y == 0
        assert anchor == "bottom"

    def test_totals_default_fallback(self) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        y, anchor = plot._get_total_position(10.0, "Unknown", "End")
        assert y == 10.0
        assert anchor == "bottom"

    def test_totals_threshold_skips_small(self) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        config: Dict[str, Any] = {
            "x": "bench",
            "y_columns": ["ipc"],
            "show_totals": True,
            "total_threshold": 100.0,  # All values below threshold
        }
        fig = plot.create_figure(_sample_stacked_data(), config)

        assert len(fig.layout.annotations) == 0

    def test_get_legend_column(self) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        assert plot.get_legend_column({}) is None


# ===========================================================================
# HistogramPlot
# ===========================================================================


class TestHistogramRenderConfigUI:
    """Lines 51-55, 145 in histogram_plot.py."""

    @patch("src.web.pages.ui.plotting.types.histogram_plot.st")
    def test_no_histogram_vars_detected(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        # No ".." columns → no histogram variables
        df = pd.DataFrame({"a": [1], "b": [2]})

        # render_common_config needs mocking since BasePlot calls st
        with patch.object(
            plot,
            "render_common_config",
            return_value={
                "title": "T",
                "xlabel": "X",
                "ylabel": "Y",
                "categorical_cols": ["a"],
            },
        ):
            result = plot.render_config_ui(df, {})

        assert result["histogram_variable"] is None
        mock_st.warning.assert_called()


class TestHistogramCreateFigure:
    """Lines 238-249, 364, 373-374."""

    def test_no_histogram_var_raises(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        with pytest.raises(ValueError, match="No histogram variable"):
            plot.create_figure(_sample_histogram_data(), {"histogram_variable": None})

    def test_no_bucket_cols_raises(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(ValueError, match="No histogram bucket columns"):
            plot.create_figure(df, {"histogram_variable": "latency"})

    def test_single_histogram(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        config: Dict[str, Any] = {
            "histogram_variable": "latency",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "normalization": "count",
            "cumulative": False,
        }
        fig = plot.create_figure(_sample_histogram_data(), config)

        assert len(fig.data) == 1

    def test_grouped_histogram(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        config: Dict[str, Any] = {
            "histogram_variable": "latency",
            "group_by": "group",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "normalization": "count",
            "cumulative": False,
        }
        fig = plot.create_figure(_sample_histogram_data(), config)

        assert len(fig.data) == 2  # g1 and g2

    def test_normalization_probability(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        vals = plot._normalize_values([10.0, 20.0, 30.0], {"normalization": "probability"})
        assert abs(sum(vals) - 1.0) < 1e-10

    def test_normalization_percent(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        vals = plot._normalize_values([10.0, 20.0, 30.0], {"normalization": "percent"})
        assert abs(sum(vals) - 100.0) < 1e-10

    def test_normalization_density(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        vals = plot._normalize_values([10.0, 20.0], {"normalization": "density", "bucket_size": 5})
        total = sum([10.0, 20.0])
        expected = [10.0 / (total * 5), 20.0 / (total * 5)]
        assert vals == pytest.approx(expected)

    def test_normalization_cumulative(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        vals = plot._normalize_values(
            [10.0, 20.0, 30.0],
            {"normalization": "count", "cumulative": True},
        )
        assert vals == [10.0, 30.0, 60.0]

    def test_normalization_zero_total(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        vals = plot._normalize_values([0.0, 0.0], {"normalization": "probability"})
        assert vals == [0.0, 0.0]

    def test_get_legend_column(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        assert plot.get_legend_column({"group_by": "bench"}) == "bench"
        assert plot.get_legend_column({}) is None

    def test_detect_histogram_variables(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        detected = plot._detect_histogram_variables(_sample_histogram_data())
        assert "latency" in detected


# ===========================================================================
# PlotConfigComponents
# ===========================================================================


class TestPlotConfigComponentsBranches:
    """Lines 43->59 (no group_col), 97-114 (statistics fallbacks), 165->174 (legend title)."""

    @patch("src.web.pages.ui.components.plot_config_components.st")
    def test_filter_no_group_col(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.components.plot_config_components import PlotConfigComponents

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.multiselect.return_value = ["A"]

        df = pd.DataFrame({"x": ["A", "B"]})
        x_vals, g_vals = PlotConfigComponents.render_filter_multiselects(
            data=df, x_col="x", group_col=None, saved_config={}, plot_id=1
        )

        assert x_vals == ["A"]
        assert g_vals == []

    @patch("src.web.pages.ui.components.plot_config_components.st")
    def test_filter_x_col_not_in_data(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.components.plot_config_components import PlotConfigComponents

        mock_st.columns.side_effect = _columns_side_effect

        df = pd.DataFrame({"a": [1]})
        x_vals, g_vals = PlotConfigComponents.render_filter_multiselects(
            data=df, x_col="missing", group_col=None, saved_config={}, plot_id=1
        )

        assert x_vals == []
        assert g_vals == []

    @patch("src.web.pages.ui.components.plot_config_components.st")
    def test_statistics_multiselect_fallback_2_cols(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.components.plot_config_components import PlotConfigComponents

        mock_st.multiselect.return_value = ["a", "b"]

        result = PlotConfigComponents.render_statistics_multiselect(
            numeric_cols=["a", "b", "c"],
            saved_config={},  # no y_columns → triggers fallback
            plot_id=1,
        )

        assert result == ["a", "b"]

    @patch("src.web.pages.ui.components.plot_config_components.st")
    def test_statistics_multiselect_fallback_1_col(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.components.plot_config_components import PlotConfigComponents

        mock_st.multiselect.return_value = ["a"]

        result = PlotConfigComponents.render_statistics_multiselect(
            numeric_cols=["a"],  # only 1 column
            saved_config={},
            plot_id=1,
        )

        assert result == ["a"]

    @patch("src.web.pages.ui.components.plot_config_components.st")
    def test_title_labels_with_legend_title(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.components.plot_config_components import PlotConfigComponents

        mock_st.text_input.side_effect = ["Title", "X", "Y", "Legend"]

        result = PlotConfigComponents.render_title_labels_section(
            saved_config={},
            plot_id=1,
            include_legend_title=True,
            default_legend_title="LT",
        )

        assert result["legend_title"] == "Legend"

    @patch("src.web.pages.ui.components.plot_config_components.st")
    def test_title_labels_without_legend_title(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.components.plot_config_components import PlotConfigComponents

        mock_st.text_input.side_effect = ["Title", "X", "Y"]

        result = PlotConfigComponents.render_title_labels_section(
            saved_config={},
            plot_id=1,
            include_legend_title=False,
        )

        assert "legend_title" not in result


# ===========================================================================
# BaseConverter
# ===========================================================================


class TestBaseConverterBranches:
    """Lines 68, 77, 98, 100, 102."""

    def _make_converter(self) -> Any:
        from src.web.pages.ui.plotting.export.converters.base_converter import BaseConverter

        class ConcreteConverter(BaseConverter):
            def convert(self, figure: go.Figure, format: str) -> Any:
                return None

        preset = MagicMock()
        return ConcreteConverter(preset)

    def test_get_supported_formats_empty(self) -> None:
        conv = self._make_converter()
        assert conv.get_supported_formats() == []

    def test_validate_empty_figure(self) -> None:
        conv = self._make_converter()
        fig = go.Figure()  # no traces
        assert conv.validate_figure(fig) is False

    def test_validate_with_x_data(self) -> None:
        conv = self._make_converter()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[1, 2], y=[3, 4]))
        assert conv.validate_figure(fig) is True

    def test_validate_trace_no_data(self) -> None:
        conv = self._make_converter()
        fig = go.Figure()
        fig.add_trace(go.Bar())  # no x, y, z, or values
        assert conv.validate_figure(fig) is False

    def test_validate_with_z_data(self) -> None:
        conv = self._make_converter()
        fig = go.Figure()
        fig.add_trace(go.Surface(z=[[1, 2], [3, 4]]))
        assert conv.validate_figure(fig) is True

    def test_validate_with_values_data(self) -> None:
        conv = self._make_converter()
        fig = go.Figure()
        fig.add_trace(go.Pie(values=[10, 20, 30]))
        assert conv.validate_figure(fig) is True


# ===========================================================================
# colors.py
# ===========================================================================


class TestColorsBranches:
    """Lines 61->71, 64-65, 73."""

    def test_get_palette_case_insensitive(self) -> None:
        from src.web.pages.ui.plotting.styles.colors import get_palette_colors

        # "plotly" (lowercase) should match "Plotly" (case-insensitive)
        result = get_palette_colors("plotly")
        assert len(result) > 0

    def test_get_palette_unknown_returns_default(self) -> None:
        from src.web.pages.ui.plotting.styles.colors import get_palette_colors

        result = get_palette_colors("NonExistentPaletteXYZ123")
        assert len(result) > 0  # Should return default

    def test_to_hex_rgb(self) -> None:
        from src.web.pages.ui.plotting.styles.colors import to_hex

        assert to_hex("rgb(255, 0, 0)") == "#ff0000"

    def test_to_hex_already_hex(self) -> None:
        from src.web.pages.ui.plotting.styles.colors import to_hex

        assert to_hex("#ff0000") == "#ff0000"

    def test_to_hex_non_string(self) -> None:
        from src.web.pages.ui.plotting.styles.colors import to_hex

        assert to_hex(123) == "#000000"  # type: ignore[arg-type]

    def test_to_hex_long_hex(self) -> None:
        from src.web.pages.ui.plotting.styles.colors import to_hex

        assert to_hex("#ff0000ff") == "#ff0000"
