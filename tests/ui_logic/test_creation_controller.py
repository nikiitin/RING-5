"""Tests for PlotCreationController — UI orchestration logic.

Verifies that the controller correctly orchestrates:
    - Presenter calls with correct arguments
    - Domain operations via PlotLifecycleService
    - UI state updates via UIStateManager
    - Rerun triggers after state mutations
"""

from typing import Any
from unittest.mock import MagicMock, patch

from tests.ui_logic.conftest import StubPlotHandle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_controller(
    api: MagicMock | None = None,
    ui_state: MagicMock | None = None,
    lifecycle: MagicMock | None = None,
    registry: MagicMock | None = None,
) -> Any:
    """Build a PlotCreationController with sane mock defaults."""
    from src.web.controllers.plot.creation_controller import PlotCreationController

    api = api or MagicMock()
    if not hasattr(api, "state_manager"):
        api.state_manager = MagicMock()
    if not hasattr(api, "shapers"):
        api.shapers = MagicMock()
    api.state_manager.get_plot_counter.return_value = 3

    ui_state = ui_state or MagicMock()
    lifecycle = lifecycle or MagicMock()
    registry = registry or MagicMock()
    registry.get_available_types.return_value = ["bar", "line", "scatter"]

    return PlotCreationController(api, ui_state, lifecycle, registry)


