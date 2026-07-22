"""Public background-job progress, cancellation, retry, and result workflow."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_background_jobs")]


def _settled(session: ring5.Session, job_id: str) -> ring5.BackgroundJobInfo:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = next(item for item in session.background_jobs() if item.job_id == job_id)
        if job.terminal:
            return job
        time.sleep(0.01)
    raise AssertionError(f"Background job {job_id} did not settle")


def test_background_transformations_and_export_are_non_blocking(tmp_path: Path) -> None:
    # [test->req~ring5.workspace.background-jobs~1]
    frame = pd.DataFrame({"category": ["A", "B"], "value": [1.0, 2.0]})
    pipeline = [{"type": "columnSelector", "columns": ["category"]}]

    with ring5.Session() as session:
        shape_job = session.shape_submit(frame, cast(list[ring5.ShaperStepConfig], pipeline))
        frame.loc[0, "category"] = "mutated after submission"
        pipeline[0]["columns"] = ["value"]

        shaped = _settled(session, shape_job.job_id)
        result = session.background_job_result(shaped)
        assert shaped.kind == "transformation"
        assert shaped.status == "completed"
        assert shaped.progress == 1.0
        assert shaped.result_available
        assert isinstance(result, pd.DataFrame)
        assert result.to_dict(orient="list") == {"category": ["A", "B"]}

        table_job = session.shape_submit(
            ring5.Table(pd.DataFrame({"x": [1.0]})),
            cast(list[ring5.ShaperStepConfig], []),
            label="Keep public table type",
        )
        table_result = session.background_job_result(_settled(session, table_job.job_id))
        assert isinstance(table_result, ring5.Table)

        figure = session.plot(
            "bar",
            data=pd.DataFrame({"category": ["A"], "value": [1.0]}),
            config={"x": "category", "y": "value"},
        )
        output = tmp_path / "background.html"
        export_job = session.export_submit(figure, str(output))
        exported = _settled(session, export_job.job_id)
        assert exported.kind == "export"
        assert session.background_job_result(exported.job_id) == str(output)
        assert output.read_text(encoding="utf-8").lstrip().startswith("<html>")

        jobs = session.background_jobs()
        assert isinstance(jobs[0], ring5.BackgroundJobInfo)
        assert all(
            isinstance(error, ring5.BackgroundJobLogEntry) for job in jobs for error in job.errors
        )
        assert session.dismiss_finished_background_jobs() == 3
        assert session.background_jobs() == ()


def test_failed_background_job_has_bounded_error_and_retries() -> None:
    # [test->req~ring5.workspace.background-jobs~1]
    invalid_pipeline = cast(list[ring5.ShaperStepConfig], [{"type": "does-not-exist"}])

    with ring5.Session() as session:
        submitted = session.shape_submit(
            pd.DataFrame({"x": [1.0]}),
            invalid_pipeline,
            label="Invalid transformation",
        )
        failed = _settled(session, submitted.job_id)
        assert failed.status == "failed"
        assert failed.retryable
        assert len(failed.errors) == 1
        assert "does-not-exist" in failed.errors[0].message
        assert "Traceback" not in failed.errors[0].message
        with pytest.raises(ring5.JobError, match="did not complete"):
            session.background_job_result(failed)

        retried = session.retry_background_job(failed.job_id)
        failed_again = _settled(session, retried.job_id)
        assert failed_again.attempt == 2
        assert [error.attempt for error in failed_again.errors] == [1, 2]


def test_cancellation_is_honest_and_public_errors_are_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [test->req~ring5.workspace.background-jobs~1]
    started = threading.Event()
    release = threading.Event()

    def blocking_export() -> str:
        started.set()
        assert release.wait(2)
        return "finished"

    session = ring5.Session()
    try:
        submitted = session.api.submit_background_operation(
            "export", "Controlled export", blocking_export
        )
        assert started.wait(1)
        with pytest.raises(ring5.JobError, match="still running"):
            session.background_job_result(submitted)
        with pytest.raises(ring5.JobError, match="finished"):
            session.retry_background_job(submitted)

        cancelling = session.cancel_background_job(submitted)
        assert cancelling.status == "cancelling"
        assert cancelling.cancel_requested
        release.set()
        cancelled = _settled(session, submitted.job_id)
        assert cancelled.status == "cancelled"

        retried = session.retry_background_job(cancelled)
        completed = _settled(session, retried.job_id)
        assert completed.attempt == 2
        assert session.background_job_result(completed) == "finished"

        with pytest.raises(ring5.JobError, match="not found"):
            session.cancel_background_job("missing")
        with pytest.raises(ring5.JobError, match="non-empty"):
            session.background_job_result(cast(Any, None))

        original_submit = session.api.submit_background_operation
        monkeypatch.setattr(
            session.api,
            "submit_background_operation",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("closed center")),
        )
        with pytest.raises(ring5.JobError, match="closed center"):
            session.shape_submit(pd.DataFrame({"x": [1.0]}), [])
        with pytest.raises(ring5.JobError, match="closed center"):
            session.export_submit(cast(Any, object()), "figure.html", label="Export")
        monkeypatch.setattr(session.api, "submit_background_operation", original_submit)
    finally:
        release.set()
        session.close()
