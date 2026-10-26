"""Tests for stacked bars, histograms, and plot configuration components."""

from ring5 import Session
from ring5.errors import RenderError

from typing import Any, cast
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go
import pytest


def _columns_side_effect(*args: Any, **kwargs: Any) -> list[MagicMock]:
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
            "latency..0-9": [100, 200, 150, 250],
            "latency..10-19": [50, 60, 70, 80],
            "latency..0-9.sd": [5.0, 6.0, 7.0, 8.0],
            "group": ["g1", "g2", "g1", "g2"],
        }
    )


_STACKED_CFG = "src.web.components.plotting.config.stacked_bar_config"
_HIST_CFG = "src.web.components.plotting.config.histogram_config"


class TestStackedBarRenderConfigUI:
    """Tests for stacked-bar configuration controls."""

    @patch(f"{_STACKED_CFG}.PlotConfigComponents")
    @patch(f"{_STACKED_CFG}.detect_column_types")
    @patch(f"{_STACKED_CFG}.st")
    def test_render_config_ui_basic(
        self, mock_st: MagicMock, mock_detect: MagicMock, mock_pcc: MagicMock
    ) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        mock_detect.return_value = (["ipc", "cpi"], ["bench"])
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

    @patch(f"{_STACKED_CFG}.PlotConfigComponents")
    @patch(f"{_STACKED_CFG}.detect_column_types")
    @patch(f"{_STACKED_CFG}.st")
    def test_render_config_ui_with_saved(
        self, mock_st: MagicMock, mock_detect: MagicMock, mock_pcc: MagicMock
    ) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        mock_detect.return_value = (["ipc", "cpi"], ["bench"])
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
    """Tests for stacked-bar figure creation."""

    def test_empty_config_returns_placeholder(self, plot_session: Session) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        plot.processed_data = _sample_stacked_data()
        plot.config = {"x": None, "y_columns": []}
        fig = cast(go.Figure, plot_session.render(plot))
        layout = cast(Any, fig.layout)
        assert "Please select" in layout.title.text

    def test_basic_stacked(self, plot_session: Session) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        config: dict[str, Any] = {
            "x": "bench",
            "y_columns": ["ipc", "cpi"],
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "legend_title": "Stats",
        }
        plot.processed_data = _sample_stacked_data()
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        assert len(list(fig.data)) == 2
        layout = fig.layout
        assert layout.barmode == "stack"

    def test_with_error_bars_and_styles(self, plot_session: Session) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        config: dict[str, Any] = {
            "x": "bench",
            "y_columns": ["ipc"],
            "show_error_bars": True,
            "series_styles": {"ipc": {"color": "#ff0000", "use_color": True, "pattern": "/"}},
            "legend_labels": {"ipc": "IPC"},
        }
        plot.processed_data = _sample_stacked_data()
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        assert len(list(fig.data)) == 1
        trace0 = cast(go.Bar, fig.data[0])
        assert trace0.error_y is not None
        marker = cast(Any, trace0.marker)
        assert marker.color == "#ff0000"

    def test_with_x_filter(self, plot_session: Session) -> None:
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        config: dict[str, Any] = {
            "x": "bench",
            "y_columns": ["ipc"],
            "x_filter": ["A"],
        }
        plot.processed_data = _sample_stacked_data()
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        trace0_x = cast(go.Bar, fig.data[0]).x
        assert trace0_x is not None
        assert len(list(trace0_x)) == 1

    def test_show_totals_annotations(self, plot_session: Session) -> None:
        # [test->req~ring5.figure.stack-totals~1]
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        config: dict[str, Any] = {
            "x": "bench",
            "y_columns": ["ipc", "cpi"],
            "show_totals": True,
            "total_threshold": 0.0,
        }
        plot.processed_data = _sample_stacked_data()
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        layout = fig.layout
        annotations = cast("tuple[Any, ...]", layout.annotations)
        assert annotations is not None
        assert len(annotations) == 3

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

    def test_totals_threshold_skips_small(self, plot_session: Session) -> None:
        # [test->req~ring5.figure.stack-totals~1]
        from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot

        plot = StackedBarPlot(plot_id=1, name="test")
        config: dict[str, Any] = {
            "x": "bench",
            "y_columns": ["ipc"],
            "show_totals": True,
            "total_threshold": 100.0,  # All values below threshold
        }
        plot.processed_data = _sample_stacked_data()
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        layout = fig.layout
        annotations = cast("tuple[Any, ...]", layout.annotations)
        assert len(annotations) == 0


