"""Explicit current typed values for parser-boundary tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from src.core.common.parsed_output import ParsedOutputIO
from src.core.common.source_context_codec import SourceContextCodec
from src.core.models.parsed_output_models import (
    ParsedCell,
    ParsedFileResult,
    ParsedOutput,
    ParsedVariableResult,
)
from src.core.models.parsing_models import StatConfig
from src.core.models.source_context_models import ParserSourceContext


def numeric_file(source: str, values: Mapping[str, float]) -> ParsedFileResult:
    """Declare finalized numeric scalar variables with exact provenance."""
    return ParsedFileResult(
        source,
        tuple(
            ParsedVariableResult(name, "number", "scalar", (ParsedCell(name, "number", value),))
            for name, value in values.items()
        ),
    )


def numeric_output(path: Path, values: Mapping[str, float]) -> ParsedOutput:
    """Publish a real current descriptor rather than faking a result pathname."""
    result = numeric_file("source", values)
    return ParsedOutputIO.publish(path, ParsedOutputIO.resolve([result], list(values), ("source",)))


def parser_context(
    names: Sequence[str] = ("x",), *, stats_path: str = "runs"
) -> ParserSourceContext:
    """Own the complete current request associated with a numeric test batch."""
    return SourceContextCodec.parser(
        stats_path=stats_path,
        stats_pattern="stats.txt",
        strategy_type="simple",
        variables=[StatConfig(name, "scalar", params={"source_type": "scalar"}) for name in names],
        scanned_variables=[],
        simulator="gem5",
        scan_limit=None,
        strict=True,
    )
