"""Integration tests for PlotRenderController and ChartDisplayComponent.

Covers Scenario #2 (Controller→Component behavioral chain) and #4 (UI orchestration).

Tests:
    - PlotRenderController.render() with mocked Streamlit widgets
    - ChartDisplayComponent.render_refresh_controls() logic
    - Config change detection → should_generate flow
    - PlotLifecycleService.change_plot_type integration
    - Config error recovery in render pipeline
"""

from typing import Any, cast
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go

from src.core.application_api import ApplicationAPI
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.components.common.chart_display import ChartDisplayComponent
from src.web.controllers.plot.render_controller import PlotRenderController
from src.web.models.plot_protocols import PlotHandle, RenderablePlot
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.plot_service import PlotService

# Helpers — minimal protocol-satisfying adapters


class _LifecycleAdapter:
    """Adapter wrapping PlotService static methods for PlotLifecycleService."""

    def create_plot(self, name: str, plot_type: str, state_manager: Any) -> PlotHandle:
        return PlotService.create_plot(name, plot_type, state_manager)

    def delete_plot(self, plot_id: int, state_manager: Any) -> None:
        PlotService.delete_plot(plot_id, state_manager)

    def duplicate_plot(self, plot: PlotHandle, state_manager: Any) -> PlotHandle:
        return PlotService.duplicate_plot(plot, state_manager)  # type: ignore[arg-type]

    def change_plot_type(self, plot: PlotHandle, new_type: str, state_manager: Any) -> PlotHandle:
        return PlotService.change_plot_type(plot, new_type, state_manager)  # type: ignore[arg-type]


class _RegistryAdapter:
    """Adapter wrapping PlotFactory for PlotTypeRegistry."""

    def get_available_types(self) -> list[str]:
        return PlotFactory.get_available_plot_types()


