"""Tests for the human-first report builder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from src.core.models import EnvironmentMetadata
from src.core.models.visualization.dashboard_spec import DashboardSpec
from src.web.pages.ui.plotting.plot_factory import PlotFactory


def _context() -> MagicMock:
    value = MagicMock()
    value.__enter__.return_value = value
    value.__exit__.return_value = False
    return value


def _environment() -> EnvironmentMetadata:
    return EnvironmentMetadata(1, "1.0.0", "3.14", "CPython", "Linux", "x86_64")


@patch("src.web.components.report_composer.EnvironmentMetadataService.capture")
@patch("src.web.components.report_composer.render_report", return_value=b"<html>report</html>")
@patch("src.web.components.report_composer.st")
def test_report_composer_builds_panel_table_narrative_and_download(
    mock_st: MagicMock, mock_render: MagicMock, mock_environment: MagicMock
) -> None:
    # [test->req~ring5.export.batch-reports~1]
    from src.web.components.report_composer import ReportComposer

    data = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 1.2]})
    first = PlotFactory.create_plot("bar", 1, "Bars")
    second = PlotFactory.create_plot("line", 2, "Trend")
    for plot in (first, second):
        plot.processed_data = data
        plot.config = {"x": "benchmark", "y": "ipc"}

    api = MagicMock()
    state = api.state_manager
    state.get_plots.return_value = [first, second]
    state.get_data.return_value = data
    state.is_using_parser.return_value = False
    state.get_csv_path.return_value = "measurements.csv"
    state.get_stats_path.return_value = ""
    state.get_stats_pattern.return_value = "stats.txt"
    state.get_parse_variables.return_value = []
    state.get_portfolio_history.return_value = []
    api.create_dashboard.return_value = DashboardSpec(
        plot_ids=(1, 2),
        rows=1,
        columns=2,
        panel_titles=("Bars", "Trend"),
        title="Selected figures",
        panel_labels=("(a)", "(b)"),
    )
    mock_environment.return_value = _environment()

    mock_st.expander.return_value = _context()
    mock_st.columns.return_value = [_context(), _context(), _context()]
    mock_st.multiselect.return_value = [1, 2]
    mock_st.text_input.side_effect = ["Performance report", "Finding"]
    mock_st.text_area.return_value = "IPC improved."
    mock_st.checkbox.side_effect = [True, True]
    mock_st.number_input.return_value = 2
    mock_st.radio.return_value = "HTML"
    mock_st.button.return_value = True
    mock_st.session_state = {}

    ReportComposer(api).render()

    report = mock_render.call_args.args[1]
    assert report.title == "Performance report"
    assert report.figures[0].dashboard is not None
    assert report.tables[0].title == "Current workspace data"
    assert report.narrative[0].heading == "Finding"
    assert report.provenance.source_kind == "CSV"
    mock_st.download_button.assert_called_once()
    assert mock_st.download_button.call_args.kwargs["data"] == b"<html>report</html>"
    assert mock_st.download_button.call_args.kwargs["file_name"] == "Performance report.html"


@patch("src.web.components.report_composer.st")
def test_report_composer_explains_missing_plots(mock_st: MagicMock) -> None:
    from src.web.components.report_composer import ReportComposer

    api = MagicMock()
    api.state_manager.get_plots.return_value = []
    mock_st.expander.return_value = _context()

    ReportComposer(api).render()

    mock_st.info.assert_called_once_with("Create at least one plot before building a report.")
