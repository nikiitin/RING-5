"""Tests for PlotFactory and BarStyleUI — branch coverage."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestPlotFactory:
    """Cover PlotFactory branches."""

    def test_create_known_types(self) -> None:
        from src.web.pages.ui.plotting.plot_factory import PlotFactory

        known_types = [
            "bar",
            "line",
            "scatter",
            "grouped_bar",
            "stacked_bar",
            "grouped_stacked_bar",
            "histogram",
            "dual_axis_bar_dot",
        ]
        for plot_type in known_types:
            plot = PlotFactory.create_plot(plot_type, 1, "test")
            assert plot is not None

    def test_create_unknown_type_raises(self) -> None:
        from src.web.pages.ui.plotting.plot_factory import PlotFactory

        with pytest.raises(ValueError, match="Unknown plot type"):
            PlotFactory.create_plot("nonexistent", 1, "test")

    def test_register_and_create(self) -> None:
        from src.web.pages.ui.plotting.base_plot import BasePlot
        from src.web.pages.ui.plotting.plot_factory import PlotFactory

        class CustomPlot(BasePlot):
            def __init__(self, plot_id: int, name: str):
                super().__init__(plot_id, name, "custom")

            def render_config_ui(
                self, data: pd.DataFrame, saved_config: Dict[str, Any]
            ) -> Dict[str, Any]:
                return {}

            def create_traces(self, data: pd.DataFrame, config: Dict[str, Any]):
                from src.core.models.visualization.trace_build_result import TraceBuildResult

                return TraceBuildResult(traces=[])

            def get_legend_column(self, config: Dict[str, Any]) -> None:
                return None

        PlotFactory.register_plot_type("custom", CustomPlot)
        plot = PlotFactory.create_plot("custom", 1, "test_custom")
        assert plot is not None
        # Clean up
        del PlotFactory._plot_classes["custom"]

    def test_register_invalid_class_raises(self) -> None:
        from src.web.pages.ui.plotting.plot_factory import PlotFactory

        with pytest.raises(ValueError, match="subclass of BasePlot"):
            PlotFactory.register_plot_type("invalid", str)  # type: ignore


class TestBarStyleUI:
    """Cover BarStyleUI._render_specific_series_visuals."""

    @patch("src.web.pages.ui.plotting.styles.bar_ui.st")
    def test_render_with_string_pattern(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.plotting.styles.bar_ui import BarStyleUI

        ui = BarStyleUI(plot_id=1, plot_type="bar")
        mock_st.selectbox.return_value = "/"
        style: Dict[str, Any] = {"pattern": "/"}

        ui._render_specific_series_visuals(style, "trace_0")
        assert style["pattern"] == "/"

    @patch("src.web.pages.ui.plotting.styles.bar_ui.st")
    def test_render_with_dict_pattern(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.plotting.styles.bar_ui import BarStyleUI

        ui = BarStyleUI(plot_id=1, plot_type="bar")
        mock_st.selectbox.return_value = "x"
        style: Dict[str, Any] = {"pattern": {"shape": "x"}}

        ui._render_specific_series_visuals(style, "trace_0")
        assert style["pattern"] == "x"

    @patch("src.web.pages.ui.plotting.styles.bar_ui.st")
    def test_render_with_unknown_pattern(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.plotting.styles.bar_ui import BarStyleUI

        ui = BarStyleUI(plot_id=1, plot_type="bar")
        mock_st.selectbox.return_value = ""
        style: Dict[str, Any] = {"pattern": "unknown_pat"}

        ui._render_specific_series_visuals(style, "trace_0")
        assert style["pattern"] == ""
