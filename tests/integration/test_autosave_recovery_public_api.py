"""Public API proof for explicit recovery after a lost workspace session."""

from __future__ import annotations

import pandas as pd
import pytest

import ring5
from src.core.services.data_services.path_service import PathService

pytestmark = pytest.mark.public_api


@pytest.fixture
def recovery_dir(tmp_path, monkeypatch):
    root = tmp_path / "recovery"
    root.mkdir()
    monkeypatch.setattr(PathService, "get_recovery_drafts_dir", lambda: root)
    return root


def test_expired_session_workspace_is_explicitly_recovered_by_owner(recovery_dir) -> None:
    # [test->req~ring5.workspace.autosave-recovery~1]
    data = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 1.2]})
    owner_key = "browser-secret-for-recovery"
    with ring5.Session() as interrupted:
        interrupted.add_dataset("nightly", data)
        interrupted.create_plot(
            "bar",
            data=data,
            config={"x": "benchmark", "y": "ipc"},
            name="Recovered IPC",
        )
        captured = interrupted.create_recovery_draft(owner_key)

    assert isinstance(captured, ring5.RecoveryDraftCapture)
    assert isinstance(captured.draft, ring5.RecoveryDraftInfo)

    with ring5.Session() as replacement:
        assert replacement.list_recovery_drafts("different-browser") == ()
        drafts = replacement.list_recovery_drafts(owner_key)
        report = replacement.restore_recovery_draft(owner_key, drafts[0].draft_id)
        recovered_plots = replacement.plots
        replacement.delete_recovery_draft(owner_key, drafts[0].draft_id)
        remaining = replacement.list_recovery_drafts(owner_key)

    assert report.complete
    assert [plot.name for plot in recovered_plots] == ["Recovered IPC"]
    pd.testing.assert_frame_equal(recovered_plots[0].processed_data, data)
    assert not remaining


def test_public_recovery_errors_are_typed_and_empty_state_is_not_saved(recovery_dir) -> None:
    with ring5.Session() as session:
        assert session.create_recovery_draft("empty-browser") is None
        with pytest.raises(ring5.PortfolioError, match="could not be created"):
            session.create_recovery_draft("")
        with pytest.raises(ring5.PortfolioError, match="could not be listed"):
            session.list_recovery_drafts("")
        with pytest.raises(ring5.PortfolioError, match="could not be restored"):
            session.restore_recovery_draft("owner", "bad")
        with pytest.raises(ring5.PortfolioError, match="could not be deleted"):
            session.delete_recovery_draft("owner", "bad")
