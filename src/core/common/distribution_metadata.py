"""Strict, owned Distribution declarations and explicit dataframe operation policies.

The reserved attribute records caller-declared physical bindings. It never infers
geometry from names, values, pandas attribute inheritance or producer provenance.
"""

from __future__ import annotations

import json
from copy import deepcopy
from collections.abc import Iterable, Mapping, Sequence
from itertools import zip_longest
from numbers import Integral

import pandas as pd

from src.core.common.distribution_layout_codec import (
    decode_distribution_layout,
    encode_distribution_layout,
    iter_distribution_layout_encoding,
)
from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.common.security_limits import (
    MAX_INCREMENTAL_CACHE_COLUMNS,
    MAX_PARSED_SCHEMA_BYTES,
    MAX_PARSE_VARIABLES,
)
from src.core.models.native_distribution_layout import DistributionLayout

DISTRIBUTION_LAYOUTS_ATTR = "ring5.distribution_layouts"


class _MetadataBudget:
    """Charge mapping framing and the layout codec's exact canonical fragments."""

    def __init__(self) -> None:
        self.size = 2  # The enclosing object braces.
        self.columns = 0

    def admit(self, fragment: bytes) -> None:
        self.size += len(fragment)
        if self.size > MAX_PARSED_SCHEMA_BYTES:
            raise ValueError("Distribution metadata exceeds its schema byte budget.")

    def entry(self, name: str, count: int, *, first: bool) -> None:
        if type(name) is not str or not name or len(name) > MAX_INPUT_LENGTH:
            raise ValueError("Distribution metadata requires bounded non-empty output names.")
        self.columns += count
        if self.columns > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ValueError("Distribution metadata exceeds its physical column budget.")
        self.admit(json.dumps(name, ensure_ascii=False).encode("utf-8"))
        self.admit(b":" if first else b",:")


def _bindings_valid(frame: pd.DataFrame, layout: DistributionLayout) -> bool:
    for binding in layout.columns:
        try:
            position = frame.columns.get_loc(binding.column)
        except KeyError:
            return False
        if not isinstance(position, Integral):
            return False
        dtype = frame.iloc[:, int(position)].dtype
        if (
            not pd.api.types.is_numeric_dtype(dtype)
            or pd.api.types.is_bool_dtype(dtype)
            or pd.api.types.is_complex_dtype(dtype)
        ):
            return False
    return True


def _claim_bindings(layout: DistributionLayout, claimed: set[str]) -> None:
    for binding in layout.columns:
        if binding.column in claimed:
            raise ValueError("Distribution metadata contains overlapping physical bindings.")
        claimed.add(binding.column)


def inspect_distribution_layouts(frame: pd.DataFrame) -> dict[str, DistributionLayout]:
    """Validate reserved attrs before admitting a dataframe to an owned boundary.

    Args:
        frame: Data with optional current primitive Distribution declarations.

    Returns:
        Immutable typed declarations keyed by logical output name.

    Raises:
        TypeError: The reserved value or a layout has an unsupported exact type.
        ValueError: A declaration exceeds its budget or has invalid numeric bindings.
    """
    if DISTRIBUTION_LAYOUTS_ATTR not in frame.attrs:
        return {}
    raw = frame.attrs[DISTRIBUTION_LAYOUTS_ATTR]
    if type(raw) is not dict:
        raise TypeError("Distribution metadata must be a current object.")
    if len(raw) > MAX_PARSE_VARIABLES:
        raise ValueError("Distribution metadata exceeds its logical output budget.")
    result: dict[str, DistributionLayout] = {}
    budget = _MetadataBudget()
    claimed: set[str] = set()
    for index, (name, value) in enumerate(raw.items()):
        if type(value) is not dict or type(value.get("columns")) is not list:
            raise ValueError("Distribution metadata requires present layout declarations.")
        budget.entry(name, len(value["columns"]), first=index == 0)
        layout = decode_distribution_layout(value, admit=budget.admit)
        assert layout is not None
        _claim_bindings(layout, claimed)
        if not _bindings_valid(frame, layout):
            raise ValueError("Distribution metadata requires unique present real numeric columns.")
        result[name] = layout
    return result


