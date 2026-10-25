"""Honest source contract evidence, declarations and immutable JSON boundaries."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.models.source_evidence import (
    AmbiguousSourceKind,
    ResolvedSourceKind,
    SourceKindBinding,
    SourceKindEvidence,
    decode_source_kind_binding,
    decode_source_kind_evidence,
    encode_source_kind_binding,
    encode_source_kind_evidence,
)


@pytest.mark.parametrize("basis", ["backend_metadata", "wire_contract"])
def test_resolved_evidence_retains_kind_and_its_limited_basis(basis: str) -> None:
    evidence = decode_source_kind_evidence({"state": "resolved", "kind": "scalar", "basis": basis})
    assert evidence == ResolvedSourceKind("scalar", basis)  # type: ignore[arg-type]
    assert encode_source_kind_evidence(evidence) == {
        "state": "resolved",
        "kind": "scalar",
        "basis": basis,
    }
    assert not hasattr(evidence, "source_type")


def test_ambiguous_evidence_does_not_choose_a_source_or_output_kind() -> None:
    candidates = ("distribution", "histogram", "vector")
    evidence = AmbiguousSourceKind(candidates)
    assert evidence.candidates == candidates
    assert not hasattr(evidence, "kind")
    assert not hasattr(evidence, "source_type")
    for kind in candidates:
        binding = SourceKindBinding(kind, evidence)
        assert binding.declared_kind == kind
        assert binding.evidence is evidence
        assert binding.evidence.state == "ambiguous"
        assert binding.basis == "request"


@pytest.mark.parametrize(
    "evidence",
    [
        ResolvedSourceKind("scalar", "wire_contract"),
        ResolvedSourceKind("distribution", "backend_metadata"),
        AmbiguousSourceKind(("distribution", "histogram", "vector")),
    ],
)
def test_request_kind_must_match_the_observed_compatible_contract(
    evidence: SourceKindEvidence,
) -> None:
    with pytest.raises(ValueError, match="contradicts"):
        SourceKindBinding("configuration", evidence)


def test_models_preserve_registered_backend_kind_spelling_without_registry_import() -> None:
    evidence = ResolvedSourceKind("plugin.CounterCPU00", "backend_metadata")
    binding = SourceKindBinding("plugin.CounterCPU00", evidence)
    assert decode_source_kind_binding(encode_source_kind_binding(binding)) == binding
    with pytest.raises(ValueError, match="contradicts"):
        SourceKindBinding("plugin.countercpu00", evidence)


@pytest.mark.parametrize("kind", [None, True, 1, "", "x" * (MAX_INPUT_LENGTH + 1)])
def test_kind_fields_are_actual_bounded_text(kind: object) -> None:
    with pytest.raises(ValueError, match="bounded non-empty text"):
        ResolvedSourceKind(cast(str, kind), "wire_contract")
    with pytest.raises(ValueError, match="bounded non-empty text"):
        SourceKindBinding(cast(str, kind), ResolvedSourceKind("scalar", "wire_contract"))


@pytest.mark.parametrize("basis", [None, True, "inferred", "request", "Wire_Contract"])
def test_resolved_evidence_rejects_inferred_or_declared_provenance(basis: object) -> None:
    with pytest.raises(ValueError, match="evidence basis"):
        decode_source_kind_evidence({"state": "resolved", "kind": "vector", "basis": basis})


@pytest.mark.parametrize(
    "candidates",
    [(), ("vector",), ("vector", "vector"), ("vector", "distribution"), ("", "vector")],
)
def test_ambiguous_candidates_are_a_current_canonical_set(candidates: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        AmbiguousSourceKind(candidates)


def test_candidate_size_is_checked_before_sorting_or_copying_unbounded_wire_lists() -> None:
    with pytest.raises(ValueError, match="bounded collection"):
        decode_source_kind_evidence(
            {"state": "ambiguous", "candidates": ["vector"] * (MAX_INPUT_LENGTH + 1)}
        )
    with pytest.raises(ValueError, match="text budget"):
        AmbiguousSourceKind(("a" * MAX_INPUT_LENGTH, "vector"))


@pytest.mark.parametrize("candidates", [["distribution", "vector"], "distribution,vector", {}])
def test_model_does_not_adapt_mutable_or_comma_separated_candidates(candidates: object) -> None:
    with pytest.raises(TypeError, match="immutable tuple"):
        AmbiguousSourceKind(cast(tuple[str, ...], candidates))


@pytest.mark.parametrize("candidates", [("distribution", "vector"), "distribution,vector", None])
def test_wire_candidates_require_the_current_list_container(candidates: object) -> None:
    with pytest.raises(TypeError, match="must be a list"):
        decode_source_kind_evidence({"state": "ambiguous", "candidates": candidates})


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"source_type": "vector"},
        {"state": "inferred", "kind": "vector"},
        {"state": "resolved", "kind": "vector"},
        {"state": "resolved", "kind": "vector", "basis": "wire_contract", "source_type": "vector"},
        {"state": "ambiguous", "candidates": ["distribution", "vector"], "kind": "vector"},
        {"state": None, "kind": "vector"},
    ],
)
def test_evidence_codec_rejects_incomplete_retired_and_redundant_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        decode_source_kind_evidence(payload)


@pytest.mark.parametrize("payload", [None, [], (), "vector"])
def test_evidence_codec_requires_an_object(payload: object) -> None:
    with pytest.raises(TypeError, match="object"):
        decode_source_kind_evidence(payload)


def test_codec_output_and_inputs_cannot_mutate_evidence_or_request_binding() -> None:
    wire: dict[str, object] = {"state": "ambiguous", "candidates": ["distribution", "vector"]}
    evidence = decode_source_kind_evidence(wire)
    cast(list[str], wire["candidates"]).append("histogram")
    assert evidence == AmbiguousSourceKind(("distribution", "vector"))
    binding = SourceKindBinding("distribution", evidence)
    encoded = encode_source_kind_binding(binding)
    nested = cast(dict[str, object], encoded["evidence"])
    cast(list[str], nested["candidates"]).append("scalar")
    assert binding.evidence == AmbiguousSourceKind(("distribution", "vector"))
    exact = encode_source_kind_binding(binding)
    assert decode_source_kind_binding(json.loads(json.dumps(exact))) == binding
    with pytest.raises(FrozenInstanceError):
        setattr(binding, "declared_kind", "vector")
    with pytest.raises(FrozenInstanceError):
        setattr(evidence, "candidates", ("scalar", "vector"))


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"declared_kind": "vector", "evidence": {}, "basis": "inferred"},
        {"declared_kind": "vector", "evidence": {}, "basis": "request", "source_type": "vector"},
        {
            "declared_kind": "vector",
            "evidence": {"state": "ambiguous", "candidates": ["distribution", "vector"]},
        },
    ],
)
def test_binding_codec_rejects_other_admission_shapes(payload: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        decode_source_kind_binding(payload)


def test_bindings_and_encoders_require_the_actual_current_models() -> None:
    with pytest.raises(TypeError, match="typed source evidence"):
        SourceKindBinding("vector", cast(SourceKindEvidence, {"kind": "vector"}))
    with pytest.raises(TypeError, match="typed variant"):
        encode_source_kind_evidence(cast(SourceKindEvidence, {"kind": "vector"}))
    with pytest.raises(TypeError, match="typed model"):
        encode_source_kind_binding(cast(SourceKindBinding, {"declared_kind": "vector"}))
