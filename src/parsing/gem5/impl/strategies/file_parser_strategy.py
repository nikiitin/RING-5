"""Per-file asynchronous work contracts for gem5 parsing strategies."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from src.parsing.parser_protocol import ParseWorkItem
from src.core.models.parsed_output_models import ParsedColumn

if TYPE_CHECKING:
    from src.parsing.gem5.impl.source_bindings import SourcePlan


class FileParserStrategy(Protocol):
    """Discover and compose source-owned work without a second finalization path."""

    metadata_columns: tuple[ParsedColumn, ...]

    def get_work_items(
        self,
        files: tuple[str, ...],
        plan: SourcePlan,
    ) -> Sequence[ParseWorkItem]:
        """Return independent typed work for every selected statistics source."""
        raise NotImplementedError