def with_distribution_layouts(
    frame: pd.DataFrame, layouts: Mapping[str, DistributionLayout]
) -> pd.DataFrame:
    """Return a new frame with independently owned current primitive declarations.

    Existing reserved attrs are replaced explicitly, including stale pandas-inherited
    attrs after projection. An empty declaration removes the reserved key. Other
    output attrs remain owned by the new frame; public cell ownership is enforced
    separately by ``copy_dataframe``.

    Args:
        frame: Output whose numeric columns must satisfy every declared binding.
        layouts: Explicit current typed declarations, without absent/null entries.

    Returns:
        An independent dataframe carrying canonical owned metadata.

    Raises:
        TypeError: A layout is not a current typed declaration.
        ValueError: Bindings, names, width or exact canonical bytes are invalid.
    """
    if len(layouts) > MAX_PARSE_VARIABLES:
        raise ValueError("Distribution metadata exceeds its logical output budget.")
    budget = _MetadataBudget()
    claimed: set[str] = set()
    payload: dict[str, object] = {}
    for index, (name, layout) in enumerate(layouts.items()):
        # The codec validates the exact variant before its bindings are accessed.
        fragments = iter_distribution_layout_encoding(layout)
        first = next(fragments)
        if layout is None:
            raise TypeError("Distribution metadata requires present typed declarations.")
        budget.entry(name, len(layout.columns), first=index == 0)
        budget.admit(first)
        for fragment in fragments:
            budget.admit(fragment)
        _claim_bindings(layout, claimed)
        if not _bindings_valid(frame, layout):
            raise ValueError("Distribution metadata requires unique present real numeric columns.")
        payload[name] = encode_distribution_layout(layout)
    # Do not deepcopy a stale/untrusted inherited declaration before replacing it.
    # The constructor copies values without pandas' automatic attrs finalization.
    result = pd.DataFrame(frame, copy=True)
    result.index = frame.index.copy(deep=True)
    result.columns = frame.columns.copy(deep=True)
    result.flags["allows_duplicate_labels"] = frame.flags["allows_duplicate_labels"]
    result.attrs = deepcopy(
        {key: value for key, value in frame.attrs.items() if key != DISTRIBUTION_LAYOUTS_ATTR}
    )
    if payload:
        result.attrs[DISTRIBUTION_LAYOUTS_ATTR] = payload
    return result


def preserve_distribution_layouts(
    source: pd.DataFrame,
    result: pd.DataFrame,
    *,
    invalidated_columns: Iterable[str] = (),
) -> pd.DataFrame:
    """Retain whole declarations for an explicitly coordinate-preserving operation.

    A layout is dropped when any binding is invalidated, missing, duplicated or
    nonnumeric. Column order can change; the declaration's native order cannot.
    Callers must establish operation semantics rather than infer them from names.

    Args:
        source: Admitted input carrying explicit primitive declarations.
        result: Output of the caller's reviewed operation.
        invalidated_columns: Physical destinations whose coordinate roles changed.

    Returns:
        A new frame with independently owned whole retained declarations.

    Raises:
        TypeError: Reserved source metadata has an unsupported current type.
        ValueError: Source declarations or retained output bindings are invalid.
    """
    invalidated = set(invalidated_columns)
    retained = {
        name: layout
        for name, layout in inspect_distribution_layouts(source).items()
        if not any(binding.column in invalidated for binding in layout.columns)
        and _bindings_valid(result, layout)
    }
    return with_distribution_layouts(result, retained)


def _same_declaration(left: DistributionLayout, right: DistributionLayout) -> bool:
    # Canonical bytes distinguish declarations such as signed-zero grid origins.
    return all(
        first == second
        for first, second in zip_longest(
            iter_distribution_layout_encoding(left), iter_distribution_layout_encoding(right)
        )
    )


def concat_distribution_layouts(
    frames: Sequence[pd.DataFrame], result: pd.DataFrame
) -> pd.DataFrame:
    """Retain only declarations identically bound in every row-stacked input.

    Missing or conflicting declarations drop the affected whole logical output.
    This policy does not authorize column-wise reconstruction or pandas merges.

    Args:
        frames: Every original row-stacked input in publication order.
        result: Row-stack output whose retained bindings must remain numeric.

    Returns:
        A new frame carrying only whole declarations shared by every input.

    Raises:
        TypeError: Any input reserved value has an unsupported current type.
        ValueError: Any input declaration or retained output binding is invalid.
    """
    retained: dict[str, DistributionLayout] = {}
    # Keep at most two admitted role graphs, rather than multiplying the metadata
    # budget by the number of frames. Still validate inputs after parity is lost.
    for index, frame in enumerate(frames):
        current = inspect_distribution_layouts(frame)
        if index == 0:
            retained = current
        else:
            retained = {
                name: layout
                for name, layout in retained.items()
                if name in current and _same_declaration(layout, current[name])
            }
    retained = {
        name: layout for name, layout in retained.items() if _bindings_valid(result, layout)
    }
    return with_distribution_layouts(result, retained)
