"""Polling UI for session-scoped background parse jobs."""

from __future__ import annotations

import logging

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import (
    ParseJobNotConsumableError,
    ParseJobNotFoundError,
    ParseJobSnapshot,
    ParseJobStatus,
)

_JOB_ID_KEY = "_ring5_parse_job_id"
_FLASH_KEY = "_ring5_parse_job_flash"
logger = logging.getLogger(__name__)


def remember_parse_job(snapshot: ParseJobSnapshot) -> None:
    """Make a submitted job visible across page navigation and reruns."""
    st.session_state[_JOB_ID_KEY] = snapshot.job_id


def render_parse_job_panel(api: ApplicationAPI) -> None:
    """Render detailed parsing progress on the Data Source page."""
    snapshot = get_visible_parse_job(api)
    if snapshot is not None:
        _parse_job_panel_fragment(api, snapshot.job_id)


def render_sidebar_parse_job(api: ApplicationAPI) -> None:
    """Render compact parsing progress and cancellation in the sidebar."""
    snapshot = get_visible_parse_job(api)
    if snapshot is not None:
        _sidebar_parse_job_fragment(api, snapshot.job_id)


def get_visible_parse_job(api: ApplicationAPI) -> ParseJobSnapshot | None:
    """Return the job currently exposed for progress or acknowledgement."""
    job_id = _visible_job_id(api)
    return api.get_parse_job(job_id) if job_id is not None else None


def show_parse_job_flash() -> None:
    """Show a one-shot completion message after an application rerun."""
    message = st.session_state.pop(_FLASH_KEY, None)
    if isinstance(message, str):
        st.toast(message, icon="✅")


@st.fragment(run_every="1s")
def _parse_job_panel_fragment(api: ApplicationAPI, job_id: str) -> None:
    """Poll and render a full parse-job status card."""
    snapshot = api.get_parse_job(job_id)
    if snapshot is None:
        _forget_job(job_id)
        return
    if snapshot.status == ParseJobStatus.SUCCEEDED:
        _consume_success(api, snapshot, source="panel")
        return

    st.markdown("### Background parsing")
    _render_snapshot(snapshot, compact=False)

    if snapshot.status.is_active:
        if st.button(
            "Cancel parsing",
            key=f"cancel_parse_job_{job_id}",
            type="secondary",
        ):
            api.cancel_parse_job(job_id)
            st.rerun(scope="app")
        return

    if snapshot.status == ParseJobStatus.PARTIAL:
        load_col, retry_col, dismiss_col = st.columns(3)
        with load_col:
            if st.button(
                "Load Partial",
                key=f"load_partial_parse_job_{job_id}",
                type="primary",
                width="stretch",
            ):
                try:
                    receipt = api.consume_parse_job(job_id, allow_partial=True)
                except Exception as exc:
                    logger.error(
                        "Could not consume partial parse job %s: %s",
                        job_id,
                        exc,
                        exc_info=True,
                    )
                    st.error(f"Could not load the partial parse result: {exc}")
                else:
                    _complete_job(job_id, f"Loaded partial CSV: {receipt.csv_path}")
        with retry_col:
            _render_retry_button(api, snapshot)
        with dismiss_col:
            _render_dismiss_button(api, snapshot)
        return

    if snapshot.status in {ParseJobStatus.FAILED, ParseJobStatus.CANCELLED}:
        retry_col, dismiss_col = st.columns(2)
        with retry_col:
            _render_retry_button(api, snapshot)
        with dismiss_col:
            _render_dismiss_button(api, snapshot)


@st.fragment(run_every="1s")
def _sidebar_parse_job_fragment(api: ApplicationAPI, job_id: str) -> None:
    """Poll and render compact status while the user navigates other pages."""
    snapshot = api.get_parse_job(job_id)
    if snapshot is None:
        _forget_job(job_id)
        return
    if snapshot.status == ParseJobStatus.SUCCEEDED:
        _consume_success(api, snapshot, source="sidebar")
        return

    st.markdown("#### Parse job")
    _render_snapshot(snapshot, compact=True)
    if snapshot.status.is_active:
        if st.button(
            "Cancel",
            key=f"sidebar_cancel_parse_job_{job_id}",
            width="stretch",
        ):
            api.cancel_parse_job(job_id)
            st.rerun(scope="app")
    elif st.button(
        "Review on Data Source",
        key=f"review_parse_job_{job_id}",
        width="stretch",
    ):
        st.session_state["_nav_page"] = "Data Source"
        st.rerun(scope="app")


