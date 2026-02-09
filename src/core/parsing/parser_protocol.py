"""
Parser Protocol - Simulator-agnostic parsing interface.

Defines the contract for all parser implementations. Any simulator backend
(gem5, SST, etc.) must implement this Protocol to integrate with RING-5.
"""

from typing import Any, List, Optional, Protocol

from src.core.models import ParseBatchResult, StatConfig


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
    ) -> ParseBatchResult:
        """
        Submit async parsing job and return a ParseBatchResult.

        Args:
            stats_path: Root directory containing simulation outputs
            stats_pattern: Glob pattern for file matching (e.g., "stats.txt")
            variables: List of StatConfig objects defining what to extract
            output_dir: Directory for output files
            strategy_type: Parsing strategy identifier (default: "simple")
            scanned_vars: Optional pre-scanned variable metadata for expansion

        Returns:
            ParseBatchResult containing futures and var_names for the batch
        """
        ...

    @staticmethod
    def finalize_parsing(
        output_dir: str,
        results: List[Any],
        strategy_type: str = "simple",
        var_names: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Post-process and aggregate parsing results into final CSV.

        Args:
            output_dir: Directory to write output CSV
            results: Resolved parse results from submit_parse_async futures
            strategy_type: Strategy used for post-processing
            var_names: Ordered variable names from ParseBatchResult

        Returns:
            Path to the generated CSV file, or None if no results
        """
        ...

    @staticmethod
    def construct_final_csv(
        output_dir: str,
        results: List[Any],
        var_names: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Build the final CSV from aggregated results.

        Args:
            output_dir: Directory to write output CSV
            results: Post-processed results ready for CSV generation
            var_names: Ordered variable names for column consistency

        Returns:
            Path to the generated CSV file, or None if no results
        """
        ...