class TestHistogramRenderConfigUI:
    """Tests for histogram configuration controls."""

    # [test->req~ring5.figure.histogram-controls~1]

    @patch(f"{_HIST_CFG}.render_common_config")
    @patch(f"{_HIST_CFG}.st")
    def test_no_histogram_vars_detected(self, mock_st: MagicMock, mock_common: MagicMock) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        # No ".." columns → no histogram variables
        df = pd.DataFrame({"a": [1], "b": [2]})

        mock_common.return_value = {
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
        }

        result = plot.render_config_ui(df, {})

        assert result["histogram_variable"] is None
        mock_st.warning.assert_called()


class TestHistogramCreateFigure:
    """Tests for histogram figure creation."""

    # [test->req~ring5.figure.histogram-controls~1]

    def test_no_histogram_var_raises(self, plot_session: Session) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        with pytest.raises(RenderError, match="No histogram variable"):
            plot.processed_data = _sample_histogram_data()
            plot.config = {"histogram_variable": None}
            cast(go.Figure, plot_session.render(plot))

    def test_no_bucket_cols_raises(self, plot_session: Session) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(RenderError, match="No histogram bucket columns"):
            plot.processed_data = df
            plot.config = {"histogram_variable": "latency"}
            cast(go.Figure, plot_session.render(plot))

    def test_single_histogram(self, plot_session: Session) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        config: dict[str, Any] = {
            "histogram_variable": "latency",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "normalization": "count",
            "cumulative": False,
        }
        plot.processed_data = _sample_histogram_data()
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        assert len(list(fig.data)) == 1

    def test_grouped_histogram(self, plot_session: Session) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        config: dict[str, Any] = {
            "histogram_variable": "latency",
            "group_by": "group",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "normalization": "count",
            "cumulative": False,
        }
        plot.processed_data = _sample_histogram_data()
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        assert len(list(fig.data)) == 2  # g1 and g2

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
        vals = plot._normalize_values([10.0, 20.0], {"normalization": "density"}, widths=[5.0, 5.0])
        total = sum([10.0, 20.0])
        expected = [10.0 / (total * 5), 20.0 / (total * 5)]
        assert vals == pytest.approx(expected)

    def test_normalization_cumulative(self) -> None:
        # [test->req~ring5.figure.histogram-cumulative~1]
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

    def test_detect_histogram_variables(self) -> None:
        from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

        plot = HistogramPlot(plot_id=1, name="test")
        detected = plot._detect_histogram_variables(_sample_histogram_data())
        assert "latency" in detected


