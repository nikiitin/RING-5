"""Resolve explicit statistic sources once before constructing per-file workers."""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
    MAX_REGEX_CANDIDATES,
    MAX_REGEX_EXPANSION_SECONDS,
    MAX_REGEX_MATCH_ATTEMPTS,
)
from src.core.common.stat_config_codec import StatConfigCodec
from src.core.models.parsing_models import ScannedVariable, SourceInstance, StatConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceTarget:
    """One logical accumulator receiving a concrete source observation."""

    output_name: str
    entry_name: str | None = None


@dataclass(frozen=True)
class SourceRoute:
    """The explicit raw source kind and its independent logical destinations."""

    source_type: str
    targets: tuple[SourceTarget, ...]


@dataclass(frozen=True)
class AccumulatorSpec:
    """The original request and its resolved output lifecycle and entry schema."""

    config: StatConfig
    output_name: str
    output_type: str
    repeat: int
    entries: tuple[str, ...] | None

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

    @property
    def workload_width(self) -> int:
        """Count accumulators and source bindings for the bounded file workload."""
        return sum(len(route.targets) for route in self.routes.values())


@dataclass(frozen=True)
class _ScannedSource:
    source_type: str
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
    variables: Sequence[StatConfig], scanned_variables: Sequence[ScannedVariable] | None
) -> SourcePlan:
    """Compile current source selections into exact routes and accumulator specifications.

    Args:
        variables: Runnable configurations declaring each raw source kind.
        scanned_variables: Current explicit source records required for numeric patterns.

    Returns:
        A bounded plan with one independent accumulator per output.

    Raises:
        TypeError: A configuration or metadata record has an invalid type.
        ValueError: Source identity, selection, output schema, or a bound is invalid.
        RuntimeError: The selected source/accumulator workload exceeds a configured cap.
    """
    # [impl->req~ring5.ingestion.pattern-index-selection~1]
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
                variable.source_type, variable.name, instance
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
            if concrete in index and index[concrete].source_type != source_type:
                raise ValueError(f"Raw source kind for {concrete!r} does not match source_type.")
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
        elif config.type == "histogram" and config.params.get("entries"):
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
                )
                append_output(spec)
                targets.setdefault(concrete, []).append(SourceTarget(spec.output_name))
        else:
            expected_repeat = config.repeat if scalar_vector else config.repeat * len(selected)
            spec = AccumulatorSpec(config, config.name, config.type, expected_repeat, entry_schema)
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

    routes = {
        name: SourceRoute(source_types[name], tuple(destinations))
        for name, destinations in targets.items()
    }
    return SourcePlan(tuple(outputs), MappingProxyType(routes))
