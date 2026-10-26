"""Resolve explicit statistic sources once before constructing per-file workers."""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import cast

from src.core.common.safe_regex import (
    MAX_INPUT_LENGTH,
    SafeRegexError,
    normalize_stat_pattern,
    numeric_pattern_id,
)
from src.core.common.security_limits import (
    MAX_PARSE_VARIABLES,
    MAX_INCREMENTAL_CACHE_COLUMNS,
    MAX_PARSE_MATRIX_CELLS,
    MAX_PARSE_RESULT_BYTES,
    MAX_REGEX_CANDIDATES,
    MAX_REGEX_EXPANSION_SECONDS,
    MAX_REGEX_MATCH_ATTEMPTS,
)
from src.core.common.stat_config_codec import StatConfigCodec
from src.core.common.source_entry_labels import canonical_source_entry
from src.core.common.parsed_output_codec import ParsedSchemaBudget
from src.core.common.distribution_layout_codec import (
    DISTRIBUTION_LAYOUT_PREFIX,
    encode_distribution_column,
    distribution_layout_suffix,
)
from src.core.models.distribution_geometry import DistributionGeometry, native_bucket_label
from src.core.models.native_distribution_layout import (
    DistributionColumn,
    DistributionLayout,
    NativeDistributionLayout,
    OpaqueDistributionLayout,
    ZeroPolicy,
    DistributionRole,
)
from src.core.models.parsed_output_models import ParsedColumn, ParsedKind
from src.core.models.parse_failure_models import ParseDataValueError
from src.core.models.parsing_models import ScannedVariable, SourceInstance, StatConfig
from src.core.models.source_evidence import SourceKindEvidence, SourceKindBinding

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceTarget:
    """One logical accumulator receiving a concrete source observation."""

    output_name: str
    entry_name: str | None = None


@dataclass(frozen=True)
class SourceRoute:
    """Independent destinations sharing one checked request source declaration."""

    targets: tuple[SourceTarget, ...]


@dataclass(frozen=True)
class AccumulatorSpec:
    """The original request and its resolved output lifecycle and entry schema."""

    config: StatConfig
    output_name: str
    output_type: str
    repeat: int
    entries: tuple[str, ...] | None
    layout: DistributionLayout | None = field(kw_only=True)

    def __post_init__(self) -> None:
        if not isinstance(self.config, StatConfig):
            raise TypeError("Accumulator specifications require a typed statistic request.")
        if not self.output_name or not self.output_type:
            raise ValueError("Accumulator specifications require exact output identity and kind.")
        if type(self.repeat) is not int or self.repeat < 1:
            raise ValueError("Accumulator repeat must be a positive integer.")
        if self.entries is not None and (
            not isinstance(self.entries, tuple)
            or any(not isinstance(entry, str) for entry in self.entries)
        ):
            raise TypeError("Accumulator entry schemas must be immutable text tuples.")


@dataclass(frozen=True)
class SourcePlan:
    """Owned accumulator specifications and immutable concrete-source routes."""

    accumulators: tuple[AccumulatorSpec, ...]
    routes: Mapping[str, SourceRoute]


@dataclass(frozen=True)
class _ScannedSource:
    evidence: SourceKindEvidence
    pattern_name: str
    instance: SourceInstance


def max_source_instances() -> int:
    """Return the configured per-output source cap; zero permits trusted unbounded use."""
    raw = os.environ.get("RING5_MAX_VAR_REPEAT")
    if raw is not None:
        try:
            value = int(raw)
            if value >= 0:
                return value
            logger.warning("RING5_MAX_VAR_REPEAT=%r is negative; using default", raw)
        except ValueError:
            logger.warning("RING5_MAX_VAR_REPEAT=%r is not an integer; using default", raw)
    return 1024


def literal_source_filter(source_name: str) -> str:
    """Escape an exact source identifier without admitting numeric placeholders."""
    if not source_name or len(source_name) > MAX_INPUT_LENGTH:
        raise ValueError("Concrete source name exceeds the matching input limit.")
    if "::" in source_name or any(
        not ((character.isascii() and character.isalnum()) or character in "._:")
        for character in source_name
    ):
        raise ValueError(
            f"Concrete source name is not an exact statistic identifier: {source_name!r}."
        )
    return re.escape(source_name)


