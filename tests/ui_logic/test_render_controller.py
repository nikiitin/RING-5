"""Tests for PlotRenderController — config gathering and chart display.

Verifies that the controller correctly orchestrates:
    - No-data guard (early return with warning)
    - Plot type selector + type change delegation
    - Config gathering via ConfigPresenter (type-specific, advanced, theme)
    - Config change detection
    - Refresh controls and auto-refresh toggle
    - Chart display delegation
    - Error resilience (config errors don't crash the flow)
"""

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pandas as pd

from tests.ui_logic.conftest import StubPlotHandle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_render_controller(
    api: Optional[MagicMock] = None,
    ui_state: Optional[MagicMock] = None,
    lifecycle: Optional[MagicMock] = None,
    registry: Optional[MagicMock] = None,
    chart_display: Optional[MagicMock] = None,
) -> Any:
    """Build a PlotRenderController with sane mock defaults."""
    from src.web.controllers.plot.render_controller import PlotRenderController

    api = api or MagicMock()
    ui_state = ui_state or MagicMock()
    ui_state.plot.get_auto_refresh.return_value = True

    lifecycle = lifecycle or MagicMock()
    registry = registry or MagicMock()
    registry.get_available_types.return_value = ["bar", "line", "scatter"]
    chart_display = chart_display or MagicMock()

    return PlotRenderController(api, ui_state, lifecycle, registry, chart_display)


def _default_type_result(type_changed: bool = False) -> Dict[str, Any]:
    """Default type selector result."""
    return {"new_type": None, "type_changed": type_changed}


def _default_refresh_controls(
    should_generate: bool = True,
    auto_refresh: bool = True,
) -> Dict[str, Any]:
    """Default refresh controls result."""
    return {
        "auto_refresh": auto_refresh,
        "manual_refresh": False,
        "should_generate": should_generate,
    }


# ---------------------------------------------------------------------------
# No-data guard
# ---------------------------------------------------------------------------
class TestNoDataGuard:
    """When processed_data is None, only a warning is shown."""

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_no_data_warning")
    def test_no_data_shows_warning(self, mock_warn: MagicMock, mock_st: MagicMock) -> None:
        """Controller calls render_no_data_warning and returns early."""
        plot = StubPlotHandle(processed_data=None)
        ctrl = _make_render_controller()
        ctrl.render(plot)

        mock_warn.assert_called_once()

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_no_data_warning")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_section_headers")
    def test_no_data_skips_rest_of_flow(
        self, mock_headers: MagicMock, mock_warn: MagicMock, mock_st: MagicMock
    ) -> None:
        """When no data, section headers are NOT rendered."""
        plot = StubPlotHandle(processed_data=None)
        ctrl = _make_render_controller()
        ctrl.render(plot)

        mock_headers.assert_not_called()


