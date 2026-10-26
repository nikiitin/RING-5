"""Immutable declared native slots and geometry-free Distribution label views."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.common.security_limits import MAX_INCREMENTAL_CACHE_COLUMNS
from src.core.models.distribution_geometry import DistributionGeometry, native_bucket_label

ZeroPolicy = Literal["missing", "nozero"]
DistributionRole = Literal["bucket", "underflow", "overflow", "summary", "source"]


def _text(value: object) -> None:
    if type(value) is not str or not value or len(value) > MAX_INPUT_LENGTH:
        raise ValueError("Distribution bindings require bounded non-empty text.")


@dataclass(frozen=True, slots=True)
class DistributionColumn:
    """Bind one output column to its literal label and declared coordinate role.

    Attributes:
        column: Exact published numeric column name.
        source_label: Literal source entry label, independent of output naming.
        role: Bucket, tail, selected summary or opaque source binding.
        native_index: Nonnegative allocated slot for a bucket; None for other roles.

    Raises:
        ValueError: Text, role or the role/index relationship is invalid.
    """

    column: str
    source_label: str
    role: DistributionRole
    native_index: int | None

    def __post_init__(self) -> None:
        _text(self.column)
        _text(self.source_label)
        if type(self.role) is not str or self.role not in {
            "bucket",
            "underflow",
            "overflow",
            "summary",
            "source",
        }:
            raise ValueError("Distribution columns require a current explicit role.")
        if self.role == "bucket":
            if type(self.native_index) is not int or self.native_index < 0:
                raise ValueError("Native bucket bindings require a non-negative integer slot.")
        elif self.native_index is not None:
            raise ValueError("Only native bucket bindings have an allocated slot.")


def _columns(value: object) -> tuple[DistributionColumn, ...]:
    if type(value) is not tuple:
        raise TypeError("Distribution columns must be an immutable tuple.")
    if not value or len(value) > MAX_INCREMENTAL_CACHE_COLUMNS:
        raise ValueError("Distribution columns exceed their physical width budget.")
    if any(type(column) is not DistributionColumn for column in value):
        raise TypeError("Distribution columns require typed bindings.")
    if len({column.column for column in value}) != len(value):
        raise ValueError("Distribution physical column bindings must be unique.")
    if len({column.source_label for column in value}) != len(value):
        raise ValueError("Distribution source labels collide after native formatting.")
    return value


@dataclass(frozen=True, slots=True)
class NativeDistributionLayout:
    """A caller-declared native grid and its complete numeric output bindings.

    The request basis asserts a decoder contract. It does not authenticate the
    producer's hidden storage class or its externally supplied omission guarantee.

    Attributes:
        geometry: Full-precision declared native grid.
        zero_policy: Explicit missing or nozero omission guarantee for present frames.
        columns: Complete ordered bindings: underflow, all native slots, overflow,
            then any selected summaries. Physical names and source labels are unique.
        kind: The fixed gem5_distribution layout identifier.
        basis: The fixed request declaration basis.

    Raises:
        TypeError: Geometry or immutable typed bindings have unsupported types.
        ValueError: Policy, physical width, labels, slot order or ownership is invalid.
    """

    geometry: DistributionGeometry
    zero_policy: ZeroPolicy
    columns: tuple[DistributionColumn, ...]
    kind: Literal["gem5_distribution"] = field(default="gem5_distribution", init=False)
    basis: Literal["request"] = field(default="request", init=False)

    def __post_init__(self) -> None:
        if type(self.geometry) is not DistributionGeometry:
            raise TypeError("Native layouts require full declared DistributionGeometry.")
        if type(self.zero_policy) is not str or self.zero_policy not in {"missing", "nozero"}:
            raise ValueError("Native layouts require explicit missing or nozero policy.")
        if self.geometry.bucket_count + 2 > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ValueError("Native layout exceeds its physical column budget.")
        columns = _columns(self.columns)
        count = self.geometry.bucket_count
        if len(columns) < count + 2:
            raise ValueError("Native layouts require every allocated slot and both tails.")
        for position, column in enumerate(columns):
            if position == 0:
                role, label, index = "underflow", "underflows", None
            elif position <= count:
                index = position - 1
                role, label = "bucket", native_bucket_label(self.geometry, index)
            elif position == count + 1:
                role, label, index = "overflow", "overflows", None
            else:
                role, label, index = "summary", column.source_label, None
            if (column.role, column.source_label, column.native_index) != (role, label, index):
                raise ValueError("Native columns contradict declared slot order, labels or roles.")


@dataclass(frozen=True, slots=True)
class OpaqueDistributionLayout:
    """Literal selected labels from an explicitly declared Distribution source.

    The request supplies no native grid. These numeric bindings preserve usable
    Vector extraction without claiming continuous support or native slot indices.

    Attributes:
        columns: Nonempty ordered source-only bindings, with unique physical names
            and literal labels; every native_index is None.
        kind: The fixed distribution_source_labels layout identifier.
        basis: The fixed request declaration basis.

    Raises:
        TypeError: Bindings are not an immutable tuple of DistributionColumn values.
        ValueError: Width, uniqueness or source-only role constraints are invalid.
    """

    columns: tuple[DistributionColumn, ...]
    kind: Literal["distribution_source_labels"] = field(
        default="distribution_source_labels", init=False
    )
    basis: Literal["request"] = field(default="request", init=False)

    def __post_init__(self) -> None:
        if any(column.role != "source" for column in _columns(self.columns)):
            raise ValueError("Opaque Distribution bindings carry source labels without slot roles.")


DistributionLayout = NativeDistributionLayout | OpaqueDistributionLayout
