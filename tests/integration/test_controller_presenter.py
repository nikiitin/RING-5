"""Integration tests for PlotRenderController and ChartPresenter.

Covers Scenario #2 (Controller→Presenter behavioral chain) and #4 (UI orchestration).

Tests:
    - PlotRenderController.render() with mocked Streamlit widgets
    - ChartPresenter.render_refresh_controls() logic
    - Config change detection → should_generate flow
    - PlotLifecycleService.change_plot_type integration
    - Config error recovery in render pipeline
"""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go

from src.core.application_api import ApplicationAPI
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.controllers.plot.render_controller import PlotRenderController
from src.web.models.plot_protocols import PlotHandle
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.plot_service import PlotService
from src.web.presenters.plot.chart_presenter import ChartPresenter

# ---------------------------------------------------------------------------
# Helpers — minimal protocol-satisfying adapters
# ---------------------------------------------------------------------------


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

    def get_available_types(self) -> List[str]:
        return PlotFactory.get_available_plot_types()


class _MockChartDisplay:
    """Tracks render_chart calls for assertions."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.last_plot: Optional[PlotHandle] = None
        self.last_should_gen: Optional[bool] = None

    def render_chart(self, plot: PlotHandle, should_generate: bool) -> None:
        self.calls.append({"plot": plot, "should_generate": should_generate})
        self.last_plot = plot
        self.last_should_gen = should_generate


# ===========================================================================
# Test Class 1: PlotRenderController integration
# ===========================================================================


class TestPlotRenderControllerIntegration:
    """Test PlotRenderController.render() with mocked Streamlit layer."""

    def _build_controller(
        self,
        api: ApplicationAPI,
    ) -> tuple[PlotRenderController, _MockChartDisplay]:
        """Build a controller with real adapters and mock chart display."""
        from src.web.state.ui_state_manager import UIStateManager

        chart_display = _MockChartDisplay()

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
            chart_display=chart_display,
        )
        return controller, chart_display

    @patch("src.web.presenters.plot.chart_presenter.st")
    @patch("src.web.presenters.plot.config_presenter.st")
    @patch("src.web.controllers.plot.render_controller.st")
    def test_render_with_data_calls_chart_display(
        self,
        mock_ctrl_st: MagicMock,
        mock_config_st: MagicMock,
        mock_chart_st: MagicMock,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Controller.render() reaches chart_display when data is present."""
        controller, chart_display = self._build_controller(loaded_facade)

        # Create a real plot with data
        plot: BasePlot = PlotFactory.create_plot("bar", plot_id=1, name="Test")
        data: pd.DataFrame = loaded_facade.state_manager.get_data()
        plot.processed_data = data
        plot.config = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
        }

        # Mock Streamlit widgets to return values
        mock_ctrl_st.rerun = MagicMock()
        mock_config_st.columns.return_value = [MagicMock(), MagicMock()]
        mock_config_st.selectbox.return_value = "bar"

        # ConfigPresenter.render_plot_type_selector returns dict
        with (
            patch(
                "src.web.presenters.plot.config_presenter.ConfigPresenter.render_plot_type_selector",  # noqa: E501
                return_value={"type_changed": False, "new_type": "bar"},
            ),
            patch(
                "src.web.presenters.plot.config_presenter.ConfigPresenter.render_type_config",  # noqa: E501
                return_value=plot.config.copy(),
            ),
            patch(
                "src.web.presenters.plot.config_presenter.ConfigPresenter.render_advanced_and_theme",  # noqa: E501
                return_value={},
            ),
            patch(
                "src.web.presenters.plot.config_presenter.ConfigPresenter.render_section_headers",
                return_value=None,
            ),
            patch(
                "src.web.presenters.plot.chart_presenter.ChartPresenter.render_refresh_controls",
                return_value={
                    "auto_refresh": True,
                    "manual_refresh": False,
                    "should_generate": True,
                },
            ),
        ):
            controller.render(plot)

        # Chart display should have been called
        assert len(chart_display.calls) == 1
        assert chart_display.last_should_gen is True

    @patch("src.web.presenters.plot.chart_presenter.st")
    @patch("src.web.presenters.plot.config_presenter.st")
    @patch("src.web.controllers.plot.render_controller.st")
    def test_render_no_data_shows_warning(
        self,
        mock_ctrl_st: MagicMock,
        mock_config_st: MagicMock,
        mock_chart_st: MagicMock,
        facade: ApplicationAPI,
    ) -> None:
        """Controller.render() shows warning when processed_data is None."""
        controller, chart_display = self._build_controller(facade)

        plot: BasePlot = PlotFactory.create_plot("bar", plot_id=1, name="Empty")
        plot.processed_data = None  # No data

        with patch(
            "src.web.presenters.plot.config_presenter.ConfigPresenter.render_no_data_warning",
        ) as mock_warning:
            controller.render(plot)

        mock_warning.assert_called_once()
        assert len(chart_display.calls) == 0

    @patch("src.web.presenters.plot.chart_presenter.st")
    @patch("src.web.presenters.plot.config_presenter.st")
    @patch("src.web.controllers.plot.render_controller.st")
    def test_config_error_prevents_generation(
        self,
        mock_ctrl_st: MagicMock,
        mock_config_st: MagicMock,
        mock_chart_st: MagicMock,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """When type config raises, should_generate is False."""
        controller, chart_display = self._build_controller(loaded_facade)

        plot: BasePlot = PlotFactory.create_plot("bar", plot_id=1, name="Error")
        plot.processed_data = loaded_facade.state_manager.get_data()
        plot.config = {"x": "benchmark_name", "y": "system.cpu.ipc"}

        with (
            patch(
                "src.web.presenters.plot.config_presenter.ConfigPresenter.render_plot_type_selector",  # noqa: E501
                return_value={"type_changed": False, "new_type": "bar"},
            ),
            patch(
                "src.web.presenters.plot.config_presenter.ConfigPresenter.render_type_config",  # noqa: E501
                side_effect=ValueError("bad config"),
            ),
            patch(
                "src.web.presenters.plot.config_presenter.ConfigPresenter.render_advanced_and_theme",  # noqa: E501
                return_value={},
            ),
            patch(
                "src.web.presenters.plot.config_presenter.ConfigPresenter.render_section_headers",
                return_value=None,
            ),
            patch(
                "src.web.presenters.plot.chart_presenter.ChartPresenter.render_refresh_controls",
                return_value={
                    "auto_refresh": True,
                    "manual_refresh": True,  # Even manual refresh clicked
                    "should_generate": True,
                },
            ),
        ):
            controller.render(plot)

        # Chart display called but with should_gen=False due to error
        assert len(chart_display.calls) == 1
        assert chart_display.last_should_gen is False


# ===========================================================================
# Test Class 2: ChartPresenter refresh logic integration
# ===========================================================================


class TestChartPresenterIntegration:
    """Test ChartPresenter.render_refresh_controls() logic."""

    @patch("src.web.presenters.plot.chart_presenter.st")
    def test_auto_refresh_with_config_change_triggers_generation(self, mock_st: MagicMock) -> None:
        """Auto-refresh ON + config changed → should_generate is True."""
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        mock_st.toggle.return_value = True  # auto-refresh ON
        mock_st.button.return_value = False  # no manual click

        result: Dict[str, Any] = ChartPresenter.render_refresh_controls(
            plot_id=1, auto_refresh=True, config_changed=True
        )

        assert result["auto_refresh"] is True
        assert result["should_generate"] is True

    @patch("src.web.presenters.plot.chart_presenter.st")
    def test_auto_refresh_without_config_change_skips(self, mock_st: MagicMock) -> None:
        """Auto-refresh ON + no config change → should_generate is False."""
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        mock_st.toggle.return_value = True  # auto-refresh ON
        mock_st.button.return_value = False  # no manual click

        result: Dict[str, Any] = ChartPresenter.render_refresh_controls(
            plot_id=2, auto_refresh=True, config_changed=False
        )

        assert result["auto_refresh"] is True
        assert result["should_generate"] is False

    @patch("src.web.presenters.plot.chart_presenter.st")
    def test_manual_refresh_triggers_generation(self, mock_st: MagicMock) -> None:
        """Manual refresh click → should_generate is True regardless of auto."""
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        mock_st.toggle.return_value = False  # auto-refresh OFF
        mock_st.button.return_value = True  # manual clicked

        result: Dict[str, Any] = ChartPresenter.render_refresh_controls(
            plot_id=3, auto_refresh=False, config_changed=False
        )

        assert result["manual_refresh"] is True
        assert result["should_generate"] is True

    @patch("src.web.presenters.plot.chart_presenter.st")
    def test_no_refresh_no_generation(self, mock_st: MagicMock) -> None:
        """Auto OFF + no manual click + no change → should_generate is False."""
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        mock_st.toggle.return_value = False
        mock_st.button.return_value = False

        result: Dict[str, Any] = ChartPresenter.render_refresh_controls(
            plot_id=4, auto_refresh=False, config_changed=True  # even though changed
        )

        assert result["auto_refresh"] is False
        assert result["should_generate"] is False


# ===========================================================================
# Test Class 3: PlotLifecycleService integration (real state)
# ===========================================================================


class TestPlotLifecycleIntegration:
    """Test plot lifecycle operations with real RepositoryStateManager."""

    def test_create_plot_with_data_then_render(
        self, state_manager: RepositoryStateManager, rich_sample_data: pd.DataFrame
    ) -> None:
        """Create plot through service → assign data → generate figure."""
        # 1. Create
        plot: BasePlot = PlotService.create_plot(
            "Integration Bar", "bar", state_manager
        )  # type: ignore[assignment]
        assert plot.plot_type == "bar"

        # 2. Assign data
        plot.processed_data = rich_sample_data

        # 3. Configure
        plot.config = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "Integration Test",
            "xlabel": "X",
            "ylabel": "Y",
        }

        # 4. Generate figure
        fig: go.Figure = plot.create_figure(rich_sample_data, plot.config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

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

        # Modify copy config — should NOT affect original
        copy_plot.config["title"] = "Modified"
        assert "title" not in plot.config

    def test_delete_removes_from_state(self, state_manager: RepositoryStateManager) -> None:
        """After deletion, plot is no longer in state manager."""
        plot: BasePlot = PlotService.create_plot(
            "Delete Me", "bar", state_manager
        )  # type: ignore[assignment]
        plot_id: int = plot.plot_id

        # Verify it exists
        plots: List[Any] = state_manager.get_plots()
        plot_ids: List[int] = [p.plot_id for p in plots]
        assert plot_id in plot_ids

        # Delete
        PlotService.delete_plot(plot_id, state_manager)

        # Verify removed
        plots_after: List[Any] = state_manager.get_plots()
        plot_ids_after: List[int] = [p.plot_id for p in plots_after]
        assert plot_id not in plot_ids_after
