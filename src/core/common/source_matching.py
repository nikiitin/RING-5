"""Bounded matching of current concrete sources without changing observed evidence."""

from __future__ import annotations

import time
from collections.abc import Sequence

from src.core.common.safe_regex import SafeRegexError, normalize_stat_pattern, numeric_pattern_id
from src.core.common.security_limits import (
    MAX_REGEX_CANDIDATES,
    MAX_REGEX_EXPANSION_SECONDS,
    MAX_REGEX_MATCH_ATTEMPTS,
)
from src.core.models.data_models import ScannedVariableDict, SourceInstanceDict
from src.core.models.parsing_models import ScannedVariable, SourceInstance, StatConfig


def _validated_records(
    variables: Sequence[ScannedVariableDict], deadline: float | None
) -> tuple[list[ScannedVariable], list[str]]:
    """Validate the full catalog before selecting any of its original records."""
    records: list[ScannedVariable] = []
    names: list[str] = []
    seen: set[str] = set()
    for value in variables:
        variable = ScannedVariable.from_dict(value)
        records.append(variable)
        for instance in variable.instances:
            if deadline is not None and time.monotonic() > deadline:
                raise SafeRegexError("Source selection exceeded its execution deadline.")
            if instance.source_name in seen:
                raise ValueError(
                    f"Scanned source {instance.source_name!r} is declared more than once."
                )
            seen.add(instance.source_name)
            names.append(instance.source_name)
            if deadline is not None and len(names) > MAX_REGEX_CANDIDATES:
                raise ValueError("Source selection exceeds the concrete candidate limit.")
    return records, names


def _matching_ids(
    pattern: str, names: Sequence[str], deadline: float, attempts: int
) -> tuple[dict[str, str], int]:
    """Match numeric names through one bounded primitive and shared work budget."""
    canonical = normalize_stat_pattern(pattern)
    if r"\d+" not in canonical:
        raise ValueError("Instance selection requires a numeric source pattern.")
    matched: dict[str, str] = {}
    for name in names:
        attempts += 1
        if attempts > MAX_REGEX_MATCH_ATTEMPTS:
            raise SafeRegexError("Source selection exceeded the candidate match limit.")
        if time.monotonic() > deadline:
            raise SafeRegexError("Source selection exceeded its execution deadline.")
        numeric_id = numeric_pattern_id(canonical, name)
        if numeric_id is not None:
            matched[name] = numeric_id
    return matched, attempts


def matching_source_instances(
    pattern: str, variables: Sequence[ScannedVariableDict]
) -> list[SourceInstanceDict]:
    """Project concrete names into coordinates for the numeric selection display.

    Original source evidence is not reconstructed by this presentation view.

    Raises:
        TypeError: Scan metadata has invalid field types.
        ValueError: Metadata is malformed, duplicated or over its candidate limit.
        SafeRegexError: Matching exceeds its grammar, deadline or attempt bound.
    """
    deadline = time.monotonic() + MAX_REGEX_EXPANSION_SECONDS
    _records, names = _validated_records(variables, deadline)
    matched, _attempts = _matching_ids(pattern, names, deadline, 0)
    return [
        SourceInstance(name, tuple(numeric_id.split("_"))).to_dict()
        for name, numeric_id in matched.items()
    ]


def request_scanned_variables(
    configs: Sequence[StatConfig], variables: Sequence[ScannedVariableDict]
) -> list[ScannedVariableDict]:
    """Retain whole records relevant to the request after validating all discovery.

    Literal aliases select concrete identities. Numeric patterns retain every
    matching record, including currently unselected instances; the backend still
    owns selected_sources admission and execution. Evidence and coordinates stay
    exactly as observed rather than taking the display matcher's projection.

    Raises:
        TypeError: Any supplied record has invalid field types.
        ValueError: Discovery is malformed, duplicated or over its candidate limit.
        SafeRegexError: Numeric matching exceeds its grammar or work bounds.
    """
    has_patterns = any(config.is_regex for config in configs)
    deadline = time.monotonic() + MAX_REGEX_EXPANSION_SECONDS if has_patterns else None
    records, names = _validated_records(variables, deadline)
    required = {config.source_name or config.name for config in configs if not config.is_regex}
    patterns = dict.fromkeys(
        normalize_stat_pattern(config.source_name or config.name)
        for config in configs
        if config.is_regex
    )
    attempts = 0
    for pattern in patterns:
        assert deadline is not None
        matches, attempts = _matching_ids(pattern, names, deadline, attempts)
        required.update(matches)
    return [
        variable.to_dict()
        for variable in records
        if any(instance.source_name in required for instance in variable.instances)
    ]