class TestPlotConfigComponents:
    """Tests for shared plot configuration controls."""

    @patch("src.web.components.plotting.config.plot_config_components.st")
    def test_filter_mapping_change_selects_values_from_new_column(self, mock_st: MagicMock) -> None:
        # [test->req~ring5.figure.plot-filtering~1]
        from src.web.components.plotting.config.plot_config_components import (
            PlotConfigComponents,
        )

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.session_state = {}
        mock_st.multiselect.side_effect = lambda _label, **kwargs: mock_st.session_state.get(
            kwargs["key"], kwargs.get("default", [])
        )
        df = pd.DataFrame(
            {
                "benchmark_name": ["mcf", "omnetpp"],
                "config_description": ["baseline", "optimized"],
            }
        )

        _x_values, group_values = PlotConfigComponents.render_filter_multiselects(
            data=df,
            x_col="benchmark_name",
            group_col="config_description",
            saved_config={"group": None, "group_filter": []},
            plot_id=4,
        )

        assert group_values == ["baseline", "optimized"]
        assert mock_st.session_state["plot.4.widgets.group_filter_column"] == "config_description"
        assert mock_st.session_state["plot.4.widgets.group_filter"] == ["baseline", "optimized"]

    @patch("src.web.components.plotting.config.plot_config_components.st")
    def test_filter_no_group_col(self, mock_st: MagicMock) -> None:
        from src.web.components.plotting.config.plot_config_components import (
            PlotConfigComponents,
        )

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.multiselect.return_value = ["A"]

        df = pd.DataFrame({"x": ["A", "B"]})
        x_vals, g_vals = PlotConfigComponents.render_filter_multiselects(
            data=df, x_col="x", group_col=None, saved_config={}, plot_id=1
        )

        assert x_vals == ["A"]
        assert g_vals == []

    @patch("src.web.components.plotting.config.plot_config_components.st")
    def test_filter_x_col_not_in_data(self, mock_st: MagicMock) -> None:
        from src.web.components.plotting.config.plot_config_components import (
            PlotConfigComponents,
        )

        mock_st.columns.side_effect = _columns_side_effect

        df = pd.DataFrame({"a": [1]})
        x_vals, g_vals = PlotConfigComponents.render_filter_multiselects(
            data=df, x_col="missing", group_col=None, saved_config={}, plot_id=1
        )

        assert x_vals == []
        assert g_vals == []

    @patch("src.web.components.plotting.config.plot_config_components.st")
    def test_statistics_multiselect_fallback_2_cols(self, mock_st: MagicMock) -> None:
        from src.web.components.plotting.config.plot_config_components import (
            PlotConfigComponents,
        )

        mock_st.multiselect.return_value = ["a", "b"]

        result = PlotConfigComponents.render_statistics_multiselect(
            numeric_cols=["a", "b", "c"],
            saved_config={},  # no y_columns → triggers fallback
            plot_id=1,
        )

        assert result == ["a", "b"]

    @patch("src.web.components.plotting.config.plot_config_components.st")
    def test_statistics_multiselect_fallback_1_col(self, mock_st: MagicMock) -> None:
        from src.web.components.plotting.config.plot_config_components import (
            PlotConfigComponents,
        )

        mock_st.multiselect.return_value = ["a"]

        result = PlotConfigComponents.render_statistics_multiselect(
            numeric_cols=["a"],  # only 1 column
            saved_config={},
            plot_id=1,
        )

        assert result == ["a"]

    @patch("src.web.components.plotting.config.plot_config_components.st")
    def test_title_labels_with_legend_title(self, mock_st: MagicMock) -> None:
        from src.web.components.plotting.config.plot_config_components import (
            PlotConfigComponents,
        )

        mock_st.text_input.side_effect = ["Title", "X", "Y", "Legend"]

        result = PlotConfigComponents.render_title_labels_section(
            saved_config={},
            plot_id=1,
            include_legend_title=True,
            default_legend_title="LT",
        )

        assert result["legend_title"] == "Legend"

    @patch("src.web.components.plotting.config.plot_config_components.st")
    def test_title_labels_without_legend_title(self, mock_st: MagicMock) -> None:
        from src.web.components.plotting.config.plot_config_components import (
            PlotConfigComponents,
        )

        mock_st.text_input.side_effect = ["Title", "X", "Y"]

        result = PlotConfigComponents.render_title_labels_section(
            saved_config={},
            plot_id=1,
            include_legend_title=False,
        )

        assert "legend_title" not in result

    @patch("src.web.components.plotting.config.plot_config_components.st")
    def test_title_labels_reuse_session_state_without_widget_defaults(
        self, mock_st: MagicMock
    ) -> None:
        from src.web.components.plotting.config.plot_config_components import (
            PlotConfigComponents,
        )

        mock_st.session_state = {
            "plot.7.widgets.title": "Updated title",
            "plot.7.widgets.xlabel": "Updated X",
            "plot.7.widgets.ylabel": "Updated Y",
        }
        mock_st.text_input.side_effect = lambda _label, **kwargs: mock_st.session_state[
            kwargs["key"]
        ]

        result = PlotConfigComponents.render_title_labels_section(
            saved_config={"title": "Old title"},
            plot_id=7,
        )

        assert result == {
            "title": "Updated title",
            "xlabel": "Updated X",
            "ylabel": "Updated Y",
        }
        assert all("value" not in call.kwargs for call in mock_st.text_input.call_args_list)


class TestColors:
    """Tests for color palette lookup and conversion."""

    def test_picker_hex_rgb(self) -> None:
        from src.web.rendering._color_utils import picker_hex_color

        assert picker_hex_color("rgb(255, 0, 0)") == "#ff0000"

    def test_picker_hex_already_hex(self) -> None:
        from src.web.rendering._color_utils import picker_hex_color

        assert picker_hex_color("#ff0000") == "#ff0000"

    def test_picker_hex_non_string(self) -> None:
        from src.web.rendering._color_utils import picker_hex_color

        with pytest.raises(ValueError, match="CSS text"):
            picker_hex_color(123)  # type: ignore[arg-type]

    def test_picker_hex_long_hex(self) -> None:
        from src.web.rendering._color_utils import picker_hex_color

        assert picker_hex_color("#ff0000ff") == "#ff0000"
