"""
Tests for Plot Controllers — verify orchestration logic.

Controllers are tested with mocked presenters and injected dependencies.
We verify:
    1. Correct delegation to presenters
    2. Correct calls to injected services based on presenter results
    3. Correct state updates via UIStateManager
    4. Error handling

Dependencies (PlotLifecycleService, PlotTypeRegistry, PipelineExecutor,
ChartDisplay) are injected as mocks — no module-level patching needed.
"""

from unittest.mock import MagicMock, patch

import pytest

# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_api() -> MagicMock:
    """Create a mock ApplicationAPI."""
    api: MagicMock = MagicMock()
    api.state_manager.get_plot_counter.return_value = 3
    api.state_manager.get_plots.return_value = []
    api.state_manager.get_current_plot_id.return_value = None
    api.state_manager.get_data.return_value = None
    return api


@pytest.fixture
def mock_ui_state() -> MagicMock:
    """Create a mock UIStateManager."""
    ui_state: MagicMock = MagicMock()
    ui_state.plot.get_auto_refresh.return_value = True
    ui_state.plot.is_dialog_visible.return_value = False
    return ui_state


@pytest.fixture
def mock_lifecycle() -> MagicMock:
    """Create a mock PlotLifecycleService."""
    return MagicMock()


@pytest.fixture
def mock_registry() -> MagicMock:
    """Create a mock PlotTypeRegistry."""
    registry: MagicMock = MagicMock()
    registry.get_available_types.return_value = ["bar", "line"]
    return registry


@pytest.fixture
def mock_pipeline_executor() -> MagicMock:
    """Create a mock PipelineExecutor."""
    return MagicMock()


@pytest.fixture
def mock_chart_display() -> MagicMock:
    """Create a mock ChartDisplay."""
    return MagicMock()


# ─── PlotCreationController Tests ────────────────────────────────────────────


class TestPlotCreationController:
    """Tests for PlotCreationController."""

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotCreationPresenter")
    def test_render_create_section_calls_presenter(
        self,
        mock_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_lifecycle: MagicMock,
        mock_registry: MagicMock,
    ) -> None:
        """render_create_section delegates to PlotCreationPresenter."""
        from src.web.controllers.plot.creation_controller import PlotCreationController

        mock_presenter.render.return_value = {
            "name": "P1",
            "plot_type": "bar",
            "create_clicked": False,
        }

        controller = PlotCreationController(mock_api, mock_ui_state, mock_lifecycle, mock_registry)
        controller.render_create_section()

        mock_presenter.render.assert_called_once()
        mock_registry.get_available_types.assert_called_once()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotCreationPresenter")
    def test_create_calls_lifecycle_on_click(
        self,
        mock_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_lifecycle: MagicMock,
        mock_registry: MagicMock,
    ) -> None:
        """When create_clicked=True, lifecycle.create_plot is called."""
        from src.web.controllers.plot.creation_controller import PlotCreationController

        mock_presenter.render.return_value = {
            "name": "New Plot",
            "plot_type": "bar",
            "create_clicked": True,
        }

        controller = PlotCreationController(mock_api, mock_ui_state, mock_lifecycle, mock_registry)
        controller.render_create_section()

        mock_lifecycle.create_plot.assert_called_once_with(
            "New Plot", "bar", mock_api.state_manager
        )
        mock_st.rerun.assert_called_once()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorPresenter")
    def test_render_selector_returns_none_when_no_plots(
        self,
        mock_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_lifecycle: MagicMock,
        mock_registry: MagicMock,
    ) -> None:
        """Returns None when there are no plots."""
        from src.web.controllers.plot.creation_controller import PlotCreationController

        mock_api.state_manager.get_plots.return_value = []

        controller = PlotCreationController(mock_api, mock_ui_state, mock_lifecycle, mock_registry)
        result = controller.render_selector()

        assert result is None
        mock_st.warning.assert_called_once()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotSelectorPresenter")
    def test_render_selector_returns_selected_plot(
        self,
        mock_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_lifecycle: MagicMock,
        mock_registry: MagicMock,
    ) -> None:
        """Returns the plot matching the selected name."""
        from src.web.controllers.plot.creation_controller import PlotCreationController

        plot1: MagicMock = MagicMock()
        plot1.name = "Plot A"
        plot1.plot_id = 1
        plot2: MagicMock = MagicMock()
        plot2.name = "Plot B"
        plot2.plot_id = 2

        mock_api.state_manager.get_plots.return_value = [plot1, plot2]
        mock_api.state_manager.get_current_plot_id.return_value = 1
        mock_presenter.render.return_value = "Plot B"

        controller = PlotCreationController(mock_api, mock_ui_state, mock_lifecycle, mock_registry)
        result = controller.render_selector()

        assert result is plot2
        # Also updated current ID
        mock_api.state_manager.set_current_plot_id.assert_called_once_with(2)

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsPresenter")
    def test_render_controls_handles_delete(
        self,
        mock_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_lifecycle: MagicMock,
        mock_registry: MagicMock,
    ) -> None:
        """Delete action cleans up UI state and calls lifecycle.delete_plot."""
        from src.web.controllers.plot.creation_controller import PlotCreationController

        mock_presenter.render.return_value = {
            "new_name": "Plot",
            "save_clicked": False,
            "load_clicked": False,
            "delete_clicked": True,
            "duplicate_clicked": False,
        }

        plot: MagicMock = MagicMock()
        plot.plot_id = 42
        plot.name = "Plot"

        controller = PlotCreationController(mock_api, mock_ui_state, mock_lifecycle, mock_registry)
        controller.render_controls(plot)

        # UI state cleanup
        mock_ui_state.plot.cleanup.assert_called_once_with(42)
        # Service call via injected lifecycle
        mock_lifecycle.delete_plot.assert_called_once_with(42, mock_api.state_manager)
        mock_st.rerun.assert_called()

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsPresenter")
    def test_render_controls_handles_rename(
        self,
        mock_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_lifecycle: MagicMock,
        mock_registry: MagicMock,
    ) -> None:
        """Rename updates the plot's name."""
        from src.web.controllers.plot.creation_controller import PlotCreationController

        mock_presenter.render.return_value = {
            "new_name": "Renamed",
            "save_clicked": False,
            "load_clicked": False,
            "delete_clicked": False,
            "duplicate_clicked": False,
        }
        mock_ui_state.plot.is_dialog_visible.return_value = False

        plot: MagicMock = MagicMock()
        plot.plot_id = 1
        plot.name = "Original"

        controller = PlotCreationController(mock_api, mock_ui_state, mock_lifecycle, mock_registry)
        controller.render_controls(plot)

        assert plot.name == "Renamed"


