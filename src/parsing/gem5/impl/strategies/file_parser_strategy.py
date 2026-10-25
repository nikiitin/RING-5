"""Per-file asynchronous work contracts for gem5 parsing strategies."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from src.core.models.parsed_output_models import ParsedFileResult

if TYPE_CHECKING:
    from src.parsing.gem5.impl.source_bindings import SourcePlan


class ParseWorkItem(Protocol):
    """One source-owned callable returning only finalized immutable values."""

    @property
    def source_path(self) -> str:
        """Return the exact planned source file for this work item."""
        raise NotImplementedError

    def __call__(self) -> ParsedFileResult:
        """Return finalized variables and metadata, or raise a visible failure."""
        raise NotImplementedError


class FileParserStrategy(Protocol):
    """Discover and compose source-owned work without a second finalization path."""

    def get_work_items(
        self,
        stats_path: str,
        stats_pattern: str,
        plan: SourcePlan,
        *,
        file_paths: list[str] | None = None,
    ) -> Sequence[ParseWorkItem]:
        """Return independent typed work for every selected statistics source."""
        raise NotImplementedError
