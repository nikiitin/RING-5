"""
Gem5 Parser API - Unified facade for gem5 parsing and scanning.

Implements the ParserAPI protocol, wrapping Gem5Parser and Gem5Scanner
into a single cohesive API for the gem5 simulator backend.
"""

from concurrent.futures import Future
from typing import Any, List, Optional

from src.core.models import ParseBatchResult, ScannedVariable, StatConfig
from src.core.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.core.parsing.gem5.impl.gem5_scanner import Gem5Scanner


class Gem5ParserAPI:
    """
    Unified facade for gem5 parsing and scanning operations.

    Combines Gem5Parser (parsing) and Gem5Scanner (scanning) behind a
    single API, implementing the ParserAPI protocol.

    Usage:
        >>> api = Gem5ParserAPI()
        >>> futures = api.submit_scan_async("/path/to/stats")
        >>> results = [f.result() for f in futures]
        >>> variables = api.aggregate_scan_results(results)
    """

    def submit_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: List[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: Optional[List[ScannedVariable]] = None,
    ) -> ParseBatchResult:
        """Submit async parsing job via Gem5Parser."""
        return Gem5Parser.submit_parse_async(
            stats_path,
            stats_pattern,
            variables,
            output_dir,
            strategy_type,
            scanned_vars,
        )

    def finalize_parsing(
        self,
        output_dir: str,
        results: List[Any],
        strategy_type: str = "simple",
        var_names: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Post-process and aggregate results into CSV via Gem5Parser."""
        return Gem5Parser.finalize_parsing(output_dir, results, strategy_type, var_names=var_names)

    def submit_scan_async(
        self,
        stats_path: str,
        stats_pattern: str = "stats.txt",
        limit: int = 5,
    ) -> List[Future[List[ScannedVariable]]]:
        """Submit async scanning job via Gem5Scanner."""
        return Gem5Scanner.submit_scan_async(stats_path, stats_pattern, limit)

    def aggregate_scan_results(
        self,
        results: List[List[ScannedVariable]],
    ) -> List[ScannedVariable]:
        """Aggregate scan results via Gem5Scanner."""
        return Gem5Scanner.aggregate_scan_results(results)