# ─── PipelineController Tests ───────────────────────────────────────────────


class TestPipelineController:
    """Tests for PipelineController."""

    @patch("src.web.controllers.plot.pipeline_controller.st")
    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    def test_render_shows_warning_when_no_data(
        self,
        mock_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_pipeline_executor: MagicMock,
    ) -> None:
        """Shows warning when no data is loaded."""
        from src.web.controllers.plot.pipeline_controller import PipelineController

        mock_api.state_manager.get_data.return_value = None

        plot: MagicMock = MagicMock()
        controller = PipelineController(mock_api, mock_ui_state, mock_pipeline_executor)
        controller.render(plot)

        mock_st.warning.assert_called_once()

    @patch("src.web.controllers.plot.pipeline_controller.st")
    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    def test_render_add_shaper_on_click(
        self,
        mock_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_pipeline_executor: MagicMock,
    ) -> None:
        """Adding a shaper appends to pipeline and reruns."""
        import pandas as pd

        from src.web.controllers.plot.pipeline_controller import PipelineController

        mock_api.state_manager.get_data.return_value = pd.DataFrame({"a": [1]})
        mock_presenter.render_add_shaper.return_value = {
            "add_clicked": True,
            "shaper_type": "sort",
        }

        # Make st.rerun() raise to simulate actual Streamlit behavior
        # (rerun halts execution)
        mock_st.rerun.side_effect = Exception("rerun")

        plot: MagicMock = MagicMock()
        plot.pipeline = []  # Empty pipeline → no steps to render
        plot.pipeline_counter = 0
        plot.plot_id = 1

        controller = PipelineController(mock_api, mock_ui_state, mock_pipeline_executor)

        with pytest.raises(Exception, match="rerun"):
            controller.render(plot)

        assert len(plot.pipeline) == 1
        assert plot.pipeline[0]["type"] == "sort"
        assert plot.pipeline_counter == 1
        mock_st.rerun.assert_called_once()

    @patch("src.web.controllers.plot.pipeline_controller.st")
    @patch("src.web.controllers.plot.pipeline_controller.PipelineStepPresenter")
    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    def test_incremental_pipeline_computation(
        self,
        mock_presenter: MagicMock,
        mock_step_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_pipeline_executor: MagicMock,
    ) -> None:
        """Pipeline steps use incremental output as input to the next step."""
        import pandas as pd

        from src.web.controllers.plot.pipeline_controller import PipelineController

        raw: pd.DataFrame = pd.DataFrame({"a": [1, 2]})
        step0_output: pd.DataFrame = pd.DataFrame({"a": [10, 20]})
        step1_output: pd.DataFrame = pd.DataFrame({"a": [100, 200]})

        mock_api.state_manager.get_data.return_value = raw
        mock_presenter.render_add_shaper.return_value = {"add_clicked": False}
        mock_presenter.render_finalize_button.return_value = False

        # Each call to render_step returns step_output used for next step
        mock_step_presenter.render_step.side_effect = [
            {
                "new_config": {"type": "sort"},
                "move_up": False,
                "move_down": False,
                "delete": False,
                "preview_data": step0_output.head(5),
                "preview_error": None,
                "step_output": step0_output,
            },
            {
                "new_config": {"type": "rename"},
                "move_up": False,
                "move_down": False,
                "delete": False,
                "preview_data": step1_output.head(5),
                "preview_error": None,
                "step_output": step1_output,
            },
        ]

        plot: MagicMock = MagicMock()
        plot.pipeline = [
            {"id": 0, "type": "sort", "config": {"type": "sort"}},
            {"id": 1, "type": "rename", "config": {"type": "rename"}},
        ]
        plot.plot_id = 1

        controller = PipelineController(mock_api, mock_ui_state, mock_pipeline_executor)
        controller.render(plot)

        # Verify step 0 receives raw_data
        call_args_0 = mock_step_presenter.render_step.call_args_list[0]
        assert call_args_0.kwargs["step_input"] is raw

        # Verify step 1 receives step 0's output (incremental, not raw)
        call_args_1 = mock_step_presenter.render_step.call_args_list[1]
        assert call_args_1.kwargs["step_input"] is step0_output

        # apply_shapers should NOT have been called by the controller
        # (only by PipelineStepPresenter internally, which we mocked)
        mock_pipeline_executor.apply_shapers.assert_not_called()


