"""
Parser Protocol - Simulator-agnostic parsing interface.

Defines the contract for all parser implementations. Any simulator backend
(gem5, SST, etc.) must implement this Protocol to integrate with RING-5.
"""

from concurrent.futures import Future
from typing import Any, List, Optional, Protocol

from src.core.models import StatConfig


class ParserProtocol(Protocol):
    """
    Protocol defining the contract for parsing simulator output files.

    A parser implementation handles:
    - Submitting async parse jobs for parallel file processing
    - Finalizing (post-processing and aggregating) parse results into CSV

    Implementations:
        - Gem5Parser: gem5 simulator stats parsing
    """

    @staticmethod
    def submit_parse_async(
        stats_path: str,
        stats_pattern: str,
        variables: List[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: Optional[List[Any]] = None,
    ) -> List[Future[Any]]:
        """
        Submit async parsing job and return futures.

        Args:
            stats_path: Root directory containing simulation outputs
            stats_pattern: Glob pattern for file matching (e.g., "stats.txt")
            variables: List of StatConfig objects defining what to extract
            output_dir: Directory for output files
            strategy_type: Parsing strategy identifier (default: "simple")
            scanned_vars: Optional pre-scanned variable metadata for expansion

        Returns:
            List of Future objects that will resolve to parse results
        """
        ...

    @staticmethod
    def finalize_parsing(
        output_dir: str,
        results: List[Any],
        strategy_type: str = "simple",
    ) -> Optional[str]:
        """
        Post-process and aggregate parsing results into final CSV.

        Args:
            output_dir: Directory to write output CSV
            results: Resolved parse results from submit_parse_async futures
            strategy_type: Strategy used for post-processing

        Returns:
            Path to the generated CSV file, or None if no results
        """
        ...

    @staticmethod
    def construct_final_csv(
        output_dir: str,
        results: List[Any],
    ) -> Optional[str]:
        """
        Build the final CSV from aggregated results.

        Args:
            output_dir: Directory to write output CSV
            results: Post-processed results ready for CSV generation

        Returns:
            Path to the generated CSV file, or None if no results
        """
        ...
