"""Observed source-kind evidence and separate explicit request bindings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, cast

from src.core.common.safe_regex import MAX_INPUT_LENGTH

SourceKindBasis = Literal["backend_metadata", "wire_contract"]


def _kind(value: object) -> None:
    """Validate structure only; the selected backend owns registered-kind admission."""
    if type(value) is not str or not value or len(value) > MAX_INPUT_LENGTH:
        raise ValueError("A source kind must be bounded non-empty text.")


@dataclass(frozen=True, slots=True)
class ResolvedSourceKind:
    """One compatible backend contract with honest evidence provenance.

    ``wire_contract`` identifies a decoder contract, not hidden native storage.
    ``backend_metadata`` requires an actual producer kind tag. Neither basis is
    supplied merely because a summary name or entry label looks familiar.
    """

    kind: str
    basis: SourceKindBasis
    state: Literal["resolved"] = field(default="resolved", init=False)

    def __post_init__(self) -> None:
        _kind(self.kind)
        if type(self.basis) is not str or self.basis not in ("backend_metadata", "wire_contract"):
            raise ValueError("Resolved source evidence requires a current evidence basis.")


@dataclass(frozen=True, slots=True)
class AmbiguousSourceKind:
    """Multiple compatible current contracts, without a guessed runnable default.

    Candidates are immutable, distinct and sorted. Their combined text uses the
    existing source-input budget; backend registration is checked by its codec.
    """

    candidates: tuple[str, ...]
    state: Literal["ambiguous"] = field(default="ambiguous", init=False)

    def __post_init__(self) -> None:
        if type(self.candidates) is not tuple:
            raise TypeError("Source kind candidates must be an immutable tuple.")
        if not 2 <= len(self.candidates) <= MAX_INPUT_LENGTH:
            raise ValueError(
                "Ambiguous source evidence requires a bounded set of at least two kinds."
            )
        for candidate in self.candidates:
            _kind(candidate)
        if sum(map(len, self.candidates)) > MAX_INPUT_LENGTH:
            raise ValueError("Source kind candidates exceed the source-input text budget.")
        if self.candidates != tuple(sorted(set(self.candidates))):
            raise ValueError("Source kind candidates must be distinct and canonically sorted.")


SourceKindEvidence = ResolvedSourceKind | AmbiguousSourceKind


@dataclass(frozen=True, slots=True)
class SourceKindBinding:
    """An explicit request kind checked against compatible observed contracts.

    The request declaration resolves execution ambiguity without claiming that
    the observed bytes uniquely establish a physical producer storage class.
    """

    declared_kind: str
    evidence: SourceKindEvidence
    basis: Literal["request"] = field(default="request", init=False)

    def __post_init__(self) -> None:
        _kind(self.declared_kind)
        if type(self.evidence) is ResolvedSourceKind:
            compatible = self.declared_kind == self.evidence.kind
        elif type(self.evidence) is AmbiguousSourceKind:
            compatible = self.declared_kind in self.evidence.candidates
        else:
            raise TypeError("A source binding requires current typed source evidence.")
        if not compatible:
            raise ValueError("Declared source kind contradicts the observed source evidence.")


def encode_source_kind_evidence(evidence: SourceKindEvidence) -> dict[str, object]:
    """Encode exact observed evidence without a redundant source_type projection.

    Args:
        evidence: One current immutable evidence variant.

    Returns:
        An independently owned JSON object with its explicit state.

    Raises:
        TypeError: Evidence is not a current typed variant.
    """
    if type(evidence) is ResolvedSourceKind:
        return {"state": evidence.state, "kind": evidence.kind, "basis": evidence.basis}
    if type(evidence) is AmbiguousSourceKind:
        return {"state": evidence.state, "candidates": list(evidence.candidates)}
    raise TypeError("Source evidence requires a current typed variant.")


def decode_source_kind_evidence(value: object) -> SourceKindEvidence:
    """Decode one strict resolved or ambiguous current evidence object.

    Args:
        value: A JSON object with exactly the fields of its state.

    Returns:
        Immutable validated evidence without kind inference or registration lookup.

    Raises:
        TypeError: The object or candidate container has the wrong type.
        ValueError: The state, fields, evidence basis or candidates are invalid.
    """
    if type(value) is not dict:
        raise TypeError("Source kind evidence must be an object.")
    if type(value.get("state")) is not str:
        raise ValueError("Source kind evidence requires an explicit current state.")
    if value["state"] == "resolved":
        if set(value) != {"state", "kind", "basis"}:
            raise ValueError("Resolved source evidence requires exactly state, kind and basis.")
        return ResolvedSourceKind(cast(str, value["kind"]), cast(SourceKindBasis, value["basis"]))
    if value["state"] == "ambiguous":
        if set(value) != {"state", "candidates"}:
            raise ValueError("Ambiguous source evidence requires exactly state and candidates.")
        candidates = value["candidates"]
        if type(candidates) is not list:
            raise TypeError("Serialized source kind candidates must be a list.")
        if not 2 <= len(candidates) <= MAX_INPUT_LENGTH:
            raise ValueError("Source kind candidates exceed their bounded collection size.")
        return AmbiguousSourceKind(tuple(candidates))
    raise ValueError("Source kind evidence requires a current resolved or ambiguous state.")


def source_kind_candidates(evidence: SourceKindEvidence) -> frozenset[str]:
    """Return the compatible contracts without choosing an execution default."""
    if type(evidence) is ResolvedSourceKind:
        return frozenset((evidence.kind,))
    if type(evidence) is AmbiguousSourceKind:
        return frozenset(evidence.candidates)
    raise TypeError("Source evidence requires a current typed variant.")


def intersect_source_kind_evidence(
    left: SourceKindEvidence, right: SourceKindEvidence
) -> SourceKindEvidence:
    """Intersect independent observations or reject their explicit contradiction."""
    candidates = source_kind_candidates(left) & source_kind_candidates(right)
    if not candidates:
        raise ValueError("Observed source contracts contradict one another.")
    if len(candidates) == 1:
        basis: SourceKindBasis = (
            "backend_metadata"
            if type(left) is ResolvedSourceKind
            and type(right) is ResolvedSourceKind
            and left.basis == right.basis == "backend_metadata"
            else "wire_contract"
        )
        return ResolvedSourceKind(next(iter(candidates)), basis)
    return AmbiguousSourceKind(tuple(sorted(candidates)))
