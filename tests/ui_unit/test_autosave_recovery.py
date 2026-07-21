"""Presentation coverage for explicit browser-private draft recovery."""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

from src.core.models import RecoveryDraftInfo, RestoreReport


@patch("src.web.components.autosave_recovery.time.monotonic", return_value=120.0)
@patch("src.web.components.autosave_recovery.st")
def test_render_autosaves_and_explicitly_restores_selected_draft(
    mock_st: MagicMock,
    _mock_time: MagicMock,
) -> None:
    # [test->req~ring5.workspace.autosave-recovery~1]
    from src.web.components.autosave_recovery import AutosaveRecoveryComponent

    draft = RecoveryDraftInfo(
        draft_id=f"{'0' * 20}-{'a' * 64}",
        created_at="2026-07-21T10:00:00+00:00",
        size_bytes=1024,
    )
    mock_st.context.cookies = {"_streamlit_xsrf": "browser-cookie-secret"}
    mock_st.query_params = {}
    mock_st.session_state = {}
    mock_st.expander.return_value.__enter__.return_value = MagicMock()
    mock_st.columns.return_value = (MagicMock(), MagicMock())
    mock_st.button.side_effect = [False, True, False]
    mock_st.selectbox.return_value = draft
    api = MagicMock()
    api.create_recovery_draft.return_value = MagicMock(created=True)
    api.list_recovery_drafts.return_value = (draft,)
    api.restore_recovery_draft.return_value = RestoreReport(data_restored=True)

    AutosaveRecoveryComponent.render(api)

    owner_key = hashlib.sha256(b"browser-cookie-secret").hexdigest()
    api.create_recovery_draft.assert_called_once_with(owner_key)
    api.restore_recovery_draft.assert_called_once_with(
        owner_key,
        draft.draft_id,
    )
    mock_st.toast.assert_called_once()
    mock_st.rerun.assert_called_once_with(scope="app")


@patch("src.web.components.autosave_recovery.secrets.token_urlsafe")
@patch("src.web.components.autosave_recovery.st")
def test_browser_owner_falls_back_to_a_persistent_random_url_token(
    mock_st: MagicMock,
    mock_token: MagicMock,
) -> None:
    from src.web.components.autosave_recovery import AutosaveRecoveryComponent

    generated = "a" * 43
    mock_token.return_value = generated
    mock_st.context.cookies = {}
    mock_st.query_params = {}

    assert AutosaveRecoveryComponent.browser_owner_key() == generated
    assert mock_st.query_params["_ring5_recovery"] == generated