class _RenderVisualizationTracker:
    """Tracks _render_visualization calls for assertions."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.last_plot: PlotHandle | None = None
        self.last_should_gen: bool | None = None

    def __call__(self, plot: PlotHandle, should_generate: bool) -> None:
        self.calls.append({"plot": plot, "should_generate": should_generate})
        self.last_plot = plot
        self.last_should_gen = should_generate


# Test Class 1: PlotRenderController integration


class TestPlotRenderControllerIntegration:
    """Test PlotRenderController.render() with mocked Streamlit layer."""

    def _build_controller(
        self,
        api: ApplicationAPI,
    ) -> tuple[PlotRenderController, _RenderVisualizationTracker]:
        """Build a controller with real adapters and tracked visualization."""
        from src.web.state.ui_state_manager import UIStateManager

        tracker = _RenderVisualizationTracker()

        # We need to mock UIStateManager since it uses st.session_state
        ui_state = MagicMock(spec=UIStateManager)
        ui_state.plot = MagicMock()
        ui_state.plot.get_auto_refresh.return_value = True
        ui_state.plot.set_auto_refresh.return_value = None

        controller = PlotRenderController(
            api=api,
            ui_state=ui_state,
            lifecycle=_LifecycleAdapter(),
            registry=_RegistryAdapter(),
        )
        # Patch _render_visualization to track calls
        controller._render_visualization = tracker  # type: ignore[assignment]
        return controller, tracker

    @patch(
        "src.web.controllers.plot.render_controller.render_settings_pills",
        return_value=None,
    )
    @patch("src.web.controllers.plot.render_controller.st")
    def test_render_with_data_calls_chart_display(
        self,
        mock_ctrl_st: MagicMock,
        mock_pills: MagicMock,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Controller.render() reaches _render_visualization when data is present."""
        controller, tracker = self._build_controller(loaded_facade)

        # Create a real plot with data
        plot: BasePlot = PlotFactory.create_plot("bar", plot_id=1, name="Test")
        data_or_none = loaded_facade.state_manager.get_data()
        assert data_or_none is not None
        data: pd.DataFrame = data_or_none
        plot.processed_data = data
        plot.config = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
        }

        # Mock inline Streamlit widgets
        mock_ctrl_st.selectbox.return_value = "bar"
        mock_ctrl_st.toggle.return_value = False

        # Mock plot methods to avoid real Streamlit calls inside BasePlot
        plot.render_config_ui = MagicMock(  # type: ignore[assignment]
            return_value=plot.config.copy()
        )
        plot.render_settings_section = MagicMock(return_value={})  # type: ignore[assignment]

        with patch(
            "src.web.components.common.chart_display.ChartDisplayComponent.render_refresh_controls",
            return_value={
                "auto_refresh": True,
                "manual_refresh": False,
                "should_generate": True,
            },
        ):
            controller.render(cast(RenderablePlot, plot))

        # _render_visualization should have been called
        assert len(tracker.calls) == 1
        assert tracker.last_should_gen is True

    @patch("src.web.controllers.plot.render_controller.st")
    def test_render_no_data_shows_warning(
        self,
        mock_ctrl_st: MagicMock,
        facade: ApplicationAPI,
    ) -> None:
        """Controller.render() shows warning when processed_data is None."""
        controller, tracker = self._build_controller(facade)

        plot: BasePlot = PlotFactory.create_plot("bar", plot_id=1, name="Empty")
        plot.processed_data = None  # No data

        controller.render(cast(RenderablePlot, plot))

        mock_ctrl_st.warning.assert_called_once_with("No processed data available.")
        assert len(tracker.calls) == 0

    @patch(
        "src.web.controllers.plot.render_controller.render_settings_pills",
        return_value=None,
    )
    @patch("src.web.controllers.plot.render_controller.st")
    def test_config_error_prevents_generation(
        self,
        mock_ctrl_st: MagicMock,
        mock_pills: MagicMock,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """When type config raises, should_generate is False."""
        controller, tracker = self._build_controller(loaded_facade)

        plot: BasePlot = PlotFactory.create_plot("bar", plot_id=1, name="Error")
        plot.processed_data = loaded_facade.state_manager.get_data()
        plot.config = {"x": "benchmark_name", "y": "system.cpu.ipc"}

        # Mock inline Streamlit widgets
        mock_ctrl_st.selectbox.return_value = "bar"
        mock_ctrl_st.toggle.return_value = False

        # Make render_config_ui raise to test error recovery
        plot.render_config_ui = MagicMock(  # type: ignore[assignment]
            side_effect=ValueError("bad config")
        )
        plot.render_settings_section = MagicMock(return_value={})  # type: ignore[assignment]

        with patch(
            "src.web.components.common.chart_display.ChartDisplayComponent.render_refresh_controls",
            return_value={
                "auto_refresh": True,
                "manual_refresh": True,  # Even manual refresh clicked
                "should_generate": True,
            },
        ):
            controller.render(cast(RenderablePlot, plot))

        # _render_visualization called but with should_gen=False due to error
        assert len(tracker.calls) == 1
        assert tracker.last_should_gen is False


# Test Class 2: ChartDisplayComponent refresh logic integration


class TestChartDisplayComponentIntegration:
    """Test ChartDisplayComponent.render_refresh_controls() logic."""

    @patch("src.web.components.common.chart_display.st")
    def test_auto_refresh_with_config_change_triggers_generation(self, mock_st: MagicMock) -> None:
        """Auto-refresh ON + config changed → should_generate is True."""
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        mock_st.toggle.return_value = True  # auto-refresh ON
        mock_st.button.return_value = False  # no manual click

        result: dict[str, Any] = ChartDisplayComponent.render_refresh_controls(
            plot_id=1, auto_refresh=True, config_changed=True
        )

        assert result["auto_refresh"] is True
        assert result["should_generate"] is True

    @patch("src.web.components.common.chart_display.st")
    def test_auto_refresh_without_config_change_skips(self, mock_st: MagicMock) -> None:
        """Auto-refresh ON + no config change → should_generate is False."""
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        mock_st.toggle.return_value = True  # auto-refresh ON
        mock_st.button.return_value = False  # no manual click

        result: dict[str, Any] = ChartDisplayComponent.render_refresh_controls(
            plot_id=2, auto_refresh=True, config_changed=False
        )

        assert result["auto_refresh"] is True
        assert result["should_generate"] is False

    @patch("src.web.components.common.chart_display.st")
    def test_manual_refresh_triggers_generation(self, mock_st: MagicMock) -> None:
        """Manual refresh click → should_generate is True regardless of auto."""
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        mock_st.toggle.return_value = False  # auto-refresh OFF
        mock_st.button.return_value = True  # manual clicked

        result: dict[str, Any] = ChartDisplayComponent.render_refresh_controls(
            plot_id=3, auto_refresh=False, config_changed=False
        )

        assert result["manual_refresh"] is True
        assert result["should_generate"] is True

    @patch("src.web.components.common.chart_display.st")
    def test_no_refresh_no_generation(self, mock_st: MagicMock) -> None:
        """Auto OFF + no manual click + no change → should_generate is False."""
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        mock_st.toggle.return_value = False
        mock_st.button.return_value = False

        result: dict[str, Any] = ChartDisplayComponent.render_refresh_controls(
            plot_id=4, auto_refresh=False, config_changed=True  # even though changed
        )

        assert result["auto_refresh"] is False
        assert result["should_generate"] is False


# Test Class 3: PlotLifecycleService integration (real state)


class TestPlotLifecycleIntegration:
    """Test plot lifecycle operations with real RepositoryStateManager."""

    def test_create_plot_with_data_then_render(
        self, state_manager: RepositoryStateManager, rich_sample_data: pd.DataFrame
    ) -> None:
        """Create plot through service → assign data → generate figure."""
        # Create
        plot: BasePlot = PlotService.create_plot(
            "Integration Bar", "bar", state_manager
        )  # type: ignore[assignment]
        assert plot.plot_type == "bar"

        # Assign data
        plot.processed_data = rich_sample_data

        # Configure
        plot.config = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "Integration Test",
            "xlabel": "X",
            "ylabel": "Y",
        }

        # Generate figure
        fig: go.Figure = plot.create_figure(rich_sample_data, plot.config)
        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) > 0

    def test_change_plot_type_preserves_data(
        self, state_manager: RepositoryStateManager, rich_sample_data: pd.DataFrame
    ) -> None:
        """Changing plot type preserves processed_data but resets config."""
        # Create and populate
        plot: BasePlot = PlotService.create_plot(
            "Type Change", "bar", state_manager
        )  # type: ignore[assignment]
        plot.processed_data = rich_sample_data
        plot.config = {"x": "benchmark_name", "y": "system.cpu.ipc"}

        # Change type
        new_plot: BasePlot = PlotService.change_plot_type(
            plot, "line", state_manager
        )  # type: ignore[assignment]

        assert new_plot.plot_type == "line"
        assert new_plot.processed_data is not None
        # Config should be reset
        assert new_plot.config == {}

    def test_duplicate_creates_independent_copy(
        self, state_manager: RepositoryStateManager, rich_sample_data: pd.DataFrame
    ) -> None:
        """Duplicated plot is independent — changes don't affect original."""
        # Create and populate
        plot: BasePlot = PlotService.create_plot(
            "Original", "bar", state_manager
        )  # type: ignore[assignment]
        plot.processed_data = rich_sample_data
        plot.config = {"x": "benchmark_name", "y": "system.cpu.ipc"}

        # Duplicate
        copy_plot: BasePlot = PlotService.duplicate_plot(
            plot, state_manager
        )  # type: ignore[assignment]

        assert copy_plot.plot_id != plot.plot_id
        assert "(copy)" in copy_plot.name

        # Mutating the copy must leave the original unchanged.
        copy_plot.config["title"] = "Modified"
        assert "title" not in plot.config

    def test_delete_removes_from_state(self, state_manager: RepositoryStateManager) -> None:
        """After deletion, plot is no longer in state manager."""
        plot: BasePlot = PlotService.create_plot(
            "Delete Me", "bar", state_manager
        )  # type: ignore[assignment]
        plot_id: int = plot.plot_id

        # Verify it exists
        plots: list[Any] = state_manager.get_plots()
        plot_ids: list[int] = [p.plot_id for p in plots]
        assert plot_id in plot_ids

        # Delete
        PlotService.delete_plot(plot_id, state_manager)

        # Verify removed
        plots_after: list[Any] = state_manager.get_plots()
        plot_ids_after: list[int] = [p.plot_id for p in plots_after]
        assert plot_id not in plot_ids_after
