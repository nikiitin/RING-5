from concurrent.futures import Future
from typing import Protocol, runtime_checkable

from src.core.models.parsed_output_models import ParsedFileResult, ParsedOutput
from src.core.models.parsing_models import (
    IncrementalParseBatchResult,
    IncrementalParseResult,
    ParserPlaygroundBatchResult,
    ParserPlaygroundResult,
    ParseBatchResult,
    ScanFileResult,
    ScannedVariable,
    ScanResult,
    StatConfig,
)


class ParseWorkItem(Protocol):
    """One source-owned callable returning only finalized immutable values."""

    @property
    def source_path(self) -> str:
        """Return the exact planned source file for this work item."""
        raise NotImplementedError

    def __call__(self) -> ParsedFileResult:
        """Return finalized variables and metadata, or raise a visible failure."""
        raise NotImplementedError


@runtime_checkable
class SimulationParser(Protocol):
    """
    Unified architectural protocol for simulation data parsing and variable scanning.

    Any class implementing this protocol can be injected into the Streamlit frontend
    or core Facade, decoupling the application from 'gem5' specifics.
    """

    # [impl->req~ring5.extension.parser-protocol~1]

    def submit_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | None = None,
        *,
        file_paths: list[str] | None = None,
    ) -> ParseBatchResult:
        """
        Submit an asynchronous parsing job over the simulation output files.
        """
        raise NotImplementedError

    def submit_incremental_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | None = None,
        cache_path: str | None = None,
    ) -> IncrementalParseBatchResult:
        """Submit only new or changed files while retaining an explicit reuse plan."""
        raise NotImplementedError

    def finalize_parsing(
        self,
        batch: ParseBatchResult,
        results: list[ParsedFileResult],
        *,
        complete: bool = True,
    ) -> ParsedOutput:
        """Resolve required batch context and publish exact typed rows.

        Complete output covers every planned source. Partial output still rejects
        duplicate or unplanned provenance and requires at least one usable row.
        """
        raise NotImplementedError

    def finalize_incremental_parsing(
        self,
        batch: IncrementalParseBatchResult,
        results: list[ParsedFileResult],
        *,
        complete: bool = True,
    ) -> IncrementalParseResult:
        """Publish accepted changed and reused rows, promoting the cache only when complete.

        Args:
            batch: Submitted input and cache-reuse plan.
            results: Successful changed-file results with source provenance.
            complete: Require every planned row and update the success cache.
                False permits partial output without replacing the cache.

        Returns:
            Published CSV and accepted counts against the planned total file count.
        """
        raise NotImplementedError

    def submit_parser_playground_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | None = None,
    ) -> ParserPlaygroundBatchResult:
        # [impl->req~ring5.ingestion.parser-playground~1]
        """Submit a bounded real-parser sample for configuration review."""
        raise NotImplementedError

    def finalize_parser_playground(
        self,
        batch: ParserPlaygroundBatchResult,
        results: list[ParsedFileResult],
    ) -> ParserPlaygroundResult:
        # [impl->req~ring5.ingestion.parser-playground~1]
        """Turn bounded parser results into a non-mutating human preview."""
        raise NotImplementedError

    def submit_scan_async(
        self,
        stats_path: str,
        stats_pattern: str = "stats.txt",
        limit: int = 5,
    ) -> list[Future[ScanFileResult]]:
        """
        Submit an async scanning job to discover potential variables across files.

        Each future resolves to a ``ScanFileResult`` (variables on success,
        error on failure).
        """
        raise NotImplementedError

    def aggregate_scan_results(
        self,
        results: list[ScanFileResult],
    ) -> ScanResult:
        """
        Aggregate per-file scan results into a ``ScanResult`` (merged,
        deduplicated variables plus any per-file failures).
        """
        raise NotImplementedError
