from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.web.pages.ui.components.plot_manager_components import PlotManagerComponents
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_streamlit() -> Generator[None, None, None]:
    with patch("src.web.pages.ui.components.plot_manager_components.st") as mock_st:
        mock_st.session_state = {}

        mock_st.columns.side_effect = columns_side_effect

        mock_st.button.return_value = False

        yield mock_st


@pytest.fixture
def mock_api() -> Any:
    """Create a mock ApplicationAPI with pipeline sub-API."""
    api = MagicMock()
    return api


@pytest.fixture
def mock_plot() -> Any:
    plot = MagicMock()
    plot.name = "TestPlot"
    plot.plot_id = "test_id"
    plot.pipeline = [{"type": "sort", "config": {}}]
    return plot


def test_save_pipeline_dialog_success(mock_streamlit: Any, mock_api: Any, mock_plot: Any) -> None:

    # Setup inputs
    mock_streamlit.text_input.return_value = "MyPipeline"

    # Simulate Save button click
    mock_streamlit.button.side_effect = lambda label, **k: label == "Save"

    PlotManagerComponents._render_save_pipeline_dialog(mock_api, mock_plot)

    mock_api.shapers.save_pipeline.assert_called_with(
        "MyPipeline", mock_plot.pipeline, description="Source: TestPlot"
    )
    mock_streamlit.toast.assert_called()
    mock_streamlit.rerun.assert_called()
    assert mock_streamlit.session_state["plot.test_id.dialog.save"] is False


def test_save_pipeline_dialog_cancel(mock_streamlit: Any, mock_api: Any, mock_plot: Any) -> None:

    def button_side_effect(label: Any, on_click: Any = None, **k: Any) -> int:

        if label == "Cancel":
            if on_click:
                on_click()
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    PlotManagerComponents._render_save_pipeline_dialog(mock_api, mock_plot)

    mock_api.shapers.save_pipeline.assert_not_called()
    assert mock_streamlit.session_state["plot.test_id.dialog.save"] is False


def test_load_pipeline_dialog_empty(mock_streamlit: Any, mock_api: Any, mock_plot: Any) -> None:

    mock_api.shapers.list_pipelines.return_value = []

    # Close button click
    def button_side_effect(label: Any, on_click: Any = None, **k: Any) -> int:

        if label == "Close":
            if on_click:
                on_click()
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    PlotManagerComponents._render_load_pipeline_dialog(mock_api, mock_plot)

    mock_streamlit.warning.assert_called_with("No saved pipelines found.")
    assert mock_streamlit.session_state["plot.test_id.dialog.load"] is False


def test_load_pipeline_dialog_success(mock_streamlit: Any, mock_api: Any, mock_plot: Any) -> None:

    mock_api.shapers.list_pipelines.return_value = ["MyPipe"]
    mock_api.shapers.load_pipeline.return_value = {"pipeline": [{"type": "mean"}]}

    mock_streamlit.selectbox.return_value = "MyPipe"
    mock_streamlit.button.side_effect = lambda label, **k: label == "Load"

    PlotManagerComponents._render_load_pipeline_dialog(mock_api, mock_plot)

    mock_api.shapers.load_pipeline.assert_called_with("MyPipe")
    # Verify plot updated (deep copied)
    assert len(mock_plot.pipeline) == 1
    assert mock_plot.pipeline[0]["type"] == "mean"
    assert mock_plot.processed_data is None  # Should reset

    mock_streamlit.toast.assert_called()
    assert mock_streamlit.session_state["plot.test_id.dialog.load"] is False
    mock_streamlit.rerun.assert_called()


def test_load_pipeline_dialog_cancel(mock_streamlit: Any, mock_api: Any, mock_plot: Any) -> None:

    mock_api.shapers.list_pipelines.return_value = ["MyPipe"]

    def button_side_effect(label: Any, on_click: Any = None, **k: Any) -> int:

        if label == "Cancel":
            if on_click:
                on_click()
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    PlotManagerComponents._render_load_pipeline_dialog(mock_api, mock_plot)

    mock_api.shapers.load_pipeline.assert_not_called()
    assert mock_streamlit.session_state["plot.test_id.dialog.load"] is False
