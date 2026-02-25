"""Tests for PlotRenderController — config gathering and chart display.

Verifies that the controller correctly orchestrates:
    - No-data guard (early return with warning)
    - Plot type selector + type change delegation
    - Config gathering (type-specific via plot, advanced via inline)
    - Config change detection
    - Refresh controls and auto-refresh toggle
    - Visualization delegation (figure generation + chart display)
    - Error resilience (config errors don't crash the flow)
"""

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pandas as pd

from tests.ui_logic.conftest import StubPlotHandle

_CTRL = "src.web.controllers.plot.render_controller"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_render_controller(
    api: Optional[MagicMock] = None,
    ui_state: Optional[MagicMock] = None,
    lifecycle: Optional[MagicMock] = None,
    registry: Optional[MagicMock] = None,
) -> Any:
    """Build a PlotRenderController with sane mock defaults."""
    from src.web.controllers.plot.render_controller import PlotRenderController

    api = api or MagicMock()
    ui_state = ui_state or MagicMock()
    ui_state.plot.get_auto_refresh.return_value = True

    lifecycle = lifecycle or MagicMock()
    registry = registry or MagicMock()
    registry.get_available_types.return_value = ["bar", "line", "scatter"]

    return PlotRenderController(api, ui_state, lifecycle, registry)


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

    @patch(f"{_CTRL}.render_settings_pills")
    @patch(f"{_CTRL}.st")
    def test_no_data_shows_warning(self, mock_st: MagicMock, mock_pills: MagicMock) -> None:
        """Controller calls st.warning and returns early."""
        plot = StubPlotHandle(processed_data=None)
        ctrl = _make_render_controller()
        ctrl.render(plot)

        mock_st.warning.assert_called_once_with("No processed data available.")

    @patch(f"{_CTRL}.render_settings_pills")
    @patch(f"{_CTRL}.st")
    def test_no_data_skips_rest_of_flow(self, mock_st: MagicMock, mock_pills: MagicMock) -> None:
        """When no data, st.markdown (section headers) is NOT called."""
        plot = StubPlotHandle(processed_data=None)
        ctrl = _make_render_controller()
        ctrl.render(plot)

        mock_st.markdown.assert_not_called()


# ---------------------------------------------------------------------------
# Type selector and type change
# ---------------------------------------------------------------------------
class TestTypeSelector:
    """Plot type selector rendering and type change delegation."""

    @patch(f"{_CTRL}.PlotRenderController._render_visualization")
    @patch(f"{_CTRL}.ChartDisplayComponent.render_refresh_controls")
    @patch(f"{_CTRL}.render_settings_pills")
    @patch(f"{_CTRL}.st")
    def test_type_selector_called_with_correct_args(
        self,
        mock_st: MagicMock,
        mock_pills: MagicMock,
        mock_refresh: MagicMock,
        mock_viz: MagicMock,
    ) -> None:
        """st.selectbox for plot type is rendered with correct options."""
        mock_st.selectbox.return_value = "grouped_bar"  # no change
        mock_st.toggle.return_value = False
        mock_pills.return_value = None
        mock_refresh.return_value = _default_refresh_controls()

        data = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        plot = StubPlotHandle(plot_id=42, plot_type="grouped_bar", processed_data=data)
        ctrl = _make_render_controller()
        ctrl.render(plot)

        mock_st.selectbox.assert_called_once_with(
            "Plot Type",
            options=["bar", "line", "scatter"],
            index=0,  # grouped_bar not in list, defaults to 0
            key="plot_type_sel_42",
        )

    @patch(f"{_CTRL}.render_settings_pills")
    @patch(f"{_CTRL}.st")
    def test_type_change_delegates_to_lifecycle(
        self,
        mock_st: MagicMock,
        mock_pills: MagicMock,
    ) -> None:
        """When selectbox returns a different type, lifecycle.change_plot_type + rerun."""
        mock_st.selectbox.return_value = "line"
        mock_st.toggle.return_value = False
        mock_pills.return_value = None

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
    """Verify config is gathered from plot methods and merged."""

    @patch(f"{_CTRL}.PlotRenderController._render_visualization")
    @patch(f"{_CTRL}.ChartDisplayComponent.render_refresh_controls")
    @patch(f"{_CTRL}.render_settings_pills")
    @patch(f"{_CTRL}.st")
    def test_config_merges_type_and_advanced(
        self,
        mock_st: MagicMock,
        mock_pills: MagicMock,
        mock_refresh: MagicMock,
        mock_viz: MagicMock,
    ) -> None:
        """Config from render_config_ui and render_settings_section is merged."""
        mock_st.selectbox.return_value = "bar"  # no type change
        mock_st.toggle.return_value = False
        mock_pills.return_value = None
        mock_refresh.return_value = _default_refresh_controls(should_generate=True)

        data = pd.DataFrame({"time": [1], "value": [2]})
        plot = StubPlotHandle(processed_data=data, config={})
        # Override render_config_ui to return specific config
        plot.render_config_ui = lambda d, c: {"x_col": "time", "y_col": "value"}
        plot.render_settings_section = lambda s, c, d=None: {"title": "My Chart", "legend": True}
        ctrl = _make_render_controller()
        ctrl.render(plot)

        assert plot.config["x_col"] == "time"
        assert plot.config["y_col"] == "value"
        assert plot.config["title"] == "My Chart"
        assert plot.config["legend"] is True


