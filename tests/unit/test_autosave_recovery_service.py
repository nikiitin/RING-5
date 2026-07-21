"""Unit coverage for bounded private local workspace recovery drafts."""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.core.services import autosave_recovery_service as recovery_module
from src.core.services.autosave_recovery_service import AutosaveRecoveryService
from src.core.services.data_services.path_service import PathService


@pytest.fixture
def recovery_dir(tmp_path, monkeypatch):
    root = tmp_path / "recovery"
    root.mkdir()
    monkeypatch.setattr(PathService, "get_recovery_drafts_dir", lambda: root)
    return root


def _state(value: int = 1) -> MagicMock:
    state = MagicMock()
    state.get_data.return_value = pd.DataFrame({"value": [value]})
    state.get_plots.return_value = []
    state.get_config.return_value = {"draft_value": value}
    state.get_parse_variables.return_value = []
    state.get_plot_counter.return_value = 0
    state.get_csv_path.return_value = ""
    state.is_using_parser.return_value = False
    state.get_stats_path.return_value = ""
    state.get_stats_pattern.return_value = "stats.txt"
    state.get_scanned_variables.return_value = []
    state.get_manager_history.return_value = []
    state.get_portfolio_history.return_value = []
    return state


def test_capture_deduplicates_lists_loads_and_isolates_owner_namespaces(recovery_dir) -> None:
    # [test->req~ring5.workspace.autosave-recovery~1]
    first = AutosaveRecoveryService.capture(_state(), "browser-secret-a")
    duplicate = AutosaveRecoveryService.capture(_state(), "browser-secret-a")

    assert first is not None and first.created is True
    assert duplicate is not None and duplicate.created is False
    assert duplicate.draft.draft_id == first.draft.draft_id
    assert AutosaveRecoveryService.list_drafts("browser-secret-b") == ()
    assert (
        AutosaveRecoveryService.load("browser-secret-a", first.draft.draft_id)["data_csv"]
        == "value\n1\n"
    )
    owner_directory = recovery_dir / hashlib.sha256(b"browser-secret-a").hexdigest()
    assert owner_directory.stat().st_mode & 0o777 == 0o700
    assert next(owner_directory.glob("*.json")).stat().st_mode & 0o777 == 0o600
    assert not tuple(owner_directory.glob("*.tmp"))


def test_per_owner_history_is_pruned_by_count_and_can_be_deleted(
    recovery_dir,
    monkeypatch,
) -> None:
    monkeypatch.setattr(recovery_module, "MAX_RECOVERY_DRAFTS_PER_OWNER", 2)
    captures = [
        AutosaveRecoveryService.capture(_state(value), "bounded-owner") for value in (1, 2, 3)
    ]
    drafts = AutosaveRecoveryService.list_drafts("bounded-owner")

    assert len(drafts) == 2
    assert captures[0] is not None
    assert all(draft.draft_id != captures[0].draft.draft_id for draft in drafts)
    AutosaveRecoveryService.delete("bounded-owner", drafts[0].draft_id)
    AutosaveRecoveryService.delete("bounded-owner", drafts[1].draft_id)
    assert AutosaveRecoveryService.list_drafts("bounded-owner") == ()


def test_modified_oversized_and_invalid_drafts_are_refused(recovery_dir, monkeypatch) -> None:
    captured = AutosaveRecoveryService.capture(_state(), "secure-owner")
    assert captured is not None
    owner_directory = recovery_dir / hashlib.sha256(b"secure-owner").hexdigest()
    path = next(owner_directory.glob("*.json"))
    path.write_bytes(path.read_bytes().replace(b"draft_value", b"changed_value", 1))

    with pytest.raises(ValueError, match="integrity manifest"):
        AutosaveRecoveryService.load("secure-owner", captured.draft.draft_id)
    with pytest.raises(ValueError, match="invalid format"):
        AutosaveRecoveryService.load("secure-owner", "../bad")
    with pytest.raises(FileNotFoundError, match="was not found"):
        AutosaveRecoveryService.load(
            "secure-owner",
            f"{'0' * 20}-{'f' * 64}",
        )

    monkeypatch.setattr(recovery_module, "MAX_RECOVERY_DRAFT_BYTES", 10)
    with pytest.raises(ValueError, match="limited to 10 bytes"):
        AutosaveRecoveryService.capture(_state(2), "oversized-owner")


def test_empty_state_and_invalid_owner_keys_do_not_create_drafts(recovery_dir) -> None:
    state = _state()
    state.get_data.return_value = None
    state.get_config.return_value = {}

    assert AutosaveRecoveryService.capture(state, "empty-owner") is None
    with pytest.raises(ValueError, match="non-empty"):
        AutosaveRecoveryService.list_drafts("")
    with pytest.raises(ValueError, match="control characters"):
        AutosaveRecoveryService.list_drafts("bad\nowner")


def test_owner_directory_symlinks_are_refused_before_capture(recovery_dir, tmp_path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    owner = hashlib.sha256(b"linked-owner").hexdigest()
    (recovery_dir / owner).symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="owner storage must not be a symbolic link"):
        AutosaveRecoveryService.capture(_state(), "linked-owner")
    assert not tuple(outside.iterdir())
