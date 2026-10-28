"""Workspace ownership separates dataset revisions from finalized plot relations."""

from __future__ import annotations

from typing import Literal

import pandas as pd
import pytest

from src.core.common.content_identity import frame_signature
from src.core.common.source_contributions import (
    SOURCE_CONTRIBUTIONS_ATTR,
    identity_source_contributions,
    require_source_contributions,
)
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.state.repositories.data_repository import DataRepository


@pytest.mark.parametrize("destination", ["primary", "processed", "named"])
@pytest.mark.parametrize("changed", [False, True], ids=["exact-input", "inherited-after-transform"])
def test_workspace_entry_detaches_plot_proof_before_copying_or_revision_identity(
    destination: Literal["primary", "processed", "named"],
    changed: bool,
) -> None:
    source = pd.DataFrame(
        {"kind": ["A", "B"], "value": [1.0, 2.0], "notes": [["first"], ["second"]]}
    )
    source.attrs["retained"] = {"tags": ["scientific metadata"]}
    finalized = identity_source_contributions(source)
    incoming = finalized.assign(value=[3.0, 4.0]) if changed else finalized
    original_payload = finalized.attrs[SOURCE_CONTRIBUTIONS_ATTR]
    repository = DataRepository()
    if destination == "primary":
        repository.set_data(incoming)
        stored = repository.get_data()
    elif destination == "processed":
        repository.set_processed_data(incoming)
        stored = repository.get_processed_data()
    else:
        repository.add_dataset("source", incoming)
        stored = repository.get_dataset("source")
    assert stored is not None
    assert SOURCE_CONTRIBUTIONS_ATTR not in stored.attrs
    assert stored["value"].tolist() == ([3.0, 4.0] if changed else [1.0, 2.0])
    assert stored.attrs["retained"] == {"tags": ["scientific metadata"]}
    assert finalized.attrs[SOURCE_CONTRIBUTIONS_ATTR] is original_payload
    require_source_contributions(source, finalized)
    decoded = TypedTableCodec.decode(TypedTableCodec.encode(stored))
    assert decoded is not None
    pd.testing.assert_frame_equal(decoded, stored)
    if destination == "named":
        revision = repository.get_dataset_lineage().revisions[0]
        assert revision.fingerprint == frame_signature(stored)
    stored.loc[0, "notes"].append("edited")
    stored.attrs["retained"]["tags"].append("edited")
    assert finalized.loc[0, "notes"] == ["first"]
    assert finalized.attrs["retained"] == {"tags": ["scientific metadata"]}


def test_named_workspace_recovery_keeps_each_independent_revision_serializable() -> None:
    source = pd.DataFrame({"kind": ["A", "B"], "value": [1.0, 2.0]})
    finalized = identity_source_contributions(source)
    repository = DataRepository()
    repository.add_dataset("source", finalized)
    initial_id = repository.get_dataset_lineage().current_revision_id
    repository.set_data(finalized.assign(value=[3.0, 4.0]), operation="Change measurement")
    updated_id = repository.get_dataset_lineage().current_revision_id
    assert initial_id != updated_id
    for revision_id, values in [(initial_id, [1.0, 2.0]), (updated_id, [3.0, 4.0])]:
        revision = repository.get_dataset_revision(revision_id)
        assert SOURCE_CONTRIBUTIONS_ATTR not in revision.attrs
        assert revision["value"].tolist() == values
        TypedTableCodec.encode(revision)
    repository.undo_dataset()
    assert repository.get_dataset()["value"].tolist() == [1.0, 2.0]
    repository.redo_dataset()
    assert repository.get_dataset()["value"].tolist() == [3.0, 4.0]
    repository.restore_dataset_revision(initial_id)
    recovered = repository.get_data()
    assert recovered is not None
    assert SOURCE_CONTRIBUTIONS_ATTR not in recovered.attrs
    assert recovered["value"].tolist() == [1.0, 2.0]
    require_source_contributions(source, finalized)