# ---------------------------------------------------------------------------
# render_create_section
# ---------------------------------------------------------------------------
class TestRenderCreateSection:
    """Tests for the create-new-plot flow."""

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotCreationComponent.render")
    def test_render_calls_presenter_with_counter(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """Presenter receives default_name based on plot_counter + 1."""
        mock_render.return_value = {
            "name": "Plot 4",
            "plot_type": None,
            "create_clicked": False,
        }

        ctrl = _make_controller()
        ctrl.render_create_section()

        mock_render.assert_called_once_with(
            default_name="Plot 4",
            available_types=["bar", "line", "scatter"],
        )

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotCreationComponent.render")
    def test_create_clicked_delegates_to_lifecycle(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """When create_clicked=True, lifecycle.create_plot is called."""
        mock_render.return_value = {
            "name": "My Plot",
            "plot_type": "bar",
            "create_clicked": True,
        }

        lifecycle = MagicMock()
        api = MagicMock()
        ctrl = _make_controller(api=api, lifecycle=lifecycle)
        ctrl.render_create_section()

        lifecycle.create_plot.assert_called_once_with("My Plot", "bar", api.state_manager)
        mock_st.rerun.assert_called_once()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotCreationComponent.render")
    def test_create_skipped_when_no_type(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """When plot_type is None, lifecycle.create_plot is NOT called."""
        mock_render.return_value = {
            "name": "Plot",
            "plot_type": None,
            "create_clicked": True,
        }

        lifecycle = MagicMock()
        ctrl = _make_controller(lifecycle=lifecycle)
        ctrl.render_create_section()

        lifecycle.create_plot.assert_not_called()
        mock_st.rerun.assert_not_called()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotCreationComponent.render")
    def test_no_action_when_button_not_clicked(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """When create_clicked=False, nothing happens."""
        mock_render.return_value = {
            "name": "Plot 1",
            "plot_type": "line",
            "create_clicked": False,
        }

        lifecycle = MagicMock()
        ctrl = _make_controller(lifecycle=lifecycle)
        ctrl.render_create_section()

        lifecycle.create_plot.assert_not_called()
        mock_st.rerun.assert_not_called()


# ---------------------------------------------------------------------------
# render_selector
# ---------------------------------------------------------------------------
class TestRenderSelector:
    """Tests for plot selection logic."""

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorComponent")
    def test_no_plots_returns_none(self, mock_presenter: MagicMock, mock_st: MagicMock) -> None:
        """When no plots exist, returns None and shows a warning."""
        api = MagicMock()
        api.state_manager.get_plots.return_value = []
        ctrl = _make_controller(api=api)

        result = ctrl.render_selector()

        assert result is None
        mock_presenter.render_no_plots_warning.assert_called_once()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorComponent.render")
    def test_single_plot_selected(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """With one plot, it is returned as the selected plot."""
        plot = StubPlotHandle(plot_id=1, name="Alpha")
        api = MagicMock()
        api.state_manager.get_plots.return_value = [plot]
        api.state_manager.get_current_plot_id.return_value = 1

        mock_render.return_value = "Alpha"
        ctrl = _make_controller(api=api)
        result = ctrl.render_selector()

        assert result is plot
        mock_render.assert_called_once_with(["Alpha"], default_index=0)

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorComponent.render")
    def test_selects_correct_plot_by_name(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """When user selects a plot by name, the matching plot is returned."""
        p1 = StubPlotHandle(plot_id=1, name="Alpha")
        p2 = StubPlotHandle(plot_id=2, name="Beta")
        api = MagicMock()
        api.state_manager.get_plots.return_value = [p1, p2]
        api.state_manager.get_current_plot_id.return_value = 1

        mock_render.return_value = "Beta"
        ctrl = _make_controller(api=api)
        result = ctrl.render_selector()

        assert result is p2
        api.state_manager.set_current_plot_id.assert_called_once_with(2)

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorComponent.render")
    def test_default_index_matches_current_id(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """SelectorPresenter receives default_index matching current_plot_id."""
        p1 = StubPlotHandle(plot_id=10, name="First")
        p2 = StubPlotHandle(plot_id=20, name="Second")
        p3 = StubPlotHandle(plot_id=30, name="Third")

        api = MagicMock()
        api.state_manager.get_plots.return_value = [p1, p2, p3]
        api.state_manager.get_current_plot_id.return_value = 30

        mock_render.return_value = "Third"
        ctrl = _make_controller(api=api)
        ctrl.render_selector()

        mock_render.assert_called_once_with(["First", "Second", "Third"], default_index=2)

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorComponent.render")
    def test_no_current_id_defaults_to_zero(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """When current_plot_id is None, default_index is 0."""
        p1 = StubPlotHandle(plot_id=1, name="Alpha")
        api = MagicMock()
        api.state_manager.get_plots.return_value = [p1]
        api.state_manager.get_current_plot_id.return_value = None

        mock_render.return_value = "Alpha"
        ctrl = _make_controller(api=api)
        ctrl.render_selector()

        mock_render.assert_called_once_with(["Alpha"], default_index=0)

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorComponent.render")
    def test_same_plot_does_not_update_id(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """When selected plot matches current_id, set_current_plot_id is skipped."""
        plot = StubPlotHandle(plot_id=5, name="Same")
        api = MagicMock()
        api.state_manager.get_plots.return_value = [plot]
        api.state_manager.get_current_plot_id.return_value = 5

        mock_render.return_value = "Same"
        ctrl = _make_controller(api=api)
        ctrl.render_selector()

        api.state_manager.set_current_plot_id.assert_not_called()


# ---------------------------------------------------------------------------
# render_controls
# ---------------------------------------------------------------------------
class TestRenderControls:
    """Tests for the plot controls bar (rename, delete, duplicate, dialogs)."""

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsComponent.render")
    def test_rename_updates_plot_name(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """When presenter returns a different name, plot.name is updated."""
        mock_render.return_value = {
            "new_name": "Renamed Plot",
            "delete_clicked": False,
            "duplicate_clicked": False,
        }

        plot = StubPlotHandle(plot_id=1, name="Original")
        ctrl = _make_controller()
        ctrl.render_controls(plot)

        assert plot.name == "Renamed Plot"

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsComponent.render")
    def test_delete_calls_lifecycle_and_cleanup(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """Delete triggers ui cleanup, lifecycle.delete_plot, and rerun."""
        mock_render.return_value = {
            "new_name": "Plot",
            "delete_clicked": True,
            "duplicate_clicked": False,
        }

        plot = StubPlotHandle(plot_id=7, name="Plot")
        ui_state = MagicMock()
        lifecycle = MagicMock()
        api = MagicMock()
        ctrl = _make_controller(api=api, ui_state=ui_state, lifecycle=lifecycle)
        ctrl.render_controls(plot)

        ui_state.plot.cleanup.assert_called_once_with(7)
        lifecycle.delete_plot.assert_called_once_with(7, api.state_manager)
        mock_st.rerun.assert_called()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsComponent.render")
    def test_duplicate_calls_lifecycle(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """Duplicate triggers lifecycle.duplicate_plot and rerun."""
        mock_render.return_value = {
            "new_name": "Plot",
            "delete_clicked": False,
            "duplicate_clicked": True,
        }

        plot = StubPlotHandle(plot_id=3, name="Plot")
        lifecycle = MagicMock()
        api = MagicMock()
        ctrl = _make_controller(api=api, lifecycle=lifecycle)
        ctrl.render_controls(plot)

        lifecycle.duplicate_plot.assert_called_once_with(plot, api.state_manager)
        mock_st.rerun.assert_called()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsComponent.render")
    def test_no_action_on_idle(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """When no button clicked and name unchanged, no side effects."""
        mock_render.return_value = {
            "new_name": "Idle Plot",
            "delete_clicked": False,
            "duplicate_clicked": False,
        }

        plot = StubPlotHandle(plot_id=1, name="Idle Plot")
        lifecycle = MagicMock()
        ctrl = _make_controller(lifecycle=lifecycle)
        ctrl.render_controls(plot)

        lifecycle.delete_plot.assert_not_called()
        lifecycle.duplicate_plot.assert_not_called()
        mock_st.rerun.assert_not_called()


# NOTE: TestHandleSaveDialog, TestHandleLoadDialog, and save/load callback
# Pipeline save/load tests were removed with that feature.