class TestPlotCreationControllerCallbacks:
    """Tests for callback-based Save/Load dialog in PlotCreationController."""

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsPresenter")
    def test_render_controls_passes_callbacks_to_presenter(
        self,
        mock_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_lifecycle: MagicMock,
        mock_registry: MagicMock,
    ) -> None:
        """render_controls passes on_save/on_load callbacks to presenter."""
        from src.web.controllers.plot.creation_controller import PlotCreationController

        mock_presenter.render.return_value = {
            "new_name": "Plot",
            "save_clicked": False,
            "load_clicked": False,
            "delete_clicked": False,
            "duplicate_clicked": False,
        }
        mock_ui_state.plot.is_dialog_visible.return_value = False

        plot: MagicMock = MagicMock()
        plot.plot_id = 1
        plot.name = "Plot"

        controller = PlotCreationController(mock_api, mock_ui_state, mock_lifecycle, mock_registry)
        controller.render_controls(plot)

        # on_save and on_load must be callable
        call_kwargs = mock_presenter.render.call_args.kwargs
        assert callable(call_kwargs["on_save"])
        assert callable(call_kwargs["on_load"])

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsPresenter")
    def test_save_callback_sets_dialog_visibility(
        self,
        mock_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_lifecycle: MagicMock,
        mock_registry: MagicMock,
    ) -> None:
        """Save callback sets save visible and load hidden."""
        from src.web.controllers.plot.creation_controller import PlotCreationController

        mock_presenter.render.return_value = {
            "new_name": "Plot",
            "save_clicked": False,
            "load_clicked": False,
            "delete_clicked": False,
            "duplicate_clicked": False,
        }
        mock_ui_state.plot.is_dialog_visible.return_value = False

        plot: MagicMock = MagicMock()
        plot.plot_id = 7
        plot.name = "Plot"

        controller = PlotCreationController(mock_api, mock_ui_state, mock_lifecycle, mock_registry)
        controller.render_controls(plot)

        # Extract and call the on_save callback
        on_save = mock_presenter.render.call_args.kwargs["on_save"]
        on_save()

        mock_ui_state.plot.set_dialog_visible.assert_any_call(7, "save", True)
        mock_ui_state.plot.set_dialog_visible.assert_any_call(7, "load", False)

    @patch("src.web.controllers.plot.creation_controller.st")
    @patch("src.web.controllers.plot.creation_controller.PlotControlsPresenter")
    def test_no_rerun_for_save_load_clicks(
        self,
        mock_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_lifecycle: MagicMock,
        mock_registry: MagicMock,
    ) -> None:
        """Save/Load clicks do NOT trigger st.rerun (callbacks handle it)."""
        from src.web.controllers.plot.creation_controller import PlotCreationController

        mock_presenter.render.return_value = {
            "new_name": "Plot",
            "save_clicked": True,  # save was clicked
            "load_clicked": False,
            "delete_clicked": False,
            "duplicate_clicked": False,
        }
        mock_ui_state.plot.is_dialog_visible.return_value = False

        plot: MagicMock = MagicMock()
        plot.plot_id = 1
        plot.name = "Plot"

        controller = PlotCreationController(mock_api, mock_ui_state, mock_lifecycle, mock_registry)
        controller.render_controls(plot)

        # No st.rerun() since callbacks handle dialog toggles
        mock_st.rerun.assert_not_called()