def resolve_sources(
    variables: Sequence[StatConfig],
    scanned_variables: Sequence[ScannedVariable] | None,
    *,
    file_count: int,
    metadata_columns: tuple[ParsedColumn, ...],
) -> SourcePlan:
    """Compile current source selections into exact routes and accumulator specifications.

    Args:
        variables: Runnable configurations declaring each raw source kind.
        scanned_variables: Current explicit source records required for numeric patterns.
        file_count: Actual selected source count, including reusable cache records.
        metadata_columns: Strategy-owned physical metadata columns.

    Returns:
        A bounded plan with one independent accumulator per output.

    Raises:
        TypeError: A configuration or metadata record has an invalid type.
        ValueError: Source identity, selection, output schema, or a bound is invalid.
        RuntimeError: The selected source/accumulator workload exceeds a configured cap.
    """
    # [impl->req~ring5.ingestion.pattern-index-selection~1]
    if type(file_count) is not int or file_count < 1:
        raise ValueError("Source planning requires the actual positive selected file count.")
    if type(metadata_columns) is not tuple or any(
        type(column) is not ParsedColumn or column.owner is not None for column in metadata_columns
    ):
        raise TypeError("Source planning requires immutable strategy metadata declarations.")
    configs = StatConfigCodec.validate_many(variables)
    if not configs:
        raise ValueError("A parse request requires at least one runnable variable.")
    has_patterns = any(config.is_regex for config in configs)
    index: dict[str, _ScannedSource] = {}
    for variable in scanned_variables or ():
        if not isinstance(variable, ScannedVariable):
            raise TypeError("Parser source metadata must contain ScannedVariable values.")
        for instance in variable.instances:
            if instance.source_name in index:
                raise ValueError(
                    f"Scanned source {instance.source_name!r} is declared more than once."
                )
            if has_patterns and len(index) >= MAX_REGEX_CANDIDATES:
                raise ValueError(
                    f"Regex expansion exceeds the {MAX_REGEX_CANDIDATES}-candidate limit."
                )
            index[instance.source_name] = _ScannedSource(
                variable.source_evidence, variable.name, instance
            )

    deadline = time.monotonic() + MAX_REGEX_EXPANSION_SECONDS
    attempts = 0
    captures: dict[tuple[str, str], tuple[str, ...] | None] = {}
    verified: set[str] = set()

    def capture(pattern_name: str, concrete_name: str) -> tuple[str, ...] | None:
        nonlocal attempts
        canonical = normalize_stat_pattern(pattern_name)
        key = (canonical, concrete_name)
        if key not in captures:
            attempts += 1
            if attempts > MAX_REGEX_MATCH_ATTEMPTS:
                raise SafeRegexError("Regex expansion exceeded the candidate match limit.")
            if time.monotonic() > deadline:
                raise SafeRegexError("Regex expansion exceeded its execution deadline.")
            numeric_id = numeric_pattern_id(canonical, concrete_name)
            captures[key] = tuple(numeric_id.split("_")) if numeric_id is not None else None
        return captures[key]

    def verify_source(source_name: str) -> None:
        if source_name in verified:
            return
        literal_source_filter(source_name)
        record = index.get(source_name)
        if record is not None:
            if r"\d+" in record.pattern_name:
                if capture(record.pattern_name, source_name) != record.instance.indices:
                    raise ValueError(f"Scanned source coordinates do not identify {source_name!r}.")
            elif record.pattern_name != source_name or record.instance.indices:
                raise ValueError(f"Literal scanner metadata does not identify {source_name!r}.")
        verified.add(source_name)

    outputs: list[AccumulatorSpec] = []
    output_names: set[str] = set()
    targets: dict[str, list[SourceTarget]] = {}
    source_types: dict[str, str] = {}

    def append_output(spec: AccumulatorSpec) -> None:
        if spec.output_name in output_names:
            raise ValueError(f"Duplicate parser output name: {spec.output_name!r}.")
        output_names.add(spec.output_name)
        outputs.append(spec)

    for config in configs:
        source_name = config.source_name or config.name
        source_type = cast(str, config.params["source_type"])
        selected: list[tuple[str, tuple[str, ...]]] = []
        if config.is_regex:
            canonical = normalize_stat_pattern(source_name)
            if r"\d+" not in canonical:
                raise ValueError("Numeric pattern requests require a numeric placeholder.")
            if not index:
                raise ValueError("Numeric patterns require explicit current scan source records.")
            matching = {
                concrete: indices
                for concrete in index
                if (indices := capture(canonical, concrete)) is not None
            }
            requested = cast(list[str], config.params.get("selected_sources", list(matching)))
            for concrete in requested:
                if concrete not in matching:
                    raise ValueError(
                        f"Selected source {concrete!r} is not a scanned pattern instance."
                    )
                selected.append((concrete, matching[concrete]))
            if not selected:
                raise ValueError(f"Source pattern {source_name!r} has no scanned instances.")
        else:
            selected = [(source_name, ())]

        cap = max_source_instances()
        if cap and len(selected) > cap:
            raise RuntimeError(
                f"Parser output {config.name!r} expands to {len(selected)} instances, "
                f"exceeding the cap of {cap}."
            )
        for concrete, _indices in selected:
            verify_source(concrete)
            if concrete in index:
                SourceKindBinding(source_type, index[concrete].evidence)
            if concrete in source_types and source_types[concrete] != source_type:
                raise ValueError(f"Conflicting raw source kinds for {concrete!r}.")
            source_types[concrete] = source_type

        scalar_vector = config.type == "vector" and source_type == "scalar"
        if scalar_vector and not config.is_regex:
            raise ValueError("A scalar-to-vector representation requires numeric source instances.")
        if scalar_vector and (config.statistics_only or config.params.get("statistics")):
            raise ValueError(
                "Scalar pattern vectors expose instance entries, not source summaries."
            )
        if config.type == "vector":
            entries = cast(list[str], config.params.get("entries", []))
            statistics = cast(list[str], config.params.get("statistics", []))
            entry_schema: tuple[str, ...] | None = (
                tuple("_".join(indices) for _concrete, indices in selected)
                if scalar_vector
                else tuple(dict.fromkeys(([] if config.statistics_only else entries) + statistics))
            )
        elif (
            config.type == "histogram"
            and not config.statistics_only
            and config.params.get("entries")
        ):
            entry_schema = tuple(cast(list[str], config.params["entries"]))
        else:
            entry_schema = None
        if config.keep_indices:
            if not config.is_regex:
                raise ValueError("Keeping source indices requires a numeric pattern request.")
            for concrete, _indices in selected:
                spec = AccumulatorSpec(
                    config,
                    concrete,
                    "scalar" if scalar_vector else config.type,
                    config.repeat,
                    None if scalar_vector else entry_schema,
                    layout=None,
                )
                append_output(spec)
                targets.setdefault(concrete, []).append(SourceTarget(spec.output_name))
        else:
            expected_repeat = config.repeat if scalar_vector else config.repeat * len(selected)
            spec = AccumulatorSpec(
                config, config.name, config.type, expected_repeat, entry_schema, layout=None
            )
            append_output(spec)
            for concrete, indices in selected:
                entry_name = "_".join(indices) if scalar_vector else None
                targets.setdefault(concrete, []).append(SourceTarget(spec.output_name, entry_name))

        width = sum(len(items) for items in targets.values())
        if width > MAX_PARSE_VARIABLES:
            raise RuntimeError(
                f"Parser request has {len(outputs)} outputs and {width} source bindings; "
                f"the limit is {MAX_PARSE_VARIABLES}."
            )

    routes = {name: SourceRoute(tuple(destinations)) for name, destinations in targets.items()}
    if file_count * sum(len(route.targets) for route in routes.values()) > MAX_PARSE_MATRIX_CELLS:
        raise ParseDataValueError(
            "Parser request exceeds the selected file/source-binding workload limit."
        )
    planned = _admit_outputs(outputs, file_count, metadata_columns)
    return SourcePlan(planned, MappingProxyType(routes))


