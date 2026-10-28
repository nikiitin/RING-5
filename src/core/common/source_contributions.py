"""Owned, bounded raw-row contributions for one finalized plot pipeline."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from copy import deepcopy
import re
from typing import Any

import pandas as pd

from src.core.common.content_identity import content_signature, frame_signature
from src.core.common.security_limits import MAX_TYPED_TABLE_ITEMS, MAX_TYPED_TABLE_ROWS

SOURCE_CONTRIBUTIONS_ATTR = "ring5.source_contributions"
_SIGNATURE = re.compile(r"sha256:[0-9a-f]{64}")


def contribution_frame_identity(frame: pd.DataFrame) -> str:
    """Identify a table without its self-referential contribution declaration."""
    plain = frame.copy(deep=False)
    plain.attrs = {
        key: value for key, value in frame.attrs.items() if key != SOURCE_CONTRIBUTIONS_ATTR
    }
    return frame_signature(plain)


@dataclass(frozen=True, slots=True)
class SourceContributions:
    """A validated DAG mapping output positions to original input positions."""

    source_identity: str
    output_identity: str
    source_rows: int
    roots: tuple[int, ...]
    unions: tuple[tuple[int, ...], ...]

    def resolve(self, output_positions: Iterable[int]) -> list[int]:
        """Return original positions once each, in their input-table order."""
        pending = [self.roots[position] for position in output_positions]
        seen: set[int] = set()
        positions: set[int] = set()
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            seen.add(node)
            if node < self.source_rows:
                positions.add(node)
            else:
                pending.extend(self.unions[node - self.source_rows])
        return sorted(positions)

    def payload(self) -> dict[str, Any]:
        """Return the one primitive serialization accepted by the table codec."""
        value: dict[str, Any] = {
            "version": 1,
            "source_identity": self.source_identity,
            "output_identity": self.output_identity,
            "source_rows": self.source_rows,
            "roots": list(self.roots),
            "unions": [list(children) for children in self.unions],
        }
        value["relation_identity"] = content_signature(value)
        return value


def inspect_source_contributions(frame: pd.DataFrame) -> SourceContributions | None:
    """Validate present contribution metadata against its exact output table."""
    if SOURCE_CONTRIBUTIONS_ATTR not in frame.attrs:
        return None
    value = frame.attrs[SOURCE_CONTRIBUTIONS_ATTR]
    required = {
        "version",
        "source_identity",
        "output_identity",
        "source_rows",
        "roots",
        "unions",
        "relation_identity",
    }
    if type(value) is not dict or set(value) != required or type(value["version"]) is not int:
        raise ValueError("Source contribution metadata has invalid fields.")
    if value["version"] != 1:
        raise ValueError("Source contribution metadata has an unsupported version.")
    if any(
        type(value[key]) is not str or _SIGNATURE.fullmatch(value[key]) is None
        for key in ("source_identity", "output_identity", "relation_identity")
    ):
        raise ValueError("Source contribution identities must be SHA-256 signatures.")
    count = value["source_rows"]
    roots, unions = value["roots"], value["unions"]
    if type(count) is not int or not 0 <= count <= MAX_TYPED_TABLE_ROWS:
        raise ValueError("Source contribution row count is invalid.")
    if type(roots) is not list or len(roots) != len(frame) or type(unions) is not list:
        raise ValueError("Source contribution roots do not match the output table.")
    items = len(roots) + len(unions)
    if items > MAX_TYPED_TABLE_ITEMS:
        raise ValueError("Source contribution DAG exceeds its item budget.")
    for ordinal, children in enumerate(unions):
        if type(children) is not list or len(children) < 2:
            raise ValueError("Source contribution union nodes require at least two children.")
        items += len(children)
        if items > MAX_TYPED_TABLE_ITEMS:
            raise ValueError("Source contribution DAG exceeds its item budget.")
        limit = count + ordinal
        if any(type(child) is not int or not 0 <= child < limit for child in children):
            raise ValueError("Source contribution DAG contains an invalid or cyclic reference.")
        if children != sorted(set(children)):
            raise ValueError("Source contribution union children must be unique and sorted.")
    limit = count + len(unions)
    if any(type(root) is not int or not 0 <= root < limit for root in roots):
        raise ValueError("Source contribution output roots contain invalid references.")
    identity = content_signature(
        {key: item for key, item in value.items() if key != "relation_identity"}
    )
    if identity != value["relation_identity"]:
        raise ValueError("Source contribution checksum does not match the relation.")
    if value["output_identity"] != contribution_frame_identity(frame):
        raise ValueError("Source contribution output identity does not match the table.")
    return SourceContributions(
        value["source_identity"],
        value["output_identity"],
        count,
        tuple(roots),
        tuple(tuple(children) for children in unions),
    )


def require_source_contributions(source: pd.DataFrame, output: pd.DataFrame) -> SourceContributions:
    """Require an exact original-source and finalized-output contribution relation."""
    relation = inspect_source_contributions(output)
    if relation is None:
        raise ValueError(
            "Insufficient source provenance; finalize the pipeline before exploring rows."
        )
    if relation.source_rows != len(
        source
    ) or relation.source_identity != contribution_frame_identity(source):
        raise ValueError("Source contribution input identity does not match the retained source.")
    return relation


def validate_present_source_pair(source: pd.DataFrame | None, output: pd.DataFrame | None) -> None:
    """Reject a declared but mismatched source/output pair; unproven tables remain renderable."""
    if output is None or SOURCE_CONTRIBUTIONS_ATTR not in output.attrs:
        return
    if source is None:
        raise ValueError("Source contribution metadata requires its retained original source.")
    require_source_contributions(source, output)


@dataclass(slots=True)
class _ContributionGraph:
    source_identity: str
    source_rows: int
    unions: list[tuple[int, ...]] = field(default_factory=list)
    interned: dict[tuple[int, ...], int] = field(default_factory=dict)
    references: int = 0

    def union(self, roots: Iterable[int]) -> int:
        """Intern a nonempty union within the shared contribution budget."""
        children = tuple(sorted(set(roots)))
        if not children:
            raise ValueError("A generated observation has no original source contribution.")
        if len(children) == 1:
            return children[0]
        existing = self.interned.get(children)
        if existing is not None:
            return existing
        self.references += len(children)
        if self.references + len(self.unions) + self.source_rows > MAX_TYPED_TABLE_ITEMS:
            raise ValueError("Source contribution DAG exceeds its item budget.")
        node = self.source_rows + len(self.unions)
        self.unions.append(children)
        self.interned[children] = node
        return node


class SourceTracker:
    """Track one canonical execution without inserting columns into scientific data."""

    def __init__(self, source: pd.DataFrame) -> None:
        if not isinstance(source, pd.DataFrame):
            raise TypeError("Source contributions require a pandas DataFrame.")
        if len(source) > MAX_TYPED_TABLE_ROWS:
            raise ValueError("Source contribution row count exceeds its budget.")
        inspect_source_contributions(source)
        self.graph = _ContributionGraph(contribution_frame_identity(source), len(source))
        self.roots = list(range(len(source)))
        self.revision = 0

    def fork(self) -> SourceTracker:
        """Share immutable source nodes while giving a branch its own row ordering."""
        result = object.__new__(SourceTracker)
        result.graph = self.graph
        result.roots = self.roots.copy()
        result.revision = 0
        return result

    def select(self, positions: Iterable[int]) -> None:
        """Apply the operation's actual row selection or permutation."""
        self.roots = [self.roots[int(position)] for position in positions]
        self.revision += 1

    def append_groups(self, groups: Iterable[Iterable[int]]) -> None:
        """Append the original contributors behind each actual aggregate group."""
        original = self.roots.copy()
        self.roots.extend(
            self.graph.union(original[int(position)] for position in group) for group in groups
        )
        self.revision += 1

    def normalize(self, groups: Iterable[tuple[Sequence[int], int]]) -> None:
        """Record each actual baseline dependency without changing output ordering."""
        original = self.roots.copy()
        for positions, baseline in groups:
            for position in positions:
                self.roots[int(position)] = self.graph.union(
                    (original[int(position)], original[baseline])
                )
        self.revision += 1

    def combine_groups(self, groups: Iterable[Iterable[int]]) -> None:
        """Replace rows with the unions selected by an actual regrouping operation."""
        original = self.roots
        self.roots = [
            self.graph.union(original[int(position)] for position in group) for group in groups
        ]
        self.revision += 1

    def merge_branches(
        self,
        left: pd.DataFrame,
        left_roots: Sequence[int],
        right: pd.DataFrame,
        right_roots: Sequence[int],
        keys: Sequence[str],
        output: pd.DataFrame,
    ) -> None:
        """Mirror a one-to-one outer key join to retain both branches' contributors."""
        left_name, right_name = "__ring5_left_position", "__ring5_right_position"
        while left_name in left.columns or left_name in right.columns:
            left_name += "_"
        while right_name in left.columns or right_name in right.columns or right_name == left_name:
            right_name += "_"
        lhs = left[list(keys)].assign(**{left_name: range(len(left))})
        rhs = right[list(keys)].assign(**{right_name: range(len(right))})
        joined = lhs.merge(rhs, on=list(keys), how="outer", validate="one_to_one")
        if not joined[list(keys)].equals(output[list(keys)]):
            raise ValueError("Source contribution join order differs from the actual operation.")
        roots: list[int] = []
        for left_position, right_position in joined[[left_name, right_name]].itertuples(
            index=False, name=None
        ):
            contributors = []
            if pd.notna(left_position):
                contributors.append(left_roots[int(left_position)])
            if pd.notna(right_position):
                contributors.append(right_roots[int(right_position)])
            roots.append(self.graph.union(contributors))
        self.roots = roots
        self.revision += 1

    def publish(self, output: pd.DataFrame) -> pd.DataFrame:
        """Own and seal the final relation against the exact numeric result."""
        if len(self.roots) != len(output):
            raise ValueError("Source contribution roots do not match the finalized output.")
        relation = SourceContributions(
            self.graph.source_identity,
            contribution_frame_identity(output),
            self.graph.source_rows,
            tuple(self.roots),
            tuple(self.graph.unions),
        )
        result = output.copy(deep=False)
        result.attrs = deepcopy(output.attrs)
        result.attrs[SOURCE_CONTRIBUTIONS_ATTR] = relation.payload()
        inspect_source_contributions(result)
        return result


def without_source_contributions(frame: pd.DataFrame) -> pd.DataFrame:
    """Detach a finalized relation when an independent transformation creates new data."""
    result = frame.copy(deep=False)
    result.attrs = {
        key: value for key, value in frame.attrs.items() if key != SOURCE_CONTRIBUTIONS_ATTR
    }
    return result


def identity_source_contributions(frame: pd.DataFrame) -> pd.DataFrame:
    """Establish a newly created plot's explicit input as its original source."""
    return SourceTracker(frame).publish(frame)
