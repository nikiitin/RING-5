"""Human-first background-job sidebar tests."""

from __future__ import annotations

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from src.core.models import BackgroundJobInfo, BackgroundJobLogEntry


def _job(
    job_id: str,
    status: str,
    *,
    retryable: bool = False,
    errors: tuple[BackgroundJobLogEntry, ...] = (),
) -> BackgroundJobInfo:
    return BackgroundJobInfo(
        job_id=job_id,
        kind="export" if job_id == "active" else "transformation",
        label="Download paper" if job_id == "active" else "Shape results",
        status=status,  # type: ignore[arg-type]
        completed_units=0 if status == "running" else 1,
        total_units=1,
        attempt=2 if status == "failed" else 1,
        created_at="2026-07-21T10:00:00+00:00",
        started_at="2026-07-21T10:00:01+00:00",
        finished_at=None if status == "running" else "2026-07-21T10:00:02+00:00",
        cancel_requested=False,
        retryable=retryable,
        result_available=False,
        errors=errors,
    )


def _contexts(mock_st: MagicMock) -> None:
    mock_st.expander.return_value = nullcontext()
    mock_st.container.return_value = nullcontext()
    mock_st.columns.return_value = (nullcontext(), nullcontext())


@patch("src.web.components.background_job_center.st")
def test_empty_center_explains_session_scope(mock_st: MagicMock) -> None:
    from src.web.components.background_job_center import BackgroundJobCenter

    api = MagicMock()
    api.list_background_jobs.return_value = ()
    _contexts(mock_st)

    BackgroundJobCenter.render(api)

    mock_st.expander.assert_called_once_with("Background jobs", expanded=False)
    mock_st.info.assert_called_once_with("No background jobs in this session.")
    mock_st.button.assert_not_called()


@patch("src.web.components.background_job_center.st")
def test_center_shows_progress_errors_and_lifecycle_actions(mock_st: MagicMock) -> None:
    # [test->req~ring5.workspace.background-jobs~1]
    from src.web.components.background_job_center import BackgroundJobCenter

    errors = tuple(
        BackgroundJobLogEntry("2026-07-21T10:00:02+00:00", attempt, f"failure {attempt}")
        for attempt in range(1, 5)
    )
    active = _job("active", "running")
    failed = _job("failed", "failed", retryable=True, errors=errors)
    api = MagicMock()
    api.list_background_jobs.return_value = (active, failed)
    _contexts(mock_st)
    mock_st.button.side_effect = lambda _label, **kwargs: kwargs["key"] in {
        "background_job_cancel_active",
        "background_job_retry_failed",
        "background_jobs_clear",
    }

    BackgroundJobCenter.render(api)

    mock_st.expander.assert_called_once_with("Background jobs (1 active)", expanded=True)
    assert mock_st.progress.call_count == 2
    assert any("failure 4" in call.args[0] for call in mock_st.caption.call_args_list)
    assert any("1 earlier error" in call.args[0] for call in mock_st.caption.call_args_list)
    api.cancel_background_job.assert_called_once_with("active")
    api.retry_background_job.assert_called_once_with("failed")
    api.dismiss_finished_background_jobs.assert_called_once_with()
    assert mock_st.rerun.call_count == 3


@patch("src.web.components.background_job_center.st")
def test_center_keeps_action_failures_human_readable(mock_st: MagicMock) -> None:
    from src.web.components.background_job_center import BackgroundJobCenter

    active = _job("active", "running")
    failed = _job("failed", "failed", retryable=True)
    api = MagicMock()
    api.list_background_jobs.return_value = (active, failed)
    api.cancel_background_job.side_effect = RuntimeError("already finished")
    api.retry_background_job.side_effect = ValueError("retry unavailable")
    _contexts(mock_st)
    mock_st.button.side_effect = lambda _label, **kwargs: kwargs["key"] in {
        "background_job_cancel_active",
        "background_job_retry_failed",
    }

    BackgroundJobCenter.render(api)

    assert [call.args[0] for call in mock_st.error.call_args_list] == [
        "already finished",
        "retry unavailable",
    ]
    mock_st.rerun.assert_not_called()