# ---------------------------------------------------------------------------
# Config change detection + refresh
# ---------------------------------------------------------------------------
class TestRefreshLogic:
    """Auto-refresh and manual refresh controls."""

    @patch(f"{_CTRL}.PlotRenderController._render_visualization")
    @patch(f"{_CTRL}.ChartDisplayComponent.render_refresh_controls")
    @patch(f"{_CTRL}.render_settings_pills")
    @patch(f"{_CTRL}.st")
    def test_visualization_called_with_should_generate(
        self,
        mock_st: MagicMock,
        mock_pills: MagicMock,
        mock_refresh: MagicMock,
        mock_viz: MagicMock,
    ) -> None:
        """_render_visualization receives (plot, should_generate=True)."""
        mock_st.selectbox.return_value = "bar"
        mock_st.toggle.return_value = False
        mock_pills.return_value = None
        mock_refresh.return_value = _default_refresh_controls(should_generate=True)

        data = pd.DataFrame({"a": [1]})
        plot = StubPlotHandle(processed_data=data, config={})
        ctrl = _make_render_controller()
        ctrl.render(plot)

        mock_viz.assert_called_once_with(plot, True)

    @patch(f"{_CTRL}.PlotRenderController._render_visualization")
    @patch(f"{_CTRL}.ChartDisplayComponent.render_refresh_controls")
    @patch(f"{_CTRL}.render_settings_pills")
    @patch(f"{_CTRL}.st")
    def test_no_generate_when_should_generate_false(
        self,
        mock_st: MagicMock,
        mock_pills: MagicMock,
        mock_refresh: MagicMock,
        mock_viz: MagicMock,
    ) -> None:
        """_render_visualization gets should_generate=False when controls say so."""
        mock_st.selectbox.return_value = "bar"
        mock_st.toggle.return_value = False
        mock_pills.return_value = None
        mock_refresh.return_value = _default_refresh_controls(should_generate=False)

        data = pd.DataFrame({"a": [1]})
        plot = StubPlotHandle(processed_data=data, config={})
        ctrl = _make_render_controller()
        ctrl.render(plot)

        mock_viz.assert_called_once_with(plot, False)

    @patch(f"{_CTRL}.PlotRenderController._render_visualization")
    @patch(f"{_CTRL}.ChartDisplayComponent.render_refresh_controls")
    @patch(f"{_CTRL}.render_settings_pills")
    @patch(f"{_CTRL}.st")
    def test_auto_refresh_stored_in_ui_state(
        self,
        mock_st: MagicMock,
        mock_pills: MagicMock,
        mock_refresh: MagicMock,
        mock_viz: MagicMock,
    ) -> None:
        """Auto-refresh toggle value is persisted to UI state."""
        mock_st.selectbox.return_value = "bar"
        mock_st.toggle.return_value = False
        mock_pills.return_value = None
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

    @patch(f"{_CTRL}.PlotRenderController._render_visualization")
    @patch(f"{_CTRL}.ChartDisplayComponent.render_refresh_controls")
    @patch(f"{_CTRL}.render_settings_pills")
    @patch(f"{_CTRL}.st")
    def test_type_config_error_shows_st_exception(
        self,
        mock_st: MagicMock,
        mock_pills: MagicMock,
        mock_refresh: MagicMock,
        mock_viz: MagicMock,
    ) -> None:
        """If render_config_ui raises, st.exception is called; flow continues."""
        mock_st.selectbox.return_value = "bar"
        mock_st.toggle.return_value = False
        mock_pills.return_value = None
        mock_refresh.return_value = _default_refresh_controls(should_generate=True)

        data = pd.DataFrame({"a": [1]})
        plot = StubPlotHandle(processed_data=data, config={})
        plot.render_config_ui = MagicMock(side_effect=ValueError("bad column"))
        ctrl = _make_render_controller()
        ctrl.render(plot)

        mock_st.exception.assert_called_once()
        mock_viz.assert_called_once_with(plot, False)

    @patch(f"{_CTRL}.PlotRenderController._render_visualization")
    @patch(f"{_CTRL}.ChartDisplayComponent.render_refresh_controls")
    @patch(f"{_CTRL}.render_settings_pills")
    @patch(f"{_CTRL}.st")
    def test_advanced_config_error_shows_st_exception(
        self,
        mock_st: MagicMock,
        mock_pills: MagicMock,
        mock_refresh: MagicMock,
        mock_viz: MagicMock,
    ) -> None:
        """If render_settings_section raises, st.exception is called."""
        mock_st.selectbox.return_value = "bar"
        mock_st.toggle.return_value = False
        mock_pills.return_value = None
        mock_refresh.return_value = _default_refresh_controls(should_generate=True)

        data = pd.DataFrame({"a": [1]})
        plot = StubPlotHandle(processed_data=data, config={})
        plot.render_settings_section = MagicMock(side_effect=TypeError("wrong type"))
        ctrl = _make_render_controller()
        ctrl.render(plot)

        mock_st.exception.assert_called_once()
        mock_viz.assert_called_once_with(plot, False)

    @patch(f"{_CTRL}.PlotRenderController._render_visualization")
    @patch(f"{_CTRL}.ChartDisplayComponent.render_refresh_controls")
    @patch(f"{_CTRL}.render_settings_pills")
    @patch(f"{_CTRL}.st")
    def test_both_config_errors_block_generation(
        self,
        mock_st: MagicMock,
        mock_pills: MagicMock,
        mock_refresh: MagicMock,
        mock_viz: MagicMock,
    ) -> None:
        """Two config errors still result in should_generate=False."""
        mock_st.selectbox.return_value = "bar"
        mock_st.toggle.return_value = False
        mock_pills.return_value = None
        mock_refresh.return_value = _default_refresh_controls(should_generate=True)

        data = pd.DataFrame({"a": [1]})
        plot = StubPlotHandle(processed_data=data, config={})
        plot.render_config_ui = MagicMock(side_effect=RuntimeError("err1"))
        plot.render_settings_section = MagicMock(side_effect=RuntimeError("err2"))
        ctrl = _make_render_controller()
        ctrl.render(plot)

        assert mock_st.exception.call_count == 2
        mock_viz.assert_called_once_with(plot, False)
