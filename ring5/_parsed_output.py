"""Public typed parser result resolution and publication composition."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsed_output_models import ParsedFileResult, ParsedOutput, ResolvedParsedRows

from ring5.errors import ParseError


def resolve_parsed_output(
    results: Sequence[ParsedFileResult],
    variable_order: Sequence[str],
    source_paths: Sequence[str],
    *,
    complete: bool = True,
) -> ResolvedParsedRows:
    """Resolve finalized file values against an explicit ordered source plan.

    Args:
        results: Owned typed file results from successful workers.
        variable_order: Logical variables in their declared output order.
        source_paths: Exact unique planned source IDs.
        complete: Require every planned source; False permits usable partial rows.

    Returns:
        Immutable schema, resolved rows and aligned source provenance.

    Raises:
        ParseError: Results, ownership, coverage or resource limits are invalid.
    """
    # [impl->req~ring5.extension.parser-protocol~1]
    try:
        return ParsedOutputIO.resolve(results, variable_order, source_paths, complete=complete)
    except (TypeError, ValueError) as exc:
        raise ParseError(f"Could not resolve parser output: {exc}") from exc


def publish_parsed_output(value: ResolvedParsedRows, path: str | Path) -> ParsedOutput:
    """Atomically publish one resolved typed value through the canonical CSV owner.

    Args:
        value: Immutable resolved rows returned by resolve_parsed_output.
        path: Destination CSV path.

    Returns:
        Path, exact schema and schema-bound typed-content SHA-256 descriptor.

    Raises:
        ParseError: Publication, encoding or resource validation fails. Existing
            output is retained when publication fails.
    """
    # [impl->req~ring5.extension.parser-protocol~1]
    try:
        return ParsedOutputIO.publish(Path(path), value)
    except (OSError, TypeError, ValueError) as exc:
        raise ParseError(f"Could not publish parser output: {exc}") from exc
