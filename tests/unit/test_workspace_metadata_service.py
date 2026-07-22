"""Unit coverage for bounded workspace favorites and tags."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.core.models import DatasetInfo
from src.core.services import workspace_metadata_service as metadata_module
from src.core.services.workspace_metadata_service import WorkspaceMetadataService


def _state() -> MagicMock:
    config: dict[str, object] = {}
    state = MagicMock()
    state.get_config.side_effect = lambda: dict(config)
    state.update_config.side_effect = lambda key, value: config.__setitem__(key, value)
    state.get_parse_variables.return_value = [
        {"name": "system.cpu.ipc", "type": "scalar", "_id": "v1"}
    ]
    state.get_scanned_variables.return_value = [
        {"name": "system.cpu.ipc", "type": "scalar", "entries": []},
        {"name": "system.cache.misses", "type": "vector", "entries": []},
    ]
    state.list_datasets.return_value = (DatasetInfo("nightly", 3, 2, True),)
    state.get_plots.return_value = [
        SimpleNamespace(
            plot_id=7,
            name="IPC plot",
            pipeline=[{"id": 11, "type": "sort", "config": {}}],
        )
    ]
    state._metadata_config = config
    return state


def test_every_artifact_kind_can_be_tagged_favorited_and_filtered(portfolios_dir) -> None:
    # [test->req~ring5.workspace.favorites-tags~1]
    state = _state()
    targets = (
        ("variable", "system.cpu.ipc"),
        ("dataset", "nightly"),
        ("plot", "7"),
        ("pipeline", "7:11"),
        ("portfolio", "paper"),
    )
    for kind, identifier in targets:
        saved = WorkspaceMetadataService.set_metadata(
            state,
            ["paper"],
            kind,  # type: ignore[arg-type]
            identifier,
            tags=(" Nightly ", "CPU", "nightly"),
            favorite=True,
        )
        assert saved.tags == ("nightly", "cpu")
        assert saved.favorite is True

    response = WorkspaceMetadataService.list_artifacts(
        state,
        ["paper"],
        tags=("NIGHTLY", "cpu"),
        favorites_only=True,
    )

    assert {artifact.kind for artifact in response.artifacts} == {
        "variable",
        "dataset",
        "plot",
        "pipeline",
        "portfolio",
    }
    assert response.available_tags == ("cpu", "nightly")
    assert response.returned_matches == response.total_matches == 5
    assert (portfolios_dir / ".workspace-metadata").is_file()
    assert not tuple(portfolios_dir.glob(".workspace-metadata-*"))


def test_workspace_records_survive_config_restore_and_portfolio_records_are_local(
    portfolios_dir,
) -> None:
    first = _state()
    WorkspaceMetadataService.set_metadata(
        first,
        ["paper"],
        "variable",
        "system.cpu.ipc",
        tags=("reusable",),
    )
    WorkspaceMetadataService.set_metadata(
        first,
        ["paper"],
        "portfolio",
        "paper",
        favorite=True,
    )

    restored = _state()
    restored._metadata_config.update(first._metadata_config)
    response = WorkspaceMetadataService.list_artifacts(restored, ["paper"])

    by_identity = {(item.kind, item.identifier): item for item in response.artifacts}
    assert by_identity[("variable", "system.cpu.ipc")].tags == ("reusable",)
    assert by_identity[("portfolio", "paper")].favorite is True


@pytest.mark.parametrize(
    ("kind", "identifier", "tags", "favorite", "message"),
    [
        ("unknown", "x", (), False, "kind must be one of"),
        ("variable", "missing", (), False, "not currently available"),
        ("variable", "system.cpu.ipc", "tag", False, "sequence"),
        ("variable", "system.cpu.ipc", ("bad!",), False, "may contain"),
        ("variable", "system.cpu.ipc", ("x" * 33,), False, "32 characters"),
        ("variable", "system.cpu.ipc", tuple(str(i) for i in range(17)), False, "at most 16"),
        ("variable", "system.cpu.ipc", (), 1, "must be a boolean"),
    ],
)
def test_invalid_targets_and_metadata_are_rejected(
    portfolios_dir,
    kind: object,
    identifier: str,
    tags: object,
    favorite: object,
    message: str,
) -> None:
    with pytest.raises((KeyError, TypeError, ValueError), match=message):
        WorkspaceMetadataService.set_metadata(
            _state(),
            ["paper"],
            kind,  # type: ignore[arg-type]
            identifier,
            tags=tags,  # type: ignore[arg-type]
            favorite=favorite,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("CPU_2026", "cpu_2026"),
        ("_internal_", "_internal_"),
        ("Nightly Run", "nightly run"),
        ("release-candidate", "release-candidate"),
    ],
)
def test_workspace_tag_validation_preserves_supported_forms(tag: str, expected: str) -> None:
    assert WorkspaceMetadataService._normalize_tag(tag) == expected


@pytest.mark.parametrize("tag", ["-leading", "trailing-", "two--parts", "bad!tag"])
def test_workspace_tag_validation_rejects_unsupported_forms(tag: str) -> None:
    with pytest.raises(ValueError, match="may contain"):
        WorkspaceMetadataService._normalize_tag(tag)


def test_empty_metadata_removes_records_and_filters_are_bounded(portfolios_dir) -> None:
    state = _state()
    WorkspaceMetadataService.set_metadata(
        state,
        ["paper"],
        "dataset",
        "nightly",
        tags=("temporary",),
        favorite=True,
    )
    cleared = WorkspaceMetadataService.set_metadata(
        state,
        ["paper"],
        "dataset",
        "nightly",
    )

    assert cleared.tags == ()
    assert cleared.favorite is False
    assert state._metadata_config["_workspace_artifact_metadata"] == []
    with pytest.raises(ValueError, match="from 1 through 100"):
        WorkspaceMetadataService.list_artifacts(state, ["paper"], limit=0)
    with pytest.raises(TypeError, match="boolean"):
        WorkspaceMetadataService.list_artifacts(
            state, ["paper"], favorites_only=1  # type: ignore[arg-type]
        )


def test_discovery_reports_per_kind_truncation(monkeypatch, portfolios_dir) -> None:
    monkeypatch.setattr(metadata_module, "MAX_WORKSPACE_SEARCH_ENTRIES_PER_KIND", 1)
    response = WorkspaceMetadataService.list_artifacts(_state(), ["paper"], limit=100)

    assert response.index_truncated is True
    assert response.available_artifacts > response.indexed_artifacts
    assert sum(artifact.kind == "variable" for artifact in response.artifacts) == 1