def _admit_outputs(
    outputs: Sequence[AccumulatorSpec],
    file_count: int,
    metadata_columns: tuple[ParsedColumn, ...],
) -> tuple[AccumulatorSpec, ...]:
    """Admit known physical width and schema bytes before constructing any worker."""
    geometries: dict[str, DistributionGeometry] = {}
    widths = len(metadata_columns)
    for spec in outputs:
        if spec.output_type == "distribution" and not spec.config.statistics_only:
            params = spec.config.params
            declared_geometry = DistributionGeometry(
                cast(float, params["minimum"]),
                cast(float, params["maximum"]),
                cast(float, params["bucket_size"]),
            )
            geometries[spec.output_name] = declared_geometry
            widths += (
                declared_geometry.bucket_count
                + 2
                + len(cast(list[str], params.get("statistics", [])))
            )
        elif spec.output_type in {"scalar", "configuration"}:
            widths += 1
        elif spec.entries is not None:
            if spec.output_type == "histogram":
                widths += len(
                    {
                        *(canonical_source_entry("histogram", entry) for entry in spec.entries),
                        *cast(list[str], spec.config.params.get("statistics", [])),
                    }
                )
            else:
                widths += len(spec.entries)
        else:
            summary_count = len(cast(list[str], spec.config.params.get("statistics", [])))
            bins = (
                cast(int, spec.config.params.get("bins", 0))
                if spec.output_type == "histogram" and not spec.config.statistics_only
                else 0
            )
            widths += max(bins, summary_count)
    if widths > MAX_INCREMENTAL_CACHE_COLUMNS:
        raise ParseDataValueError("Parser request exceeds the physical column limit.")
    if file_count * widths > MAX_PARSE_MATRIX_CELLS:
        raise ParseDataValueError("Parser request exceeds the selected file/physical column limit.")
    budget = ParsedSchemaBudget()
    physical_names: set[str] = set()
    layout_bytes = 0
    planned: list[AccumulatorSpec] = []

    def physical(name: str, owner: str | None, kind: str = "number") -> None:
        if name in physical_names:
            raise ParseDataValueError(f"Duplicate planned physical column: {name!r}.")
        if len(physical_names) + 1 > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ParseDataValueError("Parser request exceeds the physical column limit.")
        if file_count * (len(physical_names) + 1) > MAX_PARSE_MATRIX_CELLS:
            raise ParseDataValueError(
                "Parser request exceeds the selected file/physical column limit."
            )
        column = ParsedColumn(name, cast(ParsedKind, kind), owner)
        budget.column(column)
        physical_names.add(name)

    for spec in outputs:
        scalar = spec.output_type in {"scalar", "configuration"}
        kind = "text" if spec.output_type == "configuration" else "number"
        budget.variable(spec.output_name, cast(ParsedKind, kind), "scalar" if scalar else "entries")
        geometry = geometries.get(spec.output_name)
        opaque = (
            spec.output_type == "vector"
            and spec.config.params["source_type"] == "distribution"
            and bool(spec.entries)
        )
        if geometry is None and not opaque:
            budget.admit(b"null")
            if scalar:
                physical(spec.output_name, spec.output_name, kind)
            else:
                entries = spec.entries
                if spec.output_type == "histogram":
                    from src.parsing.gem5.types.histogram import Histogram

                    entries = Histogram.declared_entries(
                        entries or (),
                        tuple(cast(list[str], spec.config.params.get("statistics", []))),
                        cast(int, spec.config.params.get("bins", 0)),
                        cast(float, spec.config.params.get("max_range", 0.0)),
                        spec.config.statistics_only,
                    )
                elif entries is None:
                    entries = tuple(cast(list[str], spec.config.params.get("statistics", [])))
                for entry in entries:
                    physical(f"{spec.output_name}..{entry}", spec.output_name)
            planned.append(spec)
            continue
        budget.admit(DISTRIBUTION_LAYOUT_PREFIX)
        layout_bytes += len(DISTRIBUTION_LAYOUT_PREFIX)
        bindings: list[DistributionColumn] = []

        def binding(label: str, role: str, native_index: int | None) -> None:
            nonlocal layout_bytes
            column = DistributionColumn(
                f"{spec.output_name}..{label}", label, cast(DistributionRole, role), native_index
            )
            fragment = (b"," if bindings else b"") + encode_distribution_column(column)
            budget.admit(fragment)
            physical(column.column, spec.output_name)
            layout_bytes += len(fragment)
            if file_count * layout_bytes > MAX_PARSE_RESULT_BYTES:
                raise ParseDataValueError("Repeated per-file layouts exceed the result byte limit.")
            bindings.append(column)

        if geometry is not None:
            binding("underflows", "underflow", None)
            for index in range(geometry.bucket_count):
                binding(native_bucket_label(geometry, index), "bucket", index)
            binding("overflows", "overflow", None)
            for summary in cast(list[str], spec.config.params.get("statistics", [])):
                binding(summary, "summary", None)
            policy = cast(ZeroPolicy, spec.config.params["zero_policy"])
            suffix = distribution_layout_suffix(geometry, policy)

        else:
            assert spec.entries is not None
            for entry in spec.entries:
                binding(entry, "source", None)
            suffix = distribution_layout_suffix(None, None)

        budget.admit(suffix)
        layout_bytes += len(suffix)
        if file_count * layout_bytes > MAX_PARSE_RESULT_BYTES:
            raise ParseDataValueError("Repeated per-file layouts exceed the result byte limit.")
        layout: DistributionLayout = (
            NativeDistributionLayout(geometry, policy, tuple(bindings))
            if geometry is not None
            else OpaqueDistributionLayout(tuple(bindings))
        )
        planned.append(replace(spec, layout=layout))
    for column in metadata_columns:
        physical(column.name, None, column.kind)
    return tuple(planned)
