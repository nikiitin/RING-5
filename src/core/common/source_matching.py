"""Bounded presentation of current concrete sources for numeric pattern selection."""

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
from src.core.models.parsing_models import ScannedVariable, SourceInstance


def matching_source_instances(
    pattern: str, variables: Sequence[ScannedVariableDict]
) -> list[SourceInstanceDict]:
    """Project current concrete names into a numeric pattern's display coordinates.

    Source kinds and selections remain explicit caller choices. Matching uses the
    same bounded numeric primitive as parse submission and never reconstructs names.

    Args:
        pattern: Current numeric source pattern, with literal hierarchy separators.
        variables: Complete current scan metadata, including literal source records.

    Returns:
        Matching concrete identities with coordinates relative to the requested pattern.

    Raises:
        TypeError: Scan metadata uses an invalid field type.
        ValueError: Metadata is malformed, duplicated, or exceeds the candidate limit.
        SafeRegexError: The pattern is invalid or matching exceeds an execution bound.
    """
    canonical = normalize_stat_pattern(pattern)
    if r"\d+" not in canonical:
        raise ValueError("Instance selection requires a numeric source pattern.")
    deadline = time.monotonic() + MAX_REGEX_EXPANSION_SECONDS
    names: list[str] = []
    seen: set[str] = set()
    for value in variables:
        variable = ScannedVariable.from_dict(value)
        for instance in variable.instances:
            if time.monotonic() > deadline:
                raise SafeRegexError("Source selection exceeded its execution deadline.")
            if instance.source_name in seen:
                raise ValueError(
                    f"Scanned source {instance.source_name!r} is declared more than once."
                )
            seen.add(instance.source_name)
            names.append(instance.source_name)
            if len(names) > MAX_REGEX_CANDIDATES:
                raise ValueError("Source selection exceeds the concrete candidate limit.")
    matched: list[SourceInstanceDict] = []
    for attempt, name in enumerate(names, start=1):
        if attempt > MAX_REGEX_MATCH_ATTEMPTS:
            raise SafeRegexError("Source selection exceeded the candidate match limit.")
        if time.monotonic() > deadline:
            raise SafeRegexError("Source selection exceeded its execution deadline.")
        numeric_id = numeric_pattern_id(canonical, name)
        if numeric_id is not None:
            matched.append(SourceInstance(name, tuple(numeric_id.split("_"))).to_dict())
    return matched
