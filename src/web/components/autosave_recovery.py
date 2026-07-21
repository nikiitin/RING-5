"""Browser-private automatic drafts and explicit recovery controls."""

from __future__ import annotations

import hashlib
import re
import secrets
import time

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import RecoveryDraftInfo

_RECOVERY_QUERY_KEY = "_ring5_recovery"
_RECOVERY_TOKEN = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
_AUTOSAVE_INTERVAL_SECONDS = 60.0


class AutosaveRecoveryComponent:
    """Capture bounded browser-owned drafts and recover only on explicit action."""

    @classmethod
    def render(cls, api: ApplicationAPI) -> None:
        """Capture when due and render private recovery controls in the sidebar."""
        # [impl->req~ring5.workspace.autosave-recovery~1]
        owner_key = cls.browser_owner_key()
        cls._capture_when_due(api, owner_key)
        with st.expander("Autosave & recovery", expanded=False):
            error = st.session_state.pop("_recovery_capture_error", None)
            if isinstance(error, str):
                st.warning(f"Automatic draft could not be saved: {error}")
            st.caption(
                "RING-5 keeps up to five integrity-checked drafts for this browser. "
                "Nothing is restored without your confirmation."
            )
            if st.button(
                "Save recovery draft now",
                key="_recovery_capture_now",
                use_container_width=True,
            ):
                cls._capture_now(api, owner_key)

            try:
                drafts = api.list_recovery_drafts(owner_key)
            except (OSError, TypeError, ValueError) as exc:
                st.error(f"Recovery drafts could not be listed: {exc}")
                return
            if not drafts:
                st.info("No recovery drafts for this browser yet.")
                return

            selected = st.selectbox(
                "Recovery point",
                drafts,
                format_func=cls._label,
                key="_recovery_selected_draft",
            )
            recover_column, delete_column = st.columns(2)
            with recover_column:
                if st.button(
                    "Recover",
                    key=f"_recovery_restore_{selected.draft_id}",
                    use_container_width=True,
                    type="primary",
                ):
                    cls._restore(api, owner_key, selected)
            with delete_column:
                if st.button(
                    "Delete draft",
                    key=f"_recovery_delete_{selected.draft_id}",
                    use_container_width=True,
                    type="tertiary",
                ):
                    try:
                        api.delete_recovery_draft(owner_key, selected.draft_id)
                    except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
                        st.error(f"Recovery draft could not be deleted: {exc}")
                    else:
                        st.toast("Recovery draft deleted", icon="🗑️")
                        st.rerun()

    @staticmethod
    def browser_owner_key() -> str:
        """Return a browser-held secret without persisting the raw value server-side."""
        candidate = st.query_params.get(_RECOVERY_QUERY_KEY)
        if isinstance(candidate, str) and _RECOVERY_TOKEN.fullmatch(candidate):
            return candidate
        cookies = st.context.cookies
        cookie = cookies.get("_streamlit_xsrf")
        if isinstance(cookie, str) and cookie.strip():
            candidate = hashlib.sha256(cookie.encode("utf-8")).hexdigest()
        else:
            candidate = secrets.token_urlsafe(32)
        st.query_params[_RECOVERY_QUERY_KEY] = candidate
        return candidate

    @staticmethod
    def _capture_when_due(api: ApplicationAPI, owner_key: str) -> None:
        now = time.monotonic()
        previous = st.session_state.get("_recovery_last_capture_at")
        if isinstance(previous, (int, float)) and now - previous < _AUTOSAVE_INTERVAL_SECONDS:
            return
        try:
            captured = api.create_recovery_draft(owner_key)
        except (OSError, TypeError, ValueError) as exc:
            st.session_state["_recovery_capture_error"] = str(exc)
            st.session_state["_recovery_last_capture_at"] = now
            return
        if captured is not None:
            st.session_state["_recovery_last_capture_at"] = now

    @staticmethod
    def _capture_now(api: ApplicationAPI, owner_key: str) -> None:
        try:
            captured = api.create_recovery_draft(owner_key)
        except (OSError, TypeError, ValueError) as exc:
            st.error(f"Recovery draft could not be saved: {exc}")
            return
        st.session_state["_recovery_last_capture_at"] = time.monotonic()
        if captured is None:
            st.info("The workspace is still empty, so there is nothing to save.")
        elif captured.created:
            st.success("Recovery draft saved.")
            st.rerun()
        else:
            st.info("The newest draft already matches this workspace.")

    @staticmethod
    def _restore(
        api: ApplicationAPI,
        owner_key: str,
        draft: RecoveryDraftInfo,
    ) -> None:
        try:
            report = api.restore_recovery_draft(owner_key, draft.draft_id)
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as exc:
            st.error(f"Recovery draft could not be restored: {exc}")
            return
        if report.complete:
            st.toast("Workspace recovered from the selected draft", icon="✅")
        else:
            issues = [*report.plots_skipped]
            if report.data_error:
                issues.append(f"data: {report.data_error}")
            if report.parse_variables_skipped:
                issues.append(
                    f"{report.parse_variables_skipped} malformed parse-variable entries skipped"
                )
            st.toast(
                "Recovery was incomplete — " + "; ".join(issues[:3]),
                icon="⚠️",
            )
        st.session_state["_recovery_last_capture_at"] = time.monotonic()
        st.rerun(scope="app")

    @staticmethod
    def _label(draft: RecoveryDraftInfo) -> str:
        when = draft.created_at.replace("T", " ").replace("+00:00", " UTC")[:23]
        size = draft.size_bytes / 1024
        return f"{when} · {size:,.1f} KiB"