# ---------------------------------------------------------------------------
# Type selector and type change
# ---------------------------------------------------------------------------
class TestTypeSelector:
    """Plot type selector rendering and type change delegation."""

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ChartPresenter.render_refresh_controls")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_advanced_and_theme")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_type_config")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_plot_type_selector")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_section_headers")
    def test_type_selector_called_with_correct_args(
        self,
        mock_headers: MagicMock,
        mock_type_sel: MagicMock,
        mock_type_cfg: MagicMock,
        mock_adv: MagicMock,
        mock_refresh: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Type selector receives plot_type, available_types, and plot_id."""
        mock_type_sel.return_value = _default_type_result()
        mock_type_cfg.return_value = {}
        mock_adv.return_value = {}
        mock_refresh.return_value = _default_refresh_controls()

        data = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        plot = StubPlotHandle(plot_id=42, plot_type="grouped_bar", processed_data=data)
        ctrl = _make_render_controller()
        ctrl.render(plot)

        mock_type_sel.assert_called_once_with(
            plot_type="grouped_bar",
            available_types=["bar", "line", "scatter"],
            plot_id=42,
        )

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_plot_type_selector")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_section_headers")
    def test_type_change_delegates_to_lifecycle(
        self,
        mock_headers: MagicMock,
        mock_type_sel: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """When type_changed=True, lifecycle.change_plot_type + rerun."""
        mock_type_sel.return_value = {
            "new_type": "line",
            "type_changed": True,
        }

        data = pd.DataFrame({"x": [1]})
        plot = StubPlotHandle(plot_type="bar", processed_data=data)
        lifecycle = MagicMock()
        api = MagicMock()
        ctrl = _make_render_controller(api=api, lifecycle=lifecycle)
        ctrl.render(plot)

        lifecycle.change_plot_type.assert_called_once_with(plot, "line", api.state_manager)
        mock_st.rerun.assert_called_once()


# ---------------------------------------------------------------------------
# Config gathering
# ---------------------------------------------------------------------------
class TestConfigGathering:
    """Verify config is gathered from ConfigPresenter and merged."""

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ChartPresenter.render_refresh_controls")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_advanced_and_theme")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_type_config")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_plot_type_selector")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_section_headers")
    def test_config_merges_type_and_advanced(
        self,
        mock_headers: MagicMock,
        mock_type_sel: MagicMock,
        mock_type_cfg: MagicMock,
        mock_adv: MagicMock,
        mock_refresh: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Config from type_config and advanced_and_theme is merged onto plot."""
        mock_type_sel.return_value = _default_type_result()
        mock_type_cfg.return_value = {"x_col": "time", "y_col": "value"}
        mock_adv.return_value = {"title": "My Chart", "legend": True}
        mock_refresh.return_value = _default_refresh_controls(should_generate=True)

        data = pd.DataFrame({"time": [1], "value": [2]})
        plot = StubPlotHandle(processed_data=data, config={})
        chart = MagicMock()
        ctrl = _make_render_controller(chart_display=chart)
        ctrl.render(plot)

        # The final config on the plot should contain both sets of keys
        assert plot.config["x_col"] == "time"
        assert plot.config["y_col"] == "value"
        assert plot.config["title"] == "My Chart"
        assert plot.config["legend"] is True


# ---------------------------------------------------------------------------
# Config change detection + refresh
# ---------------------------------------------------------------------------
class TestRefreshLogic:
    """Auto-refresh and manual refresh controls."""

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ChartPresenter.render_refresh_controls")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_advanced_and_theme")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_type_config")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_plot_type_selector")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_section_headers")
    def test_chart_display_called_with_should_generate(
        self,
        mock_headers: MagicMock,
        mock_type_sel: MagicMock,
        mock_type_cfg: MagicMock,
        mock_adv: MagicMock,
        mock_refresh: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """ChartDisplay.render_chart receives (plot, should_generate)."""
        mock_type_sel.return_value = _default_type_result()
        mock_type_cfg.return_value = {}
        mock_adv.return_value = {}
        mock_refresh.return_value = _default_refresh_controls(should_generate=True)

        data = pd.DataFrame({"a": [1]})
        plot = StubPlotHandle(processed_data=data, config={})
        chart = MagicMock()
        ctrl = _make_render_controller(chart_display=chart)
        ctrl.render(plot)

        chart.render_chart.assert_called_once_with(plot, True)

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ChartPresenter.render_refresh_controls")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_advanced_and_theme")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_type_config")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_plot_type_selector")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_section_headers")
    def test_no_generate_when_should_generate_false(
        self,
        mock_headers: MagicMock,
        mock_type_sel: MagicMock,
        mock_type_cfg: MagicMock,
        mock_adv: MagicMock,
        mock_refresh: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """ChartDisplay gets should_generate=False when controls say so."""
        mock_type_sel.return_value = _default_type_result()
        mock_type_cfg.return_value = {}
        mock_adv.return_value = {}
        mock_refresh.return_value = _default_refresh_controls(should_generate=False)

        data = pd.DataFrame({"a": [1]})
        plot = StubPlotHandle(processed_data=data, config={})
        chart = MagicMock()
        ctrl = _make_render_controller(chart_display=chart)
        ctrl.render(plot)

        chart.render_chart.assert_called_once_with(plot, False)

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ChartPresenter.render_refresh_controls")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_advanced_and_theme")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_type_config")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_plot_type_selector")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_section_headers")
    def test_auto_refresh_stored_in_ui_state(
        self,
        mock_headers: MagicMock,
        mock_type_sel: MagicMock,
        mock_type_cfg: MagicMock,
        mock_adv: MagicMock,
        mock_refresh: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Auto-refresh toggle value is persisted to UI state."""
        mock_type_sel.return_value = _default_type_result()
        mock_type_cfg.return_value = {}
        mock_adv.return_value = {}
        mock_refresh.return_value = _default_refresh_controls(auto_refresh=False)

        data = pd.DataFrame({"a": [1]})
        plot = StubPlotHandle(plot_id=10, processed_data=data, config={})
        ui_state = MagicMock()
        ui_state.plot.get_auto_refresh.return_value = True
        ctrl = _make_render_controller(ui_state=ui_state)
        ctrl.render(plot)

        ui_state.plot.set_auto_refresh.assert_called_once_with(10, False)


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------
class TestErrorResilience:
    """Config errors don't crash the controller flow."""

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ChartPresenter.render_refresh_controls")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_advanced_and_theme")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_type_config")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_plot_type_selector")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_section_headers")
    def test_type_config_error_shows_st_error(
        self,
        mock_headers: MagicMock,
        mock_type_sel: MagicMock,
        mock_type_cfg: MagicMock,
        mock_adv: MagicMock,
        mock_refresh: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """If render_type_config raises, st.error is called; flow continues."""
        mock_type_sel.return_value = _default_type_result()
        mock_type_cfg.side_effect = ValueError("bad column")
        mock_adv.return_value = {}
        mock_refresh.return_value = _default_refresh_controls(should_generate=True)

        data = pd.DataFrame({"a": [1]})
        plot = StubPlotHandle(processed_data=data, config={})
        chart = MagicMock()
        ctrl = _make_render_controller(chart_display=chart)
        ctrl.render(plot)

        mock_st.error.assert_called_once()
        # should_generate is blocked by config_error
        chart.render_chart.assert_called_once_with(plot, False)

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ChartPresenter.render_refresh_controls")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_advanced_and_theme")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_type_config")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_plot_type_selector")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_section_headers")
    def test_advanced_config_error_shows_st_error(
        self,
        mock_headers: MagicMock,
        mock_type_sel: MagicMock,
        mock_type_cfg: MagicMock,
        mock_adv: MagicMock,
        mock_refresh: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """If render_advanced_and_theme raises, st.error is called."""
        mock_type_sel.return_value = _default_type_result()
        mock_type_cfg.return_value = {"x": "a"}
        mock_adv.side_effect = TypeError("wrong type")
        mock_refresh.return_value = _default_refresh_controls(should_generate=True)

        data = pd.DataFrame({"a": [1]})
        plot = StubPlotHandle(processed_data=data, config={})
        chart = MagicMock()
        ctrl = _make_render_controller(chart_display=chart)
        ctrl.render(plot)

        mock_st.error.assert_called_once()
        chart.render_chart.assert_called_once_with(plot, False)

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ChartPresenter.render_refresh_controls")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_advanced_and_theme")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_type_config")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_plot_type_selector")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter.render_section_headers")
    def test_both_config_errors_block_generation(
        self,
        mock_headers: MagicMock,
        mock_type_sel: MagicMock,
        mock_type_cfg: MagicMock,
        mock_adv: MagicMock,
        mock_refresh: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Two config errors still result in should_generate=False."""
        mock_type_sel.return_value = _default_type_result()
        mock_type_cfg.side_effect = RuntimeError("err1")
        mock_adv.side_effect = RuntimeError("err2")
        mock_refresh.return_value = _default_refresh_controls(should_generate=True)

        data = pd.DataFrame({"a": [1]})
        plot = StubPlotHandle(processed_data=data, config={})
        chart = MagicMock()
        ctrl = _make_render_controller(chart_display=chart)
        ctrl.render(plot)

        assert mock_st.error.call_count == 2
        chart.render_chart.assert_called_once_with(plot, False)
