from unittest.mock import MagicMock, patch

import pytest

from src.web.ui.components.plot_manager_components import PlotManagerComponents


@pytest.fixture
def mock_streamlit():
    with patch("src.web.ui.components.plot_manager_components.st") as mock_st:
        mock_st.session_state = {}

        # Mock columns
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]

        mock_st.columns.side_effect = columns_side_effect

        mock_st.button.return_value = False

        yield mock_st


@pytest.fixture
def mock_pipeline_service():
    with patch("src.web.ui.components.plot_manager_components.PipelineService") as mock_ps:
        yield mock_ps


@pytest.fixture
def mock_plot():
    plot = MagicMock()
    plot.name = "TestPlot"
    plot.plot_id = "test_id"
    plot.pipeline = [{"type": "sort", "config": {}}]
    return plot


def test_save_pipeline_dialog_success(mock_streamlit, mock_pipeline_service, mock_plot):
    # Setup inputs
    mock_streamlit.text_input.return_value = "MyPipeline"

    # Simulate Save button click
    mock_streamlit.button.side_effect = lambda label, **k: label == "Save"

    PlotManagerComponents._render_save_pipeline_dialog(mock_plot)

    mock_pipeline_service.save_pipeline.assert_called_with(
        "MyPipeline", mock_plot.pipeline, description="Source: TestPlot"
    )
    mock_streamlit.success.assert_called()
    mock_streamlit.rerun.assert_called()
    assert mock_streamlit.session_state["show_save_for_plot_test_id"] is False


def test_save_pipeline_dialog_cancel(mock_streamlit, mock_pipeline_service, mock_plot):
    mock_streamlit.button.side_effect = lambda label, **k: label == "Cancel"

    PlotManagerComponents._render_save_pipeline_dialog(mock_plot)

    mock_pipeline_service.save_pipeline.assert_not_called()
    assert mock_streamlit.session_state["show_save_for_plot_test_id"] is False
    mock_streamlit.rerun.assert_called()


def test_load_pipeline_dialog_empty(mock_streamlit, mock_pipeline_service, mock_plot):
    mock_pipeline_service.list_pipelines.return_value = []

    # Close button click
    mock_streamlit.button.side_effect = lambda label, **k: label == "Close"

    PlotManagerComponents._render_load_pipeline_dialog(mock_plot)

    mock_streamlit.warning.assert_called_with("No saved pipelines found.")
    assert mock_streamlit.session_state["show_load_for_plot_test_id"] is False
    mock_streamlit.rerun.assert_called()


def test_load_pipeline_dialog_success(mock_streamlit, mock_pipeline_service, mock_plot):
    mock_pipeline_service.list_pipelines.return_value = ["MyPipe"]
    mock_pipeline_service.load_pipeline.return_value = {"pipeline": [{"type": "mean"}]}

    mock_streamlit.selectbox.return_value = "MyPipe"
    mock_streamlit.button.side_effect = lambda label, **k: label == "Load"

    PlotManagerComponents._render_load_pipeline_dialog(mock_plot)

    mock_pipeline_service.load_pipeline.assert_called_with("MyPipe")
    # Verify plot updated (deep copied)
    assert len(mock_plot.pipeline) == 1
    assert mock_plot.pipeline[0]["type"] == "mean"
    assert mock_plot.processed_data is None  # Should reset

    mock_streamlit.success.assert_called()
    assert mock_streamlit.session_state["show_load_for_plot_test_id"] is False
    mock_streamlit.rerun.assert_called()


def test_load_pipeline_dialog_cancel(mock_streamlit, mock_pipeline_service, mock_plot):
    mock_pipeline_service.list_pipelines.return_value = ["MyPipe"]
    mock_streamlit.button.side_effect = lambda label, **k: label == "Cancel"

    PlotManagerComponents._render_load_pipeline_dialog(mock_plot)

    mock_pipeline_service.load_pipeline.assert_not_called()
    assert mock_streamlit.session_state["show_load_for_plot_test_id"] is False
