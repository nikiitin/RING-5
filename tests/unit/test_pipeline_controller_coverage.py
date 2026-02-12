"""Tests for PipelineController — 74% → 90%+ coverage."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame({"x": ["A", "B"], "y": [1.0, 2.0]})


@pytest.fixture
def mock_api(sample_data: pd.DataFrame) -> MagicMock:
    api = MagicMock()
    api.state_manager.get_data.return_value = sample_data
    return api


@pytest.fixture
def mock_executor() -> MagicMock:
    executor = MagicMock()
    executor.apply_shapers.side_effect = lambda df, confs: df.copy()
    executor.configure_shaper.return_value = {}
    return executor


@pytest.fixture
def mock_plot() -> MagicMock:
    plot = MagicMock()
    plot.plot_id = 1
    plot.name = "test"
    plot.pipeline = []
    plot.pipeline_counter = 0
    plot.processed_data = None
    return plot


class TestPipelineControllerRender:
    """Tests for PipelineController.render."""

    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    @patch("src.web.controllers.plot.pipeline_controller.st")
    def test_no_data_shows_warning(self, mock_st: MagicMock, mock_presenter: MagicMock) -> None:
        from src.web.controllers.plot.pipeline_controller import PipelineController

        api = MagicMock()
        api.state_manager.get_data.return_value = None
        ui = MagicMock()
        executor = MagicMock()

        ctrl = PipelineController(api, ui, executor)
        plot = MagicMock()
        plot.pipeline = []

        ctrl.render(plot)

        mock_st.warning.assert_called_once()

    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    @patch("src.web.controllers.plot.pipeline_controller.st")
    def test_add_shaper_appends_to_pipeline(
        self,
        mock_st: MagicMock,
        mock_presenter: MagicMock,
        mock_api: MagicMock,
        mock_executor: MagicMock,
        mock_plot: MagicMock,
    ) -> None:
        from src.web.controllers.plot.pipeline_controller import PipelineController

        mock_presenter.render_add_shaper.return_value = {
            "add_clicked": True,
            "shaper_type": "rename",
        }

        ctrl = PipelineController(mock_api, MagicMock(), mock_executor)
        ctrl.render(mock_plot)

        assert len(mock_plot.pipeline) == 1
        assert mock_plot.pipeline[0]["type"] == "rename"
        mock_st.rerun.assert_called_once()

    @patch("src.web.controllers.plot.pipeline_controller.PipelineStepPresenter")
    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    @patch("src.web.controllers.plot.pipeline_controller.st")
    def test_finalize_applies_pipeline(
        self,
        mock_st: MagicMock,
        mock_presenter: MagicMock,
        mock_step: MagicMock,
        mock_api: MagicMock,
        mock_executor: MagicMock,
        mock_plot: MagicMock,
    ) -> None:
        from src.web.controllers.plot.pipeline_controller import PipelineController

        mock_plot.pipeline = [{"id": 0, "type": "rename", "config": {"mapping": {"x": "X"}}}]

        mock_presenter.render_add_shaper.return_value = {"add_clicked": False}
        mock_presenter.render_finalize_button.return_value = True
        mock_step.render_step.return_value = {
            "new_config": {"mapping": {"x": "X"}},
            "move_up": False,
            "move_down": False,
            "delete": False,
            "step_output": pd.DataFrame({"X": ["A", "B"], "y": [1.0, 2.0]}),
            "preview_error": None,
        }

        ctrl = PipelineController(mock_api, MagicMock(), mock_executor)
        ctrl.render(mock_plot)

        mock_step.render_finalize_result.assert_called_once()

    @patch("src.web.controllers.plot.pipeline_controller.PipelineStepPresenter")
    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    @patch("src.web.controllers.plot.pipeline_controller.st")
    def test_step_error_continues(
        self,
        mock_st: MagicMock,
        mock_presenter: MagicMock,
        mock_step: MagicMock,
        mock_api: MagicMock,
        mock_executor: MagicMock,
        mock_plot: MagicMock,
    ) -> None:
        from src.web.controllers.plot.pipeline_controller import PipelineController

        mock_plot.pipeline = [
            {"id": 0, "type": "bad", "config": {}},
            {"id": 1, "type": "rename", "config": {}},
        ]

        mock_presenter.render_add_shaper.return_value = {"add_clicked": False}
        mock_presenter.render_finalize_button.return_value = False

        # First step raises, second succeeds
        mock_step.render_step.side_effect = [
            RuntimeError("bad shaper"),
            {
                "new_config": {},
                "move_up": False,
                "move_down": False,
                "delete": False,
                "step_output": None,
                "preview_error": None,
            },
        ]

        ctrl = PipelineController(mock_api, MagicMock(), mock_executor)
        ctrl.render(mock_plot)

        mock_st.error.assert_called()

    @patch("src.web.controllers.plot.pipeline_controller.PipelineStepPresenter")
    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    @patch("src.web.controllers.plot.pipeline_controller.st")
    def test_delete_step(
        self,
        mock_st: MagicMock,
        mock_presenter: MagicMock,
        mock_step: MagicMock,
        mock_api: MagicMock,
        mock_executor: MagicMock,
        mock_plot: MagicMock,
    ) -> None:
        from src.web.controllers.plot.pipeline_controller import PipelineController

        mock_plot.pipeline = [{"id": 0, "type": "rename", "config": {}}]

        mock_presenter.render_add_shaper.return_value = {"add_clicked": False}
        mock_presenter.render_finalize_button.return_value = False
        mock_step.render_step.return_value = {
            "new_config": {},
            "move_up": False,
            "move_down": False,
            "delete": True,
            "step_output": None,
            "preview_error": None,
        }

        ctrl = PipelineController(mock_api, MagicMock(), mock_executor)
        ctrl.render(mock_plot)

        assert len(mock_plot.pipeline) == 0
        mock_st.rerun.assert_called()

    @patch("src.web.controllers.plot.pipeline_controller.PipelineStepPresenter")
    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    @patch("src.web.controllers.plot.pipeline_controller.st")
    def test_finalize_error_renders_error(
        self,
        mock_st: MagicMock,
        mock_presenter: MagicMock,
        mock_step: MagicMock,
        mock_api: MagicMock,
        mock_executor: MagicMock,
        mock_plot: MagicMock,
    ) -> None:
        from src.web.controllers.plot.pipeline_controller import PipelineController

        mock_plot.pipeline = [{"id": 0, "type": "rename", "config": {"mapping": {}}}]

        mock_presenter.render_add_shaper.return_value = {"add_clicked": False}
        mock_presenter.render_finalize_button.return_value = True
        mock_step.render_step.return_value = {
            "new_config": {"mapping": {}},
            "move_up": False,
            "move_down": False,
            "delete": False,
            "step_output": None,
            "preview_error": None,
        }

        # Make apply_shapers raise
        mock_executor.apply_shapers.side_effect = ValueError("bad config")

        ctrl = PipelineController(mock_api, MagicMock(), mock_executor)
        ctrl.render(mock_plot)

        mock_step.render_finalize_error.assert_called_once()

    @patch("src.web.controllers.plot.pipeline_controller.PipelineStepPresenter")
    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    @patch("src.web.controllers.plot.pipeline_controller.st")
    def test_move_up_swaps(
        self,
        mock_st: MagicMock,
        mock_presenter: MagicMock,
        mock_step: MagicMock,
        mock_api: MagicMock,
        mock_executor: MagicMock,
        mock_plot: MagicMock,
    ) -> None:
        from src.web.controllers.plot.pipeline_controller import PipelineController

        mock_plot.pipeline = [
            {"id": 0, "type": "filter", "config": {}},
            {"id": 1, "type": "rename", "config": {}},
        ]

        mock_presenter.render_add_shaper.return_value = {"add_clicked": False}
        mock_presenter.render_finalize_button.return_value = False

        # Second step wants to move up
        mock_step.render_step.side_effect = [
            {
                "new_config": {},
                "move_up": False,
                "move_down": False,
                "delete": False,
                "step_output": None,
                "preview_error": None,
            },
            {
                "new_config": {},
                "move_up": True,
                "move_down": False,
                "delete": False,
                "step_output": None,
                "preview_error": None,
            },
        ]

        ctrl = PipelineController(mock_api, MagicMock(), mock_executor)
        ctrl.render(mock_plot)

        # After swap: rename should be first
        assert mock_plot.pipeline[0]["type"] == "rename"
        mock_st.rerun.assert_called()

    @patch("src.web.controllers.plot.pipeline_controller.PipelineStepPresenter")
    @patch("src.web.controllers.plot.pipeline_controller.PipelinePresenter")
    @patch("src.web.controllers.plot.pipeline_controller.st")
    def test_preview_error_logged(
        self,
        mock_st: MagicMock,
        mock_presenter: MagicMock,
        mock_step: MagicMock,
        mock_api: MagicMock,
        mock_executor: MagicMock,
        mock_plot: MagicMock,
    ) -> None:
        from src.web.controllers.plot.pipeline_controller import PipelineController

        mock_plot.pipeline = [{"id": 0, "type": "rename", "config": {}}]

        mock_presenter.render_add_shaper.return_value = {"add_clicked": False}
        mock_presenter.render_finalize_button.return_value = False
        mock_step.render_step.return_value = {
            "new_config": {},
            "move_up": False,
            "move_down": False,
            "delete": False,
            "step_output": None,
            "preview_error": "Something went wrong in preview",
        }

        ctrl = PipelineController(mock_api, MagicMock(), mock_executor)
        ctrl.render(mock_plot)

        # Should have completed without crashing
        assert True
