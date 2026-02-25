"""
Gem5 Parser API - Unified facade for gem5 parsing and scanning.

Implements the ParserAPI protocol, wrapping Gem5Parser and Gem5Scanner
into a single cohesive API for the gem5 simulator backend.
"""

from concurrent.futures import Future
from typing import Any

from src.core.models import ParseBatchResult, ScannedVariable, StatConfig
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.impl.gem5_scanner import Gem5Scanner
from src.parsing.parser_protocol import SimulationParser


class Gem5ParserAPI(SimulationParser):
    """
    Unified facade for gem5 parsing and scanning operations.

    Combines Gem5Parser (parsing) and Gem5Scanner (scanning) behind a
    single API, implementing the SimulationParser protocol.

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
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | None = None,
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
        results: list[dict[str, Any]],
        strategy_type: str = "simple",
        var_names: list[str] | None = None,
    ) -> str | None:
        """Post-process and aggregate results into CSV via Gem5Parser."""
        return Gem5Parser.finalize_parsing(output_dir, results, strategy_type, var_names=var_names)

    def submit_scan_async(
        self,
        stats_path: str,
        stats_pattern: str = "stats.txt",
        limit: int = 5,
    ) -> list[Future[list[ScannedVariable]]]:
        """Submit async scanning job via Gem5Scanner."""
        return Gem5Scanner.submit_scan_async(stats_path, stats_pattern, limit)

    def aggregate_scan_results(
        self,
        results: list[list[ScannedVariable]],
    ) -> list[ScannedVariable]:
        """Aggregate scan results via Gem5Scanner."""
        return Gem5Scanner.aggregate_scan_results(results)