# ─── Error Resilience Tests ─────────────────────────────────────────────────


class TestPipelineControllerErrorResilience:
    """Verify that pipeline step errors don't kill the rest of the UI."""

    @patch("src.web.controllers.plot.pipeline_controller.st")
    @patch("src.web.controllers.plot.pipeline_controller.PipelineStepPresenter")
    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    def test_step_error_does_not_kill_loop(
        self,
        mock_presenter: MagicMock,
        mock_step_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_pipeline_executor: MagicMock,
    ) -> None:
        """A crashing step shows error but subsequent steps still render."""
        import pandas as pd

        from src.web.controllers.plot.pipeline_controller import PipelineController

        raw: pd.DataFrame = pd.DataFrame({"a": [1]})
        mock_api.state_manager.get_data.return_value = raw
        mock_presenter.render_add_shaper.return_value = {"add_clicked": False}
        mock_presenter.render_finalize_button.return_value = False

        step1_output: pd.DataFrame = pd.DataFrame({"b": [2]})

        # Step 0 crashes, Step 1 succeeds
        mock_step_presenter.render_step.side_effect = [
            ValueError("Column 'a' already exists"),
            {
                "new_config": {"type": "rename"},
                "move_up": False,
                "move_down": False,
                "delete": False,
                "preview_data": step1_output.head(5),
                "preview_error": None,
                "step_output": step1_output,
            },
        ]

        plot: MagicMock = MagicMock()
        plot.pipeline = [
            {"id": 0, "type": "transformer", "config": {}},
            {"id": 1, "type": "rename", "config": {"type": "rename"}},
        ]
        plot.plot_id = 1
        plot.name = "Test"

        controller = PipelineController(mock_api, mock_ui_state, mock_pipeline_executor)
        controller.render(plot)

        # Both steps were attempted
        assert mock_step_presenter.render_step.call_count == 2
        # Error was displayed for step 0
        mock_st.error.assert_called_once()
        assert "Step 1 error" in mock_st.error.call_args[0][0]
        # Finalize button was still rendered
        mock_presenter.render_finalize_button.assert_called_once()

    @patch("src.web.controllers.plot.pipeline_controller.st")
    @patch("src.web.controllers.plot.pipeline_controller.PipelineStepPresenter")
    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    def test_failed_step_preserves_last_good_input(
        self,
        mock_presenter: MagicMock,
        mock_step_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_pipeline_executor: MagicMock,
    ) -> None:
        """After a failed step, the next step gets the last good data."""
        import pandas as pd

        from src.web.controllers.plot.pipeline_controller import PipelineController

        raw: pd.DataFrame = pd.DataFrame({"a": [1]})
        step0_output: pd.DataFrame = pd.DataFrame({"a": [10]})
        mock_api.state_manager.get_data.return_value = raw
        mock_presenter.render_add_shaper.return_value = {"add_clicked": False}
        mock_presenter.render_finalize_button.return_value = False

        # Step 0 ok, Step 1 crashes, Step 2 ok
        mock_step_presenter.render_step.side_effect = [
            {
                "new_config": {"type": "sort"},
                "move_up": False,
                "move_down": False,
                "delete": False,
                "preview_data": None,
                "preview_error": None,
                "step_output": step0_output,
            },
            RuntimeError("duplicate column"),
            {
                "new_config": {"type": "mean"},
                "move_up": False,
                "move_down": False,
                "delete": False,
                "preview_data": None,
                "preview_error": None,
                "step_output": None,
            },
        ]

        plot: MagicMock = MagicMock()
        plot.pipeline = [
            {"id": 0, "type": "sort", "config": {}},
            {"id": 1, "type": "transformer", "config": {}},
            {"id": 2, "type": "mean", "config": {}},
        ]
        plot.plot_id = 1
        plot.name = "Test"

        controller = PipelineController(mock_api, mock_ui_state, mock_pipeline_executor)
        controller.render(plot)

        # Step 2 got step 0's output (step 1 failed, no advancement)
        call_args_2 = mock_step_presenter.render_step.call_args_list[2]
        assert call_args_2.kwargs["step_input"] is step0_output


