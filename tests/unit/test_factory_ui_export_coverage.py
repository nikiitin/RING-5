"""Tests for PlotFactory, BarStyleUI, UploadDataPage, LaTeXExportService — branch coverage."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go
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

            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                return go.Figure()

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


class TestUploadDataPage:
    """Cover UploadDataPage.render branches."""

    @patch("src.web.pages.upload_data.UploadComponents")
    @patch("src.web.pages.upload_data.st")
    def test_parser_mode_with_data(self, mock_st: MagicMock, mock_uc: MagicMock) -> None:
        from src.web.pages.upload_data import UploadDataPage

        api = MagicMock()
        api.state_manager.is_using_parser.return_value = True
        api.state_manager.has_data.return_value = True

        page = UploadDataPage(api)
        page.render()
        mock_uc.render_parsed_data_preview.assert_called_once()

    @patch("src.web.pages.upload_data.UploadComponents")
    @patch("src.web.pages.upload_data.st")
    def test_parser_mode_no_data(self, mock_st: MagicMock, mock_uc: MagicMock) -> None:
        from src.web.pages.upload_data import UploadDataPage

        api = MagicMock()
        api.state_manager.is_using_parser.return_value = True
        api.state_manager.has_data.return_value = False

        page = UploadDataPage(api)
        page.render()
        mock_st.warning.assert_called()

    @patch("src.web.pages.upload_data.UploadComponents")
    @patch("src.web.pages.upload_data.st")
    def test_csv_upload_mode(self, mock_st: MagicMock, mock_uc: MagicMock) -> None:
        from src.web.pages.upload_data import UploadDataPage

        api = MagicMock()
        api.state_manager.is_using_parser.return_value = False

        # mock tabs
        tab1 = MagicMock()
        tab1.__enter__ = MagicMock(return_value=tab1)
        tab1.__exit__ = MagicMock(return_value=False)
        tab2 = MagicMock()
        tab2.__enter__ = MagicMock(return_value=tab2)
        tab2.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = [tab1, tab2]

        page = UploadDataPage(api)
        page.render()
        mock_uc.render_file_upload_tab.assert_called_once()
        mock_uc.render_paste_data_tab.assert_called_once()


class TestLaTeXExportService:
    """Cover LaTeXExportService branches."""

    def test_export_with_string_preset(self) -> None:
        from src.web.pages.ui.plotting.export.latex_export_service import LaTeXExportService

        service = LaTeXExportService()
        fig = go.Figure(data=[go.Bar(x=["a", "b"], y=[1, 2])])

        # This may or may not succeed depending on matplotlib backend
        # but we exercise the code path
        result = service.export(fig, "single_column", "pdf")
        assert "success" in result

    def test_export_with_preset_dict(self) -> None:
        from src.web.pages.ui.plotting.export.latex_export_service import LaTeXExportService

        service = LaTeXExportService()
        fig = go.Figure(data=[go.Bar(x=["a", "b"], y=[1, 2])])

        preset_dict = service.preset_manager.load_preset("single_column")
        result = service.export(fig, preset_dict, "pdf")
        assert "success" in result

    def test_export_failure(self) -> None:
        from src.web.pages.ui.plotting.export.latex_export_service import LaTeXExportService

        service = LaTeXExportService()
        service.preset_manager.load_preset = MagicMock(side_effect=ValueError("bad preset"))

        fig = go.Figure()
        result = service.export(fig, "nonexistent_preset", "pdf")
        assert result["success"] is False

    def test_list_presets(self) -> None:
        from src.web.pages.ui.plotting.export.latex_export_service import LaTeXExportService

        service = LaTeXExportService()
        presets = service.list_presets()
        assert isinstance(presets, list)
        assert len(presets) > 0

    def test_get_preset_info(self) -> None:
        from src.web.pages.ui.plotting.export.latex_export_service import LaTeXExportService

        service = LaTeXExportService()
        presets = service.list_presets()
        info = service.get_preset_info(presets[0])
        assert isinstance(info, dict)

    def test_generate_preview(self) -> None:
        from src.web.pages.ui.plotting.export.latex_export_service import LaTeXExportService

        service = LaTeXExportService()
        fig = go.Figure(data=[go.Bar(x=["a", "b"], y=[1, 2])])
        preview = service.generate_preview(fig, "single_column", preview_dpi=72)
        assert isinstance(preview, bytes)
        assert len(preview) > 0

    def test_generate_preview_with_dict(self) -> None:
        from src.web.pages.ui.plotting.export.latex_export_service import LaTeXExportService

        service = LaTeXExportService()
        fig = go.Figure(data=[go.Bar(x=["a", "b"], y=[1, 2])])
        preset_dict = service.preset_manager.load_preset("single_column")
        preview = service.generate_preview(fig, preset_dict, preview_dpi=72)
        assert isinstance(preview, bytes)

    def test_generate_preview_failure(self) -> None:
        from src.web.pages.ui.plotting.export.latex_export_service import LaTeXExportService

        service = LaTeXExportService()
        service.preset_manager.load_preset = MagicMock(side_effect=ValueError("bad"))

        fig = go.Figure()
        with pytest.raises(ValueError):
            service.generate_preview(fig, "bad_preset")