def _render_snapshot(snapshot: ParseJobSnapshot, *, compact: bool) -> None:
    """Render phase, elapsed time, progress, and bounded error details."""
    label = snapshot.status.value.replace("_", " ").title()
    st.caption(f"{label} · {snapshot.elapsed_seconds:.1f}s")
    st.write(snapshot.phase)
    if snapshot.total_files > 0:
        st.progress(
            snapshot.progress,
            text=f"{snapshot.completed_files}/{snapshot.total_files} files",
        )
    elif snapshot.status.is_active:
        st.progress(0.0, text="Preparing file work")

    if snapshot.error_count:
        st.error(f"{snapshot.error_count} file error(s)")
        if not compact and snapshot.errors:
            with st.expander("Error details"):
                for error in snapshot.errors:
                    st.code(error, language=None)


def _render_retry_button(
    api: ApplicationAPI,
    snapshot: ParseJobSnapshot,
) -> None:
    """Render the explicit retry action for one terminal attempt."""
    if st.button(
        "Retry",
        key=f"retry_parse_job_{snapshot.job_id}",
        width="stretch",
    ):
        retried = api.retry_parse_job(snapshot.job_id)
        remember_parse_job(retried)
        st.rerun(scope="app")


def _render_dismiss_button(
    api: ApplicationAPI,
    snapshot: ParseJobSnapshot,
) -> None:
    """Render acknowledgement and cleanup for one terminal attempt."""
    if st.button(
        "Dismiss",
        key=f"dismiss_parse_job_{snapshot.job_id}",
        width="stretch",
    ):
        api.dismiss_parse_job(snapshot.job_id)
        _forget_job(snapshot.job_id)
        st.rerun(scope="app")


def _consume_success(
    api: ApplicationAPI,
    snapshot: ParseJobSnapshot,
    *,
    source: str,
) -> None:
    """Load a clean result automatically and preserve actionable failures."""
    try:
        receipt = api.consume_parse_job(snapshot.job_id)
    except (FileNotFoundError, ParseJobNotConsumableError) as exc:
        _render_consumption_error(api, snapshot, source=source, error=exc)
        return
    except ParseJobNotFoundError:
        _forget_job(snapshot.job_id)
        return
    except Exception as exc:
        logger.error("Could not consume parse job %s: %s", snapshot.job_id, exc, exc_info=True)
        _render_consumption_error(api, snapshot, source=source, error=exc)
        return
    reused = "Reused" if receipt.reused else "Loaded"
    _complete_job(snapshot.job_id, f"{reused} parsed CSV from Recent")


def _render_consumption_error(
    api: ApplicationAPI,
    snapshot: ParseJobSnapshot,
    *,
    source: str,
    error: BaseException,
) -> None:
    """Keep an unloadable result actionable instead of losing its metadata."""
    st.error(f"Could not load the completed parse result: {error}")
    if st.button(
        "Dismiss result",
        key=f"{source}_dismiss_unloadable_parse_job_{snapshot.job_id}",
        width="stretch",
    ):
        api.dismiss_parse_job(snapshot.job_id)
        _forget_job(snapshot.job_id)
        st.rerun(scope="app")


def _complete_job(job_id: str, message: str) -> None:
    """Queue a one-shot completion toast and rerun the full application."""
    _forget_job(job_id)
    st.session_state[_FLASH_KEY] = message
    st.rerun(scope="app")


def _visible_job_id(api: ApplicationAPI) -> str | None:
    """Resolve the remembered job, falling back to the active session job."""
    stored = st.session_state.get(_JOB_ID_KEY)
    if isinstance(stored, str):
        if api.get_parse_job(stored) is not None:
            return stored
        st.session_state.pop(_JOB_ID_KEY, None)
    active = api.get_active_parse_job()
    if active is None:
        return None
    remember_parse_job(active)
    return active.job_id


def _forget_job(job_id: str) -> None:
    """Forget the visible job only when its identifier still matches."""
    if st.session_state.get(_JOB_ID_KEY) == job_id:
        st.session_state.pop(_JOB_ID_KEY, None)