class TestRenderControllerErrorResilience:
    """Verify that config errors don't kill the chart display."""

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ChartPresenter")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter")
    def test_type_config_error_still_renders_chart(
        self,
        mock_config_presenter: MagicMock,
        mock_chart_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_lifecycle: MagicMock,
        mock_registry: MagicMock,
        mock_chart_display: MagicMock,
    ) -> None:
        """Config error shows st.error but chart still renders."""
        import pandas as pd

        from src.web.controllers.plot.render_controller import PlotRenderController

        mock_registry.get_available_types.return_value = ["bar"]
        mock_config_presenter.render_plot_type_selector.return_value = {
            "type_changed": False,
            "new_type": "bar",
        }
        # Type-specific config raises
        mock_config_presenter.render_type_config.side_effect = KeyError("bad col")
        # Advanced config succeeds
        mock_config_presenter.render_advanced_and_theme.return_value = {}

        mock_chart_presenter.render_refresh_controls.return_value = {
            "auto_refresh": True,
            "manual_refresh": False,
            "should_generate": True,
        }
        mock_ui_state.plot.get_auto_refresh.return_value = True

        plot: MagicMock = MagicMock()
        plot.processed_data = pd.DataFrame({"x": [1]})
        plot.config = {}
        plot.plot_type = "bar"
        plot.plot_id = 1
        plot.name = "Test"

        controller = PlotRenderController(
            mock_api,
            mock_ui_state,
            mock_lifecycle,
            mock_registry,
            mock_chart_display,
        )
        controller.render(plot)

        # Error was shown
        mock_st.error.assert_called()
        # Chart was still rendered (but should_gen=False due to config error)
        mock_chart_display.render_chart.assert_called_once()
        # should_gen is False because config_error=True
        call_args = mock_chart_display.render_chart.call_args
        assert call_args[0][1] is False  # should_gen

    @patch("src.web.controllers.plot.render_controller.st")
    @patch("src.web.controllers.plot.render_controller.ChartPresenter")
    @patch("src.web.controllers.plot.render_controller.ConfigPresenter")
    def test_advanced_config_error_still_renders_chart(
        self,
        mock_config_presenter: MagicMock,
        mock_chart_presenter: MagicMock,
        mock_st: MagicMock,
        mock_api: MagicMock,
        mock_ui_state: MagicMock,
        mock_lifecycle: MagicMock,
        mock_registry: MagicMock,
        mock_chart_display: MagicMock,
    ) -> None:
        """Advanced options error shows st.error but chart still renders."""
        import pandas as pd

        from src.web.controllers.plot.render_controller import PlotRenderController

        mock_registry.get_available_types.return_value = ["bar"]
        mock_config_presenter.render_plot_type_selector.return_value = {
            "type_changed": False,
            "new_type": "bar",
        }
        mock_config_presenter.render_type_config.return_value = {"x": "col"}
        # Advanced config raises
        mock_config_presenter.render_advanced_and_theme.side_effect = ValueError("invalid margin")

        mock_chart_presenter.render_refresh_controls.return_value = {
            "auto_refresh": True,
            "manual_refresh": False,
            "should_generate": True,
        }
        mock_ui_state.plot.get_auto_refresh.return_value = True

        plot: MagicMock = MagicMock()
        plot.processed_data = pd.DataFrame({"x": [1]})
        plot.config = {}
        plot.plot_type = "bar"
        plot.plot_id = 1
        plot.name = "Test"

        controller = PlotRenderController(
            mock_api,
            mock_ui_state,
            mock_lifecycle,
            mock_registry,
            mock_chart_display,
        )
        controller.render(plot)

        # Error displayed
        mock_st.error.assert_called()
        # Chart container still rendered (with should_gen=False)
        mock_chart_display.render_chart.assert_called_once()
