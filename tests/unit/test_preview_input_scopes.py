"""Reviewed previews follow their real source scope across revisions and resets."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import asdict
from typing import Any

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.core.models.preview_models import ActivePreviewInputs, DatasetPreviewInputs

_NAMES = ("baseline", "candidate")
_OPTIONS = {"baseline": "baseline", "candidate": "candidate", "keys": ["key"], "metrics": ["v"]}


def _seed(api: ApplicationAPI, baseline: float = 10, candidate: float = 20) -> None:
    api.add_dataset("baseline", pd.DataFrame({"key": ["a"], "v": [baseline]}))
    api.add_dataset("candidate", pd.DataFrame({"key": ["a"], "v": [candidate]}), select=False)


@pytest.fixture
def api() -> Generator[ApplicationAPI, None, None]:
    instance = ApplicationAPI()
    _seed(instance)
    try:
        yield instance
    finally:
        instance.close(wait=True)


def _store(api: ApplicationAPI) -> tuple[DatasetPreviewInputs, pd.DataFrame]:
    captured = api.capture_preview_inputs(_NAMES)
    assert isinstance(captured, DatasetPreviewInputs)
    result = api.compare_datasets(*_NAMES, ["key"], ["v"])
    api.set_preview("comparison", result, operation_config=_OPTIONS, inputs=captured)
    return captured, result


def test_named_capture_retains_exact_sources_without_materializing_revision_history(
    api: ApplicationAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        api.state_manager,
        "get_dataset_lineage",
        lambda *_: pytest.fail("Input capture must not copy full revision history."),
    )
    captured, result = _store(api)
    assert [source.dataset_name for source in captured.sources] == list(_NAMES)
    assert len({source.workspace_generation for source in captured.sources}) == 1
    assert api.preview_matches("comparison", operation_config=_OPTIONS)
    pd.testing.assert_frame_equal(api.get_preview("comparison"), result)


@pytest.mark.parametrize("name", _NAMES)
@pytest.mark.parametrize("change", ["replace", "remove", "recreate", "undo", "redo"])
def test_named_result_invalidates_when_either_source_revision_changes(
    api: ApplicationAPI, name: str, change: str
) -> None:
    if change in {"undo", "redo"}:
        api.add_dataset(name, pd.DataFrame({"key": ["a"], "v": [30.0]}), select=False, replace=True)
        if change == "redo":
            api.undo_dataset(name)
    _store(api)
    if change == "replace":
        api.add_dataset(name, pd.DataFrame({"key": ["a"], "v": [40.0]}), select=False, replace=True)
    elif change in {"remove", "recreate"}:
        api.remove_dataset(name)
        if change == "recreate":
            api.add_dataset(name, pd.DataFrame({"key": ["a"], "v": [40.0]}), select=False)
    elif change == "undo":
        api.undo_dataset(name)
    else:
        api.redo_dataset(name)
    assert not api.preview_matches("comparison", operation_config=_OPTIONS)
    assert api.get_preview("comparison") is None


def test_unrelated_selection_and_revisions_preserve_named_results(api: ApplicationAPI) -> None:
    captured, result = _store(api)
    api.add_dataset("unrelated", pd.DataFrame({"v": [99.0]}))
    api.add_dataset("unrelated", pd.DataFrame({"v": [101.0]}), replace=True)
    api.select_dataset("candidate")
    api.select_dataset("unrelated")
    assert api.capture_preview_inputs(_NAMES) == captured
    assert api.preview_matches("comparison", operation_config=_OPTIONS)
    pd.testing.assert_frame_equal(api.get_preview("comparison"), result)


@pytest.mark.parametrize("replace_name", _NAMES)
def test_named_inflight_publication_rejects_changed_source_and_keeps_prior_result(
    api: ApplicationAPI, replace_name: str
) -> None:
    _, prior = _store(api)
    captured = api.capture_preview_inputs(_NAMES)
    api.add_dataset(
        replace_name, pd.DataFrame({"key": ["a"], "v": [200.0]}), select=False, replace=True
    )
    with pytest.raises(ValueError, match="source changed during computation"):
        api.set_preview("comparison", prior, operation_config=_OPTIONS, inputs=captured)
    assert api.state_manager.has_preview("comparison")
    assert api.get_preview("comparison") is None
    pd.testing.assert_frame_equal(api.state_manager.get_preview("comparison"), prior)


@pytest.mark.parametrize("reset", ["session", "restore", "data"])
@pytest.mark.parametrize("values", [(10.0, 20.0), (100.0, 50.0)])
def test_pre_reset_named_inputs_cannot_publish_against_reused_names_and_revision_ids(
    api: ApplicationAPI, reset: str, values: tuple[float, float]
) -> None:
    # [test->req~ring5.data.preview-confirm~1]
    captured, old_result = _store(api)
    if reset == "session":
        api.reset_session()
    elif reset == "restore":
        api.state_manager.restore_session(
            {"parser_strategy": "simple", "loaded_origin": None, "simulator": "gem5", "plots": []}
        )
    else:
        api.state_manager.clear_data()
    _seed(api, *values)
    fresh = api.capture_preview_inputs(_NAMES)
    assert isinstance(fresh, DatasetPreviewInputs)
    assert [source.revision_id for source in fresh.sources] == [
        source.revision_id for source in captured.sources
    ]
    assert fresh.sources[0].workspace_generation != captured.sources[0].workspace_generation
    with pytest.raises(ValueError, match="source changed during computation"):
        api.set_preview("comparison", old_result, operation_config=_OPTIONS, inputs=captured)
    assert api.get_preview("comparison") is None


def test_identical_other_session_cannot_authorize_named_publication(api: ApplicationAPI) -> None:
    captured, result = _store(api)
    other = ApplicationAPI()
    try:
        _seed(other)
        assert other.capture_preview_inputs(_NAMES) != captured
        with pytest.raises(ValueError, match="source changed during computation"):
            other.set_preview("comparison", result, operation_config=_OPTIONS, inputs=captured)
        assert not other.has_preview("comparison")
    finally:
        other.close(wait=True)


def test_named_display_result_cannot_replace_active_data(api: ApplicationAPI) -> None:
    _store(api)
    before = api.state_manager.get_data()
    with pytest.raises(ValueError, match="cannot replace active data"):
        api.confirm_preview("comparison", operation_config=_OPTIONS, operation="Replace")
    pd.testing.assert_frame_equal(api.state_manager.get_data(), before)
    assert api.preview_matches("comparison", operation_config=_OPTIONS)


def test_active_capture_and_required_record_keep_reviewed_options_and_rows_owned(
    api: ApplicationAPI,
) -> None:
    captured = api.capture_preview_inputs()
    assert isinstance(captured, ActivePreviewInputs)
    options = {"nested": {"values": [1]}}
    result = pd.DataFrame({"objects": [{"values": [2]}]})
    api.set_preview("owned", result, operation_config=options, inputs=captured)
    options["nested"]["values"].append(99)
    result.iloc[0, 0]["values"].append(99)
    context = api.state_manager.get_preview_context("owned")
    assert context is not None
    context.operation_config["nested"]["values"].append(88)
    assert api.get_preview_config("owned") == {"nested": {"values": [1]}}
    assert api.get_preview("owned").iloc[0, 0] == {"values": [2]}
    assert asdict(captured)["source_version"] >= 0


@pytest.mark.parametrize("names", ["baseline", b"baseline", None, 1, [""], [None]])
def test_capture_rejects_malformed_named_source_requests(api: ApplicationAPI, names: Any) -> None:
    with pytest.raises(ValueError, match="dataset names"):
        api.capture_preview_inputs(names)
    assert not api.has_preview("comparison")


def test_store_rejects_missing_or_untyped_review_metadata(api: ApplicationAPI) -> None:
    result = pd.DataFrame({"v": [1]})
    with pytest.raises(TypeError, match="operation_config.*inputs"):
        api.set_preview("invalid", result)
    with pytest.raises(ValueError, match="options must be a mapping"):
        api.set_preview(
            "invalid", result, operation_config=None, inputs=api.capture_preview_inputs()
        )
    with pytest.raises(ValueError, match="Capture preview inputs"):
        api.set_preview("invalid", result, operation_config={}, inputs="source")
    assert not api.has_preview("invalid")


def test_rejected_result_or_context_does_not_replace_an_owned_review_record(
    preview_context,
) -> None:
    from src.core.state.repositories.preview_repository import PreviewRepository

    repository = PreviewRepository()
    result = pd.DataFrame({"v": [2.0]})
    repository.set_preview("owned", result, context=preview_context)
    with pytest.raises(TypeError, match="pandas DataFrame"):
        repository.set_preview("owned", {"v": [99.0]}, context=preview_context)
    with pytest.raises(TypeError, match="context is required"):
        repository.set_preview("owned", pd.DataFrame({"v": [99.0]}), context=None)
    pd.testing.assert_frame_equal(repository.get_preview("owned"), result)
    assert repository.get_preview_context("owned") == preview_context


@pytest.mark.parametrize("name", _NAMES)
@pytest.mark.parametrize("revert", ["undo", "redo", "restore"])
def test_inflight_named_result_rejects_change_and_revert_to_its_captured_revision(
    api: ApplicationAPI, name: str, revert: str
) -> None:
    # [test->req~ring5.data.preview-confirm~1]
    intermediate = pd.DataFrame({"key": ["a"], "v": [50.0 if name == "baseline" else 5.0]})
    if revert == "redo":
        original = api.get_dataset(name)
        api.add_dataset(name, intermediate, select=False, replace=True)
        api.add_dataset(name, original, select=False, replace=True)
    captured, prior = _store(api)
    before = next(source for source in captured.sources if source.dataset_name == name)
    if revert == "redo":
        api.undo_dataset(name)
    else:
        api.add_dataset(name, intermediate, select=False, replace=True)
    transient = api.compare_datasets(*_NAMES, ["key"], ["v"])
    assert transient["outcome"].tolist() == ["regression"]
    if revert == "undo":
        api.undo_dataset(name)
    elif revert == "redo":
        api.redo_dataset(name)
    else:
        api.restore_dataset_revision(before.revision_id)
    fresh = api.capture_preview_inputs(_NAMES)
    assert isinstance(fresh, DatasetPreviewInputs)
    after = next(source for source in fresh.sources if source.dataset_name == name)
    assert after.revision_id == before.revision_id
    assert after.workspace_generation == before.workspace_generation
    assert after.mutation_version > before.mutation_version
    assert fresh != captured
    with pytest.raises(ValueError, match="source changed during computation"):
        api.set_preview("comparison", transient, operation_config=_OPTIONS, inputs=captured)
    assert api.get_preview("comparison") is None
    pd.testing.assert_frame_equal(api.state_manager.get_preview("comparison"), prior)
    _, corrected = _store(api)
    assert corrected["outcome"].tolist() == ["improvement"]
    pd.testing.assert_frame_equal(api.get_preview("comparison"), corrected)
