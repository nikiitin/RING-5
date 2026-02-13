"""Tests for PlotCreationController — UI orchestration logic.

Verifies that the controller correctly orchestrates:
    - Presenter calls with correct arguments
    - Domain operations via PlotLifecycleService
    - UI state updates via UIStateManager
    - Rerun triggers after state mutations
"""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from tests.ui_logic.conftest import StubPlotHandle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_controller(
    api: Optional[MagicMock] = None,
    ui_state: Optional[MagicMock] = None,
    lifecycle: Optional[MagicMock] = None,
    registry: Optional[MagicMock] = None,
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
    @patch("src.web.controllers.plot.creation_controller.PlotCreationPresenter.render")
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
    @patch("src.web.controllers.plot.creation_controller.PlotCreationPresenter.render")
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
    @patch("src.web.controllers.plot.creation_controller.PlotCreationPresenter.render")
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
    @patch("src.web.controllers.plot.creation_controller.PlotCreationPresenter.render")
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
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorPresenter.render")
    def test_no_plots_returns_none(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """When no plots exist, returns None and shows a warning."""
        api = MagicMock()
        api.state_manager.get_plots.return_value = []
        ctrl = _make_controller(api=api)

        result = ctrl.render_selector()

        assert result is None
        mock_st.warning.assert_called_once()
        mock_render.assert_not_called()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorPresenter.render")
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
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorPresenter.render")
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
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorPresenter.render")
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
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorPresenter.render")
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
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorPresenter.render")
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
    @patch("src.web.controllers.plot.creation_controller.PlotControlsPresenter.render")
    def test_rename_updates_plot_name(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """When presenter returns a different name, plot.name is updated."""
        mock_render.return_value = {
            "new_name": "Renamed Plot",
            "save_clicked": False,
            "load_clicked": False,
            "delete_clicked": False,
            "duplicate_clicked": False,
        }

        plot = StubPlotHandle(plot_id=1, name="Original")
        ui_state = MagicMock()
        ui_state.plot.is_dialog_visible.return_value = False
        ctrl = _make_controller(ui_state=ui_state)
        ctrl.render_controls(plot)

        assert plot.name == "Renamed Plot"

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsPresenter.render")
    def test_delete_calls_lifecycle_and_cleanup(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """Delete triggers ui cleanup, lifecycle.delete_plot, and rerun."""
        mock_render.return_value = {
            "new_name": "Plot",
            "save_clicked": False,
            "load_clicked": False,
            "delete_clicked": True,
            "duplicate_clicked": False,
        }

        plot = StubPlotHandle(plot_id=7, name="Plot")
        ui_state = MagicMock()
        ui_state.plot.is_dialog_visible.return_value = False
        lifecycle = MagicMock()
        api = MagicMock()
        ctrl = _make_controller(api=api, ui_state=ui_state, lifecycle=lifecycle)
        ctrl.render_controls(plot)

        ui_state.plot.cleanup.assert_called_once_with(7)
        lifecycle.delete_plot.assert_called_once_with(7, api.state_manager)
        mock_st.rerun.assert_called()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsPresenter.render")
    def test_duplicate_calls_lifecycle(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """Duplicate triggers lifecycle.duplicate_plot and rerun."""
        mock_render.return_value = {
            "new_name": "Plot",
            "save_clicked": False,
            "load_clicked": False,
            "delete_clicked": False,
            "duplicate_clicked": True,
        }

        plot = StubPlotHandle(plot_id=3, name="Plot")
        ui_state = MagicMock()
        ui_state.plot.is_dialog_visible.return_value = False
        lifecycle = MagicMock()
        api = MagicMock()
        ctrl = _make_controller(api=api, ui_state=ui_state, lifecycle=lifecycle)
        ctrl.render_controls(plot)

        lifecycle.duplicate_plot.assert_called_once_with(plot, api.state_manager)
        mock_st.rerun.assert_called()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsPresenter.render")
    def test_no_action_on_idle(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """When no button clicked and name unchanged, no side effects."""
        mock_render.return_value = {
            "new_name": "Idle Plot",
            "save_clicked": False,
            "load_clicked": False,
            "delete_clicked": False,
            "duplicate_clicked": False,
        }

        plot = StubPlotHandle(plot_id=1, name="Idle Plot")
        ui_state = MagicMock()
        ui_state.plot.is_dialog_visible.return_value = False
        lifecycle = MagicMock()
        ctrl = _make_controller(ui_state=ui_state, lifecycle=lifecycle)
        ctrl.render_controls(plot)

        lifecycle.delete_plot.assert_not_called()
        lifecycle.duplicate_plot.assert_not_called()
        mock_st.rerun.assert_not_called()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsPresenter.render")
    def test_save_dialog_opened_via_callback(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """The on_save callback sets 'save' dialog visible and hides 'load'."""
        captured_on_save = None

        def capture_render(**kwargs: Any) -> Dict[str, Any]:
            nonlocal captured_on_save
            captured_on_save = kwargs.get("on_save")
            return {
                "new_name": "P",
                "save_clicked": False,
                "load_clicked": False,
                "delete_clicked": False,
                "duplicate_clicked": False,
            }

        mock_render.side_effect = capture_render

        plot = StubPlotHandle(plot_id=5, name="P")
        ui_state = MagicMock()
        ui_state.plot.is_dialog_visible.return_value = False
        ctrl = _make_controller(ui_state=ui_state)
        ctrl.render_controls(plot)

        # Simulate the callback
        assert captured_on_save is not None
        captured_on_save()

        ui_state.plot.set_dialog_visible.assert_any_call(5, "save", True)
        ui_state.plot.set_dialog_visible.assert_any_call(5, "load", False)

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsPresenter.render")
    def test_load_dialog_opened_via_callback(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """The on_load callback sets 'load' dialog visible and hides 'save'."""
        captured_on_load = None

        def capture_render(**kwargs: Any) -> Dict[str, Any]:
            nonlocal captured_on_load
            captured_on_load = kwargs.get("on_load")
            return {
                "new_name": "P",
                "save_clicked": False,
                "load_clicked": False,
                "delete_clicked": False,
                "duplicate_clicked": False,
            }

        mock_render.side_effect = capture_render

        plot = StubPlotHandle(plot_id=5, name="P")
        ui_state = MagicMock()
        ui_state.plot.is_dialog_visible.return_value = False
        ctrl = _make_controller(ui_state=ui_state)
        ctrl.render_controls(plot)

        assert captured_on_load is not None
        captured_on_load()

        ui_state.plot.set_dialog_visible.assert_any_call(5, "load", True)
        ui_state.plot.set_dialog_visible.assert_any_call(5, "save", False)


# ---------------------------------------------------------------------------
# _handle_save_dialog
# ---------------------------------------------------------------------------
class TestHandleSaveDialog:
    """Tests for save pipeline dialog logic."""

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.SaveDialogPresenter.render")
    def test_save_delegates_and_hides_dialog(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """On save_clicked, pipeline is saved and dialog hidden."""
        mock_render.return_value = {
            "pipeline_name": "my_pipeline",
            "save_clicked": True,
            "cancel_clicked": False,
        }

        plot = StubPlotHandle(
            plot_id=1,
            name="Test",
            pipeline=[{"id": 1, "type": "sort"}],
        )
        api = MagicMock()
        ui_state = MagicMock()
        ctrl = _make_controller(api=api, ui_state=ui_state)
        ctrl._handle_save_dialog(plot)

        api.shapers.save_pipeline.assert_called_once_with(
            "my_pipeline",
            plot.pipeline,
            description="Source: Test",
        )
        ui_state.plot.set_dialog_visible.assert_called_with(1, "save", False)
        mock_st.toast.assert_called_once()
        mock_st.rerun.assert_called_once()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.SaveDialogPresenter.render")
    def test_save_error_shows_error_message(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """If save_pipeline raises, st.error is called."""
        mock_render.return_value = {
            "pipeline_name": "bad_name",
            "save_clicked": True,
            "cancel_clicked": False,
        }

        api = MagicMock()
        api.shapers.save_pipeline.side_effect = RuntimeError("disk full")

        plot = StubPlotHandle(plot_id=1, name="T", pipeline=[])
        ctrl = _make_controller(api=api)
        ctrl._handle_save_dialog(plot)

        mock_st.error.assert_called_once()
        assert "disk full" in str(mock_st.error.call_args)

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.SaveDialogPresenter.render")
    def test_cancel_hides_dialog(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """On cancel_clicked, dialog is hidden and rerun triggered."""
        mock_render.return_value = {
            "pipeline_name": "",
            "save_clicked": False,
            "cancel_clicked": True,
        }

        plot = StubPlotHandle(plot_id=2, name="X")
        ui_state = MagicMock()
        ctrl = _make_controller(ui_state=ui_state)
        ctrl._handle_save_dialog(plot)

        ui_state.plot.set_dialog_visible.assert_called_with(2, "save", False)
        mock_st.rerun.assert_called_once()


# ---------------------------------------------------------------------------
# _handle_load_dialog
# ---------------------------------------------------------------------------
class TestHandleLoadDialog:
    """Tests for load pipeline dialog logic."""

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.LoadDialogPresenter.render_empty")
    def test_no_pipelines_renders_empty(self, mock_empty: MagicMock, mock_st: MagicMock) -> None:
        """When no pipelines exist, render_empty is called."""
        mock_empty.return_value = {"close_clicked": False}

        api = MagicMock()
        api.shapers.list_pipelines.return_value = []

        plot = StubPlotHandle(plot_id=1, name="P")
        ctrl = _make_controller(api=api)
        ctrl._handle_load_dialog(plot)

        mock_empty.assert_called_once_with(plot_id=1)

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.LoadDialogPresenter.render_empty")
    def test_empty_close_hides_dialog(self, mock_empty: MagicMock, mock_st: MagicMock) -> None:
        """Close on empty dialog hides it."""
        mock_empty.return_value = {"close_clicked": True}

        api = MagicMock()
        api.shapers.list_pipelines.return_value = []
        ui_state = MagicMock()

        plot = StubPlotHandle(plot_id=4, name="P")
        ctrl = _make_controller(api=api, ui_state=ui_state)
        ctrl._handle_load_dialog(plot)

        ui_state.plot.set_dialog_visible.assert_called_with(4, "load", False)
        mock_st.rerun.assert_called_once()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.LoadDialogPresenter.render")
    def test_load_sets_pipeline_on_plot(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """On load_clicked, pipeline is deep-copied onto the plot."""
        mock_render.return_value = {
            "selected_pipeline": "saved_pipe",
            "load_clicked": True,
            "cancel_clicked": False,
        }

        loaded_pipeline: List[Dict[str, Any]] = [
            {"id": 3, "type": "sort", "config": {}},
            {"id": 7, "type": "filter", "config": {}},
        ]

        api = MagicMock()
        api.shapers.list_pipelines.return_value = ["saved_pipe"]
        api.shapers.load_pipeline.return_value = {"pipeline": loaded_pipeline}
        ui_state = MagicMock()

        plot = StubPlotHandle(plot_id=1, name="P", pipeline=[])
        ctrl = _make_controller(api=api, ui_state=ui_state)
        ctrl._handle_load_dialog(plot)

        # Pipeline should be set (deep copy, so not the same object)
        assert len(plot.pipeline) == 2
        assert plot.pipeline[0]["type"] == "sort"
        assert plot.pipeline[1]["type"] == "filter"
        # pipeline_counter should be max(id) + 1 = 8
        assert plot.pipeline_counter == 8
        # processed_data should be cleared
        assert plot.processed_data is None
        ui_state.plot.set_dialog_visible.assert_called_with(1, "load", False)
        mock_st.rerun.assert_called_once()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.LoadDialogPresenter.render")
    def test_load_empty_pipeline_resets_counter(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """Loading an empty pipeline sets pipeline_counter to 0."""
        mock_render.return_value = {
            "selected_pipeline": "empty_pipe",
            "load_clicked": True,
            "cancel_clicked": False,
        }

        api = MagicMock()
        api.shapers.list_pipelines.return_value = ["empty_pipe"]
        api.shapers.load_pipeline.return_value = {"pipeline": []}
        ui_state = MagicMock()

        plot = StubPlotHandle(plot_id=1, name="P", pipeline_counter=10)
        ctrl = _make_controller(api=api, ui_state=ui_state)
        ctrl._handle_load_dialog(plot)

        assert plot.pipeline == []
        assert plot.pipeline_counter == 0

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.LoadDialogPresenter.render")
    def test_load_error_shows_error_message(
        self, mock_render: MagicMock, mock_st: MagicMock
    ) -> None:
        """If load_pipeline raises, st.error is called."""
        mock_render.return_value = {
            "selected_pipeline": "broken",
            "load_clicked": True,
            "cancel_clicked": False,
        }

        api = MagicMock()
        api.shapers.list_pipelines.return_value = ["broken"]
        api.shapers.load_pipeline.side_effect = FileNotFoundError("missing")

        plot = StubPlotHandle(plot_id=1, name="P")
        ctrl = _make_controller(api=api)
        ctrl._handle_load_dialog(plot)

        mock_st.error.assert_called_once()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.LoadDialogPresenter.render")
    def test_cancel_hides_dialog(self, mock_render: MagicMock, mock_st: MagicMock) -> None:
        """On cancel_clicked, dialog is hidden and rerun triggered."""
        mock_render.return_value = {
            "selected_pipeline": None,
            "load_clicked": False,
            "cancel_clicked": True,
        }

        api = MagicMock()
        api.shapers.list_pipelines.return_value = ["pipe1"]
        ui_state = MagicMock()

        plot = StubPlotHandle(plot_id=9, name="P")
        ctrl = _make_controller(api=api, ui_state=ui_state)
        ctrl._handle_load_dialog(plot)

        ui_state.plot.set_dialog_visible.assert_called_with(9, "load", False)
        mock_st.rerun.assert_called_once()
