"""UI logic tests for background parsing status and actions."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import ParseJobReceipt, ParseJobSnapshot, ParseJobStatus
from src.web.components.data_source import data_source_components
from src.web.components.data_source import parse_job_status


def _snapshot(status: ParseJobStatus, *, job_id: str = "job-1") -> ParseJobSnapshot:
    return ParseJobSnapshot(
        job_id=job_id,
        fingerprint="f" * 64,
        status=status,
        phase="Working",
        completed_files=1,
        total_files=2,
        error_count=1 if status == ParseJobStatus.PARTIAL else 0,
        errors=("bad file",) if status == ParseJobStatus.PARTIAL else (),
        created_at=10.0,
        started_at=11.0,
        finished_at=12.0 if status.is_terminal else None,
        attempt=1,
        output_csv_path="/tmp/final.csv",
        published_csv_path=("/tmp/recent.csv" if status == ParseJobStatus.SUCCEEDED else None),
    )


@pytest.fixture
def mock_st() -> Any:
    with patch.object(parse_job_status, "st") as streamlit:
        streamlit.session_state = {parse_job_status._JOB_ID_KEY: "job-1"}
        columns = [MagicMock(), MagicMock(), MagicMock()]
        for column in columns:
            column.__enter__.return_value = column
            column.__exit__.return_value = False
        streamlit.columns.side_effect = lambda count: columns[:count]
        streamlit.expander.return_value.__enter__.return_value = MagicMock()
        streamlit.expander.return_value.__exit__.return_value = False
        yield streamlit


def _panel_body() -> Any:
    return getattr(parse_job_status._parse_job_panel_fragment, "__wrapped__")


def _sidebar_body() -> Any:
    return getattr(parse_job_status._sidebar_parse_job_fragment, "__wrapped__")


def test_active_job_renders_progress_and_cancels(mock_st: Any) -> None:
    api = MagicMock()
    api.get_parse_job.return_value = _snapshot(ParseJobStatus.RUNNING)
    mock_st.button.side_effect = lambda label, **_kwargs: label == "Cancel parsing"

    _panel_body()(api, "job-1")

    mock_st.progress.assert_called_once()
    api.cancel_parse_job.assert_called_once_with("job-1")
    mock_st.rerun.assert_called_once_with(scope="app")


def test_success_is_consumed_and_triggers_completion_rerun(mock_st: Any) -> None:
    api = MagicMock()
    api.get_parse_job.return_value = _snapshot(ParseJobStatus.SUCCEEDED)
    api.consume_parse_job.return_value = ParseJobReceipt(
        job_id="job-1",
        fingerprint="f" * 64,
        csv_path="/tmp/recent.csv",
        status=ParseJobStatus.SUCCEEDED,
        reused=False,
    )

    parse_job_status._render_parse_job_panel_snapshot(
        api,
        _snapshot(ParseJobStatus.SUCCEEDED),
    )

    api.consume_parse_job.assert_called_once_with("job-1")
    assert parse_job_status._JOB_ID_KEY not in mock_st.session_state
    assert "Loaded" in mock_st.session_state[parse_job_status._FLASH_KEY]
    mock_st.rerun.assert_called_once_with(scope="app")


def test_success_load_error_keeps_job_visible(mock_st: Any) -> None:
    api = MagicMock()
    api.get_parse_job.return_value = _snapshot(ParseJobStatus.SUCCEEDED)
    api.consume_parse_job.side_effect = ValueError("invalid CSV")
    mock_st.button.return_value = False

    parse_job_status._render_parse_job_panel_snapshot(
        api,
        _snapshot(ParseJobStatus.SUCCEEDED),
    )

    assert mock_st.session_state[parse_job_status._JOB_ID_KEY] == "job-1"
    mock_st.error.assert_called_once()
    mock_st.rerun.assert_not_called()


def test_partial_requires_explicit_load_choice(mock_st: Any) -> None:
    api = MagicMock()
    api.get_parse_job.return_value = _snapshot(ParseJobStatus.PARTIAL)
    api.consume_parse_job.return_value = ParseJobReceipt(
        job_id="job-1",
        fingerprint="f" * 64,
        csv_path="/tmp/partial.csv",
        status=ParseJobStatus.PARTIAL,
        reused=False,
    )
    mock_st.button.side_effect = lambda label, **_kwargs: label == "Load Partial"

    parse_job_status._render_parse_job_panel_snapshot(
        api,
        _snapshot(ParseJobStatus.PARTIAL),
    )

    api.consume_parse_job.assert_called_once_with("job-1", allow_partial=True)
    api.retry_parse_job.assert_not_called()
    api.dismiss_parse_job.assert_not_called()


def test_failed_job_can_retry(mock_st: Any) -> None:
    api = MagicMock()
    failed = _snapshot(ParseJobStatus.FAILED)
    retried = _snapshot(ParseJobStatus.QUEUED, job_id="job-2")
    api.get_parse_job.return_value = failed
    api.retry_parse_job.return_value = retried
    mock_st.button.side_effect = lambda label, **_kwargs: label == "Retry"

    parse_job_status._render_parse_job_panel_snapshot(api, failed)

    api.retry_parse_job.assert_called_once_with("job-1")
    assert mock_st.session_state[parse_job_status._JOB_ID_KEY] == "job-2"


def test_sidebar_keeps_cancel_accessible_during_navigation(mock_st: Any) -> None:
    api = MagicMock()
    api.get_parse_job.return_value = _snapshot(ParseJobStatus.RUNNING)
    mock_st.button.side_effect = lambda label, **_kwargs: label == "Cancel"

    _sidebar_body()(api, "job-1")

    mock_st.progress.assert_called_once()
    api.cancel_parse_job.assert_called_once_with("job-1")


def test_terminal_transition_stops_the_polling_fragment(mock_st: Any) -> None:
    """A terminal observation reruns the app once so subsequent rendering is static."""
    api = MagicMock()
    api.get_parse_job.return_value = _snapshot(ParseJobStatus.FAILED)

    _panel_body()(api, "job-1")

    mock_st.rerun.assert_called_once_with(scope="app")
    mock_st.markdown.assert_not_called()


def test_parse_button_submits_background_job_without_waiting() -> None:
    api = MagicMock()
    api.state_manager.get_simulator.return_value = "gem5"
    api.state_manager.get_parse_variables.return_value = [{"name": "simTicks", "type": "scalar"}]
    api.state_manager.get_scanned_variables.return_value = []
    api.state_manager.get_parser_strategy.return_value = "simple"
    api.get_active_parse_job.return_value = None
    queued = _snapshot(ParseJobStatus.QUEUED)
    api.submit_parse_job.return_value = queued

    with (
        patch.object(data_source_components, "st") as streamlit,
        patch.object(data_source_components, "render_parse_job_panel"),
        patch.object(data_source_components, "remember_parse_job") as remember,
        patch.object(data_source_components, "get_visible_parse_job", return_value=None),
        patch.object(
            data_source_components,
            "validate_web_stats_path",
            return_value=Path("/stats"),
        ),
    ):
        streamlit.session_state = {
            "stats_path_input": "/stats",
            "stats_pattern_input": "stats.txt",
        }
        streamlit.columns.return_value = (MagicMock(), MagicMock())
        streamlit.pills.return_value = "gem5"
        streamlit.button.side_effect = lambda label, **_kwargs: label.startswith("Parse gem5")

        data_source_components.DataSourceComponents.render_parser_config(api)

    api.submit_parse_job.assert_called_once()
    api.submit_parse_async.assert_not_called()
    remember.assert_called_once_with(queued)
    streamlit.rerun.assert_called_once_with()


def test_parse_button_is_disabled_while_job_needs_attention() -> None:
    api = MagicMock()
    api.state_manager.get_simulator.return_value = "gem5"
    running = _snapshot(ParseJobStatus.RUNNING)
    parse_button_calls: list[dict[str, Any]] = []

    def button(label: str, **kwargs: Any) -> bool:
        if label.startswith("Parse gem5"):
            parse_button_calls.append(kwargs)
        return False

    with (
        patch.object(data_source_components, "st") as streamlit,
        patch.object(data_source_components, "render_parse_job_panel"),
        patch.object(data_source_components, "get_visible_parse_job", return_value=running),
    ):
        streamlit.session_state = {}
        streamlit.columns.return_value = (MagicMock(), MagicMock())
        streamlit.pills.return_value = "gem5"
        streamlit.button.side_effect = button

        data_source_components.DataSourceComponents.render_parser_config(api)

    assert parse_button_calls == [
        {
            "type": "primary",
            "width": "stretch",
            "disabled": True,
            "help": "Retry, load, or dismiss the current parse attempt first.",
        }
    ]
    api.submit_parse_job.assert_not_called()
