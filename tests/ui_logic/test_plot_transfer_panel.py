"""Behavioral tests for the plot-content copy workflow."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.core.models.visualization.plot_transfer_result import PlotTransferResult


@patch("src.web.components.plotting.plot_transfer_panel.st")
def test_selected_sections_copy_into_current_plot(mock_st: MagicMock) -> None:
    # [test->req~ring5.plots.copy-settings-pipeline~1]
    from src.web.components.plotting.plot_transfer_panel import PlotTransferPanel

    source = SimpleNamespace(plot_id=1, name="Source", plot_type="bar", config={})
    target = SimpleNamespace(plot_id=2, name="Target", plot_type="line", config={"title": "Copied"})
    api = MagicMock()
    api.copy_plot_content.return_value = PlotTransferResult(
        1, 2, "settings", copied_keys=("title", "color_palette")
    )
    mock_st.expander.return_value = nullcontext()
    mock_st.selectbox.return_value = 1
    mock_st.radio.return_value = "Selected figure settings"
    mock_st.multiselect.return_value = ["Titles and labels", "Colors and series styles"]
    mock_st.button.return_value = True
    mock_st.session_state = {}

    PlotTransferPanel(api).render(target, [source, target])

    api.copy_plot_content.assert_called_once_with(1, 2, "settings", sections=["labels", "colors"])
    assert mock_st.session_state["plot_transfer_notice_2"] == "Copied 2 configuration values."
    assert mock_st.session_state["plot_transfer_reset_2"] == {"title": "Copied"}
    mock_st.rerun.assert_called_once_with()


@patch("src.web.components.plotting.plot_transfer_panel.st")
def test_pipeline_copy_explains_finalize_and_surfaces_validation(mock_st: MagicMock) -> None:
    from src.web.components.plotting.plot_transfer_panel import PlotTransferPanel

    source = SimpleNamespace(plot_id=1, name="Source", plot_type="bar", config={})
    target = SimpleNamespace(plot_id=2, name="Target", plot_type="bar", config={})
    api = MagicMock()
    mock_st.expander.return_value = nullcontext()
    mock_st.selectbox.return_value = 1
    mock_st.radio.return_value = "Shaping pipeline"
    mock_st.button.return_value = True
    mock_st.session_state = {}
    api.copy_plot_content.side_effect = ValueError("Incompatible source data")

    PlotTransferPanel(api).render(target, [source, target])

    mock_st.error.assert_called_once_with("Incompatible source data")


@patch("src.web.components.plotting.plot_transfer_panel.st")
def test_pending_reset_runs_before_destination_widgets_are_created(mock_st: MagicMock) -> None:
    from src.web.components.plotting.plot_transfer_panel import PlotTransferPanel

    mock_st.session_state = {
        "plot_transfer_reset_2": {"title": "Copied title", "xlabel": "Workload"},
        "title_2": "Stale title",
        "plot.2.mpl_fig": object(),
        "title_1": "Other plot",
    }

    PlotTransferPanel.apply_pending_widget_reset(2)

    assert mock_st.session_state == {
        "title_1": "Other plot",
        "title_2": "Copied title",
        "xlabel_2": "Workload",
    }
