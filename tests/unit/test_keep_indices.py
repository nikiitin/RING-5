"""Concrete source selection and output naming use the production source compiler."""

from src.core.models.source_evidence import ResolvedSourceKind


from dataclasses import FrozenInstanceError, replace

import pytest

from src.core.models.parsing_models import ScannedVariable, SourceInstance, StatConfig
from src.parsing.gem5.impl.source_bindings import resolve_sources


def _metadata():
    return [
        ScannedVariable(
            r"l\d+_cpu\d+.ipc",
            "vector",
            [],
            source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
            instances=(
                SourceInstance("l0_cpu1.ipc", ("0", "1")),
                SourceInstance("l1_cpu0.ipc", ("1", "0")),
                SourceInstance("l1_cpu1.ipc", ("1", "1")),
            ),
        )
    ]


def test_keep_indices_is_frozen_and_independent_of_regex():
    config = StatConfig("ipc", "scalar", params={"source_type": "scalar"})
    assert config.keep_indices is False
    changed = replace(config, keep_indices=True)
    assert changed.keep_indices and not changed.is_regex
    with pytest.raises(FrozenInstanceError):
        changed.keep_indices = False


@pytest.mark.parametrize("keep", [False, True])
def test_correlated_concrete_selection_is_preserved_without_cartesian_expansion(keep):
    # [test->req~ring5.ingestion.pattern-index-selection~1]
    config = StatConfig(
        "Output IPC",
        "scalar",
        repeat=3,
        is_regex=True,
        keep_indices=keep,
        source_name=r"l\d+_cpu\d+.ipc",
        params={"source_type": "scalar", "selected_sources": ["l0_cpu1.ipc", "l1_cpu0.ipc"]},
    )
    plan = resolve_sources([config], _metadata())
    assert set(plan.routes) == {"l0_cpu1.ipc", "l1_cpu0.ipc"}
    assert [spec.output_name for spec in plan.accumulators] == (
        ["l0_cpu1.ipc", "l1_cpu0.ipc"] if keep else ["Output IPC"]
    )
    assert [spec.repeat for spec in plan.accumulators] == ([3, 3] if keep else [6])
    assert all(spec.config == config for spec in plan.accumulators)
    assert config.params["selected_sources"] == ["l0_cpu1.ipc", "l1_cpu0.ipc"]


def test_unfiltered_request_uses_explicit_records_and_empty_selection_fails():
    config = StatConfig(
        r"l\d+_cpu\d+.ipc", "scalar", keep_indices=True, params={"source_type": "scalar"}
    )
    assert len(resolve_sources([config], _metadata()).accumulators) == 3
    with pytest.raises(ValueError, match="Selected sources"):
        resolve_sources(
            [replace(config, params={"source_type": "scalar", "selected_sources": []})], _metadata()
        )
