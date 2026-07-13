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

from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd

from tests.ui_logic.conftest import StubPlotHandle

_CTRL = "src.web.controllers.plot.render_controller"


# Helpers
def _make_render_controller(
    api: MagicMock | None = None,
    ui_state: MagicMock | None = None,
    lifecycle: MagicMock | None = None,
    registry: MagicMock | None = None,
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
) -> dict[str, Any]:
    """Default refresh controls result."""
    return {
        "auto_refresh": auto_refresh,
        "manual_refresh": False,
        "should_generate": should_generate,
    }


# No-data guard
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


# Type selector and type change
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


# Config gathering
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
        plot.render_config_ui = lambda data, config: {"x_col": "time", "y_col": "value"}
        plot.render_settings_section = lambda section, saved_config, data=None: {
            "title": "My Chart",
            "legend": True,
        }
        ctrl = _make_render_controller()
        ctrl.render(plot)

        assert plot.config["x_col"] == "time"
        assert plot.config["y_col"] == "value"
        assert plot.config["title"] == "My Chart"
        assert plot.config["legend"] is True


# Config change detection + refresh
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


# Error resilience
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


class TestFigureIdentity:
    """Figure reuse is limited to identical data, config, and engine."""

    def test_middle_row_changes_data_hash(self) -> None:
        """The fingerprint covers rows beyond the frame boundaries."""
        from src.web.controllers.plot.render_controller import PlotRenderController

        first = pd.DataFrame({"value": [1, 2, 3]})
        second = pd.DataFrame({"value": [1, 999, 3]})

        assert PlotRenderController._compute_data_hash(
            first
        ) != PlotRenderController._compute_data_hash(second)

    def test_unhashable_object_values_are_fingerprinted(self) -> None:
        """Container-valued cells use the deterministic serialization fallback."""
        from src.web.controllers.plot.render_controller import PlotRenderController

        data = pd.DataFrame({"value": [[1, 2], {"key": "value"}]})

        assert len(PlotRenderController._compute_data_hash(data)) == 12

    @patch(f"{_CTRL}.EngineManager")
    @patch(f"{_CTRL}.ChartDisplayComponent")
    def test_identical_render_reuses_figure(
        self,
        mock_chart: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """An unchanged render does not call the figure builder again."""
        mock_engine.get_engine.return_value = "plotly"
        mock_chart.render_engine_selector.return_value = "plotly"
        plot = StubPlotHandle(processed_data=pd.DataFrame({"value": [1, 2, 3]}))
        plot.create_figure = MagicMock(return_value=MagicMock())
        ctrl = _make_render_controller()

        ctrl._render_visualization(plot, should_generate=False)
        ctrl._render_visualization(plot, should_generate=False)

        plot.create_figure.assert_called_once()

    @patch(f"{_CTRL}.EngineManager")
    @patch(f"{_CTRL}.ChartDisplayComponent")
    @patch(f"{_CTRL}.st")
    def test_engine_change_regenerates_figure(
        self,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """An engine change reruns, then regenerates with the new identity."""
        mock_engine.get_engine.side_effect = ["plotly", "plotly", "matplotlib"]
        mock_chart.render_engine_selector.side_effect = [
            "plotly",
            "matplotlib",
            "matplotlib",
        ]
        plot = StubPlotHandle(processed_data=pd.DataFrame({"value": [1, 2, 3]}))
        plot.create_figure = MagicMock(return_value=MagicMock())
        ctrl = _make_render_controller()

        ctrl._render_visualization(plot, should_generate=False)
        ctrl._render_visualization(plot, should_generate=False)
        ctrl._render_visualization(plot, should_generate=False)

        assert plot.create_figure.call_count == 2
        mock_engine.set_engine.assert_called_once_with("matplotlib")
        mock_st.rerun.assert_called_once_with()

    @patch(f"{_CTRL}.EngineManager")
    @patch(f"{_CTRL}.ChartDisplayComponent")
    def test_new_processed_data_regenerates_figure(
        self,
        mock_chart: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """Replacing only a middle-row value invalidates the visible figure."""
        mock_engine.get_engine.return_value = "plotly"
        mock_chart.render_engine_selector.return_value = "plotly"
        plot = StubPlotHandle(processed_data=pd.DataFrame({"value": [1, 2, 3]}))
        plot.create_figure = MagicMock(return_value=MagicMock())
        ctrl = _make_render_controller()
        ctrl._render_visualization(plot, should_generate=False)

        plot.replace_processed_data(pd.DataFrame({"value": [1, 999, 3]}))
        ctrl._render_visualization(plot, should_generate=False)

        assert plot.create_figure.call_count == 2
