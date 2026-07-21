"""Human-first sidebar controls for session-owned background work."""

from __future__ import annotations

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import BackgroundJobInfo

_KIND_LABELS = {
    "scan": "Scan",
    "parse": "Parse",
    "transformation": "Transformation",
    "export": "Download",
}
_STATUS_LABELS = {
    "queued": "Queued",
    "running": "Running",
    "cancelling": "Cancelling",
    "cancelled": "Cancelled",
    "completed": "Completed",
    "failed": "Failed",
}


class BackgroundJobCenter:
    """Render bounded progress, cancellation, retry, and error details."""

    @staticmethod
    def render(api: ApplicationAPI) -> None:
        """Render the current browser session's background-job center."""
        # [impl->req~ring5.workspace.background-jobs~1]
        jobs = api.list_background_jobs()
        active_count = sum(not job.terminal for job in jobs)
        label = "Background jobs"
        if active_count:
            label += f" ({active_count} active)"
        with st.expander(label, expanded=bool(active_count)):
            st.caption(
                "Scan, parse, transformation, and export work stays attached to this "
                "browser session. Error details are bounded and omit tracebacks."
            )
            if not jobs:
                st.info("No background jobs in this session.")
                return
            for job in jobs:
                BackgroundJobCenter._render_job(api, job)
            refresh_column, clear_column = st.columns(2)
            with refresh_column:
                if st.button("Refresh", key="background_jobs_refresh", width="stretch"):
                    st.rerun()
            with clear_column:
                if st.button(
                    "Clear finished",
                    key="background_jobs_clear",
                    width="stretch",
                    disabled=not any(job.terminal for job in jobs),
                ):
                    api.dismiss_finished_background_jobs()
                    st.rerun()

    @staticmethod
    def _render_job(api: ApplicationAPI, job: BackgroundJobInfo) -> None:
        with st.container(border=True):
            st.markdown(f"**{job.label}**")
            status = _STATUS_LABELS[job.status]
            kind = _KIND_LABELS[job.kind]
            st.progress(
                job.progress,
                text=(
                    f"{kind} · {status} · {job.completed_units}/{job.total_units} "
                    f"· attempt {job.attempt}"
                ),
            )
            if job.errors:
                st.markdown(f"Errors ({len(job.errors)})")
                for entry in job.errors[-3:]:
                    st.caption(f"Attempt {entry.attempt}: {entry.message}")
                if len(job.errors) > 3:
                    st.caption(f"{len(job.errors) - 3} earlier error(s) retained.")
            cancel_column, retry_column = st.columns(2)
            with cancel_column:
                if st.button(
                    "Cancel",
                    key=f"background_job_cancel_{job.job_id}",
                    disabled=job.terminal or job.status == "cancelling",
                    width="stretch",
                ):
                    try:
                        api.cancel_background_job(job.job_id)
                    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
            with retry_column:
                if st.button(
                    "Retry",
                    key=f"background_job_retry_{job.job_id}",
                    disabled=not job.terminal or not job.retryable,
                    width="stretch",
                ):
                    try:
                        api.retry_background_job(job.job_id)
                    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
