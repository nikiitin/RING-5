"""
Parser API Protocol - Unified facade interface for parsing subsystem.

Defines the contract for a complete parser API that combines both
parsing and scanning operations behind a single facade.
"""

from concurrent.futures import Future
from typing import Any, List, Optional, Protocol

from src.core.models import ParseBatchResult, ScannedVariable, StatConfig


class ParserAPI(Protocol):
    """
    Unified Protocol for the complete parsing subsystem API.

    Combines parser and scanner functionality into a single facade,
    providing the full workflow: scan → select → parse → CSV.

    Implementations:
        - Gem5ParserAPI: gem5 simulator implementation
    """

    def submit_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: List[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: Optional[List[Any]] = None,
    ) -> ParseBatchResult:
        """Submit async parsing job and return a ParseBatchResult."""
        ...

    def finalize_parsing(
        self,
        output_dir: str,
        results: List[Any],
        strategy_type: str = "simple",
        var_names: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Post-process and aggregate parsing results into CSV."""
        ...

    def submit_scan_async(
        self,
        stats_path: str,
        stats_pattern: str = "stats.txt",
        limit: int = 5,
    ) -> List[Future[List[ScannedVariable]]]:
        """Submit async scanning job and return futures."""
        ...

    def aggregate_scan_results(
        self,
        results: List[List[ScannedVariable]],
    ) -> List[ScannedVariable]:
        """Aggregate scan results into unified variable list."""
        ...
