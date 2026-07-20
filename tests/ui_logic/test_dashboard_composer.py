"""UI orchestration tests for the human-first dashboard composer."""

from unittest.mock import MagicMock, patch

import plotly.graph_objects as go

from src.core.models.visualization.dashboard_spec import DashboardSpec
from src.web.components.plotting.dashboard_composer import DashboardComposer
from tests.ui_logic.conftest import StubPlotHandle

_MODULE = "src.web.components.plotting.dashboard_composer"


@patch(f"{_MODULE}.plotly_download_bytes", return_value=b"<html></html>")
@patch(f"{_MODULE}.render_dashboard", return_value=go.Figure())
@patch(f"{_MODULE}.st")
def test_composer_builds_previews_and_exports_selected_panels(
    mock_st: MagicMock,
    mock_render_dashboard: MagicMock,
    _mock_export: MagicMock,
) -> None:
    # [test->req~ring5.plots.multi-panel-dashboard~1]
    first = StubPlotHandle(plot_id=1, name="First", plot_type="bar")
    second = StubPlotHandle(plot_id=2, name="Second", plot_type="line")
    api = MagicMock()
    api.state_manager.get_plots.return_value = [first, second]
    spec = DashboardSpec(
        plot_ids=(1, 2),
        rows=1,
        columns=2,
        panel_titles=("First", "Second"),
        title="Analysis dashboard",
        width=1200,
        height=480,
        shared_legend=True,
    )
    api.create_dashboard.return_value = spec

    mock_st.session_state = {}
    mock_st.columns.side_effect = lambda count: [MagicMock() for _ in range(count)]
    mock_st.multiselect.return_value = [1, 2]
    mock_st.text_input.side_effect = ["Analysis dashboard", "", ""]
    mock_st.number_input.side_effect = [2, 1200, 480]
    mock_st.toggle.side_effect = [False, False, True]
    mock_st.pills.side_effect = ["plotly", "html"]
    mock_st.button.return_value = True

    with (
        patch(f"{_MODULE}.EngineManager.get_engine", return_value="plotly"),
        patch(f"{_MODULE}.EngineManager.set_engine"),
    ):
        DashboardComposer(api).render()

    api.create_dashboard.assert_called_once_with(
        [1, 2],
        title="Analysis dashboard",
        rows=1,
        columns=2,
        width=1200,
        height=480,
        shared_xaxes=False,
        shared_yaxes=False,
        shared_legend=True,
        x_title="",
        y_title="",
    )
    mock_render_dashboard.assert_called_once_with([first, second], spec, engine="plotly")
    mock_st.plotly_chart.assert_called_once()
    mock_st.download_button.assert_called_once()


@patch(f"{_MODULE}.st")
def test_composer_explains_that_two_plots_are_required(mock_st: MagicMock) -> None:
    api = MagicMock()
    api.state_manager.get_plots.return_value = [StubPlotHandle()]

    DashboardComposer(api).render()

    mock_st.info.assert_called_once_with("Create at least two plots to build a dashboard.")
    api.create_dashboard.assert_not_called()
