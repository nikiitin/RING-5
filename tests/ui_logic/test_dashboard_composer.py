"""UI orchestration tests for the human-first dashboard composer."""

from unittest.mock import MagicMock, patch

import plotly.graph_objects as go

from src.core.models.visualization.dashboard_spec import DashboardSpec
from src.core.models.visualization.linked_selection_spec import LinkedSelectionSpec
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
    mock_st.toggle.side_effect = [False, False, True, False, False]
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


@patch(f"{_MODULE}.plotly_download_bytes", return_value=b"<html></html>")
@patch(f"{_MODULE}.render_dashboard", return_value=go.Figure())
@patch(f"{_MODULE}.st")
def test_composer_exposes_publication_labels_captions_and_spacing(
    mock_st: MagicMock,
    _mock_render_dashboard: MagicMock,
    _mock_export: MagicMock,
) -> None:
    # [test->req~ring5.figure.panel-composition~1]
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
        panel_labels=("(a)", "(b)"),
        panel_captions=("Baseline", "Optimized"),
        horizontal_spacing=0.05,
        vertical_spacing=0.12,
    )
    api.create_dashboard.return_value = spec

    mock_st.session_state = {
        "dashboard.composer.horizontal_spacing": 30,
        "dashboard.composer.vertical_spacing": 30,
    }
    mock_st.columns.side_effect = lambda count: [MagicMock() for _ in range(count)]
    mock_st.multiselect.return_value = [1, 2]
    mock_st.text_input.side_effect = ["Analysis dashboard", "", ""]
    mock_st.text_area.return_value = "Baseline\nOptimized"
    mock_st.number_input.side_effect = [2, 1200, 480]
    mock_st.toggle.side_effect = [False, False, True, True, False]
    mock_st.pills.side_effect = ["automatic", "plotly", "html"]
    mock_st.slider.side_effect = [5, 12]
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
        panel_labels="auto",
        panel_captions=("Baseline", "Optimized"),
        horizontal_spacing=0.05,
        vertical_spacing=0.12,
    )
    assert mock_st.session_state["dashboard.composer.horizontal_spacing"] == 20
    assert mock_st.session_state["dashboard.composer.vertical_spacing"] == 20


def test_publication_text_helpers_preserve_alignment_and_bound_spacing() -> None:
    assert DashboardComposer._panel_lines("", 3) == ("", "", "")
    assert DashboardComposer._panel_lines("One\n\nThree", 3) == ("One", "", "Three")
    assert DashboardComposer._maximum_gap_percent(1) == 20
    assert DashboardComposer._maximum_gap_percent(6) == 19


@patch(f"{_MODULE}.st")
def test_composer_explains_that_two_plots_are_required(mock_st: MagicMock) -> None:
    api = MagicMock()
    api.state_manager.get_plots.return_value = [StubPlotHandle()]

    DashboardComposer(api).render()

    mock_st.info.assert_called_once_with("Create at least two plots to build a dashboard.")
    api.create_dashboard.assert_not_called()


@patch(f"{_MODULE}.interactive_plotly_chart")
@patch(f"{_MODULE}.st")
def test_linked_preview_consumes_selection_and_keeps_base_figure(
    mock_st: MagicMock,
    mock_chart: MagicMock,
) -> None:
    # [test->req~ring5.plots.linked-selections~1]
    figure = go.Figure(
        data=[
            go.Bar(x=["A", "B"], y=[1, 2]),
            go.Scatter(x=["A", "B"], y=[3, 4], mode="markers"),
        ]
    )
    snapshot = figure.to_plotly_json()
    event = {"kind": "selection", "points": [{"x": "B", "y": 2}]}
    mock_chart.return_value = event
    mock_st.session_state = {}
    spec = LinkedSelectionSpec((1, 2), axis="x", mode="highlight")

    DashboardComposer._render_plotly_preview(figure, spec)

    rendered = mock_chart.call_args.args[0]
    assert rendered.layout.dragmode == "select"
    assert mock_chart.call_args.kwargs["capture_selection"] is True
    assert mock_st.session_state["dashboard.composer.selection.values"] == ("B",)
    assert figure.to_plotly_json() == snapshot
    mock_st.rerun.assert_called_once()


@patch(f"{_MODULE}.interactive_plotly_chart")
@patch(f"{_MODULE}.st")
def test_linked_preview_clear_rotates_component_identity(
    mock_st: MagicMock,
    mock_chart: MagicMock,
) -> None:
    mock_st.session_state = {
        "dashboard.composer.selection.values": ("A",),
        "dashboard.composer.selection.config": ((1, 2), "x", "highlight"),
        "dashboard.composer.selection.generation": 2,
    }
    mock_st.columns.return_value = [MagicMock(), MagicMock()]
    mock_st.button.return_value = True
    spec = LinkedSelectionSpec((1, 2))

    DashboardComposer._render_plotly_preview(go.Figure(go.Bar(x=["A"], y=[1])), spec)

    assert "dashboard.composer.selection.values" not in mock_st.session_state
    assert mock_st.session_state["dashboard.composer.selection.generation"] == 3
    mock_st.rerun.assert_called_once()
    mock_chart.assert_not_called()
